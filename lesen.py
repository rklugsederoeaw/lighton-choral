"""Liest neue Systemausschnitte (daten/neu/systeme.jsonl) mit einem Checkpoint; ohne Referenz.

python lesen.py --model runs/s4/checkpoint-11769 --device cpu
"""

import argparse
import json
import time

import torch
from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor

from metriken import schleife, sicht
from train import HIER, eingabe


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--liste", default="daten/neu/systeme.jsonl")
    ap.add_argument("--aus", default="daten/neu/lesungen.jsonl")
    ap.add_argument("--bild", default="streifen")
    ap.add_argument("--max-tokens", type=int, default=600)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()
    device = torch.device(args.device)
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    model = LightOnOcrForConditionalGeneration.from_pretrained(
        args.model, dtype=dtype
    ).to(device)
    model.eval()
    proc = LightOnOcrProcessor.from_pretrained(args.model)
    eos = proc.tokenizer.eos_token_id
    zeilen = [
        json.loads(z)
        for z in (HIER / args.liste).read_text(encoding="utf-8").splitlines()
    ]
    t0 = time.time()
    with open(HIER / args.aus, "w", encoding="utf-8") as f:
        for i, z in enumerate(zeilen, 1):
            x = eingabe(proc, z, args.bild, device)
            if device.type == "cuda":
                x["pixel_values"] = x["pixel_values"].to(dtype)
            with torch.inference_mode():
                aus = model.generate(
                    **x, max_new_tokens=args.max_tokens, do_sample=False
                )[0, x["input_ids"].shape[1] :]
            hyp = proc.tokenizer.decode(aus, skip_special_tokens=True)
            v = sicht(hyp)
            z |= {
                "lesung": hyp,
                "abgebrochen": eos not in aus.tolist(),
                "schleife": schleife(hyp),
                "toene": len(v["toene"]),
                "schluessel": v["schl"],
                "text": " ".join(v["silben"]),
            }
            f.write(json.dumps(z, ensure_ascii=False) + "\n")
            f.flush()
            print(
                f"{i}/{len(zeilen)} {(time.time() - t0) / i:.1f} s/System {z['id']}",
                flush=True,
            )


if __name__ == "__main__":
    main()
