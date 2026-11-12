"""Paare aus Systemausschnitt und silbenweise verschränktem Ziel für eine CantusDB-Quelle.

    python korpus_cantus.py d-ka-aug-lx fcc-0002 ...

Quelle der Noten: geometrische Fassung der Pipeline (review/results_<quelle>.json), Text: fulltext_ms
der CantusDB. Eine Zeile bleibt nur, wenn ihre Töne genau der geprüften GT entsprechen. Systeme mit
fremder Notenlinie am unteren Rand oder angeschnittenem Text werden verworfen.
"""

import json
import random
import sys
import re
import sqlite3
import textwrap
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from silben_cantus import DB, NOTE, silben, text_woerter
from vergleich_gt import LAGE, toene

HIER = Path(__file__).resolve().parent
PROJEKT = HIER.parents[1]
NOTE_TOK = re.compile(r"^(b_|na_)?([lz]-?\d)(_liq)?$")


def spannen(v):
    """Silben mit Noten: (Anfang, Ende, Wortnummer, Silbennummer in diesem Wort)."""
    aus = []
    wort = -1
    for mw in re.finditer(r"[^-]+(?:-{1,2}[^-]+)*", v):
        if not NOTE.search(mw[0]):
            continue
        wort += 1
        silbe = 0
        for ms in re.finditer(r"[^-]+(?:-[^-]+)*", mw[0]):
            if NOTE.search(ms[0]):
                aus.append(
                    (mw.start() + ms.start(), mw.start() + ms.end(), wort, silbe)
                )
                silbe += 1
    return aus


def silbentexte(wort):
    """Silben in der Schreibung der Handschrift (Großschreibung bleibt)."""
    buchstaben = re.sub(r"[^\w]|\d|_", "", wort)
    if buchstaben.lower().replace("v", "u") == "euouae":
        return list(buchstaben)  # Differenz: jeder Vokal eine Silbe
    teile = silben(wort)
    if sum(map(len, teile)) != len(buchstaben):
        return None
    aus, p = [], 0
    for t in teile:
        aus.append(buchstaben[p : p + len(t)])
        p += len(t)
    return aus


def abschnitte(v):
    """Bereiche (a, b) von v zwischen den Abschnittsstrichen 3 und 4."""
    aus, a = [], 0
    for m in re.finditer(r"-{3}[34](?=-{3}|$)", v):
        aus.append((a, m.start()))
        a = m.end()
    aus.append((a, len(v)))
    return aus


def silben_index(v, ft):
    """Je Silbe von v: (Anfang, Ende, Text), Text None wo der Abschnitt nicht zum Volltext passt."""
    teile = [t for t in ft.split("|") if t.strip() and not t.strip().startswith("~")]
    aus, i = [], 0
    for a, b in abschnitte(v):
        sp = spannen(v[a:b])
        if not sp:
            continue
        texte = [None] * len(sp)
        je_wort = [sum(1 for x in sp if x[2] == w) for w in range(sp[-1][2] + 1)]
        if i < len(teile):
            w = text_woerter(teile[i])
            st = [silbentexte(x) for x in w]
            if len(w) == len(je_wort) and all(
                x is not None and len(x) == n for x, n in zip(st, je_wort)
            ):
                texte = [st[x[2]][x[3]] for x in sp]
        i += 1
        aus += [(a + x[0], a + x[1], t) for x, t in zip(sp, texte)]
    return aus


def fragmente(zeile, volpianos):
    """Teilt die Zeile an --- in je ein Bruchstück pro Gesang; None wenn das nicht aufgeht."""
    if len(volpianos) == 1:
        return [zeile] if zeile in volpianos[0] else None
    for m in re.finditer(r"-{3}", zeile):
        kopf, rest = zeile[: m.start()].strip("-"), zeile[m.end() :].strip("-")
        if kopf and rest and kopf in volpianos[0]:
            weiter = fragmente(rest, volpianos[1:])
            if weiter is not None:
                return [kopf, *weiter]
    return None


