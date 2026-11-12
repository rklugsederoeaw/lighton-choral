"""Geprüfte OMR-GT + CantusDB-Text -> Zeilen in AMNLT-GABC (`common_encoding`), ein Datensatz je Notenzeile.

Noten und Schlüssel kommen aus der GT (`export/<slug>/gt.txt`, Position = GABC-Buchstabe), Silben, Wörter, Neumengrenzen,
Liqueszenz und Art des Abschnittsstrichs aus dem Volpiano des Gesangs, der Text aus `fulltext_ms`.
Ein Wort, dessen Silbenzahl nicht zum Volpiano passt, bleibt offen; die Zeile bekommt status „offen“. Zeilen mit Psalmincipit und Differenz oder abweichendem euouae fallen weg.
Aufruf (aus natural_music_processing): python3 -I skripte/gabc_zeilen.py sbe-0611 [--ergaenzung datei.json] [--aus name.jsonl]
Schreibt daten/cantus_gabc/<slug>/zeilen.jsonl.
"""

import collections
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path("<path-to-volpiano2omr_gt>")
sys.path.insert(0, str(ROOT / "scripts"))
from page_lines import NOTE, pages  # noqa: E402

DB = f"file:{ROOT}/cantus_database.sqlite?mode=ro"
QUELLEN = {
    "sbe-0611": 123606,
    "fcc-0002": 123672,
    "d-ka-aug-lx": 123612,
    "d-ka-aug-lx-addendum": 123612,
}  # ponytail: Quellen mit review/results_<slug>.json
VOK = "aeiouy"
BUCHSTABE = {"l-2": "9", "z-2": "a", "l-1": "b", "z-1": "c"}
for k, c in zip("l1 z1 l2 z2 l3 z3 l4 z4 l5 z5 l6".split(), "defghijklmn", strict=True):
    BUCHSTABE[k] = c
SCHLUESSEL = re.compile(r"^([cf])(\d)$")
ERGAENZUNG = {}  # {node: {Volpiano-Wort: [Silben]}} aus --ergaenzung (Hand oder LLM)


def silben(wort, vokal_i=False, hi_kons=False, hiat=False):
    """Lateinische Silben: i/y konsonantisch vor Vokal am Wortanfang, zwischen Vokalen und nach Präfix (ad-iu-tor),
    ih- wie i- (Ihe-sus), ae/oe/au ein Kern außer -ael (Mi-cha-el), qu/gu + Vokal; hii/hiis einsilbig."""
    w = wort.lower()
    if w == "euouae":
        return list(wort)
    if w == "seuouae":  # Saeculorum amen, in F-Pn 12044 so verschriftet
        return [wort[:2]] + list(wort[2:])
    if w in ("hii", "hiis"):
        return [wort]
    praefix = re.match(r"(ad|in|con|ab|ob|sub)iu", w)
    ih = (
        1
        if (w.startswith("ih") or (hi_kons and w.startswith("hi")))
        and len(w) > 2
        and w[2] in "aeou"
        else 0
    )
    kerne, i = [], 0
    while i < len(w):
        nach_qu = i > 1 and w[i - 2 : i] in ("qu", "gu")
        hi_start = hi_kons and i == 1 and w[0] == "h" and len(w) > 2 and w[2] in "aeou"
        kons_i = hi_start or (
            not vokal_i
            and (
                (
                    w[i] in "iy"
                    and i + 1 + (i == 0) * ih < len(w)
                    and w[i + 1 + (i == 0) * ih] in "aeou"
                    and (i == 0 or (w[i - 1] in "aeou" and not nach_qu))
                )
                or (praefix is not None and i == praefix.end() - 2)
            )
        )
        kons_u = (
            i > 0
            and w[i] == "u"
            and w[i - 1] in "qg"
            and i + 1 < len(w)
            and w[i + 1] in VOK
        )
        if w[i] in VOK and not kons_i and not kons_u:
            hiat_hier = hiat or (w[i : i + 3] == "ael" and i + 3 == len(w))
            j = i + 2 if w[i : i + 2] in ("ae", "oe", "au") and not hiat_hier else i + 1
            kerne.append((i, j))
            i = j
        else:
            i += 1
    if not kerne:
        return [wort]
    grenzen = []
    for (_, b), (a, _) in zip(kerne, kerne[1:]):
        c = w[b:a]
        if not c:
            grenzen.append(b)
        elif c.endswith(("qu", "gu")):
            grenzen.append(a - 2)
        elif len(c) == 1:
            grenzen.append(a if c == "x" else b)
        elif (c[-1] in "lr" and c[-2] in "bcdfgpt") or c[-2:] in ("ch", "ph", "th"):
            grenzen.append(a - 2)
        else:
            grenzen.append(a - 1)
    return [wort[a:b] for a, b in zip([0] + grenzen, grenzen + [len(w)])]


