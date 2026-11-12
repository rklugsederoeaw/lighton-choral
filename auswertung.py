"""Liest Systeme mit einem Checkpoint und misst Noten und Text getrennt, je Quelle und gesamt.

    python auswertung.py --model runs/s4/checkpoint-3923 --split validation --bild streifen

Keine Wiederholungsstrafe beim Lesen: Tonwiederholungen sind im Choral regulär.
"""

import argparse
import json
import os
import time
from pathlib import Path

import torch
from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor

from metriken import messe, schleife
from train import HIER, eingabe, lade, ziel

# AMNLT-Einsiedeln und -Salzinnes haben vor jeder Silbe ein Leerzeichen, außer mit
# SYSTEME=daten/systeme_wg.jsonl (nachgetragene Wortgrenzen)
OHNE_WORTGRENZEN = (
    set()
    if "systeme_wg" in os.environ.get("SYSTEME", "")
    else {"Einsiedeln", "Salzinnes"}
)


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--split", default="validation")
    ap.add_argument("--bild", required=True, choices=("ganz", "stauchen", "streifen"))
    ap.add_argument("--kompakt", action="store_true")
    ap.add_argument("--n", type=int, default=0, help="nur die ersten n je Quelle")
    ap.add_argument(
        "--liste", help="eigene jsonl mit bild, ziel, quelle statt des AMNLT-Splits"
    )
    ap.add_argument("--max-tokens", type=int, default=600)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--out", help="Standard: <model>/lesung_<split>.jsonl")
    args = ap.parse_args()

    device = torch.device(
        ("cuda" if torch.cuda.is_available() else "cpu")
        if args.device == "auto"
        else args.device
    )
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    model = LightOnOcrForConditionalGeneration.from_pretrained(
        args.model, dtype=dtype
    ).to(device)
    model.eval()
    proc = LightOnOcrProcessor.from_pretrained(args.model)
    eos = proc.tokenizer.eos_token_id

    zeilen = (
        [
            json.loads(z)
            for z in (HIER / args.liste).read_text(encoding="utf-8").splitlines()
            if json.loads(z).get("split", args.split) == args.split
        ]
        if args.liste
        else lade([args.split])
    )
    if args.n:
        zaehler = {}
        behalten = []
        for z in zeilen:
            zaehler[z["quelle"]] = zaehler.get(z["quelle"], 0) + 1
            if zaehler[z["quelle"]] <= args.n:
                behalten.append(z)
        zeilen = behalten

    name = (
        f"lesung_{Path(args.liste).parent.name + '_' if args.liste else ''}{args.split}"
    )
    pfad = Path(args.out or Path(args.model) / f"{name}.jsonl")
    pfad.parent.mkdir(parents=True, exist_ok=True)
    lesungen = []
    t0 = time.time()
    with open(pfad, "w", encoding="utf-8") as f:
        for i, z in enumerate(zeilen, 1):
            x = eingabe(proc, z, args.bild, device)
            if device.type == "cuda":
                x["pixel_values"] = x["pixel_values"].to(dtype)
            with torch.inference_mode():
                aus = model.generate(
                    **x, max_new_tokens=args.max_tokens, do_sample=False
                )[0, x["input_ids"].shape[1] :]
            hyp = proc.tokenizer.decode(aus, skip_special_tokens=True)
            rec = {
                "id": z["id"],
                "quelle": z["quelle"],
                "ref": ziel(z, args.kompakt),
                "hyp": hyp,
                "abgebrochen": eos not in aus.tolist(),
                "schleife": schleife(hyp),
                "klammerfehler": hyp.count("(") != hyp.count(")"),
            }
            lesungen.append(rec)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if i % 50 == 0 or i == len(zeilen):
                print(
                    f"{i}/{len(zeilen)} {(time.time() - t0) / i:.2f} s/System",
                    flush=True,
                )

    def bericht(rs):
        m = messe(
            [(r["ref"], r["hyp"], r["quelle"] not in OHNE_WORTGRENZEN) for r in rs]
        )
        m["systeme"] = len(rs)
        for k in ("abgebrochen", "schleife", "klammerfehler"):
            m[k] = sum(r[k] for r in rs)
        return m

    ergebnis = {"gesamt": bericht(lesungen)}
    for q in sorted({r["quelle"] for r in lesungen}):
        ergebnis[q] = bericht([r for r in lesungen if r["quelle"] == q])
    pfad.with_suffix(".metriken.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(ergebnis, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
