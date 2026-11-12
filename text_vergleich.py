"""Misst den gelesenen Liedtext gegen die korrigierte Text-GT der Transkribus-Exporte.

Nur Seiten im Bereich korr_text_rk aus gt_uebersicht.tsv. Abkürzungen sind dort ausgeschrieben.
"""

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz.distance import Levenshtein as lev

from metriken import sicht
from systeme_pagexml import (
    EXPORTE,
    GT_QUELLEN,
    NS,
    rechteck,
    systeme,
    text_unter,
    wurzel_von,
    zeilen_bilden,
    regionen,
)

HIER = Path(__file__).resolve().parent
BEREICH = {
    "geras6": (1, 31),
    "kn65": (1, 52),
    "wn15484": (1, 100),
    "gu17": (1, 30),
    "vor254": (80, 110),
}


def regionstext(r):
    teile = []
    for z in r.findall(NS + "TextLine"):
        u = z.find(f"{NS}TextEquiv/{NS}Unicode")
        if u is not None and u.text:
            teile.append(u.text)
    if not teile:
        u = r.find(f"{NS}TextEquiv/{NS}Unicode")
        if u is not None and u.text:
            teile.append(u.text)
    return " ".join(teile)


def textregionen(w):
    aus = []
    for r in w.iter(NS + "TextRegion"):
        m = re.search(r"type:([^;}]+)", r.get("custom") or "")
        if m and m[1].strip() == "text":
            aus.append((rechteck(r), regionstext(r)))
    return aus


def norm(s):
    return re.sub(r"[^a-z]", "", s.lower().replace("j", "i").replace("v", "u"))


def referenzen():
    basis = [
        json.loads(z)
        for z in (HIER / "daten/gt/systeme.jsonl").read_text().splitlines()
    ]
    aus, zahl = {}, Counter()
    for q, export in GT_QUELLEN.items():
        e = EXPORTE / export
        xmls = {p.stem[:4]: p for p in (e / "page").glob("*.xml")}
        reg = {
            x["id"]: tuple(x["region"])
            for x in map(
                json.loads,
                (HIER.parent / "daten" / q / "music/index.jsonl")
                .read_text()
                .splitlines(),
            )
            if x.get("region")
        }
        for z in [b for b in basis if b["quelle"] == q]:
            sid = z["id"].split("/")[1]
            zahl[q, "systeme"] += 1
            if not BEREICH[q][0] <= int(sid[:4]) <= BEREICH[q][1]:
                zahl[q, "seite_ohne_korrektur"] += 1
                continue
            w = wurzel_von(xmls[sid[:4]])
            tr = textregionen(w)
            zeilen = zeilen_bilden(regionen(w, "notation"))
            i = next(k for k, g in enumerate(zeilen) if reg[sid] in g[5])
            naechste = zeilen[i + 1][1] if i + 1 < len(zeilen) else None
            treffer = sorted(text_unter(zeilen[i], [t[0] for t in tr], naechste))
            ref = " ".join(t[1] for b in treffer for t in tr if t[0] == b).strip()
            if not ref:
                zahl[q, "ohne_text"] += 1
                continue
            zahl[q, "gemessen"] += 1
            aus[z["id"]] = (q, ref)
    return aus, zahl


def main():
    ref, zahl = referenzen()
    print(sorted(zahl.items()))
    ergebnis = {}
    for name, pfad in (
        ("s4", "daten/gt/lesungen.jsonl"),
        ("s4k", "runs/s4k/checkpoint-24332/lesung_gt.jsonl"),
        ("s4g", "runs/s4g/checkpoint-38112/lesung_gt.jsonl"),
        ("s4g_ep4", "runs/s4g/checkpoint-50816/lesung_gt.jsonl"),
        ("s4w", "runs/s4w/checkpoint-50816/lesung_gt.jsonl"),
        ("s4w_ep3", "runs/s4w/checkpoint-38112/lesung_gt.jsonl"),
    ):
        c = defaultdict(Counter)
        einzel = defaultdict(list)
        for z in map(
            json.loads, (HIER / pfad).read_text(encoding="utf-8").splitlines()
        ):
            if z["id"] not in ref:
                continue
            q, r = ref[z["id"]]
            if z["schleife"] or z["abgebrochen"]:
                c[q]["ausgelassen"] += 1
                c["alle"]["ausgelassen"] += 1
                continue
            v = sicht(z["lesung"])
            a, b = re.sub(r"\s+", "", r), v["zeichen"]
            f, fn = lev.distance(a, b), lev.distance(norm(r), norm(b))
            for k in (q, "alle"):
                c[k]["n"] += len(a)
                c[k]["f"] += f
                c[k]["nn"] += len(norm(r))
                c[k]["fn"] += fn
                c[k]["sys"] += 1
                einzel[k].append(100 * fn / max(1, len(norm(r))))
        ergebnis[name] = {
            k: {
                "systeme": w["sys"],
                "ausgelassen_schleife_abbruch": w["ausgelassen"],
                "zeichen": w["n"],
                "cer_genau_pct": round(100 * w["f"] / w["n"], 2),
                "cer_normalisiert_pct": round(100 * w["fn"] / w["nn"], 2),
                "median_system_cer_norm_pct": round(statistics.median(einzel[k]), 2),
                "systeme_textgleich_norm": sum(1 for x in einzel[k] if x == 0),
            }
            for k, w in c.items()
        }
    (HIER / "text_vergleich.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    for n, e in ergebnis.items():
        print("==", n)
        for k, w in sorted(e.items()):
            print(" ", k, w)


if __name__ == "__main__":
    assert norm("Iu-Vat j!") == "iuuati"
    main()
