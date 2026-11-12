"""Volltext und Volpiano der CantusDB silbenweise gegeneinander prüfen (nur lesend).

Volpiano: --- trennt Wörter, -- Silben, - Neumen innerhalb einer Silbe. Ziffern sind Striche.
Silbentrennung: Regeln für mittelalterliches Latein, ohne Wörterbuch.

    python silben_cantus.py
"""

import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "cantus_database.sqlite"
VOKAL = set("aeiouy")
DIPHTHONG = {"ae", "oe", "au"}
ZUSAMMEN = {"bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr", "tr"}
ZUSAMMEN |= {"ch", "ph", "th", "gn", "sc", "sp", "st"}
NOTE = re.compile(r"[89a-hj-sA-HJ-S]")


def laute(w):
    """Wort in Einheiten: Vokale (auch Diphthonge) und Konsonanten (qu, gu vor Vokal als einer)."""
    aus, i = [], 0
    while i < len(w):
        zwei = w[i : i + 2]
        drei = w[i + 2 : i + 3]
        if zwei == "qu" or (
            zwei == "gu" and i and w[i - 1] == "n" and drei in VOKAL and drei
        ):
            aus.append(("k", zwei))
            i += 2
        elif zwei in DIPHTHONG:
            aus.append(("v", zwei))
            i += 2
        elif w[i] in VOKAL:
            nach = w[i + 1 : i + 2]
            vor = aus[-1][0] if aus else ""
            halb = w[i] in "ij" or w[i] == "u"
            if halb and nach in VOKAL and nach and (not vor or vor == "v"):
                aus.append(("k", w[i]))  # iam, eius, uenit, nouum
            else:
                aus.append(("v", w[i]))
            i += 1
        else:
            aus.append(("k", w[i]))
            i += 1
    return aus


def silben(wort):
    """Trennt ein Wort: V-KV, VK-KV, Muta cum Liquida bleibt beisammen."""
    w = re.sub(r"[^a-z]", "", wort.lower().replace("j", "i").replace("v", "u"))
    e = laute(w)
    kerne = [i for i, (a, _) in enumerate(e) if a == "v"]
    if len(kerne) < 2:
        return [w] if w else []
    schnitte = []
    for a, b in zip(kerne, kerne[1:]):
        mitte = [x for _, x in e[a + 1 : b]]
        if len(mitte) <= 1:
            schnitte.append(a + 1)
        elif len(mitte) >= 2 and mitte[-2] + mitte[-1] in ZUSAMMEN:
            schnitte.append(b - 2)
        else:
            schnitte.append(b - 1)
    teile = [0, *schnitte, len(e)]
    return ["".join(x for _, x in e[p:q]) for p, q in zip(teile, teile[1:])]


def text_woerter(ft):
    t = re.sub(r"[{}\[\]]", "", ft.split("|")[0].split("~")[0])
    return re.findall(r"[^\W\d_]+", t)


def volpiano_woerter(v):
    """Je Wort die Liste der Silben (nur Silben mit Noten), nur bis zum ersten Abschnittsstrich.

    Hinter Strich 3 oder 4 stehen Differenz (euouae) oder Verszeile, im Volltext hinter |.
    """
    m = re.search(r"-{3}[34](-{3}|$)", v)
    v = re.sub(r"^[12]-*", "", v[: m.start()] if m else v)
    aus = []
    for wort in re.split(r"-{3,}", v):
        s = [x for x in re.split(r"-{2}", wort) if NOTE.search(x)]
        if s:
            aus.append(s)
    return aus


def main():
    d = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    namen = dict(d.execute("select source_id, cantus_siglum from manuscripts"))
    je = defaultdict(Counter)
    for sid, ft, v in d.execute(
        "select source_id, fulltext_ms, volpiano from chants "
        "where volpiano is not null and length(volpiano) > 10"
    ):
        for k in ("alle", sid):
            je[k]["gesaenge"] += 1
        if not ft:
            continue
        w, vw = text_woerter(ft), volpiano_woerter(v)
        if not w or not vw:
            continue
        for k in ("alle", sid):
            je[k]["mit_text"] += 1
        if len(w) != len(vw):
            continue
        s = [len(silben(x)) for x in w]
        t = [len(x) for x in vw]
        for k in ("alle", sid):
            je[k]["woerter_gleich"] += 1
            je[k]["silben_gleich"] += s == t
            je[k]["silben_n"] += sum(1 for a, b in zip(s, t) if a == b)
            je[k]["silben_m"] += len(s)
    a = je["alle"]
    print("alle", dict(a))
    print(
        f"Text vorhanden {a['mit_text']}/{a['gesaenge']}; Wortzahl gleich "
        f"{100 * a['woerter_gleich'] / a['mit_text']:.1f} %; davon alle Silbenzahlen gleich "
        f"{100 * a['silben_gleich'] / a['woerter_gleich']:.1f} %; Wörter mit gleicher Silbenzahl "
        f"{100 * a['silben_n'] / a['silben_m']:.1f} %"
    )
    print("\nsource_id\tsiglum\tgesaenge\tmit_text\twoerter_gleich\tsilben_gleich")
    for sid, c in sorted(
        ((k, c) for k, c in je.items() if k != "alle"),
        key=lambda kv: -kv[1]["mit_text"],
    )[:25]:
        print(
            f"{sid}\t{namen.get(sid)}\t{c['gesaenge']}\t{c['mit_text']}\t{c['woerter_gleich']}\t{c['silben_gleich']}"
        )


if __name__ == "__main__":
    fall = {
        "Ecce": 2,
        "mitto": 2,
        "angelum": 3,
        "meum": 2,
        "qui": 1,
        "preparabit": 4,
        "viam": 2,
        "faciem": 3,
        "eius": 2,
        "iam": 1,
        "uenit": 2,
        "lingua": 2,
        "sanguis": 2,
        "aeternus": 3,
        "laudate": 3,
        "patrem": 2,
        "Dominus": 3,
        "nouum": 2,
    }
    for w, n in fall.items():
        assert len(silben(w)) == n, (w, silben(w))
    assert silben("patrem") == ["pa", "trem"] and silben("angelum") == [
        "an",
        "ge",
        "lum",
    ]
    assert volpiano_woerter("1---g--h---kl--l---lmk-kj--h--k---3") == [
        ["g", "h"],
        ["kl", "l"],
        ["lmk-kj", "h", "k"],
    ]
    assert text_woerter("Syon {ius} tum | ~Benedictus") == ["Syon", "ius", "tum"]
    main()