def varianten(wort):
    """{Silbenzahl: Trennung}, die übliche Trennung zuerst; Varianten nur, wenn das Volpiano genau diese Zahl verlangt."""
    aus = {}
    for kw in (
        {},
        {"hi_kons": True},
        {"hiat": True},
        {"vokal_i": True},
        {"vokal_i": True, "hiat": True},
    ):
        t = silben(wort, **kw)
        aus.setdefault(len(t), t)
    return aus


def ein_schluessel(t):
    """Mehrteiligen Schlüssel (f2/c4) auf einen in GABC darstellbaren zurückführen: C vor F."""
    if "/" not in t or not re.match(r"^[a-g]-?\d(/[a-g]-?\d)+$", t):
        return t
    teile = t.split("/")
    return next(
        (x for x in teile if x[0] == "c"), next((x for x in teile if x[0] == "f"), t)
    )


def lies_volpiano(v):
    """-> Noten [(wort, silbe, neume, liqueszent)], Striche {Notenzahl davor: '3'|'4'}; Trenner gelten über 7 hinweg."""
    noten, striche, wartend, w, s, n = [], {}, 3, -1, -1, -1
    for t in re.findall(r"-+|7{1,3}|.", v, re.S):
        if t[0] == "-":
            wartend = max(wartend, len(t))
        elif t in "34":
            striche[len(noten)] = t
        elif NOTE.fullmatch(t):
            if wartend >= 3:
                w, s, n = w + 1, s + 1, n + 1
            elif wartend == 2:
                s, n = s + 1, n + 1
            elif wartend == 1:
                n += 1
            noten.append((w, s, n, t.isupper()))
            wartend = 0
    return noten, striche


def text_woerter(ms):
    return [
        x
        for x in (
            re.sub(r"[^A-Za-z]", "", w)
            for w in re.sub(r"[|~#*]", " ", re.sub(r"\{[^}]*\}", " ", ms or "")).split()
        )
        if x
    ]


