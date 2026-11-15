"""Ganze Seiten statt Systemausschnitte: Seiten, auf denen jedes Notensystem ein GABC-Ziel hat.

    python seiten.py inventar

Seitenziel = Zeilenziele in Lesereihenfolge (von oben nach unten, in derselben Höhe von links
nach rechts), getrennt durch einen Zeilenumbruch. Vollständig heißt: jedes Notensystem der Seite
(PAGE-XML-Notationsregionen bei Transkribus, Systemkästen der Pipeline bei CantusDB) hat eine
Zeile mit status voll; Zeilen mit unsicherer Initiale machen die Seite unvollständig.
Ausgabe: daten/seiten/seiten.jsonl (alle Seiten mit Grund), daten/seiten/inventar.json.
"""

import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

from systeme_pagexml import NS, regionen, text_unter, wurzel_von, zeilen_bilden

HIER = Path(__file__).resolve().parent
NMP = HIER / "nmp"  # Arbeitsprojekt natural_music_processing
BASIS = NMP / ".."  # volpiano2omr_gt: images/, review/
GABC = NMP / "daten/cantus_gabc"
AUS = HIER / "daten/seiten"
TRANSKRIBUS = ("brlm33", "brlm34", "mb2", "vor259")
REVIEW = ("sbe-0611", "fcc-0002", "d-ka-aug-lx", "d-ka-aug-lx-addendum")
# Ganzseiten-Erkennung des Arbeitsprojekts (review/<datei>): Systemindex i = Zeilen-id <folio>_<i:02d>
ERKENNUNG = {
    "a-kn-1018": "kloster_a-kn-1018.json",
    "ch-p-18": "paris_ch-p-18.json",
    "f-pn-lat-12044": "paris_f-pn-lat-12044.json",
}
OHNE_PAGE = REVIEW + tuple(
    ERKENNUNG
)  # Systemkästen aus Detektoren, Schnitte über Notenlinien
# nur lage.jsonl (kennt nur Systeme mit Zuschnitt): a-kn-1010 (Erkennung zählt Teilsysteme anders),
# d-knd-1161 und a-wn-1799 (keine vollständige Erkennung gefunden), a-kn-1012 (Projektleiter: alte,
# schlecht lesbare Notation, auch im Korpus weggelassen)
LAGE = ("a-kn-1010", "a-kn-1012", "a-wn-1799", "d-knd-1161")
PRUEF = {"geras6", "kn65", "wn15484", "gu17", "vor254"}  # nie fürs Training
# Transkribus: maßgeblich ist daten/korpus_transkribus (13.11. von text_claude berichtigt: vertauschte
# Textfolgen, ergänzte Anfangsbuchstaben mitten in der Zeile, falsche Zuordnungen, unsichere Initialen).
# zeilen.jsonl ist nicht berichtigt. Darum: Ziel aus dem Korpus, wenn die Zeile dort steht; Zeilen aus
# unsicher.jsonl wie unsichere Initialen; die wegen Fehlern entfernten Zeilen (FALSCH) fallen heraus. Zeilen,
# die nur am Zuschnittfilter des Korpus scheiterten, behalten das Ziel aus zeilen.jsonl.
# train/ und train2/ (seiten_a, seiten_b) sind vor der Berichtigung gebaut.
FALSCH = {
    "brlm33": {"0012_05"},
    "brlm34": {"0005_06", "0020_10", "0021_09"},
    "mb2": {"0087_11", "0096_01"},
    # 13.11. nach der Gegenprobe: Silbe vor dem Strich bzw. jetzt offen
    "vor259": {
        "0003_01",
        "0007_03",
        "0007_06",
        "0016_07",
        "0018_02",
        "0018_07",
        "0021_05",
        "0022_01",
        "0027_02",
    },
}
MAX_KANTE = 1540
SPLIT = {"val": "validation"}


def jsonl(p):
    return [json.loads(z) for z in Path(p).read_text(encoding="utf-8").splitlines()]


def reihenfolge(kaesten):
    """Indizes in Lesereihenfolge: Zeilen nach Höhe, in derselben Zeile nach x."""
    zeilen = zeilen_bilden([tuple(k[:4]) for k in kaesten])
    rang = {}
    for zi, z in enumerate(zeilen):
        for r in z[5]:
            rang.setdefault(r, (zi, r[0]))
    return sorted(range(len(kaesten)), key=lambda i: rang[tuple(kaesten[i][:4])])


def ueberlappt(a, b):
    """Gleiche Zeile und waagerechte Überlappung."""
    hoch = min(a[3], b[3]) - max(a[1], b[1])
    breit = min(a[2], b[2]) - max(a[0], b[0])
    return hoch > 0.5 * min(a[3] - a[1], b[3] - b[1]) and breit > 0


def seite_eintrag(q, seite, bild, systeme, grund, split, extra=None):
    """systeme: Liste dicts (kasten, ziel, id) in Lesereihenfolge oder None bei Unvollständigkeit."""
    e = {
        "id": f"{q}/{seite}",
        "quelle": q,
        "split": SPLIT.get(split, split),
        "bild": bild,
        "grund": grund,
        "systeme": systeme,
    }
    if systeme and not grund:
        e["ziel"] = "\n".join(s["ziel"] for s in systeme)
    return e | (extra or {})


