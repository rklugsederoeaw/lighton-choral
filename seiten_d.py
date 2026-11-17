"""Trainingslisten für seiten_d (AUFTRAG_2.md): seiten_c plus korpus_graz14 (Gold, train) und Silber.

    python seiten_d.py            # Listen bauen (Silber, sobald daten/korpus_silber/train.jsonl vorliegt)
    python seiten_d.py test       # Selbsttest der Regeln 1, 3 und 5

Die Listen von seiten_c (daten/seiten/c/) gehen unverändert ein. Neu in daten/seiten/d/:
graz14.jsonl (korpus_graz14 train), silber_hs.jsonl (Silber-Handschriften, beide Klassen, ungedeckelt),
silber_druck.jsonl (Silber-Drucke nur Klasse doppelt, höchstens 1.500, gleichmäßig über die Drucke, fester Seed),
mehrsystem/train.jsonl (Abschnitte, Hälften, Seiten aus Graz14-Gold und Silber-Handschriften), bericht.json.
Mehrsystem-Beispiele nur aus lückenlos aufeinanderfolgenden Systemen, die alle in der Trainingsmenge sind; die
Systemfolge einer Seite kommt aus der PAGE-XML (alle Notationsregionen), nicht aus der Korpusliste. Silber-Systeme,
die auf Seite und Kasten einem Gold-System entsprechen, fallen weg (Gold geht vor; bei val/test Pflicht).
Prüfhandschriften: Assertion über alle Listen der Epoche. F-Schlüssel: ohne Verdopplung; liegt der Anteil der
Zeilen mit F-Anfangsschlüssel unter 24 %, werden F-Beispiele von Graz14 und Silber-Handschriften verdoppelt.
"""

import functools
import json
import os
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

from metriken import sicht
from seiten import (
    AUS,
    BASIS,
    GABC,
    NS,
    PRUEF,
    jsonl,
    regionen,
    seite_eintrag,
    trainmenge,
    ueberlappt,
    wurzel_von,
    zeilen_bilden,
)

HIER = Path(__file__).resolve().parent
D = AUS / os.environ.get(
    "SEITEN_D", "d"
)  # Probeläufe in einen anderen Ordner unter daten/seiten
TEXT_GT = HIER / "daten/text_gt"
SILBER = Path(os.environ.get("SILBER", HIER / "daten/korpus_silber/train.jsonl"))
# Transkribus-Export der Chorbücher (PAGE-XML je Band unter <Band>/page_xml)
CHORBUCH = Path(os.environ.get("CHORBUCH", HIER / "daten/chorbuch_text_gt"))
C_LISTEN = ("gabc_c", "transkribus_c", "graz_c", "mehrsystem_c")
DRUCK_MAX = 1500
# w3:p1R 14.11. (nach dem Signal zu seiten_c): ganze Seiten und Hälften dreifach in der Epochenliste (alte und
# neue Mehrsystem-Blöcke), Abschnitte einfach; 3/2 ergab 26,1 % Mehrsystem (< 27 %), 3/3 entschieden
GEWICHT = dict(
    zip(
        ("seite", "haelfte"),
        map(int, os.environ.get("SEITEN_GEWICHT", "3,3").split(",")),
    )
)
F_MIN = 0.24
# Prüfhandschriften auch unter Band- und Ordnernamen (A-Geras 6, A-KN_65, A-Wn15484, A-Gu_17, A-VOR_254)
PRUEF_MUSTER = re.compile(
    r"geras.?6|kn.?65(?!\d)|wn.?15484|gu.?17(?!\d)|vor.?254", re.I
)


def pruef_frei(z):
    felder = " ".join(
        str(z.get(k, ""))
        for k in ("id", "quelle", "bild", "band", "seitenbild", "pagexml")
    )
    assert z.get("quelle") not in PRUEF and not PRUEF_MUSTER.search(felder), (
        f"Prüfhandschrift im Training: {z.get('id')}"
    )


def hat_f(ziel):
    return any(k.startswith("f") for k in sicht(ziel)["schl"])


def f_zeilen(zs):
    """(Zeilen mit F-Anfangsschlüssel, Zeilen)."""
    f = n = 0
    for z in zs:
        for zeile in z["ziel"].split("\n"):
            s = sicht(zeile)["schl"]
            n += 1
            f += bool(s) and s[0].startswith("f")
    return f, n


