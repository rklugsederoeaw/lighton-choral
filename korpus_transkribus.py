"""Trainingspaare aus den vier Transkribus-Quellen mit Bildlesung (daten/cantus_gabc/{brlm33,...}).

    python korpus_transkribus.py

Kasten in lage.jsonl ist die enge Transkribus-Notationsregion (etwa 0,25 d über und unter den äußeren
Linien, d = Höhe / 3,5). Zuschnitt 1,5 d über der Region bis knapp über die nächste Notenzeile; Filter wie
korpus_cantus (fremde Notenlinie unten, Text angeschnitten). Zeilen mit unsicherer Initiale gehen in eine
eigene Datei. Ausgabe: daten/korpus_transkribus/{train,validation,test,unsicher}.jsonl, Prüfbogen je Quelle.
"""

import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from korpus_cantus import fremde_linie_unten, linienprofil, text_angeschnitten
from korpus_gabc import pruefbogen
from systeme_pagexml import regionen, wurzel_von

HIER = Path(__file__).resolve().parent
PROJEKT = HIER.parents[1]
AUS = HIER / "daten/korpus_transkribus"
QUELLEN = ("brlm33", "brlm34", "mb2", "vor259")
SPLIT = {"train": "train", "val": "validation", "test": "test"}


def main():
    alle, bericht = [], {}
    for q in QUELLEN:
        ordner = PROJEKT / "natural_music_processing/daten/cantus_gabc" / q
        zeilen = [
            json.loads(z)
            for z in (ordner / "zeilen.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        lage = {
            x["bild"]: x
            for x in map(
                json.loads,
                (ordner / "lage.jsonl").read_text(encoding="utf-8").splitlines(),
            )
        }
        ini = json.loads((ordner / "initialen.json").read_text(encoding="utf-8"))
        ini = ini if isinstance(ini, list) else list(ini.values())
        unsicher = {x["id"] for x in ini if x.get("entschieden") not in (True, "ja")}
        zahl = Counter(zeilen=len(zeilen))
        ziel = AUS / q / "bilder"
        ziel.mkdir(parents=True, exist_ok=True)
        seiten = {}
        fertig = []
        for z in zeilen:
            if z["status"] != "voll":
                zahl["offen"] += 1
                continue
            k = lage.get(z["image"])
            if k is None:
                zahl["ohne_lage"] += 1
                continue
            if z["seite"] not in seiten:
                im = Image.open(PROJEKT / z["seite"]).convert("RGB")
                # alle Notationsregionen der Seite aus der PAGE-XML, auch ohne GT (lage.jsonl kennt nur GT-Zeilen)
                p = PROJEKT / z["seite"]
                w = wurzel_von(p.parent / "page" / (p.stem + ".xml"))
                boxen = regionen(w, "notation") if w is not None else []
                seiten[z["seite"]] = (im, np.asarray(im)[:, :, 1], boxen)
            im, gruen, boxen = seiten[z["seite"]]
            x0, y0, x1, y1 = [int(v) for v in k["box"]]
            d = (y1 - y0) / 3.5
            darunter = [
                b[1]
                for b in list(boxen) + list(k.get("andere", []))
                if b[1] > y1 - d and b[1] > y0 + d and min(x1, b[2]) > max(x0, b[0])
            ]
            oben = max(0, int(y0 - 1.5 * d))
            unten = int(
                min([n + 0.1 * d for n in darunter] + [y1 + 4.5 * d, im.height])
            )
            # Linienfilter nur, wenn die nächste Notenzeile unbekannt ist: Bei diesen Quellen steht die
            # nächste Region in der PAGE-XML, und die schwere gotische Schrift würde den Filter sonst auslösen
            if not darunter and fremde_linie_unten(
                linienprofil(gruen, x0, x1), y0, y1, unten, int(round(d))
            ):
                zahl["fremde_linie_unten"] += 1
                continue
            if text_angeschnitten(gruen, x0, x1, y1, unten):
                zahl["text_angeschnitten"] += 1
                continue
            pfad = ziel / f"{z['id']}.jpg"
            im.crop((x0, oben, x1, unten)).save(pfad, quality=92)
            eintrag = {
                "id": f"{q}/transkribus/{z['id']}",
                "quelle": q,
                "split": SPLIT.get(z["split"], z["split"]),
                "bild": str(pfad.relative_to(HIER)),
                "ziel": z["transcription"].strip(),
                "initiale_unsicher": z["id"] in unsicher,
            }
            fertig.append(eintrag)
            zahl["unsicher" if eintrag["initiale_unsicher"] else "fertig"] += 1
        if fertig:
            pruefbogen(q, [e for e in fertig if not e["initiale_unsicher"]], AUS)
        bericht[q] = dict(zahl)
        print(q, dict(zahl), flush=True)
        alle += fertig
    for s in ("train", "validation", "test"):
        (AUS / f"{s}.jsonl").write_text(
            "".join(
                json.dumps(z, ensure_ascii=False) + "\n"
                for z in alle
                if z["split"] == s and not z["initiale_unsicher"]
            ),
            encoding="utf-8",
        )
    (AUS / "unsicher.jsonl").write_text(
        "".join(
            json.dumps(z, ensure_ascii=False) + "\n"
            for z in alle
            if z["initiale_unsicher"]
        ),
        encoding="utf-8",
    )
    (AUS / "bericht.json").write_text(
        json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print("gesamt", Counter((z["split"], z["initiale_unsicher"]) for z in alle))


if __name__ == "__main__":
    main()