def wortzuordnung(a, b):
    """Silbenzahlen je Volpiano-Wort gegen je Textwort (b: Menge möglicher Zahlen) (globale Ausrichtung) -> ({i: j} gleiche Silbenzahl, {i: j} ungleiche)."""
    n, m = len(a), len(b)
    D = [[-(i + j) if not (i and j) else 0 for j in range(m + 1)] for i in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i][j] = max(
                D[i - 1][j - 1] + (2 if a[i - 1] in b[j - 1] else -1),
                D[i - 1][j] - 1,
                D[i][j - 1] - 1,
            )
    i, j, p, q = n, m, {}, {}
    while i and j:
        if D[i][j] == D[i - 1][j - 1] + (2 if a[i - 1] in b[j - 1] else -1):
            (p if a[i - 1] in b[j - 1] else q)[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif D[i][j] == D[i - 1][j] - 1:
            i -= 1
        else:
            j -= 1
    return p, q


def ausgespart(g, i):
    """Offenes Wort mit Psalmincipit und Differenz oder abweichendem euouae: solche Zeilen fallen weg (Projektleiter)."""
    j = g.q.get(i)
    wort = g.text[j].lower() if j is not None else ""
    return (
        bool(re.match(r"e[uo][ou]", wort))
        or (len(g.worte[i]) >= 5 and len(g.text) <= 2)
        or len(g.worte[i]) >= 6
        and j is not None
        and len(silben(g.text[j])) <= 3
    )


class Gesang:
    def __init__(self, folio, seq, ms, v, node):
        self.folio, self.seq, self.node = folio, seq, node
        self.noten, self.striche = lies_volpiano(v)
        self.tonfolge = "".join(re.findall(NOTE, v.replace("7", "")))
        self.zeiger = 0
        je_wort = collections.defaultdict(list)
        for w, s, _, _ in self.noten:
            if s not in je_wort[w]:
                je_wort[w].append(s)
        self.worte = [je_wort[k] for k in sorted(je_wort)]
        self.text = tw = text_woerter(ms)
        var = [varianten(x) for x in tw]
        self.p, self.q = wortzuordnung(
            [len(x) for x in self.worte], [set(v) for v in var]
        )
        self.silbe = {}  # Silben-ID -> Text (fehlt: offen)
        for i, ss in enumerate(self.worte):
            if i in self.p:
                self.silbe.update(zip(ss, var[self.p[i]][len(ss)], strict=True))
        self.weg = {
            i for i in range(len(self.worte)) if i not in self.p and ausgespart(self, i)
        }
        for i, sil in ERGAENZUNG.get(str(node), {}).items():
            if len(sil) == len(self.worte[int(i)]):
                self.silbe.update(zip(self.worte[int(i)], sil, strict=True))


def gabc_zeile(tokens, teile, zuord=None):
    """tokens: GT der Zeile; teile: [(Gesang, von, bis)] mit Notenindex -> (gabc, offen, Notenfehler)."""
    plan = [(g, i) for g, a, b in teile for i in range(a, b)]
    raus, gruppe, k, vor, vorzeichen, offen = [], [], 0, None, [], 0

    def schliessen():
        nonlocal gruppe
        if gruppe:
            raus[-1][1] = "".join(gruppe)
            gruppe = []

    for t in tokens:
        if t == ",":
            continue
        m = SCHLUESSEL.match(t)
        if m:
            schliessen()
            raus.append(["", f"<m>{m[1]}<m>{m[2]}", "los"])
            vor = None
        elif t == "L":
            schliessen()
            g_i = plan[k - 1] if 0 < k <= len(plan) else None
            art = g_i and g_i[0].striche.get(g_i[1] + 1)
            raus.append(["", "<m>:<m>:" if art == "4" else "<m>:", "los"])
            vor = None
        elif t.startswith(("b_", "na_")):
            vorzeichen += [t]
        else:
            if BUCHSTABE.get(t, "?") not in "abcdefghijklm":
                return None, 0, 3
            if k >= len(plan):
                return None, 0, 1
            g, i = plan[k]
            w, s, n, liq = g.noten[i]
            if w in g.weg:
                return None, 0, 2
            schluessel = (id(g), w, s)
            neu_silbe = vor is None or vor[:3] != schluessel
            neu_start = neu_silbe or not gruppe
            aus_bild = (zuord or {}).get(
                k + 1
            )  # (Silbe, beginnt hier) aus der Bildlesung
            if aus_bild:
                if aus_bild[1]:
                    schliessen()
                    bindung = (
                        "wort" if vor is not None and vor[:2] == (id(g), w) else "los"
                    )
                    raus.append([aus_bild[0], "", bindung])
                elif not gruppe:
                    raus.append(["", "", "los"])
                elif vor is not None and vor[3] != n:
                    gruppe.append("<m>!")
            elif neu_start:
                schliessen()
                erste = i == 0 or g.noten[i - 1][1] != s
                text = g.silbe.get(s, "") if erste else ""
                if erste and s not in g.silbe:
                    offen += 1
                bindung = (
                    "wort"
                    if vor is not None and vor[:2] == (id(g), w) and neu_silbe
                    else "los"
                )
                raus.append([text, "", bindung])
            elif vor[3] != n:
                gruppe.append("<m>!")
            if any(
                BUCHSTABE.get(v.split("_")[1], "?") not in "abcdefghijklm"
                for v in vorzeichen
            ):
                return None, 0, 3
            for v in vorzeichen:
                a, p = v.split("_")
                gruppe.append(f"<m>{BUCHSTABE[p]}<m>{'x' if a == 'b' else 'y'}")
            vorzeichen = []
            gruppe.append(f"<m>{BUCHSTABE[t]}" + ("<m>~" if liq else ""))
            vor = (id(g), w, s, n)
            k += 1
    schliessen()
    if k != len(plan):
        return None, 0, 1
    aus = ""
    for text, musik, bindung in raus:
        aus += ("" if bindung == "wort" or not aus else " ") + f"{text}({musik})"
    return aus, offen, 0


def main(
    slug,
    ergaenzung=None,
    dateiname="zeilen.jsonl",
    je_zeile=None,
    zuordnung=None,
    weg_ids=(),
    strittig=(),
):
    if ergaenzung:
        ERGAENZUNG.update(json.load(open(ergaenzung, encoding="utf-8")))
    db = sqlite3.connect(DB, uri=True)
    sid = QUELLEN[slug]
    chants = {
        (f, s): (m, v, n)
        for f, s, m, v, n in db.execute(
            "select folio,sequence,fulltext_ms,volpiano,node_id from chants where source_id=? and volpiano!=''",
            (sid,),
        )
    }
    gt = dict(
        z.rstrip("\n").split(" ", 1)
        for z in open(ROOT / f"export/{slug}/gt.txt", encoding="utf-8")
    )
    res = json.load(open(ROOT / f"review/results_{slug}.json"))
    seiten = pages(sid)
    folios = [p["folio"].removesuffix("/col") for p in seiten]
    gesang_cache, z = {}, collections.Counter()
    ziel = Path(f"daten/cantus_gabc/{slug}")
    ziel.mkdir(parents=True, exist_ok=True)
    with open(ziel / dateiname, "w", encoding="utf-8") as aus:
        for r in res:
            if r["folio"] not in folios:
                z["seite_fehlt"] += 1
                continue
            p = seiten[folios.index(r["folio"])]
            for e in r["assignment"]:
                ids = [r["staves"][j]["crop"][:-4] for j in e["staves"]]
                if not all(i in gt for i in ids):
                    continue
                teile = []
                for li in e["lines"]:
                    if li >= len(p["lines"]):
                        teile = None
                        break
                    for c in p["lines"][li]:
                        ton = "".join(re.findall(NOTE, c["volpiano"]))
                        pi, g = folios.index(r["folio"]), None
                        for fo in dict.fromkeys(folios[max(0, pi - 3) : pi + 1][::-1]):
                            kand = (fo, c["seq"])
                            if kand not in chants:
                                continue
                            g = gesang_cache.setdefault(
                                kand, Gesang(fo, c["seq"], *chants[kand])
                            )
                            if ton in g.tonfolge:
                                break
                            g = None
                        if g is None:
                            teile = None
                            break
                        a = g.tonfolge.find(ton, g.zeiger)
                        a = g.tonfolge.find(ton) if a < 0 else a
                        g.zeiger = a + len(ton)
                        teile.append((g, a, a + len(ton)))
                    if teile is None:
                        break
                z["zeilen"] += len(ids)
                if teile is None:
                    z["volpiano_nicht_gefunden"] += len(ids)
                    continue
                # Bei split/merge Noten je System nach GT-Notenzahl verteilen
                rest = [(g, a, b) for g, a, b in teile]
                for i, sysid in zip(ids, e["staves"], strict=True):
                    toks = [ein_schluessel(t) for t in gt[i].split()]
                    anzahl = sum(1 for t in toks if t[0] in "lz")
                    if len(ids) == 1 and anzahl != sum(b - a for _, a, b in rest):
                        z["noten_fehlen_im_label"] += (
                            1  # zurückgestellt (Projektleiter)
                        )
                        continue
                    stueck, n = [], anzahl
                    while n and rest:
                        g, a, b = rest[0]
                        m = min(n, b - a)
                        stueck.append((g, a, a + m))
                        n -= m
                        rest[0] = (g, a + m, b)
                        if a + m == b:
                            rest.pop(0)
                    if i in weg_ids:
                        z["bild_psalmincipit"] += 1
                        continue
                    gabc, offen, fehler = gabc_zeile(
                        toks, stueck, (zuordnung or {}).get(i)
                    )
                    if fehler == 3:
                        z["position_ausserhalb_a_bis_m"] += 1
                        continue
                    if fehler == 2:
                        z["psalmincipit_euouae_ausgelassen"] += 1
                        continue
                    if fehler or n:
                        z["notenzahl_abweichend"] += 1
                        continue
                    status = (
                        "grenze_strittig"
                        if i in strittig
                        else "offen"
                        if offen
                        else "voll"
                    )
                    if je_zeile:
                        je_zeile(i, toks, stueck, r, e, sysid, status)
                    z[status] += 1
                    z["mehrere_gesaenge"] += len({id(g) for g, _, _ in stueck}) > 1
                    aus.write(
                        json.dumps(
                            {
                                "id": i,
                                "bild": f"export/{slug}/images/{i}.jpg",
                                "transcription": gabc,
                                "status": status,
                                "offene_silben": offen,
                                "silben_aus_bild": i in (zuordnung or {}),
                                "gesaenge": [
                                    {"folio": g.folio, "seq": g.seq, "node": g.node}
                                    for g in dict.fromkeys(g for g, _, _ in stueck)
                                ],
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
    print(dict(z))


if __name__ == "__main__":
    for wort, soll in {
        "iustum": "ius-tum",
        "deus": "de-us",
        "quia": "qui-a",
        "requiem": "re-qui-em",
        "Ihesus": "Ihe-sus",
        "adiutor": "ad-iu-tor",
        "michael": "mi-cha-el",
        "yesse": "yes-se",
        "alleluia": "al-le-lu-ia",
        "hiis": "hiis",
        "seuouae": "se-u-o-u-a-e",
    }.items():
        assert "-".join(silben(wort)) == soll, (wort, silben(wort))
    g = type("G", (), {"q": {0: 0}, "text": ["euouae"], "worte": [[0, 1, 2, 3, 4]]})()
    assert ausgespart(g, 0)
    g = type("G", (), {"q": {0: 0}, "text": ["Ihesus", "x", "y"], "worte": [[0, 1]]})()
    assert not ausgespart(g, 0)
    assert (
        len(varianten("Hierusalem")) >= 2
        and "-".join(varianten("Hierusalem")[4]) == "Hie-ru-sa-lem"
    )
    assert "-".join(varianten("Nicholaus")[4]) == "Ni-cho-la-us"
    assert (
        ein_schluessel("f2/c4") == "c4"
        and ein_schluessel("c4") == "c4"
        and ein_schluessel("d2/f3") == "f3"
    )
    t, st = lies_volpiano("1---g-h--j7-k---3")
    assert [x[:3] for x in t] == [
        (0, 0, 0),
        (0, 0, 1),
        (0, 1, 2),
        (0, 1, 3),
    ] and st == {4: "3"}
    a = sys.argv
    main(
        a[1],
        a[a.index("--ergaenzung") + 1] if "--ergaenzung" in a else None,
        a[a.index("--aus") + 1] if "--aus" in a else "zeilen.jsonl",
    )
