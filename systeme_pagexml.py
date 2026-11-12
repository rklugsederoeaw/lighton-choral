"""Systemausschnitte (Notenzeile + Text darunter) aus Transkribus-PAGE-XML, im Stil von AMNLT.

python systeme_pagexml.py inventar
python systeme_pagexml.py schneiden <Exportordner> <Seiten je Export> <Systeme je Seite>
"""

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

HIER = Path(__file__).resolve().parent
EXPORTE = HIER.parent / "transkribus"
NS = "{http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15}"
OBEN, UNTEN, LINKS, RECHTS = 1.5, 0.2, 1.5, 0.5  # in Linienabständen d
GT_QUELLEN = {
    "geras6": "A-Geras_6_Graduale",
    "kn65": "A-KN_65_Antiphonar-Winterteil",
    "wn15484": "A-Wn15484_OFM_Grad_Italy",
    "gu17": "A-Gu_17_Graduale_Seckau",
    "vor254": "A-VOR_254_Graduale",
}


def rechteck(region):
    xy = [
        tuple(map(int, p.split(",")))
        for p in region.find(NS + "Coords").get("points").split()
    ]
    xs, ys = zip(*xy)
    return min(xs), min(ys), max(xs), max(ys)


def regionen(wurzel, art):
    aus = []
    for r in wurzel.iter(NS + "TextRegion"):
        m = re.search(r"type:([^;}]+)", r.get("custom") or "")
        if m and m[1].strip() == art:
            aus.append(rechteck(r))
    return aus


def gleiche_zeile(a, b):
    return min(a[3], b[3]) - max(a[1], b[1]) >= 0.5 * min(a[3] - a[1], b[3] - b[1])


def zeilen_bilden(noten):
    """Notenregionen derselben Zeile (durch Initialen geteilt) vereinen, von oben nach unten."""
    gruppen = []
    for n in sorted(noten, key=lambda r: r[1]):
        for g in gruppen:
            if any(gleiche_zeile(n, m) for m in g):
                g.append(n)
                break
        else:
            gruppen.append([n])
    return [
        (
            min(r[0] for r in g),
            min(r[1] for r in g),
            max(r[2] for r in g),
            max(r[3] for r in g),
            min(r[3] - r[1] for r in g),
            g,
        )
        for g in gruppen
    ]


def text_unter(zeile, texte, naechste_oben):
    """Textregionen unter der Notenzeile, mit waagerechter Überlappung, vor der nächsten Zeile."""
    x0, y0, x1, y1 = zeile[:4]
    mitte = (y0 + y1) / 2
    grenze = naechste_oben + (y1 - y0) / 2 if naechste_oben is not None else 10**9
    return [
        t
        for t in texte
        if (t[1] + t[3]) / 2 > y1 - 0.1 * (y1 - y0)
        and t[1] > mitte
        and (t[1] + t[3]) / 2 < grenze
        and min(x1, t[2]) - max(x0, t[0]) > 0.3 * min(x1 - x0, t[2] - t[0])
    ]


def systeme(wurzel, b, h):
    """Je System: Bildrechteck und ob Text gefunden wurde."""
    zeilen = zeilen_bilden(regionen(wurzel, "notation"))
    texte = regionen(wurzel, "text")
    aus = []
    for i, z in enumerate(zeilen):
        naechste = zeilen[i + 1][1] if i + 1 < len(zeilen) else None
        t = text_unter(z, texte, naechste)
        d = z[4] / 3.5
        # Textzeile des Systems darüber nicht mit ins Bild: oberer Rand endet an ihrer Unterkante
        darueber = [
            r[3]
            for r in texte
            if (r[1] + r[3]) / 2 < z[1]
            and min(z[2], r[2]) - max(z[0], r[0]) > 0.3 * min(z[2] - z[0], r[2] - r[0])
        ]
        oben = z[1] - OBEN * d
        if darueber:
            oben = max(oben, min(max(darueber), z[1] - 0.5 * d))
        x0 = min([z[0], *[r[0] for r in t]]) - LINKS * d
        x1 = max([z[2], *[r[2] for r in t]]) + RECHTS * d
        y1 = max([z[3], *[r[3] for r in t]]) + UNTEN * d
        kasten = (
            max(0, int(x0)),
            max(0, int(oben)),
            min(b, int(x1)),
            min(h, int(y1)),
        )
        aus.append({"kasten": kasten, "mit_text": bool(t), "regionen": z[5]})
    return aus


def wurzel_von(xml):
    try:
        return ET.parse(xml).getroot()
    except ET.ParseError:
        return None


def inventar():
    print("export\tseiten\tGT\tdefekt\tnoten_zeilen\tmit_text\tanteil")
    for e in sorted(p for p in EXPORTE.iterdir() if (p / "page").is_dir()):
        seiten = gt = defekt = z = t = 0
        for xml in sorted((e / "page").glob("*.xml")):
            w = wurzel_von(xml)
            if w is None:
                defekt += 1
                continue
            seiten += 1
            m = w.find(f".//{NS}TranskribusMetadata")
            gt += m is not None and m.get("status") == "GT"
            s = systeme(w, 10**6, 10**6)
            z += len(s)
            t += sum(x["mit_text"] for x in s)
        print(
            f"{e.name}\t{seiten}\t{gt}\t{defekt}\t{z}\t{t}\t{t / z:.2f}"
            if z
            else f"{e.name}\t{seiten}\t{gt}\t{defekt}\t0\t0\t-"
        )


