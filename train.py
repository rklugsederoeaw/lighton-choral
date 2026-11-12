"""Feintuning von LightOnOCR-3-1B auf AMNLT: Bildencoder, Projektor und Decoder gemeinsam.

Angepasst aus OKAR_Pixtral-ViT/train.py (AdamW ohne Weight Decay, Warm-up, Kosinus auf 0,
Gradient Clip 0,5, bf16-Autocast auf der GPU, fp32-Gewichte). Checkpoints auf validation mit
auswertung.py nach Noten-Fehlerrate wählen, nicht nach Val-Loss.

    python train.py --bild streifen --epochs 4 --out runs/s4
"""

import argparse
import json
import math
import os
import random
import time
from pathlib import Path

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import torch  # noqa: E402
from PIL import Image  # noqa: E402
from transformers import (  # noqa: E402
    LightOnOcrForConditionalGeneration,
    LightOnOcrProcessor,
)

from bildform import bildform  # noqa: E402

HIER = Path(__file__).resolve().parent
MODELL = HIER / "models" / "LightOnOCR-3-1B-konvertiert"  # siehe konvertieren.py


def lade(splits, quellen=None):
    # SYSTEME=daten/systeme_wg.jsonl: AMNLT mit nachgetragenen Wortgrenzen (wortgrenzen_amnlt.py)
    datei = HIER / os.environ.get("SYSTEME", "daten/systeme.jsonl")
    zeilen = [json.loads(z) for z in datei.read_text(encoding="utf-8").splitlines()]
    return [
        z
        for z in zeilen
        if z["split"] in splits and (not quellen or z["quelle"] in quellen)
    ]


def ziel(z, kompakt):
    s = z["ziel"].strip()
    return s.replace("<m>", "") if kompakt else s


