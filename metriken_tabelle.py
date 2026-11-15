"""Tabellenzeilen für metriken.md, Abschnitt 7, aus einer Lesungsdatei: python metriken_tabelle.py <Name> <lesung_test.jsonl>"""

import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from metriken import messe  # noqa: E402


def p(x):
    return f"{100 * x:.2f}".replace(".", ",")


name, pfad = sys.argv[1], sys.argv[2]
rs = [json.loads(z) for z in open(pfad, encoding="utf-8")]
for q in ("Solesmes", "Einsiedeln", "Salzinnes"):
    m = messe([(r["ref"], r["hyp"], True) for r in rs if r["quelle"] == q])
    n = sum(r["quelle"] == q for r in rs)
    print(
        f"| {q} | {name} | {n} | {p(m['noten_ser'])} | {p(m['tonlage_ser'])} | {p(m['text_cer'])} | {p(m['silben_ser'])} | {p(m['amler'])} | {p(m['bwer'])} | {p(m['amler'] - m['bwer'])} | {str(m['aler']).replace('.', ',')[:4]} |"
    )