def transkribus(q):
    zeilen = jsonl(GABC / q / "zeilen.jsonl")
    ini = json.loads((GABC / q / "initialen.json").read_text(encoding="utf-8"))
    ini = ini if isinstance(ini, list) else list(ini.values())
    unsicher = {x["id"] for x in ini if x.get("entschieden") not in (True, "ja")}
    korpus = {  # berichtigte Ziele (Zeilen-id -> Ziel) aus daten/korpus_transkribus
        z["id"].split("/")[-1]: z["ziel"].strip()
        for t in ("train", "validation", "test")
        for z in jsonl(HIER / f"daten/korpus_transkribus/{t}.jsonl")
        if z["quelle"] == q
    }
    unsicher |= {
        z["id"].split("/")[-1]
        for z in jsonl(HIER / "daten/korpus_transkribus/unsicher.jsonl")
        if z["quelle"] == q
    }
    je_seite = defaultdict(list)
    for z in zeilen:
        je_seite[z["seite"]].append(z)
    aus = []
    for seite, zs in sorted(je_seite.items()):
        p = BASIS / seite
        w = wurzel_von(p.parent / "page" / (p.stem + ".xml"))
        reihen = zeilen_bilden(regionen(w, "notation")) if w is not None else []
        grund, systeme = "", []
        for r in reihen:
            treffer = [z for z in zs if ueberlappt(r[:4], z["region"])]
            # Höhe der engen Notationsregion / 3,5 = Linienabstand (min über Teilregionen)
            s = {"kasten": list(r[:4]), "d": r[4] / 3.5, "voll": False}
            systeme.append(s)
            if not treffer:
                grund = grund or "system_ohne_zeile"
                continue
            z = treffer[0]
            s |= {"id": z["id"], "ziel": z["transcription"].strip()}
            s["ziel"] = korpus.get(z["id"], s["ziel"])
            if z["id"] in FALSCH.get(q, ()):  # nie voll, auch nicht in Abschnitten
                grund = grund or "zeile_falsch"
            elif z["status"] != "voll":
                grund = grund or "zeile_offen"
            elif z["id"] in unsicher:
                grund = grund or "initiale_unsicher"
            else:
                s["voll"] = True
        if not reihen:
            grund = "keine_pagexml"
        elif len({s.get("id") for s in systeme}) != len(systeme):
            grund = grund or "zeile_doppelt"
        elif len(systeme) != len(zs):
            grund = grund or "zeile_ohne_system"
        aus.append(seite_eintrag(q, p.stem, str(p), systeme, grund, zs[0]["split"]))
    return aus


def review(q):
    zeilen = {z["id"]: z for z in jsonl(GABC / q / "zeilen.jsonl")}
    # sbe-0611 hat keinen split in zeilen.jsonl; der Datensatz (nur volle Zeilen) schon
    ds = {
        z["id"]: t
        for t in ("train", "validation", "test")
        for z in jsonl(GABC / f"datensatz/{t}.jsonl")
        if z["quelle"] == q
    }
    aus = []
    for f in json.loads((BASIS / f"review/results_{q}.json").read_text("utf-8")):
        staves = f["staves"]
        grund, systeme, leer = "", [], 0
        for i in reihenfolge([s["box"] for s in staves]):
            s = staves[i]
            eintrag = {"kasten": s["box"], "d": f["spacing"], "voll": False}
            systeme.append(eintrag)
            if s.get("leer"):
                # „leer“ heißt nur: nicht zugeordnet; auf sbe-0611 112r trägt es Noten
                leer += 1
                grund = grund or "leeres_system"
                continue
            z = zeilen.get(s["crop"][:-4])
            if z is None:
                grund = grund or "system_ohne_zeile"
                continue
            eintrag |= {
                "id": z["id"],
                "ziel": z["transcription"].strip(),
                "split": z.get("split") or ds.get(z["id"]),
                "voll": z["status"] == "voll",
            }
            if z["status"] != "voll":
                grund = grund or "zeile_offen"
        if not systeme:
            grund = grund or "keine_systeme"
        splits = {s.get("split") for s in systeme if s["voll"]}
        if len(splits) > 1:
            grund = grund or "splits_gemischt"
        bild = BASIS / f"images/{q}/{f['folio']}.jpg"
        aus.append(
            seite_eintrag(
                q,
                f["folio"],
                str(bild),
                systeme,
                grund,
                next(iter(splits), None),
                {"leere_systeme": leer},
            )
        )
    return aus


def erkennung(q):
    """Seiten aus der Ganzseiten-Erkennung (ERKENNUNG): Kasten = Linien + 1,5 d oben, 1,0 d unten."""
    zeilen = defaultdict(list)
    for z in jsonl(GABC / q / "zeilen.jsonl"):
        zeilen[z["id"]].append(z)
    aus = []
    erk = json.loads((BASIS / "review" / ERKENNUNG[q]).read_text(encoding="utf-8"))
    # Kasten jedes Zuschnitts auf der Seite (lage.jsonl): prüft die Zuordnung Systemindex = Zeilen-id.
    # ch-p-18 (38 Seiten) und f-pn-lat-12044 (80 Seiten, z. B. 229v) sind teils um ein System versetzt.
    lage_kasten = {
        Path(x["bild"]).stem: x["box"] for x in jsonl(GABC / q / "lage.jsonl")
    }
    for folio, v in sorted(erk.items()):
        sy = v.get("systeme", []) if isinstance(v, dict) else []
        grund, systeme = "" if sy else "keine_systeme", []
        for i, x in enumerate(sy, 1):
            lin = [float(y) for y in x.get("lines", x.get("linien", []))]
            d = float(x.get("d") or v["d"])
            s = {
                "kasten": [
                    int(x.get("x0", v.get("x", [0, 0])[0])),
                    int(lin[0] - 1.5 * d),
                    int(x.get("x1", v.get("x", [0, 0])[1])),
                    int(lin[-1] + d),
                ],
                "d": d,
                "linien": [lin[0], lin[-1]],
                "voll": False,
            }
            systeme.append(s)
            b = lage_kasten.get(f"{folio}_{i:02d}")
            if b and not (b[1] <= lin[0] <= b[3] and b[1] <= lin[-1] <= b[3] + 0.5 * d):
                grund = "index_versatz"
            voll = [
                z for z in zeilen.get(f"{folio}_{i:02d}", []) if z["status"] == "voll"
            ]
            if not voll or not b:  # ohne Kasten keine Prüfung der Zuordnung möglich
                grund = grund or ("zeile_offen" if not voll else "nicht_geprueft")
                continue
            z = voll[0]
            s |= {
                "id": z["id"],
                "ziel": z["transcription"].strip(),
                "split": z.get("split"),
                "voll": True,
            }
        if grund == "index_versatz":  # Zuordnung auf der ganzen Seite unsicher
            for s in systeme:
                s["voll"] = False
        splits = {s.get("split") for s in systeme if s["voll"]}
        if len(splits) > 1:
            grund = grund or "splits_gemischt"
        aus.append(
            seite_eintrag(
                q,
                folio,
                str(BASIS / f"images/{q}/{folio}.jpg"),
                systeme,
                grund,
                next(iter(splits), None),
            )
        )
    return aus