def schluessel(bild):
    """Seite = Seitenbild (aufgelöster Pfad; w3:p1R 14.11.: Systeme derselben Seite über seitenbild gruppieren)."""
    return str(Path(bild).resolve())


def gold_systeme():
    """Seitenschlüssel -> [(Kasten, split, id)] aller Gold-Systeme (korpus_graz, korpus_graz14, korpus_transkribus);
    region: quelle -> zid -> Zeile aus zeilen.jsonl, mit _bild (Pfad des Seitenbilds)."""
    region = {}

    def zeilen(q):
        if q not in region:
            # text_gt: Pfad relativ zu diesem Ordner (nmp/... oder absolut); cantus_gabc: relativ zu volpiano2omr_gt
            for o, wurzel in ((TEXT_GT / q, HIER), (GABC / q, BASIS)):
                if (o / "zeilen.jsonl").exists():
                    region[q] = {
                        z["id"]: z | {"_bild": wurzel / z["seite"]}
                        for z in jsonl(o / "zeilen.jsonl")
                    }
                    break
            else:
                raise FileNotFoundError(f"zeilen.jsonl für {q}")
        return region[q]

    aus = defaultdict(list)
    for k in ("korpus_graz", "korpus_graz14", "korpus_transkribus"):
        for t in ("train", "validation", "test"):
            for z in jsonl(HIER / f"daten/{k}/{t}.jsonl"):
                zid = z["id"].split("/")[-1]
                g = zeilen(z["quelle"])[zid]
                aus[schluessel(g["_bild"])].append((g["region"], t, z["id"]))
    return aus, region


def innen(a, b):
    """Liegt Region a in b (mit etwas Spiel)? Wie korpus_graz14.innen."""
    return (
        a[0] >= b[0] - 5 and a[1] >= b[1] - 5 and a[2] <= b[2] + 5 and a[3] <= b[3] + 5
    )


def zweifel_raus(graz14, region):
    """Gold-Systeme mit zweifelhafter GT (daten/gold_zweifel_graz14.jsonl, w3:p1R 14.11.) entfernen: ein
    Korpussystem fällt weg, wenn eine seiner Indexzeilen (Regionen im System) mit quelle und index_id in der
    Liste steht. -> (behaltene, entfernte ids, Seitenschlüssel -> Kästen aller Listeneinträge für den Silberabgleich)."""
    zw = {
        (z["quelle"], z["index_id"])
        for z in jsonl(HIER / "daten/gold_zweifel_graz14.jsonl")
    }
    index = {}
    raus = set()
    kaesten = defaultdict(
        list
    )  # Indexzeilen haben kein Seitenbild: über eine Zeile derselben Seite
    for q, i in sorted(zw):
        r = next(x for x in jsonl(TEXT_GT / q / "music/index.jsonl") if x["id"] == i)
        g = next(z for z in region[q].values() if z["id"][:4] == i[:4])
        kaesten[schluessel(g["_bild"])].append(r["region"])
    for z in graz14:
        q, zid = z["quelle"], z["id"].split("/")[-1]
        if q not in index:
            index[q] = jsonl(TEXT_GT / q / "music/index.jsonl")
        reg = region[q][zid]["region"]
        if any(
            (q, r["id"]) in zw
            for r in index[q]
            if r["id"][:4] == zid[:4] and innen(r["region"], reg)
        ):
            raus.add(z["id"])
    return [z for z in graz14 if z["id"] not in raus], raus, kaesten


def seiteninfo():
    """Silber-Kandidaten (daten/silber/*liste*.jsonl): quelle/zid -> Seitenbild, PAGE-XML, Notationskasten."""
    info = {}
    for p in sorted((HIER / "daten/silber").glob("*liste*.jsonl")):
        for z in jsonl(p):
            info.setdefault(z["id"], z)
    return info


ORT = ("notation_box", "seitenbild", "pagexml")


def ort(z, info):
    """(Seitenschlüssel, Kasten, Seitenbild, PAGE-XML, aus_liste) eines Silber-Systems oder None.
    Felder aus korpus_silber/train.jsonl; nur wenn eins fehlt, aus den Kandidatenlisten (aus_liste=True)."""
    zid = z["id"].split("/")[-1]
    i = z if all(k in z for k in ORT) else info.get(f"{z['quelle']}/{zid}")
    if i is None:
        return None
    return (schluessel(i["seitenbild"]), *(i[k] for k in ORT), i is not z)


