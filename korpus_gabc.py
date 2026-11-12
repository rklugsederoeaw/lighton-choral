"""Trainingspaare aus dem GABC-Datensatz (daten/cantus_gabc/datensatz) und eigenem Zuschnitt mit Text.

    python korpus_gabc.py [Prozesse]

Koordinaten: review/results_<quelle>.json oder daten/cantus_gabc/<quelle>/lage.jsonl. Systeme mit fremder
Notenlinie am unteren Rand oder angeschnittenem Text werden verworfen (siehe korpus_cantus.py).
Ausgabe: daten/korpus_gabc/{train,validation,test}.jsonl, Bilder und Prüfbogen je Quelle.
"""

import json
import random
import sys
import textwrap
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from korpus_cantus import fremde_linie_unten, linienprofil, text_angeschnitten

HIER = Path(__file__).resolve().parent
PROJEKT = HIER.parents[1]
NMP = HIER.parent
AUS = HIER / "daten/korpus_gabc"
MIT_RESULTS = ("sbe-0611", "fcc-0002", "d-ka-aug-lx", "d-ka-aug-lx-addendum")
WEGLASSEN = ("a-kn-1012",)  # Projektleiter: alte, schlecht lesbare Notation
SPLITS = ("train", "validation", "test")


def abstand(box):
    """Linienabstand aus dem Kasten: Höhe = 3 d System + 1,5 d oben + 1 d unten."""
    return (box[3] - box[1]) / 5.5


def koordinaten(q):
    aus = {}
    if q in MIT_RESULTS:
        for r in json.loads((PROJEKT / "review" / f"results_{q}.json").read_text()):
            boxen = [s["box"] for s in r["staves"]]
            for s in r["staves"]:
                aus[f"export/{q}/images/{s['crop']}"] = {
                    "seite": f"images/{q}/{r['folio']}.jpg",
                    "box": s["box"],
                    "andere": [b for b in boxen if b != s["box"]],
                }
    else:
        for z in (
            (NMP / "daten/cantus_gabc" / q / "lage.jsonl").read_text().splitlines()
        ):
            x = json.loads(z)
            aus[x["bild"]] = x
    return aus


def schnitte(box, andere):
    """Oberer und unterer Schnitt wie in korpus_cantus: am nächsten Kasten darunter orientiert."""
    x0, y0, x1, y1 = box
    d = abstand(box)
    darunter = [
        b[1]
        for b in andere
        if b[1] > y1 - 3 * d and b[1] > y0 + 2 * d and min(x1, b[2]) > max(x0, b[0])
    ]
    return int(y0 + d), int(min([n + 1.7 * d for n in darunter] + [y1 + 4 * d])), d


def quelle_bearbeiten(q):
    zeilen = []
    for s in SPLITS:
        for z in (
            (NMP / "daten/cantus_gabc/datensatz" / f"{s}.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ):
            r = json.loads(z)
            if r["quelle"] == q:
                r["_split"] = s
                zeilen.append(r)
    koord = koordinaten(q)
    zahl = Counter(zeilen=len(zeilen))
    je_seite = defaultdict(list)
    for r in zeilen:
        k = koord.get(r["image"])
        if k is None:
            zahl["ohne_koordinaten"] += 1
        else:
            je_seite[k["seite"]].append((r, k))
    ziel = AUS / q / "bilder"
    ziel.mkdir(parents=True, exist_ok=True)
    fertig = []
    for seite, eintraege in je_seite.items():
        pfad_seite = PROJEKT / seite
        if not pfad_seite.exists():
            zahl["seite_fehlt"] += len(eintraege)
            continue
        im = Image.open(pfad_seite).convert("RGB")
        gruen = np.asarray(im)[:, :, 1]
        for r, k in eintraege:
            box = [int(v) for v in k["box"]]
            x0, y0, x1, y1 = box
            oben, unten, d = schnitte(box, k.get("andere", []))
            if fremde_linie_unten(
                linienprofil(gruen, x0, x1), y0, y1, unten, int(round(d))
            ):
                zahl["fremde_linie_unten"] += 1
                continue
            if text_angeschnitten(gruen, x0, x1, y1, unten):
                zahl["text_angeschnitten"] += 1
                continue
            name = f"{r['zweig']}_{Path(r['image']).stem}.jpg"
            pfad = ziel / name
            im.crop((x0, oben, x1, unten)).save(pfad, quality=92)
            fertig.append(
                {
                    "id": f"{q}/{r['zweig']}/{r['id']}",
                    "quelle": q,
                    "split": r["_split"],
                    "bild": str(pfad.relative_to(HIER)),
                    "ziel": r["transcription"].strip(),
                }
            )
    zahl["fertig"] = len(fertig)
    pruefbogen(q, fertig)
    return q, fertig, zahl


def pruefbogen(q, zeilen, aus=None):
    aus = aus or AUS
    if not zeilen:
        return
    schrift = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    teile = []
    for z in random.Random(0).sample(zeilen, min(12, len(zeilen))):
        im = Image.open(HIER / z["bild"])
        k = 1400 / im.width
        im = im.resize((1400, int(im.height * k)))
        zt = textwrap.wrap(z["ziel"].replace("<m>", ""), 130)
        leiste = Image.new("RGB", (1400, 26 * (len(zt) + 1) + 10), "white")
        dr = ImageDraw.Draw(leiste)
        dr.text((6, 3), z["id"], fill=(160, 0, 0), font=schrift)
        for i, t in enumerate(zt):
            dr.text((6, 3 + 26 * (i + 1)), t, fill="black", font=schrift)
        teile += [im, leiste]
    o = Image.new("RGB", (1400, sum(t.height for t in teile)), "white")
    y = 0
    for t in teile:
        o.paste(t, (0, y))
        y += t.height
    o.save(aus / q / "pruefung_12.jpg", quality=88)


def main(prozesse):
    quellen = sorted(
        {
            json.loads(z)["quelle"]
            for s in SPLITS
            for z in (NMP / "daten/cantus_gabc/datensatz" / f"{s}.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        }
        - set(WEGLASSEN)
    )
    with Pool(prozesse) as pool:
        ergebnisse = pool.map(quelle_bearbeiten, quellen, chunksize=1)
    alle = [z for _, f, _ in ergebnisse for z in f]
    for s in SPLITS:
        (AUS / f"{s}.jsonl").write_text(
            "".join(
                json.dumps(z, ensure_ascii=False) + "\n"
                for z in alle
                if z["split"] == s
            ),
            encoding="utf-8",
        )
    bericht = {q: dict(c) for q, _, c in ergebnisse}
    (AUS / "bericht.json").write_text(
        json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    for q, c in sorted(bericht.items()):
        print(q, c, flush=True)
    print("gesamt", len(alle), Counter(z["split"] for z in alle), flush=True)


if __name__ == "__main__":
    assert abstand([0, 0, 100, 55]) == 10
    assert schnitte([0, 100, 500, 210], [[0, 240, 500, 350]])[:2] == (120, 274)
    assert schnitte([0, 100, 500, 210], [])[:2] == (120, 290)
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