def zeilentexte(fr, v, index):
    """Text je Silbengruppe des Bruchstücks; '' bei fortgesetzter Silbe, None wenn einer fehlt."""
    a = v.find(fr)
    if a < 0 or v.count(fr) > 1:
        return None
    aus = []
    for x in spannen(fr):
        p = a + x[0]
        t = next((s for s in index if s[0] <= p < s[1]), None)
        if t is None or t[2] is None:
            return None
        aus.append(t[2] if t[0] >= a else "")
    return aus


def atome(tok):
    m = NOTE_TOK.match(tok)
    if not m or m[2] not in LAGE:
        return None
    b = LAGE[m[2]]
    aus = []
    if m[1]:
        aus += [b, "x" if m[1] == "b_" else "y"]
    aus.append(b)
    if m[3]:
        aus.append(">")
    return aus


def gruppen_aus_geo(geo):
    """Je Volpiano-Silbe die Noten-Atome, dazu Striche als eigene Gruppen; None bei Unbekanntem."""
    g, aktuell, neu_wort = [], [], True

    def fertig():
        nonlocal aktuell
        if aktuell:
            g.append(("silbe", aktuell, neu_wort_merker[0]))
            neu_wort_merker[0] = False
        aktuell = []

    neu_wort_merker = [neu_wort]
    for t in geo:
        if t in ("div3", "div4"):
            fertig()
            g.append(("strich", [":"], False))
            neu_wort_merker[0] = True
        elif re.fullmatch(r"-{3,}", t):
            fertig()
            neu_wort_merker[0] = True
        elif t == "--":
            fertig()
        elif t == "-":
            if aktuell:
                aktuell.append("!")
        elif t == "lac" or t.startswith("raw_"):
            continue
        elif re.fullmatch(r"[a-g]\d(/[a-g]\d)*", t):
            fertig()
            teile = t.split("/")
            s = next((x for x in teile if x[0] in "cf"), teile[0])
            g.append(("schluessel", list(s), False))
            neu_wort_merker[0] = True
        else:
            a = atome(t)
            if a is None:
                return None
            aktuell += a
    fertig()
    return g


def ziel_bauen(gruppen, texte):
    """gruppen aus gruppen_aus_geo, texte: je Silbengruppe der Text ('' bei fortgesetzter Silbe)."""
    it = iter(texte)
    aus = []
    for art, a, neu in gruppen:
        kern = "<m>" + "<m>".join(a)
        if art == "silbe":
            t = next(it)
            aus.append((" " if neu and aus else "") + t + "(" + kern + ")")
        else:
            aus.append((" " if aus else "") + "(" + kern + ")")
    return "".join(aus)