def schneiden(export, n_seiten, n_systeme):
    e = EXPORTE / export
    r = random.Random(0)
    ziel = HIER / "daten/neu" / export
    ziel.mkdir(parents=True, exist_ok=True)
    kandidaten = []
    for xml in sorted((e / "page").glob("*.xml")):
        w = wurzel_von(xml)
        if w is not None:
            s = [x for x in systeme(w, 10**6, 10**6) if x["mit_text"]]
            if s:
                kandidaten.append(xml)
    zeilen = []
    for xml in r.sample(kandidaten, min(n_seiten, len(kandidaten))):
        w = wurzel_von(xml)
        p = w.find(NS + "Page")
        bild = e / p.get("imageFilename")
        if not bild.exists():
            print("Bild fehlt:", bild)
            continue
        im = Image.open(bild).convert("RGB")
        s = [x for x in systeme(w, *im.size) if x["mit_text"]]
        for i in sorted(r.sample(range(len(s)), min(n_systeme, len(s)))):
            pfad = ziel / f"{xml.stem}_{i:02d}.jpg"
            im.crop(s[i]["kasten"]).save(pfad, quality=92)
            zeilen.append(
                {
                    "id": f"{export}/{xml.stem}_{i:02d}",
                    "quelle": export,
                    "bild": str(pfad.relative_to(HIER)),
                    "kasten": s[i]["kasten"],
                    "seite": xml.stem,
                }
            )
    with open(HIER / "daten/neu/systeme.jsonl", "a", encoding="utf-8") as f:
        for z in zeilen:
            f.write(json.dumps(z, ensure_ascii=False) + "\n")
    print(export, len(zeilen), "Systeme")


def mit_gt(n_je_quelle):
    """Zufallsauswahl geprüfter Systeme (Label aus dem GT-Index), nur einteilige Notenzeilen."""
    r = random.Random(0)
    aus = []
    for name, export in GT_QUELLEN.items():
        e = EXPORTE / export
        rows = [
            json.loads(x)
            for x in (HIER.parent / "daten" / name / "music/index.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        rows = [
            x for x in rows if x.get("label") and x["split"] in ("train", "val", "test")
        ]
        xmls = {p.stem[:4]: p for p in (e / "page").glob("*.xml")}
        ziel = HIER / "daten/gt" / name
        ziel.mkdir(parents=True, exist_ok=True)
        r.shuffle(rows)
        zahl = Counter()
        fertig = 0
        for x in rows:
            if fertig == n_je_quelle:
                break
            xml = xmls.get(x["id"][:4])
            w = wurzel_von(xml) if xml else None
            if w is None:
                zahl["keine_seite"] += 1
                continue
            p = w.find(NS + "Page")
            bild = e / p.get("imageFilename")
            b, h = int(p.get("imageWidth")), int(p.get("imageHeight"))
            treffer = [
                s for s in systeme(w, b, h) if tuple(x["region"]) in s["regionen"]
            ]
            if not treffer:
                zahl["region_nicht_gefunden"] += 1
                continue
            s = treffer[0]
            if len(s["regionen"]) > 1:
                zahl["mehrteilig"] += 1
                continue
            if not s["mit_text"]:
                zahl["ohne_text"] += 1
                continue
            if not bild.exists():
                zahl["bild_fehlt"] += 1
                continue
            pfad = ziel / f"{x['id']}.jpg"
            Image.open(bild).convert("RGB").crop(s["kasten"]).save(pfad, quality=92)
            fertig += 1
            aus.append(
                {
                    "id": f"{name}/{x['id']}",
                    "quelle": name,
                    "bild": str(pfad.relative_to(HIER)),
                    "label": x["label"],
                    "split": x["split"],
                }
            )
        print(name, fertig, dict(zahl), flush=True)
    (HIER / "daten/gt/systeme.jsonl").write_text(
        "".join(json.dumps(z, ensure_ascii=False) + "\n" for z in aus),
        encoding="utf-8",
    )


if __name__ == "__main__":
    a, b = (0, 100, 500, 200), (510, 90, 700, 210)
    assert gleiche_zeile(a, b) and not gleiche_zeile(a, (0, 300, 500, 400))
    assert len(zeilen_bilden([a, b, (0, 300, 500, 400)])) == 2
    z = zeilen_bilden([a])[0]
    assert text_unter(z, [(10, 190, 400, 260), (10, 400, 400, 460)], 300) == [
        (10, 190, 400, 260)
    ]
    if sys.argv[1] == "inventar":
        inventar()
    elif sys.argv[1] == "gt":
        mit_gt(int(sys.argv[2]))
    else:
        schneiden(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
