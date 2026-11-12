"""Vergleicht LightOnOCR und CRNN auf den Prüfhandschriften und prüft Falschlesungen auf Plausibilität.

Plausibilität: Intervall-Trigramm aus allen Volpiano-Melodien der CantusDB. Bei falsch gelesenen Tönen
wird das Stück um die Note in Lesung und Referenz verglichen. Liegt der Anteil „Lesung wahrscheinlicher
als die Referenz“ deutlich über 50 %, schreibt das Modell eher das Erwartbare als das Gesehene.
"""

import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz.distance import Levenshtein as lev

from metriken import sicht
from silben_cantus import DB
from vergleich_gt import anfangsschluessel, toene

HIER = Path(__file__).resolve().parent
ORDER = "89abcdefghjklmnopqrs"
RAND = 16  # Intervalle jenseits zählen als ein Sonderwert


def intervalle(p):
    return [max(-RAND, min(RAND, b - a)) for a, b in zip(p, p[1:])]


def trigramme():
    tri, bi = Counter(), Counter()
    d = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    for (v,) in d.execute("select volpiano from chants where volpiano is not null"):
        p = [ORDER.index(c) for c in v.lower() if c in ORDER]
        iv = intervalle(p)
        for a, b, c in zip(iv, iv[1:], iv[2:]):
            tri[(a, b, c)] += 1
            bi[(a, b)] += 1
    return tri, bi


def lage(s):
    return [None if c == "?" else ord(c) - ord("a") for c in s]


def lokal(p, i, tri, bi):
    """Log-Wahrscheinlichkeit der zwei Intervalle an Position i; None am Rand oder bei unbekannter Lage."""
    if i < 3 or i + 1 >= len(p) or any(x is None for x in p[i - 3 : i + 2]):
        return None
    iv = intervalle(p[i - 3 : i + 2])
    s = 0.0
    for k in (2, 3):
        c = (iv[k - 2], iv[k - 1], iv[k])
        s += math.log((tri[c] + 0.1) / (bi[c[:2]] + 3.3))
    return s


def messe(name, lesung, gt, tri, bi):
    je = defaultdict(lambda: Counter())
    for i, (quelle, hyp, schl) in lesung.items():
        for q in (quelle, "alle"):
            je[q]["f"] += lev.distance(gt[i][1], hyp)
            je[q]["n"] += len(gt[i][1])
            je[q]["l"] += len(hyp)
            s = gt[i][2]
            if s:
                je[q]["sn"] += 1
                je[q]["sok"] += schl in s
        ph, pr = lage(hyp), lage(gt[i][1])
        for op in lev.editops(hyp, gt[i][1]):
            if op.tag == "replace":
                a, b = lokal(ph, op.src_pos, tri, bi), lokal(pr, op.dest_pos, tri, bi)
                if a is not None and b is not None:
                    for q in (quelle, "alle"):
                        je[q]["vn"] += 1
                        je[q]["mehr"] += a > b
                        je[q]["gleich"] += a == b
                        je[q]["sum"] += a - b
    aus = {}
    for q, c in je.items():
        aus[q] = {
            "tonlage_ser_pct": round(100 * c["f"] / c["n"], 2),
            "toene_gt": c["n"],
            "toene_gelesen": c["l"],
            "schluessel_pct": round(100 * c["sok"] / c["sn"], 1) if c["sn"] else None,
            "ersetzte_toene_vergleichbar": c["vn"],
            "lesung_plausibler_pct": round(100 * c["mehr"] / c["vn"], 1)
            if c["vn"]
            else None,
            "gleich_pct": round(100 * c["gleich"] / c["vn"], 1) if c["vn"] else None,
            "mittel_log_differenz": round(c["sum"] / c["vn"], 2) if c["vn"] else None,
        }
    return aus


def lesen(pfad):
    return [json.loads(z) for z in Path(pfad).read_text(encoding="utf-8").splitlines()]


def main():
    print("Trigramme", flush=True)
    tri, bi = trigramme()
    print(len(tri), "Trigramme", flush=True)
    basis = lesen(HIER / "daten/gt/systeme.jsonl")
    gt = {
        z["id"]: (z["quelle"], toene(z["label"]), anfangsschluessel(z["label"]))
        for z in basis
    }

    def lighton(pfad):
        aus = {}
        for z in lesen(pfad):
            v = sicht(z["lesung"])
            aus[z["id"]] = (
                z["quelle"],
                v["toene"],
                v["schl"][0] if v["schl"] else None,
            )
        return aus

    def crnn(feld):
        aus = {}
        for z in lesen(HIER / "daten/gt/crnn_hybrid_hybrid_lang.jsonl"):
            t = z[feld].split()
            aus[z["id"]] = (
                z["quelle"],
                toene(z[feld]),
                t[0] if t and re.match(r"^[a-g]\d", t[0]) else None,
            )
        return aus

    modelle = {
        "LightOn s4": lighton(HIER / "daten/gt/lesungen.jsonl"),
        "LightOn s4k": lighton(HIER / "runs/s4k/checkpoint-24332/lesung_gt.jsonl"),
        "LightOn s4g": lighton(HIER / "runs/s4g/checkpoint-38112/lesung_gt.jsonl"),
        "CRNN lang (CTC)": crnn("ctc"),
        "CRNN lang (Attention)": crnn("att"),
    }
    ergebnis = {m: messe(m, l, gt, tri, bi) for m, l in modelle.items()}
    (HIER / "vergleich_modelle.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    for m, e in ergebnis.items():
        print("\n==", m)
        for q, w in sorted(e.items()):
            print(f"  {q:9s} {w}")


if __name__ == "__main__":
    assert intervalle([1, 3, 2]) == [2, -1]
    assert lage(["c", "?"]) == [2, None]
    main()