def eingabe(proc, z, form, device, mit_ziel=None):
    """Bild-Prompt; mit mit_ziel zusätzlich Zieltext samt Endezeichen als labels."""
    bild = bildform(Image.open(HIER / z["bild"]).convert("RGB"), form)
    x = proc.apply_chat_template(
        [{"role": "user", "content": [{"type": "image", "image": bild}]}],
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    if mit_ziel is not None:
        tok = proc.tokenizer
        t = tok(
            mit_ziel + tok.eos_token, add_special_tokens=False, return_tensors="pt"
        ).input_ids
        n = x["input_ids"].shape[1]
        x["input_ids"] = torch.cat([x["input_ids"], t], 1)
        x["attention_mask"] = torch.ones_like(x["input_ids"])
        x["labels"] = x["input_ids"].clone()
        x["labels"][:, :n] = -100
    return x.to(device)


def verlust(model, proc, z, args, device):
    x = eingabe(proc, z, args.bild, device, ziel(z, args.kompakt))
    if device.type == "cuda":
        with torch.autocast("cuda", dtype=torch.bfloat16):
            return model(**x).loss
    return model(**x).loss


def val_verlust(model, proc, val, args, device):
    model.eval()
    with torch.inference_mode():
        v = sum(verlust(model, proc, z, args, device).item() for z in val) / len(val)
    model.train()
    return v


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--init", default=str(MODELL))
    ap.add_argument("--out", default=str(HIER / "runs" / "train"))
    ap.add_argument(
        "--bild", choices=("ganz", "stauchen", "streifen"), default="streifen"
    )
    ap.add_argument("--kompakt", action="store_true", help="Ziel ohne <m>")
    ap.add_argument("--quellen", nargs="*", help="Standard: alle drei")
    ap.add_argument(
        "--zusatz",
        nargs="*",
        default=[],
        help="weitere jsonl-Listen, nur fürs Training",
    )
    ap.add_argument("--epochs", type=float, default=4)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--lm-lr", type=float, default=5e-5)
    ap.add_argument(
        "--accum", type=int, default=8, help="Systeme je Optimierungsschritt"
    )
    ap.add_argument("--warmup", type=int, default=50, help="Schritte")
    ap.add_argument("--ckpt-per-epoch", type=int, default=1)
    ap.add_argument("--val-n", type=int, default=100)
    ap.add_argument(
        "--max-n", type=int, default=0, help="Abbruch nach n Systemen (Rauchtest)"
    )
    ap.add_argument("--device", default="auto")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    device = torch.device(
        ("cuda" if torch.cuda.is_available() else "cpu")
        if args.device == "auto"
        else args.device
    )
    rng = random.Random(args.seed)
    train = lade(["train"], args.quellen)
    for f in args.zusatz:
        train += [
            json.loads(z) for z in (HIER / f).read_text(encoding="utf-8").splitlines()
        ]
    val = lade(["validation"], args.quellen)
    val = rng.sample(val, min(args.val_n, len(val)))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    model = LightOnOcrForConditionalGeneration.from_pretrained(
        args.init, dtype=torch.float32
    ).to(device)
    proc = LightOnOcrProcessor.from_pretrained(args.init)
    model.requires_grad_(False)
    model.model.vision_encoder.requires_grad_(True)
    model.model.vision_projection.requires_grad_(True)
    model.model.language_model.requires_grad_(True)
    model.gradient_checkpointing_enable()
    bild_p = [
        p
        for m in (model.model.vision_encoder, model.model.vision_projection)
        for p in m.parameters()
    ]
    gesehen = {id(p) for p in bild_p}
    lm_p = [p for p in model.parameters() if p.requires_grad and id(p) not in gesehen]
    gruppen = [{"params": bild_p, "lr": args.lr}, {"params": lm_p, "lr": args.lm_lr}]
    params = bild_p + lm_p
    print(
        f"{len(train)} Systeme, Bild {sum(p.numel() for p in bild_p) / 1e6:.1f} M, "
        f"Decoder {sum(p.numel() for p in lm_p) / 1e6:.1f} M Parameter",
        flush=True,
    )

    gesamt = int(args.epochs * len(train))
    if args.max_n:
        gesamt = min(gesamt, args.max_n)
    schritte = math.ceil(gesamt / args.accum)
    opt = torch.optim.AdamW(gruppen, weight_decay=0.0)

    def lr_bei(s):
        if s < args.warmup:
            return (s + 1) / args.warmup
        return 0.5 * (
            1 + math.cos(math.pi * (s - args.warmup) / max(1, schritte - args.warmup))
        )

    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_bei)
    ckpt_alle = math.ceil(len(train) / args.ckpt_per_epoch)
    log = open(out / "log.jsonl", "a", encoding="utf-8")

    def schreibe(rec):
        print(rec, flush=True)
        log.write(json.dumps(rec) + "\n")
        log.flush()

    # ponytail: ein System je Vorwärtslauf, Gradienten akkumuliert wie in OKAR; echte Batches
    # brauchen Padding, erst wenn die GPU deutlich unausgelastet ist.
    model.train()
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
    reihe, lauf, t0 = [], 0.0, time.time()
    for n in range(1, gesamt + 1):
        if not reihe:
            reihe = rng.sample(train, len(train))
        l = verlust(model, proc, reihe.pop(), args, device)  # noqa: E741
        (l / args.accum).backward()
        lauf += l.item()
        if n % args.accum == 0 or n == gesamt:
            torch.nn.utils.clip_grad_norm_(params, 0.5)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            schritt = math.ceil(n / args.accum)
            if schritt % 10 == 0 or n == gesamt:
                schreibe(
                    {
                        "schritt": schritt,
                        "n": n,
                        "epoche": round(n / len(train), 3),
                        "loss": round(lauf / (n % args.accum or args.accum), 4),
                        "lr": sched.get_last_lr()[0],
                        "s_je_system": round((time.time() - t0) / n, 3),
                        "spitze_gb": round(torch.cuda.max_memory_allocated() / 2**30, 1)
                        if device.type == "cuda"
                        else None,
                    }
                )
            lauf = 0.0
        if n % ckpt_alle == 0 or n == gesamt:
            rec = {
                "n": n,
                "epoche": round(n / len(train), 3),
                "val_loss": round(val_verlust(model, proc, val, args, device), 4),
            }
            if not args.no_save:
                d = out / f"checkpoint-{n}"
                model.save_pretrained(d)
                proc.save_pretrained(d)
                rec["checkpoint"] = str(d)
            schreibe(rec)
    print(f"fertig: {gesamt} Systeme in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