def linienprofil(gruen, x0, x1):
    """Median der Dunkelheit je Bildzeile im mittleren Drittel: nur durchgehende Linien ragen heraus."""
    breite = x1 - x0
    return np.median(255.0 - gruen[:, x0 + breite // 3 : x1 - breite // 3], axis=1)


def fremde_linie_unten(m, y0, y1, unten, d):
    """Liegt im unteren Rand (1,2 d) eine durchgehende Linie, halb so stark wie die des Systems?"""
    grund = float(np.median(m[y0:y1]))
    spitze = float(m[y0:y1].max())
    rand = m[max(y1, unten - int(1.2 * d)) : unten]
    return rand.size > 0 and float(rand.max()) >= grund + 0.5 * (spitze - grund)


def text_angeschnitten(gruen, x0, x1, y1, unten):
    """Liegt in den letzten Bildzeilen noch Schrift, also Tinte wie im Textstreifen?"""
    breite = x1 - x0
    p = (255.0 - gruen[y1:unten, x0 + breite // 6 : x1 - breite // 6]).mean(axis=1)
    if p.size < 8:
        return True
    p = np.convolve(p, np.ones(3) / 3, mode="same")[1:-1]
    grund = float(np.percentile(p, 10))
    return float(p[-3:].mean()) >= grund + 0.35 * (float(p.max()) - grund)


def main(QUELLE):
    SOURCE_ID = json.loads(
        (PROJEKT / "sources" / f"{QUELLE}.json").read_text(encoding="utf-8")
    )["source_id"]
    R = json.loads(
        (PROJEKT / "review" / f"results_{QUELLE}.json").read_text(encoding="utf-8")
    )
    ids = {
        z.split("\t")[0]
        for z in (PROJEKT / "export" / QUELLE / "meta.tsv")
        .read_text(encoding="utf-8")
        .splitlines()
    }
    d = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    ziel = HIER / "daten/korpus" / QUELLE / "bilder"
    ziel.mkdir(parents=True, exist_ok=True)
    zahl, zeilen = Counter(), []
    for r in R:
        boxen = r["staves"]
        seite, gruen = None, None
        for e in r["assignment"]:
            if e["op"] != "match" or len(e["staves"]) != 1 or len(e["lines"]) != 1:
                continue
            j = e["staves"][0]
            sid = boxen[j]["crop"].removesuffix(".jpg")
            if sid not in ids:
                continue
            zahl["kandidaten"] += 1
            L = r["volpiano_lines"][e["lines"][0]]
            reihen = [
                d.execute(
                    "select fulltext_ms, volpiano from chants where source_id=? and folio=? and sequence=?",
                    (SOURCE_ID, r["folio"], c[0]),
                ).fetchone()
                for c in L["chants"]
            ]
            if any(not z or not z[0] or not z[1] for z in reihen):
                zahl["kein_text"] += 1
                continue
            fr = fragmente(L["volpiano"], [z[1] for z in reihen])
            if fr is None:
                zahl["nicht_eindeutig_im_gesang"] += 1
                continue
            texte, fehlt = [], False
            for f, (ft, v) in zip(fr, reihen):
                t = zeilentexte(f, v, silben_index(v, ft))
                if t is None:
                    fehlt = True
                    break
                texte += t
            if fehlt:
                zahl["silbe_ohne_text"] += 1
                continue
            gr = gruppen_aus_geo(e["geo"])
            if gr is None or sum(x[0] == "silbe" for x in gr) != len(texte):
                zahl["gruppen_passen_nicht"] += 1
                continue
            s = ziel_bauen(gr, texte)
            from metriken import sicht

            if sicht(s)["toene"] != toene(e["gt"][0]):
                zahl["toene_ungleich_gt"] += 1
                continue
            x0, y0, x1, y1 = boxen[j]["box"]
            d_ = r["spacing"]
            if seite is None:
                seite = Image.open(
                    PROJEKT / "images" / QUELLE / f"{r['folio']}.jpg"
                ).convert("RGB")
                gruen = np.asarray(seite)[:, :, 1]
            im = seite
            darunter = [
                b_["box"][1]
                for b_ in boxen
                if b_["box"][1] > y1 - 3 * d_
                and b_["box"][1] > y0 + 2 * d_
                and min(x1, b_["box"][2]) > max(x0, b_["box"][0])
            ]
            oben, unten = (
                y0 + d_,
                min([n + int(1.7 * d_) for n in darunter] + [y1 + 4 * d_]),
            )
            if fremde_linie_unten(linienprofil(gruen, x0, x1), y0, y1, unten, d_):
                zahl["fremde_linie_unten"] += 1
                continue
            if text_angeschnitten(gruen, x0, x1, y1, unten):
                zahl["text_angeschnitten"] += 1
                continue
            pfad = ziel / f"{sid}.jpg"
            im.crop((x0, oben, x1, unten)).save(pfad, quality=92)
            zeilen.append(
                {
                    "id": f"{QUELLE}/{sid}",
                    "quelle": QUELLE,
                    "bild": str(pfad.relative_to(HIER)),
                    "ziel": s,
                    "folio": r["folio"],
                }
            )
            zahl["fertig"] += 1
    (HIER / "daten/korpus" / QUELLE / "systeme.jsonl").write_text(
        "".join(json.dumps(z, ensure_ascii=False) + "\n" for z in zeilen),
        encoding="utf-8",
    )
    print(QUELLE, dict(zahl), flush=True)
    if not zeilen:
        return
    auswahl = random.Random(0).sample(zeilen, min(20, len(zeilen)))
    schrift = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    teile = []
    for z in auswahl:
        im = Image.open(HIER / z["bild"])
        k = 1400 / im.width
        im = im.resize((1400, int(im.height * k)))
        zt = textwrap.wrap(z["ziel"].replace("<m>", ""), 130)
        leiste = Image.new("RGB", (1400, 26 * (len(zt) + 1) + 10), "white")
        dr = ImageDraw.Draw(leiste)
        dr.text((6, 3), z["id"], fill=(160, 0, 0), font=schrift)
        for i, zeile in enumerate(zt):
            dr.text((6, 3 + 26 * (i + 1)), zeile, fill="black", font=schrift)
        teile += [im, leiste]
    o = Image.new("RGB", (1400, sum(t.height for t in teile)), "white")
    y = 0
    for t in teile:
        o.paste(t, (0, y))
        y += t.height
    o.save(HIER / "daten/korpus" / QUELLE / "pruefung_20.jpg", quality=88)


if __name__ == "__main__":
    assert spannen("g--h---kl--l---lmk-kj--h")[2] == (7, 9, 1, 0)
    assert silbentexte("Viam") == ["Vi", "am"]
    assert silbentexte("Euouae") == list("Euouae")
    assert abschnitte("g--h---3---k---4") == [(0, 4), (8, 12), (16, 16)]
    v = "1---g--h---k---3---l--k---m---4---g--g--g--g--g--g---3"
    ix = silben_index(v, "Deus te | Pia nos")
    assert [t for _, _, t in ix][:4] == ["De", "us", "te", "Pi"], ix
    assert [t for _, _, t in ix][-6:] == [None] * 6, (
        ix
    )  # Differenz ohne Text bleibt offen
    assert fragmente("g--h---3---1---k", ["1---g--h---3", "1---k---l"]) == [
        "g--h---3",
        "1---k",
    ]
    assert zeilentexte("h---k", "g--h---k", silben_index("g--h---k", "Deus te")) == [
        "us",
        "te",
    ]
    probe = np.full((320, 300), 230, dtype=np.uint8)
    for yy in (
        60,
        80,
        100,
        120,
        250,
    ):  # eigene Linien, dann erste Linie des nächsten Systems
        probe[yy] = 100
    probe[150:190, ::4] = 60  # Textzeile: dunkel, füllt die Zeile aber nicht
    m = linienprofil(probe, 0, 300)
    assert fremde_linie_unten(m, 40, 130, 260, 20)  # Linie 250 liegt im unteren Rand
    assert not fremde_linie_unten(m, 40, 130, 200, 20)  # nur Text im unteren Rand
    assert text_angeschnitten(probe, 0, 300, 130, 180)  # Schnitt mitten im Text
    assert not text_angeschnitten(
        probe, 0, 300, 130, 230
    )  # Schrift endet über dem Rand
    assert gruppen_aus_geo(
        ["c4", "l4", "z4", "-", "l5", "--", "l3_liq", "---", "b_z3"]
    ) == [
        ("schluessel", ["c", "4"], False),
        ("silbe", ["j", "k", "!", "l"], True),
        ("silbe", ["h", ">"], False),
        ("silbe", ["i", "x", "i"], True),
    ]
    assert (
        ziel_bauen(
            [
                ("schluessel", ["c", "4"], False),
                ("silbe", ["j"], True),
                ("silbe", ["h"], False),
                ("silbe", ["g"], True),
            ],
            ["De", "us", "me"],
        )
        == "(<m>c<m>4) De(<m>j)us(<m>h) me(<m>g)"
    )
    for q in sys.argv[1:]:
        main(q)