def lage(q):
    zeilen = {z["id"]: z for z in jsonl(GABC / q / "zeilen.jsonl")}
    je_seite = defaultdict(dict)  # Seite -> Kasten -> Zeilen-id
    for x in jsonl(GABC / q / "lage.jsonl"):
        k = je_seite[x["seite"]]
        k[tuple(x["box"])] = Path(x["bild"]).stem
        for a in x.get("andere", []):
            k.setdefault(tuple(a), None)
    aus = []
    for seite, kaesten in sorted(je_seite.items()):
        liste = list(kaesten)
        grund, systeme = "", []
        for i in reihenfolge(liste):
            zid = kaesten[liste[i]]
            z = zeilen.get(zid) if zid else None
            if z is None:
                grund = grund or "system_ohne_zeile"
                continue
            if z["status"] != "voll":
                grund = grund or "zeile_offen"
            systeme.append(
                {
                    "id": z["id"],
                    "kasten": list(liste[i]),
                    "ziel": z["transcription"].strip(),
                    "split": z.get("split"),
                }
            )
        splits = {s["split"] for s in systeme}
        if len(splits) > 1:
            grund = grund or "splits_gemischt"
        # ponytail: lage.jsonl kennt nur Systeme mit Zuschnitt (Sichtprüfung a-kn-1010, a-wn-1799,
        # ch-p-18, f-pn-lat-12044: Systeme fehlen). Erst mit eigener Systemerkennung je Seite nutzbar.
        grund = grund or "systemliste_unvollstaendig"
        aus.append(
            seite_eintrag(
                q,
                Path(seite).stem,
                str(BASIS / seite),
                systeme,
                grund,
                next(iter(splits), None),
            )
        )
    return aus


