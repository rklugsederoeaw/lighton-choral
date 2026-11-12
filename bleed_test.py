"""Erzeugt A-Wn-15484-Ausschnitte, die unten in das nächste System hineinragen (halb oder ganz)."""

import json
from pathlib import Path

from PIL import Image

from systeme_pagexml import (
    EXPORTE,
    GT_QUELLEN,
    NS,
    regionen,
    systeme,
    wurzel_von,
    zeilen_bilden,
)

HIER = Path(__file__).resolve().parent
QUELLE = "wn15484"


def main():
    e = EXPORTE / GT_QUELLEN[QUELLE]
    regionen_je_id = {
        x["id"]: tuple(x["region"])
        for x in map(
            json.loads,
            (HIER.parent / "daten" / QUELLE / "music/index.jsonl")
            .read_text()
            .splitlines(),
        )
        if x.get("region")
    }
    basis = [
        z
        for z in map(
            json.loads, (HIER / "daten/gt/systeme.jsonl").read_text().splitlines()
        )
        if z["quelle"] == QUELLE
    ]
    xmls = {p.stem[:4]: p for p in (e / "page").glob("*.xml")}
    aus = {"halb": [], "voll": []}
    ohne_naechstes = 0
    for z in basis:
        sid = z["id"].split("/")[1]
        w = wurzel_von(xmls[sid[:4]])
        p = w.find(NS + "Page")
        b, h = int(p.get("imageWidth")), int(p.get("imageHeight"))
        reg = regionen_je_id[sid]
        s = next(x for x in systeme(w, b, h) if reg in x["regionen"])
        zeilen = zeilen_bilden(regionen(w, "notation"))
        i = next(k for k, g in enumerate(zeilen) if reg in g[5])
        if i + 1 == len(zeilen):
            ohne_naechstes += 1
            continue
        n = zeilen[i + 1]
        im = Image.open(e / p.get("imageFilename")).convert("RGB")
        x0, y0, x1, y1 = s["kasten"]
        for art, unten in (
            ("halb", (n[1] + n[3]) // 2),
            ("voll", n[3] + (n[3] - n[1]) // 8),
        ):
            ziel = HIER / "daten/gt_bleed" / art
            ziel.mkdir(parents=True, exist_ok=True)
            pfad = ziel / f"{sid}.jpg"
            im.crop((x0, y0, x1, max(y1, min(h, unten)))).save(pfad, quality=92)
            aus[art].append({**z, "bild": str(pfad.relative_to(HIER))})
    for art, zeilen in aus.items():
        (HIER / f"daten/gt_bleed/{art}.jsonl").write_text(
            "".join(json.dumps(z, ensure_ascii=False) + "\n" for z in zeilen),
            encoding="utf-8",
        )
    print(len(aus["halb"]), "Systeme; ohne nächstes System:", ohne_naechstes)


if __name__ == "__main__":
    main()