@functools.cache
def xml_je_bild(band):
    """Seitenbild -> PAGE-XML eines Chorbuch-Bandes über imageFilename (Dateinummer weicht von der Seiten-ID ab,
    gf6437: Seite 0057 steht in page_xml/0055.xml)."""
    aus = {}
    for x in (CHORBUCH / band / "page_xml").glob("*.xml"):
        p = ET.parse(x).getroot().find(NS + "Page")
        aus[p.get("imageFilename")] = x
    return aus


def xml_fuer(seitenbild):
    b = Path(seitenbild)
    return xml_je_bild(b.parent.name).get(b.name)


def druck_auswahl(drucke, n_max=DRUCK_MAX, seed=0):
    """Gleichmäßig über die Drucke: kleine Drucke ganz, der Rest zu gleichen Teilen (fester Seed)."""
    je = defaultdict(list)
    for z in drucke:
        je[z["quelle"]].append(z)
    rng, aus, rest = random.Random(seed), [], n_max
    for i, q in enumerate(sorted(je, key=lambda q: len(je[q]))):
        k = min(len(je[q]), rest // (len(je) - i))
        aus += rng.sample(sorted(je[q], key=lambda z: z["id"]), k)
        rest -= k
    return aus


def silber_filtern(silber, gold, info, zweifel=None):
    """Regel 1, 2, 5: Prüfhandschriften (Assertion), Gold-Dubletten raus, Drucke nur doppelt und gedeckelt."""
    zahl, hs, dr = Counter(), [], []
    for z in silber:
        pruef_frei(z)
        if z.get("training") is False:  # von text_claude nicht fürs Training vorgesehen
            zahl["training_false"] += 1
            continue
        if z.get("gold_zweifel"):
            zahl["gold_zweifel_feld"] += 1
            continue
        o = ort(z, info)
        if o is None:
            zahl["ohne_seiteninfo"] += 1
        else:
            zahl["seiteninfo_aus_liste"] += o[4]
            pruef_frei({"id": z["id"], "seitenbild": o[2], "pagexml": o[3]})
            if any(ueberlappt(o[1], b) for b in (zweifel or {}).get(o[0], [])):
                zahl["gold_zweifel_kasten"] += 1  # gold_zweifel_graz14.jsonl
                continue
            treffer = [t for b, t, _ in gold.get(o[0], []) if ueberlappt(o[1], b)]
            if treffer:
                zahl[
                    "gleich_gold_" + ("train" if "train" in treffer else "valtest")
                ] += 1
                continue
            if any(t != "train" for _, t, _ in gold.get(o[0], [])):
                zahl["auf_gold_valtest_seite"] += 1  # w3:p1R 14.11.: ganze Seite raus
                continue
        if z["druck"]:
            if z["klasse"] == "doppelt":
                dr.append(z)
            else:
                zahl["druck_modell_raus"] += 1
        else:
            hs.append(z)
            zahl["hs_" + z["klasse"]] += 1
            zahl["hs_striche_unsicher"] += bool(z.get("striche_unsicher"))
    zahl["druck_doppelt"] = len(dr)
    dr = druck_auswahl(dr)
    zahl |= {
        f"druck_gewaehlt_{q}": n for q, n in Counter(z["quelle"] for z in dr).items()
    }
    return hs, dr, zahl


def seiten_bauen(gold, hs, info, region):
    """Seiteneinträge (seiten.py-Format) der Seiten mit Trainingssystemen; Systemfolge aus der PAGE-XML.
    gold: Handschriften-Systeme aus korpus_graz14 und korpus_graz (train); hs: Silber-Handschriften."""
    je = defaultdict(list)  # Seitenschlüssel -> Systeme der Trainingsmenge
    zahl = Counter()
    for z in gold:
        b = region[z["quelle"]][z["id"].split("/")[-1]]["_bild"]
        x = xml_fuer(b) or b.parent / "page" / (b.stem + ".xml")
        je[schluessel(b)].append(
            (region[z["quelle"]][z["id"].split("/")[-1]]["region"], z, str(b), x)
        )
    for z in hs:
        if o := ort(z, info):
            # Chorbuch-Bände: imageFilename-Zuordnung als Gegenprobe; sonst (Aldersbach) die mitgegebene PAGE-XML
            x = xml_fuer(o[2]) or Path(o[3])
            zahl["pagexml_abweichend"] += x != Path(o[3])
            je[o[0]].append((o[1], z, o[2], x))
    seiten, ids = [], set()
    for k, items in sorted(je.items()):
        assert len({i[3] for i in items}) == 1, k  # eine PAGE-XML je Seitenbild
        assert len({i[1]["quelle"] for i in items}) == 1, k
        xml = items[0][3]
        q = items[0][1]["quelle"]
        s = items[0][1]["id"].split("/")[-1][:4]
        if f"{q}/{s}" in ids:  # Seitennummer der ID nicht eindeutig: Bildname
            s = Path(items[0][2]).stem
        ids.add(f"{q}/{s}")
        w = wurzel_von(xml) if xml.exists() else None
        reihen = zeilen_bilden(regionen(w, "notation")) if w is not None else []
        if not reihen:
            zahl["keine_pagexml"] += 1
            continue
        systeme, grund, benutzt = [], "", set()
        for r in reihen:
            tr = [i for i, x in enumerate(items) if ueberlappt(r[:4], x[0])]
            sy = {"kasten": list(r[:4]), "d": r[4] / 3.5, "voll": len(tr) == 1}
            if len(tr) == 1:
                sy |= {
                    "id": items[tr[0]][1]["id"],
                    "ziel": items[tr[0]][1]["ziel"].strip(),
                }
            else:
                grund = grund or ("system_fehlt" if not tr else "system_doppelt")
            benutzt |= set(tr)
            systeme.append(sy)
        if len(benutzt) != len(items):
            grund = grund or "zeile_ohne_system"
            zahl["zeile_ohne_system"] += 1
        pruef_frei({"id": f"{q}/{s}", "seitenbild": items[0][2], "pagexml": str(xml)})
        seiten.append(
            seite_eintrag(
                q, s, str(items[0][2]), systeme, grund, "train", {"xml": str(xml)}
            )
        )
        zahl["seiten"] += 1
        zahl["vollstaendig"] += not grund
    return seiten, zahl


def pruefe_mehrsystem(beispiele, seiten):
    """Regel 3 am Ergebnis: jedes Beispiel = lückenlose Folge voller Systeme; ganze Seite nur ohne Lücke."""
    von = {e["id"]: e for e in seiten}
    for b in beispiele:
        sid, ij = b["id"].rsplit("/", 1)
        i, j = map(int, ij.split("-"))
        e = von[sid]
        assert all(s["voll"] for s in e["systeme"][i : j + 1]), b["id"]
        assert b["ziel"] == "\n".join(s["ziel"] for s in e["systeme"][i : j + 1]), b[
            "id"
        ]
        if b["art"] == "seite":
            assert not e["grund"] and i == 0 and j == len(e["systeme"]) - 1, b["id"]


def schreib(p, zs):
    p.write_text(
        "".join(json.dumps(z, ensure_ascii=False) + "\n" for z in zs), encoding="utf-8"
    )


def main():
    D.mkdir(parents=True, exist_ok=True)
    gold, region = gold_systeme()
    info = seiteninfo()
    graz14, zweifel, zweifel_kaesten = zweifel_raus(
        jsonl(HIER / "daten/korpus_graz14/train.jsonl"), region
    )
    graz_hs = [
        z for z in jsonl(HIER / "daten/korpus_graz/train.jsonl") if not z["druck"]
    ]
    silber = jsonl(SILBER) if SILBER.exists() else []
    hs, dr, zahl_silber = silber_filtern(silber, gold, info, zweifel_kaesten)
    seiten, zahl_seiten = seiten_bauen(graz14 + graz_hs, hs, info, region)
    shutil.rmtree(
        D / "mehrsystem", ignore_errors=True
    )  # keine alten Bilder im Manifest
    trainmenge(10**6, seed=0, name=f"{D.name}/mehrsystem", seiten=seiten)
    mehr = jsonl(D / "mehrsystem/train.jsonl")
    pruefe_mehrsystem(mehr, seiten)
    # Zweifels-Systeme weder einzeln noch in Mehrsystem-Seiten (dort Lücke; Silber auf dem Kasten fällt als
    # gleich_gold_train weg, weil gold_systeme alle Korpussysteme kennt)
    assert not zweifel & {s.get("id") for e in seiten for s in e["systeme"]}

    alt = {n: jsonl(AUS / f"c/{n}.jsonl") for n in C_LISTEN}
    alt["systeme_c"] = [
        z for z in jsonl(AUS / "c/systeme_c.jsonl") if z["split"] == "train"
    ]
    neu = {"graz14": graz14, "silber_hs": hs, "silber_druck": dr, "mehrsystem": mehr}
    for blk, k in ((alt, "mehrsystem_c"), (neu, "mehrsystem")):
        blk[k] = [z for z in blk[k] for _ in range(GEWICHT.get(z["art"], 1))]

    def epoche():
        return [z for zs in (*alt.values(), *neu.values()) for z in zs]

    f, n = f_zeilen(epoche())
    bericht = {"f_anteil_ohne_verdopplung": round(f / n, 4)}
    if f / n < F_MIN:
        for k in ("graz14", "silber_hs"):
            neu[k] = neu[k] + [z for z in neu[k] if hat_f(z["ziel"])]
        f, n = f_zeilen(epoche())
        bericht["f_anteil_mit_verdopplung"] = round(f / n, 4)
    for z in epoche():
        pruef_frei(z)
    # Regel 5 am Ergebnis: kein Silber-System auf einer Seite mit val/test-Gold-System
    for z in neu["silber_hs"] + neu["silber_druck"]:
        if o := ort(z, info):
            assert all(t == "train" for _, t, _ in gold.get(o[0], [])), z["id"]
    for k in ("graz14", "silber_hs", "silber_druck"):
        schreib(D / f"{k}.jsonl", neu[k])
    # alle Mehrsystem-Beispiele der Epoche, gewichtet (ersetzt mehrsystem_c und mehrsystem/train.jsonl im Jobskript)
    schreib(D / "mehrsystem_d.jsonl", alt["mehrsystem_c"] + neu["mehrsystem"])
    # Mehrsystem-Beispiele mit Silber-Systemen; Rauchtest: je ein Beispiel der neuen Blöcke, Mehrsystem mit Silber
    sil = {z["id"] for z in hs}
    von = {e["id"]: e for e in seiten}

    def mit_silber(b):
        sid, ij = b["id"].rsplit("/", 1)
        i, j = map(int, ij.split("-"))
        return any(s.get("id") in sil for s in von[sid]["systeme"][i : j + 1])

    mehr_silber = [b for b in mehr if mit_silber(b)]
    schreib(
        D / "smoke.jsonl",
        [zs[0] for zs in (graz14, hs, dr) if zs]
        + (mehr_silber or [b for b in mehr if b["art"] == "abschnitt"])[:1],
    )

    ep = epoche()
    druck = sum(bool(z.get("druck")) for z in ep)
    bericht |= {
        "beispiele_je_epoche": len(ep),
        "je_block": {k: len(v) for k, v in (*alt.items(), *neu.items())},
        "gewicht": GEWICHT,
        "mehrsystem_anteil": round(
            (len(neu["mehrsystem"]) + len(alt["mehrsystem_c"])) / len(ep), 4
        ),
        "mehrsystem_anteil_zeichen": round(
            sum(len(z["ziel"]) for z in ep if "art" in z)
            / sum(len(z["ziel"]) for z in ep),
            4,
        ),
        "mehrsystem_je_art_gewichtet": dict(
            Counter(z["art"] for z in alt["mehrsystem_c"] + neu["mehrsystem"])
        ),
        "mehrsystem_neu_je_art": dict(Counter(z["art"] for z in mehr)),
        "mehrsystem_neu_je_quelle": dict(Counter(z["quelle"] for z in mehr)),
        "mehrsystem_neu_mit_silber": len(mehr_silber),
        "f_zeilen": [f, n, round(f / n, 4)],
        "drucke_anteil": round(druck / len(ep), 4),
        "drucke": druck,
        "graz14_zweifel_raus": len(zweifel),
        "silber": dict(zahl_silber),
        "seiten_neu": dict(zahl_seiten),
    }
    (D / "bericht.json").write_text(
        json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(bericht, ensure_ascii=False, indent=1))


def selbsttest():
    # Regel 1: kleine Drucke ganz, Rest gleichmäßig, höchstens 1.500, nur Klasse doppelt
    dr = [
        {
            "id": f"{q}/{i:04d}_01",
            "quelle": q,
            "druck": True,
            "klasse": k,
            "ziel": "(<m>c<m>4)",
        }
        for q, n in (("druck65", 3000), ("druck67", 2500), ("druck72", 300))
        for i in range(n)
        for k in ("doppelt", "modell")
    ]
    _, aus, zahl = silber_filtern(dr, {}, {})
    c = Counter(z["quelle"] for z in aus)
    assert (
        len(aus) == DRUCK_MAX
        and c["druck72"] == 300
        and c["druck65"] == c["druck67"] == 600
    ), c
    assert (
        all(z["klasse"] == "doppelt" for z in aus) and zahl["druck_modell_raus"] == 5800
    )
    assert aus == silber_filtern(dr, {}, {})[1], "Stichprobe nicht fest"
    # Regel 5: Prüfhandschrift bricht ab; Silber auf einer val/test-Seite fällt weg (jeder Kasten), Silber auf
    # anderer Seite bleibt; Seiteninfo aus dem System, Rückfall auf die Liste wird gezählt
    for z in (
        {"id": "kn65/0001_01", "quelle": "kn65"},
        {
            "id": "x/0001_01",
            "quelle": "x",
            "bild": "daten/silber/A-Wn15484_OFM/0001_01.jpg",
        },
    ):
        try:
            silber_filtern(
                [z | {"druck": False, "klasse": "doppelt", "ziel": ""}], {}, {}
            )
            raise SystemExit(f"Prüfhandschrift nicht abgefangen: {z}")
        except AssertionError:
            pass
    ort_ = {"seitenbild": "s.jpg", "pagexml": "p.xml"}
    info = {
        "gf6351/0004_01": {
            "notation_box": [0, 0, 100, 50],
            "seitenbild": "t.jpg",
            "pagexml": "p.xml",
        }
    }
    gold = {schluessel("s.jpg"): [([0, 0, 100, 50], "validation", "g")]}
    sil = [
        {
            "id": f"gf6351/silber/{i}",
            "quelle": "gf6351",
            "druck": False,
            "klasse": "modell",
            "ziel": "",
        }
        | ({"notation_box": b} | ort_ if b else {})
        for i, b in (
            ("0003_01", [0, 0, 100, 50]),
            ("0003_02", [0, 200, 100, 250]),
            ("0004_01", None),
        )
    ]
    hs, _, zahl = silber_filtern(sil, gold, info)
    assert [z["id"] for z in hs] == ["gf6351/silber/0004_01"], hs
    assert (
        zahl["gleich_gold_valtest"]
        == zahl["auf_gold_valtest_seite"]
        == zahl["seiteninfo_aus_liste"]
        == 1
    ), zahl
    # Zweifelsliste und Feld gold_zweifel: Silber auf dem Kasten fällt weg
    hs, _, zahl = silber_filtern(
        [sil[0], sil[1] | {"id": "gf6351/silber/0003_09", "gold_zweifel": True}],
        {},
        info,
        {schluessel("s.jpg"): [[0, 0, 100, 50]]},
    )
    assert not hs and zahl["gold_zweifel_kasten"] == zahl["gold_zweifel_feld"] == 1, (
        zahl
    )
    # Regel 3: Lücke in der Systemfolge -> kein Beispiel über die Lücke, keine ganze Seite
    e = {
        "id": "q/0001",
        "grund": "system_fehlt",
        "systeme": [
            {"voll": True, "ziel": "a"},
            {"voll": False},
            {"voll": True, "ziel": "b"},
        ],
    }
    for b in (
        {"id": "q/0001/00-02", "art": "abschnitt", "ziel": "a\n\nb"},
        {"id": "q/0001/00-02", "art": "seite", "ziel": "a\n\nb"},
    ):
        try:
            pruefe_mehrsystem([b], [e])
            raise SystemExit(f"Lücke nicht abgefangen: {b}")
        except (AssertionError, KeyError):
            pass
    pruefe_mehrsystem([{"id": "q/0001/02-02", "art": "abschnitt", "ziel": "b"}], [e])
    print("Selbsttest Regeln 1, 3, 5: in Ordnung")


if __name__ == "__main__":
    selbsttest() if sys.argv[1:] == ["test"] else main()