def inventar():
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(
        str(HIER / "models/LightOnOCR-3-1B-konvertiert/tokenizer.json")
    )
    alle = []
    for q in TRANSKRIBUS:
        alle += transkribus(q)
    for q in REVIEW:
        alle += review(q)
    for q in ERKENNUNG:
        alle += erkennung(q)
    for q in LAGE:
        alle += lage(q)
    assert not {e["quelle"] for e in alle} & PRUEF
    AUS.mkdir(parents=True, exist_ok=True)
    bericht = {}
    for q in dict.fromkeys(e["quelle"] for e in alle):
        es = [e for e in alle if e["quelle"] == q]
        voll = [e for e in es if not e["grund"]]
        for e in voll:
            e["token"] = len(tok.encode(e["ziel"], add_special_tokens=False).ids) + 1
            b, h = Image.open(e["bild"]).size
            e["groesse"] = [b, h]
        n = [len(e["systeme"]) for e in voll]
        t = [e["token"] for e in voll]
        bericht[q] = {
            "seiten": len(es),
            "voll": len(voll),
            "splits": dict(Counter(e["split"] for e in voll)),
            "gruende": dict(Counter(e["grund"] for e in es if e["grund"])),
            "systeme_je_seite": [min(n), st.median(n), max(n)] if n else None,
            "token_min_median_p90_max": [
                min(t),
                st.median(t),
                sorted(t)[int(0.9 * (len(t) - 1))],
                max(t),
            ]
            if t
            else None,
        }
        print(q, json.dumps(bericht[q], ensure_ascii=False), flush=True)
    (AUS / "seiten.jsonl").write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in alle),
        encoding="utf-8",
    )
    (AUS / "inventar.json").write_text(
        json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def aufloesung():
    """Pixel je Tonschritt (d/2) nach der Skalierung: ganze Seite, Seitenhälfte, Systemausschnitt."""
    import math

    from aufloesung import linienabstand
    from bildform import massstab_bei, streifen_zahl

    voll = [e for e in jsonl(AUS / "seiten.jsonl") if not e["grund"]]
    bericht = {}
    for q in dict.fromkeys(e["quelle"] for e in voll):
        r = defaultdict(list)
        for e in (e for e in voll if e["quelle"] == q):
            b, h = e["groesse"]
            s_seite = MAX_KANTE / max(b, h)
            s_halb = MAX_KANTE / max(b, 0.55 * h)  # Hälfte mit 10 % Überlappung
            r["token_bild_seite"].append(
                math.ceil(b * s_seite / 28) * math.ceil(h * s_seite / 28)
            )
            for s in e["systeme"]:
                kb, kh = (
                    s["kasten"][2] - s["kasten"][0],
                    s["kasten"][3] - s["kasten"][1],
                )
                n = streifen_zahl(kb, kh)
                s_aus = massstab_bei(kb, kh, n) if n > 1 else MAX_KANTE / max(kb, kh)
                r["seite"].append(s["d"] / 2 * s_seite)
                r["haelfte"].append(s["d"] / 2 * s_halb)
                r["ausschnitt"].append(s["d"] / 2 * s_aus)
                r["d"].append(s["d"])
        # Stichprobe: d der Quelle gegen Autokorrelation am Systemkasten
        e = next(e for e in voll if e["quelle"] == q)
        im = Image.open(e["bild"]).convert("RGB")
        probe = [
            (round(s["d"], 1), linienabstand(im.crop(s["kasten"]))[0])
            for s in e["systeme"][:3]
        ]
        q10 = lambda v: round(sorted(v)[len(v) // 10], 1)  # noqa: E731
        bericht[q] = {
            "linienabstand_median": round(st.median(r["d"]), 1),
            "kontrolle_d_autokorr": probe,
            **{
                f"tonschritt_{k}": {
                    "median": round(st.median(r[k]), 1),
                    "p10": q10(r[k]),
                }
                for k in ("seite", "haelfte", "ausschnitt")
            },
            "bildtoken_seite_median": st.median(r["token_bild_seite"]),
        }
        print(q, json.dumps(bericht[q], ensure_ascii=False), flush=True)
    (AUS / "aufloesung.json").write_text(
        json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def pruef_seiten():
    """Ganze Seiten der Prüfhandschriften, auf denen jede Notationsregion ein geprüftes Label hat.

    Nur Noten-GT (Lagen l1/z2 ...), kein Text. Label je System = Labels der Teilregionen von links.
    """
    from systeme_pagexml import GT_QUELLEN

    aus = []
    for name, export in GT_QUELLEN.items():
        e = NMP / "transkribus" / export
        label = {
            tuple(x["region"]): x["label"]
            for x in jsonl(NMP / "daten" / name / "music/index.jsonl")
            if x.get("label") and x.get("region")
        }
        for xml in sorted((e / "page").glob("*.xml")):
            w = wurzel_von(xml)
            if w is None:
                continue
            reihen = zeilen_bilden(regionen(w, "notation"))
            if not reihen or not any(r in label for z in reihen for r in z[5]):
                continue
            teile = [sorted(z[5]) for z in reihen]
            voll = all(r in label for t in teile for r in t)
            bild = e / w.find(f"{NS}Page").get("imageFilename")  # type: ignore[union-attr]
            aus.append(
                {
                    "id": f"{name}/{xml.stem}",
                    "quelle": name,
                    "split": "pruef",
                    "bild": str(bild),
                    "grund": "" if voll else "region_ohne_label",
                    "systeme": [
                        {
                            "kasten": list(z[:4]),
                            "d": z[4] / 3.5,
                            "label": " ".join(label.get(r, "") for r in t),
                        }
                        for z, t in zip(reihen, teile)
                    ],
                }
            )
    return aus


def linien(im, e, s):
    """Oberste und unterste Notenlinie und Linienabstand eines Systems (Originalpixel).

    PAGE-Regionen enthalten nur die Noten: Linien per Autokorrelation (Höhe/3,5 liegt bis 25 %
    daneben, vor254: 87 statt 67). Review-Kästen beginnen an der Textzeile darüber (sbe-0611
    121v: oberste Linie 2,5 d unter der Oberkante, nicht 1,5 d) und enthalten Text, der die
    Autokorrelation fängt: dort Kamm aus vier Linien im bekannten Abstand d der Seite über den
    Median je Bildzeile (Notenlinien laufen über die ganze Breite, Text nicht).
    """
    import numpy as np

    from aufloesung import linienabstand

    x0, y0, x1, y1 = s["kasten"]
    if "linien" in s:  # Linienlagen aus der Ganzseiten-Erkennung
        return s["linien"][0], s["linien"][-1], s["d"]
    if e["quelle"] in OHNE_PAGE:
        d = s["d"]
        # Grat wie scripts/staves.py: waagerecht gemittelte Dunkelheit minus Nachbarn 3 px darüber
        # und darunter; dünne Linien bleiben, dicke Textbänder fallen weg
        # mittleres Drittel der Breite: Seitenneigung bis 0,013 verschiebt Linien sonst um ~d/2
        b3 = (x1 - x0) // 3
        g = (
            255.0
            - np.asarray(im.crop((x0 + b3, y0, x1 - b3, y1)).convert("RGB"))[:, :, 1]
        )
        h = g.mean(axis=1)
        p = np.clip(h - 0.5 * (np.roll(h, 3) + np.roll(h, -3)), 0, None)
        n = len(p) - 3 * int(round(d))
        if n > 0:
            t = max(range(n), key=lambda t: sum(p[t + round(i * d)] for i in range(4)))
            return y0 + t, y0 + t + 3 * d, d
        return y0 + 1.5 * d, y0 + 4.5 * d, d
    d, guete, lin = linienabstand(im.crop((x0, y0, x1, y1)))
    if d is None or guete < 0.6 or not lin:
        d = s[
            "d"
        ]  # ponytail: Notbehelf, enge Region etwa 0,25 d über und unter den Linien
        return y0 + 0.25 * d, y1 - 0.25 * d, d
    return y0 + lin[0], y0 + lin[-1], d


def zeile_von(e):
    """Notenzeile je System: Review-Kästen derselben Zeile (links/rechts einer Initiale) teilen sie."""
    rang = {}
    for zi, z in enumerate(zeilen_bilden([tuple(s["kasten"]) for s in e["systeme"]])):
        for r in z[5]:
            rang[r] = zi
    return [rang[tuple(s["kasten"])] for s in e["systeme"]]


def zeilenrand(z, i, j):
    """i..j auf ganze Notenzeilen erweitern."""
    while i > 0 and z[i - 1] == z[i]:
        i -= 1
    while j < len(z) - 1 and z[j + 1] == z[j]:
        j += 1
    return i, j


def schnitt(im, gruen, e, k):
    """Schnitt über Zeile von System k: unter der Textzeile der Zeile davor (dichteste Tinte
    zwischen den Notenlinien), dann die hellste Bildzeile bis knapp über die oberste Linie."""
    import numpy as np

    z = zeile_von(e)
    li = [linien(im, e, s) for s in e["systeme"]]
    unten = max(li[i][1] for i in range(len(z)) if z[i] == z[k] - 1)
    oben = min(li[i][0] for i in range(len(z)) if z[i] == z[k])
    d = li[k][2]
    x0 = min(s["kasten"][0] for s in e["systeme"])
    x1 = max(s["kasten"][2] for s in e["systeme"])
    a, b = int(unten + 0.3 * d), int(oben - 0.2 * d)
    if b - a < 4:
        return int((unten + oben) / 2)
    k_ = max(3, int(d / 3)) | 1
    p = np.convolve(
        (255.0 - gruen[a:b, x0:x1]).mean(axis=1), np.ones(k_) / k_, mode="same"
    )
    von = int(np.argmax(p)) + int(0.5 * d)
    if von >= len(p):
        return b
    return a + von + int(np.argmin(p[von:]))


def xml_von(e):
    """PAGE-XML der Seite: Feld xml (seiten_d.py) oder page/ neben dem Bild."""
    b = Path(e["bild"])
    return Path(e["xml"]) if "xml" in e else b.parent / "page" / (b.stem + ".xml")


def grenze(e, im, gruen, k):
    """Waagerechter Schnitt zwischen System k-1 und k (Originalpixel)."""
    if e["quelle"] in OHNE_PAGE:
        return schnitt(im, gruen, e, k)
    # PAGE-XML: zwischen Unterkante der Textregion von k-1 und Notenregion k
    w = wurzel_von(xml_von(e))
    reihen = zeilen_bilden(regionen(w, "notation"))
    t = text_unter(reihen[k - 1], regionen(w, "text"), reihen[k][1])
    tb = max([r[3] for r in t], default=reihen[k - 1][3])
    return int((tb + reihen[k][1]) / 2) if tb < reihen[k][1] else tb


def rand_oben(e, im, gruen):
    """Schnitt über der ersten Notenzeile (Platz für hohe Noten), statt am oberen Seitenrand."""
    if e["quelle"] in OHNE_PAGE:
        z = zeile_von(e)
        li = [linien(im, e, s) for k, s in enumerate(e["systeme"]) if z[k] == 0]
        return max(0, int(min(o for o, _, _ in li) - 2.0 * li[0][2]))
    s = e["systeme"][0]
    return max(0, int(s["kasten"][1] - 1.5 * s["d"]))


def rand_unten(e, im, gruen):
    """Schnitt unter der Textzeile der letzten Notenzeile, statt am unteren Seitenrand."""
    import numpy as np

    if e["quelle"] in OHNE_PAGE:
        z = zeile_von(e)
        li = [linien(im, e, s) for k, s in enumerate(e["systeme"]) if z[k] == z[-1]]
        unten, d = max(u for _, u, _ in li), li[0][2]
        x0 = min(s["kasten"][0] for s in e["systeme"])
        x1 = max(s["kasten"][2] for s in e["systeme"])
        a, b = int(unten + 0.3 * d), min(im.height, int(unten + 4.5 * d))
        if b - a < 4:
            return b
        k_ = max(3, int(d / 3)) | 1
        p = np.convolve(
            (255.0 - gruen[a:b, x0:x1]).mean(axis=1), np.ones(k_) / k_, mode="same"
        )
        von = int(np.argmax(p)) + int(0.5 * d)
        return b if von >= len(p) else a + von + int(np.argmin(p[von:]))
    w = wurzel_von(xml_von(e))
    reihen = zeilen_bilden(regionen(w, "notation"))
    d = e["systeme"][-1]["d"]
    t = text_unter(reihen[-1], regionen(w, "text"), None)
    tb = max([r[3] for r in t], default=reihen[-1][3] + 2.5 * d)
    return min(im.height, int(tb + 0.3 * d))


def abschnitt(e, im, gruen, i, j, rand=True):
    """Bildstreifen über die volle Seitenbreite mit den Systemen i..j (einschließlich).
    rand=False: erster/letzter Abschnitt reicht bis an den Seitenrand (wie die Hälften des Lesetests)."""
    n = len(e["systeme"])
    if i > 0:
        oben = grenze(e, im, gruen, i)
    else:
        oben = rand_oben(e, im, gruen) if rand else 0
    if j < n - 1:
        unten = grenze(e, im, gruen, j + 1)
    else:
        unten = rand_unten(e, im, gruen) if rand else im.height
    return im.crop((0, oben, im.width, unten))


def luecken(e, im):
    """Hinweise auf Notensysteme, die in der Systemliste fehlen (nur Review-Quellen; PAGE-XML ist
    von Hand erfasst). Vier-Linien-Kamm mit dem Linienabstand der Seite über den Grat-Filter
    (jede der vier Linien muss da sein, sonst greifen Seitenkanten); Treffer außerhalb aller
    Kästen = fehlendes System. Dazu Sprünge im Zeilenabstand über das 1,6-fache und unter das 0,7-fache des Medians.
    Blasse Systeme rutschen durch (d-ka-aug-lx 017r: 2 von ~8), darum zählt jeder Hinweis."""
    import numpy as np
    from scipy.signal import find_peaks

    if e["quelle"] not in OHNE_PAGE:
        return []
    sy = e["systeme"]
    x0 = min(s["kasten"][0] for s in sy)
    x1 = max(s["kasten"][2] for s in sy)
    b3 = (x1 - x0) // 3
    g = 255.0 - np.asarray(im)[:, x0 + b3 : x1 - b3, 1].astype(np.float32)
    h = g.mean(axis=1)
    p = np.clip(h - 0.5 * (np.roll(h, 3) + np.roll(h, -3)), 0, None)
    pm = np.maximum(np.maximum(p, np.roll(p, 1)), np.roll(p, -1))
    d = sy[0]["d"]
    n = len(p) - 3 * int(round(d)) - 2
    zahn = [pm[round(k * d) : round(k * d) + n] for k in range(4)]
    s = np.minimum.reduce(zahn)
    pk, _ = find_peaks(s, distance=int(3.5 * d))
    drin = lambda y: any(  # noqa: E731
        k["kasten"][1] - 0.5 * d <= y <= k["kasten"][3] for k in sy
    )
    ref = np.median([s[y] for y in pk if drin(y)] or [s.max()])
    aus = [f"system_bei_y{int(y)}" for y in pk if s[y] >= 0.4 * ref and not drin(y)]
    return aus + abstaende(e)


def abstaende(e):
    """Sprünge im Zeilenabstand (Oberkanten der Notenzeilen) über das 1,6-fache und unter das 0,7-fache des Medians."""
    z = zeile_von(e)
    sy = e["systeme"]
    aus = []
    oben = {}
    for k, x in enumerate(sy):
        oben.setdefault(z[k], x["kasten"][1])
    y = [oben[r] for r in sorted(oben)]
    abst = [b - a for a, b in zip(y, y[1:])]
    if abst:
        m = st.median(abst)
        aus += [f"abstand_zeile{r}" for r, a in enumerate(abst) if a > 1.6 * m]
        # zu eng: Doppel- oder Fehlerkennung (f-pn-lat-12044 042v: System 12 beginnt 8 px unter 11)
        aus += [f"abstand_eng_zeile{r}" for r, a in enumerate(abst) if a < 0.7 * m]
    return aus


def probe(n_pruef=4):
    """Lesetest-Menge: val/test-Seiten und ganze Seiten der Prüfhandschriften, je als Seite,
    obere/untere Hälfte und Systemausschnitte (ungefiltert, Zuschnitt wie im Korpus)."""
    import random

    import numpy as np

    from korpus_gabc import schnitte
    from systeme_pagexml import systeme as pagexml_systeme

    alle = jsonl(AUS / "seiten.jsonl")
    wahl = [e for e in alle if not e["grund"] and e["split"] in ("validation", "test")]
    pr = [e for e in pruef_seiten() if not e["grund"]]
    rng = random.Random(0)
    for q in dict.fromkeys(e["quelle"] for e in pr):
        wahl += rng.sample([e for e in pr if e["quelle"] == q], n_pruef)
    ordner = AUS / "probe"
    (ordner / "bilder").mkdir(parents=True, exist_ok=True)
    listen = defaultdict(list)

    def speichern(im, name, eintrag, art):
        p = ordner / "bilder" / f"{name}.jpg"
        k = min(1.0, 2 * MAX_KANTE / max(im.size))  # Reserve für größere Eingabekanten
        if k < 1:
            im = im.resize(
                (round(im.width * k), round(im.height * k)), Image.Resampling.LANCZOS
            )
        im.save(p, quality=92)
        listen[art].append(eintrag | {"bild": str(p.relative_to(HIER))})

    for e in wahl:
        im = Image.open(e["bild"]).convert("RGB")
        gruen = np.asarray(im)[:, :, 1]
        name = e["id"].replace("/", "_")
        sy = e["systeme"]
        ref = lambda t: (  # noqa: E731
            {"ziel": "\n".join(s["ziel"] for s in t)}
            if "ziel" in t[0]
            else {"label": [s["label"] for s in t]}
        )
        kopf = {"seite": e["id"], "quelle": e["quelle"], "split": e["split"]}
        speichern(
            im, name, kopf | {"id": e["id"], "n_systeme": len(sy)} | ref(sy), "seiten"
        )
        k = zeilenrand(zeile_von(e), len(sy) // 2, len(sy) // 2)[0]
        if k:
            y = grenze(e, im, gruen, k)
            for teil, box, t in (
                ("oben", (0, 0, im.width, y), sy[:k]),
                ("unten", (0, y, im.width, im.height), sy[k:]),
            ):
                speichern(
                    im.crop(box),
                    f"{name}_{teil}",
                    kopf
                    | {"id": f"{e['id']}/{teil}", "teil": teil, "n_systeme": len(t)}
                    | ref(t),
                    "haelften",
                )
        # Systemausschnitte
        if e["quelle"] in REVIEW:
            boxen = [s["kasten"] for s in sy]
            kaesten = []
            for b in boxen:
                oben, unten, _ = schnitte(b, [a for a in boxen if a is not b])
                kaesten.append((b[0], oben, b[2], unten))
        else:
            xml = Path(e["bild"])
            w = wurzel_von(xml.parent / "page" / (xml.stem + ".xml"))
            ps = pagexml_systeme(w, *im.size)
            assert len(ps) == len(sy), e["id"]
            kaesten = [x["kasten"] for x in ps]
        for i, (s, kast) in enumerate(zip(sy, kaesten)):
            speichern(
                im.crop(tuple(int(v) for v in kast)),
                f"{name}_{i:02d}",
                kopf | {"id": f"{e['id']}/{i:02d}", "nr": i} | ref([s]),
                "systeme",
            )
        print(e["id"], len(sy), flush=True)
    for art, z in listen.items():
        (ordner / f"{art}.jsonl").write_text(
            "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in z),
            encoding="utf-8",
        )
        print(art, len(z))


def probe_abschnitte(n_pruef=4, je=3):
    """Prüfmenge zusätzlich als Abschnitte zu je 3 Systemen (Rest an den letzten Abschnitt).
    Dieselben 45 Seiten wie probe(); Ausgabe daten/seiten/probe/abschnitte.jsonl."""
    import random

    import numpy as np

    alle = jsonl(AUS / "seiten.jsonl")
    wahl = [e for e in alle if not e["grund"] and e["split"] in ("validation", "test")]
    pr = [e for e in pruef_seiten() if not e["grund"]]
    rng = random.Random(0)
    for q in dict.fromkeys(e["quelle"] for e in pr):
        wahl += rng.sample([e for e in pr if e["quelle"] == q], n_pruef)
    assert {e["id"] for e in wahl} == {
        z["seite"] for z in jsonl(AUS / "probe/seiten.jsonl")
    }, "andere Seiten als im Lesetest"
    aus = []
    for e in wahl:
        im = Image.open(e["bild"]).convert("RGB")
        gruen = np.asarray(im)[:, :, 1]
        z = zeile_von(e)
        n = len(e["systeme"])
        starts, i = [], 0
        while i < n:
            starts.append(i)
            i = zeilenrand(z, i, min(i + je, n) - 1)[1] + 1
        if len(starts) > 1 and n - starts[-1] < 2:
            starts.pop()
        for nr, (i, j) in enumerate(zip(starts, [*[s - 1 for s in starts[1:]], n - 1])):
            t = e["systeme"][i : j + 1]
            name = f"{e['id'].replace('/', '_')}_a{nr}"
            pfad = AUS / "probe/bilder" / f"{name}.jpg"
            # wie im Training auf 1.540 px: breitere Bilder zerlegt bildform("streifen") in zwei
            # gestapelte Hälften, dann liest das Modell erst alle linken, dann alle rechten Teile
            kleiner(abschnitt(e, im, gruen, i, j)).save(pfad, quality=92)
            ref = (
                {"ziel": "\n".join(s["ziel"] for s in t)}
                if "ziel" in t[0]
                else {"label": [s["label"] for s in t]}
            )
            aus.append(
                {
                    "id": f"{e['id']}/a{nr}",
                    "seite": e["id"],
                    "quelle": e["quelle"],
                    "split": e["split"],
                    "nr": nr,
                    "von": i,
                    "bis": j,
                    "bild": str(pfad.relative_to(HIER)),
                }
                | ref
            )
    (AUS / "probe/abschnitte.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in aus),
        encoding="utf-8",
    )
    print("abschnitte", len(aus))


def laeufe(flags):
    """(Anfang, Länge) jeder Folge von True."""
    aus, start = [], None
    for i, f in enumerate([*flags, False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            aus.append((start, i - start))
            start = None
    return aus


def kleiner(im, kante=MAX_KANTE):
    """Auf höchstens kante längste Kante; das Modell skaliert ohnehin dorthin."""
    k = kante / max(im.size)
    if k >= 1:
        return im
    return im.resize(
        (round(im.width * k), round(im.height * k)), Image.Resampling.LANCZOS
    )


def trainmenge(n_abschnitte=2000, seed=0, name="train", seiten=None):
    """Mehrsystem-Trainingsbeispiele aus train-Systemen: Abschnitte mit 2-4 aufeinanderfolgenden
    vollen Systemen (je Lauf einer, ab 6 Systemen zwei), dazu ganze train-Seiten und ihre Hälften.
    seiten: Seiteneinträge mit Feld xml (seiten_d.py); dort schließt ein Sprung im Zeilenabstand die Seite aus.
    Ausgabe: daten/seiten/<name>/{train.jsonl,bilder/,pruefbogen_abschnitte.jpg}."""
    import random

    import numpy as np
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(
        str(HIER / "models/LightOnOCR-3-1B-konvertiert/tokenizer.json")
    )
    rng = random.Random(seed)
    seiten = seiten or [
        e for e in jsonl(AUS / "seiten.jsonl") if e["quelle"] in TRANSKRIBUS + OHNE_PAGE
    ]

    def ist_train(e, s):
        sp = s.get("split") if e["quelle"] in OHNE_PAGE else e["split"]
        return s["voll"] and SPLIT.get(sp, sp) == "train"

    plan, ausgeschlossen = [], {}  # (Seite, i, j, art); Seite -> Lückenhinweise
    for e in seiten:
        flags = [ist_train(e, s) for s in e["systeme"]]
        n = len(flags)
        if not any(r >= 2 for _, r in laeufe(flags)):
            continue
        nur_abschnitte = False
        if "xml" in e and (hinweise := abstaende(e)):  # möglicherweise fehlendes System
            ausgeschlossen[e["id"]] = hinweise
            continue
        if e["quelle"] in OHNE_PAGE:
            hinweise = luecken(e, Image.open(e["bild"]).convert("RGB"))
            # Erkennungsquellen: Kamm-Treffer außerhalb der Kästen sind dort meist rote Rubriken oder
            # Linierung (Sichtprüfung a-kn-1018 026v/042r, ch-p-18 123). Ein fehlendes System innerhalb
            # eines Abschnitts zeigt sich als Sprung im Zeilenabstand; Ränder schneiden Abschnitte weg.
            # Darum dort nur Abstandssprünge ausschließen, Kamm-Treffer sperren nur Seiten und Hälften.
            nur_abschnitte = (
                bool(hinweise)
                and e["quelle"] in ERKENNUNG
                and all(h.startswith("system_bei") for h in hinweise)
            )
            if (
                hinweise and not nur_abschnitte
            ):  # Systemliste unvollständig: ganze Seite raus
                ausgeschlossen[e["id"]] = hinweise
                continue
            if hinweise:
                ausgeschlossen[e["id"]] = ["nur_abschnitte", *hinweise]
        z = zeile_von(e)
        if not e["grund"] and all(flags) and not nur_abschnitte:
            k = zeilenrand(z, n // 2, n // 2)[0]
            plan.append((e, 0, n - 1, "seite"))
            if k:
                plan += [(e, 0, k - 1, "haelfte"), (e, k, n - 1, "haelfte")]
        for a, r in laeufe(flags):
            for _ in range(1 if r < 6 else 2) if r >= 2 else ():
                k = min(r, rng.choice((2, 3, 4)))
                i = a + rng.randrange(r - k + 1)
                i, j = zeilenrand(
                    z, i, i + k - 1
                )  # nie zwischen Kästen einer Zeile schneiden
                if all(flags[i : j + 1]):
                    plan.append((e, i, j, "abschnitt"))
    ab = [p for p in plan if p[3] == "abschnitt"]
    rest = [p for p in plan if p[3] != "abschnitt"]
    plan = rest + rng.sample(ab, min(n_abschnitte, len(ab)))
    plan.sort(key=lambda p: p[0]["id"])  # jede Seite nur einmal laden
    ordner = AUS / name
    (ordner / "bilder").mkdir(parents=True, exist_ok=True)
    aus, bild_von = [], None
    for e, i, j, art in plan:
        if bild_von != e["id"]:
            im = Image.open(e["bild"]).convert("RGB")
            gruen = np.asarray(im)[:, :, 1]
            bild_von = e["id"]
        if art == "seite":
            b = im
        else:  # Hälften bis an den Seitenrand wie im Lesetest, Abschnitte nicht
            b = abschnitt(e, im, gruen, i, j, rand=art == "abschnitt")
        name = f"{e['id'].replace('/', '_')}_{i:02d}-{j:02d}"
        pfad = ordner / "bilder" / f"{name}.jpg"
        kleiner(b).save(pfad, quality=92)
        ziel = "\n".join(s["ziel"] for s in e["systeme"][i : j + 1])
        aus.append(
            {
                "id": f"{e['id']}/{i:02d}-{j:02d}",
                "quelle": e["quelle"],
                "split": "train",
                "art": art,
                "n_systeme": j - i + 1,
                "bild": str(pfad.relative_to(HIER)),
                "ziel": ziel,
                "token": len(tok.encode(ziel, add_special_tokens=False).ids) + 1,
            }
        )
    rng.shuffle(aus)
    (ordner / "train.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in aus),
        encoding="utf-8",
    )
    bericht = {
        art: {
            "beispiele": len(v := [x for x in aus if x["art"] == art]),
            "systeme": sum(x["n_systeme"] for x in v),
            "quellen": dict(Counter(x["quelle"] for x in v)),
            "token_median_max": [
                st.median(x["token"] for x in v),
                max(x["token"] for x in v),
            ],
        }
        for art in ("abschnitt", "haelfte", "seite")
    }
    ganz = {k: v for k, v in ausgeschlossen.items() if v[0] != "nur_abschnitte"}
    bericht["ausgeschlossene_seiten"] = {
        "zahl": len(ganz),
        "je_quelle": dict(Counter(k.split("/")[0] for k in ganz)),
        "nur_abschnitte": dict(
            Counter(k.split("/")[0] for k in ausgeschlossen if k not in ganz)
        ),
    }
    (ordner / "ausgeschlossen.json").write_text(
        json.dumps(ausgeschlossen, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (ordner / "bericht.json").write_text(
        json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(bericht, ensure_ascii=False, indent=1))
    pruefbogen([x for x in aus if x["art"] == "abschnitt"], ordner, seed)


def pruefbogen(zeilen, ordner, seed=0, n=10):
    """Bild und Ziel (eine Zeile je System, umbrochen) untereinander, zum Abgleich von Hand."""
    import random
    import textwrap

    from PIL import ImageDraw, ImageFont

    schrift = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
    teile = []
    for z in random.Random(seed).sample(zeilen, min(n, len(zeilen))):
        im = Image.open(HIER / z["bild"]).convert("RGB")
        im = im.resize((1400, int(im.height * 1400 / im.width)))
        text = [z["id"]]
        for k, zeile in enumerate(z["ziel"].split("\n"), 1):
            text += textwrap.wrap(f"{k}: " + zeile.replace("<m>", ""), 140)
        leiste = Image.new("RGB", (1400, 22 * len(text) + 12), "white")
        dr = ImageDraw.Draw(leiste)
        for i, t in enumerate(text):
            dr.text(
                (6, 4 + 22 * i),
                t,
                fill=(160, 0, 0) if i == 0 else "black",
                font=schrift,
            )
        teile += [im, leiste, Image.new("RGB", (1400, 14), (120, 120, 120))]
    o = Image.new("RGB", (1400, sum(t.height for t in teile)), "white")
    y = 0
    for t in teile:
        o.paste(t, (0, y))
        y += t.height
    o.save(ordner / "pruefbogen_abschnitte.jpg", quality=85)


if __name__ == "__main__":
    k = [(0, 300, 500, 400), (0, 100, 300, 200), (310, 90, 600, 210)]
    assert reihenfolge(k) == [1, 2, 0]
    assert ueberlappt((0, 100, 500, 200), (10, 110, 400, 190))
    assert not ueberlappt((0, 100, 500, 200), (0, 300, 500, 400))
    assert laeufe([1, 1, 0, 1, 0, 1, 1, 1]) == [(0, 2), (3, 1), (5, 3)]
    assert zeilenrand([0, 1, 1, 2, 3, 3], 2, 4) == (1, 5)
    if sys.argv[1:] == ["inventar"]:
        inventar()
    elif sys.argv[1:] == ["aufloesung"]:
        aufloesung()
    elif sys.argv[1:] == ["probe"]:
        probe()
    elif sys.argv[1:2] == ["train"]:  # seiten.py train [Ordner [Abschnitte]]
        trainmenge(
            n_abschnitte=int(sys.argv[3]) if len(sys.argv) > 3 else 2000,
            name=sys.argv[2] if len(sys.argv) > 2 else "train",
        )
    elif sys.argv[1:] == ["probe_abschnitte"]:
        probe_abschnitte()
