"""Schlüsselt Noten- und Textfehler einer Lesung nach Art auf.

python fehlerarten.py runs/s4/checkpoint-11769/lesung_validation.jsonl
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz.distance import Levenshtein as lev

from metriken import ist_schluessel, ist_ton, sicht, zerlege


def klasse(t):
    if ist_schluessel(t):
        return "Schlüssel"
    if len(t) == 2 and t[1] == "+":
        return "Custos"
    if len(t) == 2 and t[1] in "xy":
        return "Vorzeichen"
    if ist_ton(t):
        return "Ton"
    if t == "!":
        return "Neumentrenner !"
    if t[0] in ":;,":
        return "Strich"
    return "Notenform"


def art_ersetzung(r, h):
    if ist_ton(r) and ist_ton(h):
        return "Ton: nur Groß/klein" if r.lower() == h.lower() else "Ton: falsche Lage"
    return (
        f"{klasse(r)} ersetzt"
        if klasse(r) == klasse(h)
        else f"{klasse(r)} → {klasse(h)}"
    )


def noten_fehler(ref, hyp, arten, paare):
    """Zählt die Editieroperationen je Art; die Summe ist der Editierabstand."""
    for op in lev.editops(hyp, ref):
        if op.tag == "replace":
            r, h = ref[op.dest_pos], hyp[op.src_pos]
            arten[art_ersetzung(r, h)] += 1
            paare[f"{r}→{h}"] += 1
        elif op.tag == "insert":  # fehlt in der Lesung
            arten[f"fehlt: {klasse(ref[op.dest_pos])}"] += 1
            paare[f"{ref[op.dest_pos]}→∅"] += 1
        else:
            arten[f"zu viel: {klasse(hyp[op.src_pos])}"] += 1
            paare[f"∅→{hyp[op.src_pos]}"] += 1


def text_mit_leer(s):
    paare, rest = zerlege(s)
    return re.sub(r"\s+", " ", "".join(t for t, _ in paare) + rest).strip()


def main(pfad):
    zeilen = [
        json.loads(z) for z in Path(pfad).read_text(encoding="utf-8").splitlines()
    ]
    je_quelle = defaultdict(list)
    for z in zeilen:
        je_quelle[z["quelle"]].append(z)
    ergebnis = {}
    for q, rs in sorted(je_quelle.items()):
        arten, paare, zeichen = Counter(), Counter(), Counter()
        n_ref = fehl = 0
        t = Counter()
        for z in rs:
            r, h = sicht(z["ref"]), sicht(z["hyp"])
            n_ref += len(r["token"])
            fehl += lev.distance(h["token"], r["token"])
            noten_fehler(r["token"], h["token"], arten, paare)
            for op in lev.editops(h["zeichen"], r["zeichen"]):
                a = r["zeichen"][op.dest_pos] if op.tag != "delete" else "∅"
                b = h["zeichen"][op.src_pos] if op.tag != "insert" else "∅"
                zeichen[f"{a}→{b}"] += 1
            a, b = text_mit_leer(z["ref"]), text_mit_leer(z["hyp"])
            t["zeichen_n"] += len(r["zeichen"])
            t["ohne_leer"] += lev.distance(r["zeichen"], h["zeichen"])
            t["ohne_leer_ohne_gross"] += lev.distance(
                r["zeichen"].lower(), h["zeichen"].lower()
            )
            t["mit_leer"] += lev.distance(a, b)
            t["mit_leer_n"] += len(a)
            t["woerter_n"] += len(a.split())
            t["woerter_f"] += lev.distance(a.split(), b.split())
            t["systeme_text_gleich"] += r["zeichen"] == h["zeichen"]
            t["systeme_nur_leer_anders"] += r["zeichen"] == h["zeichen"] and a != b
            t["silben_n"] += len(r["silben"])
            t["silben_f"] += lev.distance(r["silben"], h["silben"])
        assert sum(arten.values()) == fehl
        anteil = lambda x, n: round(100 * x / n, 2) if n else None  # noqa: E731
        ergebnis[q] = {
            "systeme": len(rs),
            "noten_token": n_ref,
            "noten_ser_pct": anteil(fehl, n_ref),
            "arten": {
                k: {
                    "n": v,
                    "pp_der_ser": anteil(v, n_ref),
                    "anteil_pct": anteil(v, fehl),
                }
                for k, v in arten.most_common()
            },
            "haeufigste_paare": paare.most_common(20),
            "text": {
                "cer_ohne_leerzeichen": anteil(t["ohne_leer"], t["zeichen_n"]),
                "cer_ohne_leer_ohne_gross": anteil(
                    t["ohne_leer_ohne_gross"], t["zeichen_n"]
                ),
                "cer_mit_leerzeichen": anteil(t["mit_leer"], t["mit_leer_n"]),
                "wer": anteil(t["woerter_f"], t["woerter_n"]),
                "silben_ser": anteil(t["silben_f"], t["silben_n"]),
                "systeme_text_gleich": t["systeme_text_gleich"],
                "davon_nur_leerzeichen_anders": t["systeme_nur_leer_anders"],
            },
            "haeufigste_textfehler": zeichen.most_common(15),
        }
    aus = Path(pfad).with_suffix(".fehlerarten.json")
    aus.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
    for q, e in ergebnis.items():
        print(f"\n== {q}: {e['systeme']} Systeme, SER {e['noten_ser_pct']} %")
        for k, v in e["arten"].items():
            print(
                f"  {k:32s} {v['n']:5d}  {v['pp_der_ser']:5.2f} pp  {v['anteil_pct']:5.1f} %"
            )
        print("  Paare:", e["haeufigste_paare"])
        print("  Text:", e["text"])
        print("  Textfehler:", e["haeufigste_textfehler"])


if __name__ == "__main__":
    assert klasse("c4") == "Schlüssel" and klasse("f+") == "Custos"
    assert klasse("gx") == "Vorzeichen" and klasse("G") == "Ton"
    assert klasse("v") == "Notenform" and klasse(";6") == "Strich"
    assert art_ersetzung("g", "G") == "Ton: nur Groß/klein"
    assert art_ersetzung("g", "h") == "Ton: falsche Lage"
    a, p = Counter(), Counter()
    noten_fehler(["g", "v", "h"], ["g", "h", ":"], a, p)
    assert a == Counter({"fehlt: Notenform": 1, "zu viel: Strich": 1}), a
    main(sys.argv[1])
