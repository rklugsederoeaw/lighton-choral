"""Wortgrenzen für AMNLT-Einsiedeln und -Salzinnes aus dem CantusDB-Volltext nachtragen.

AMNLT setzt dort vor jede Silbe ein Leerzeichen. Das Zielformat von Solesmes und des
CantusDB-Korpus hat Leerzeichen nur zwischen Wörtern. Je Zeile wird der Silbentext gegen die
Gesangstexte der Handschrift ausgerichtet (n-Gramm-Vorauswahl, dann Levenshtein-Abgleich) und
die Wortanfänge des Volltexts auf die Silbenanfänge übertragen. Unsichere Zeilen bleiben wie sie sind.

    python wortgrenzen_amnlt.py   -> daten/systeme_wg.jsonl, bericht_wortgrenzen.json
"""

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz.distance import Levenshtein as lev
from rapidfuzz.fuzz import partial_ratio_alignment

from metriken import zerlege
from silben_cantus import DB

HIER = Path(__file__).resolve().parent
QUELLEN = {"Einsiedeln": 123606, "Salzinnes": 123723}
MIN_SCORE = 80
N = 5


def norm(s):
    return re.sub(r"[^a-z]", "", s.lower().replace("j", "i").replace("v", "u"))


def gesaenge(sid):
    """Je Gesang: normierter Text ohne Leerzeichen und die Menge der Wortanfänge."""
    d = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    aus = []
    for ms, std in d.execute(
        "select fulltext_ms, fulltext_standardized from chants where source_id=?",
        (sid,),
    ):
        t = (ms or std or "").split("|")[0]
        woerter = [norm(w) for w in re.findall(r"[A-Za-z]+", t)]
        woerter = [w for w in woerter if w]
        if not woerter:
            continue
        starts, p = set(), 0
        for w in woerter:
            starts.add(p)
            p += len(w)
        aus.append(("".join(woerter), starts))
    return aus


def ngramm_index(chants):
    ix = defaultdict(set)
    for k, (t, _) in enumerate(chants):
        for i in range(len(t) - N + 1):
            ix[t[i : i + N]].add(k)
    return ix


def wortanfaenge(silben, chants, ix):
    """Liste bool je Silbe (beginnt ein Wort) oder None, wenn keine sichere Ausrichtung."""
    zeile = "".join(silben)
    if len(zeile) < N + 2:
        return None
    treffer = Counter()
    for i in range(len(zeile) - N + 1):
        for k in ix.get(zeile[i : i + N], ()):
            treffer[k] += 1
    if not treffer:
        return None
    bestes = None
    for k, _ in treffer.most_common(5):
        t, starts = chants[k]
        a = partial_ratio_alignment(zeile, t)
        # die Ausrichtung muss die ganze Zeile abdecken (bis auf 2 Zeichen an den Enden)
        if a is None or a.src_start > 2 or a.src_end < len(zeile) - 2:
            continue
        if bestes is None or a.score > bestes[0]:
            bestes = (a.score, a, starts)
    if bestes is None or bestes[0] < MIN_SCORE:
        return None
    _, a, starts = bestes
    t = next(c[0] for c in chants if c[1] is starts)
    stueck = t[a.dest_start : a.dest_end]
    # Abbildung Zeilenposition -> absolute Position im Gesangstext über die Editieroperationen
    abb = {}
    for op in lev.opcodes(zeile[a.src_start : a.src_end], stueck):
        for j in range(op.src_end - op.src_start):
            ziel = op.dest_start + (j if op.tag in ("equal", "replace") else 0)
            abb[a.src_start + op.src_start + j] = a.dest_start + ziel
    aus, p = [], 0
    for k, s in enumerate(silben):
        if p == 0:
            aus.append(True)
        else:
            q = abb.get(p)
            # unbekannt: Leerzeichen behalten; sonst Wortanfang, auch um ein Zeichen versetzt
            # (Abkürzungen wie xpi für christi verschieben die Ausrichtung)
            # (q + 1 nur bei Silben ab zwei Zeichen, sonst würde ein einzelner Buchstabe
            # vor einem Wortanfang selbst zum Wortanfang)
            aus.append(
                q is None
                or q in starts
                or (len(silben[k - 1]) >= 2 and (q - 1) in starts)
                or (len(s) >= 2 and (q + 1) in starts)
            )
        p += len(s)
    return aus


def neu_schreiben(ziel, anfaenge):
    """Leerzeichen nur vor Wortanfängen; Gruppen ohne Silbe behalten ihr Leerzeichen."""
    teile, k, ende, nach_strich = [], 0, 0, False
    for m in re.finditer(r"([^()]*)(\([^()]*\))", ziel):
        t = m[1].strip()
        if t:
            # nach Strich, Custos oder Schlüssel beginnt immer ein Wort
            vor = " " if ((anfaenge[k] or nach_strich) and teile) else ""
            k += 1
            nach_strich = False
        else:
            vor = " " if teile else ""
            nach_strich = True
        teile.append(vor + t + m[2])
        ende = m.end()
    return "".join(teile) + ziel[ende:]


def main():
    zeilen = [
        json.loads(z)
        for z in (HIER / "daten/systeme.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    bericht = {}
    beispiele = []
    for quelle, sid in QUELLEN.items():
        chants = gesaenge(sid)
        ix = ngramm_index(chants)
        zahl = Counter()
        for z in zeilen:
            if z["quelle"] != quelle:
                continue
            zahl["zeilen"] += 1
            paare, _ = zerlege(z["ziel"])
            silben = [norm(t) for t, _ in paare if t.strip()]
            if any(not s for s in silben):
                zahl["silbe_ohne_buchstaben"] += 1
                continue
            a = wortanfaenge(silben, chants, ix)
            if a is None:
                zahl["nicht_ausgerichtet"] += 1
                continue
            z["ziel_alt"] = z["ziel"]
            z["ziel"] = neu_schreiben(z["ziel"], a)
            zahl["umgeschrieben"] += 1
            zahl["silben"] += len(silben)
            zahl["wortanfaenge"] += sum(a)
            if len(beispiele) < 12 and len(silben) > 6:
                beispiele.append((z["id"], z["ziel"].replace("<m>", "")))
        bericht[quelle] = dict(zahl)
        print(quelle, dict(zahl), flush=True)
    (HIER / "daten/systeme_wg.jsonl").write_text(
        "".join(json.dumps(z, ensure_ascii=False) + "\n" for z in zeilen),
        encoding="utf-8",
    )
    (HIER / "bericht_wortgrenzen.json").write_text(
        json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    for b in beispiele:
        print(b[0], b[1][:150])


if __name__ == "__main__":
    z = "(<m>c<m>4) de(<m>g<m>h) us(<m>g) (<m>:) me(<m>e) us(<m>f)"
    assert (
        neu_schreiben(z, [True, False, True, False])
        == "(<m>c<m>4) de(<m>g<m>h)us(<m>g) (<m>:) me(<m>e)us(<m>f)"
    )
    chants = [("deusmeusinte", {0, 4, 8, 10}), ("aliudetaliud", {0, 5, 7})]
    ix = ngramm_index(chants)
    assert wortanfaenge(["de", "us", "me", "us", "in"], chants, ix) == [
        True,
        False,
        True,
        False,
        True,
    ]
    assert wortanfaenge(["xx"], chants, ix) is None
    main()
