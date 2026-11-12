"""Schritt 1: Vokabular, Längen, Quellenunterschiede, Zerlegung durch den Tokenizer."""

import json
import re
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

from transformers import AutoTokenizer

HIER = Path(__file__).resolve().parent
GRUPPE = re.compile(r"([^()]*)\(([^()]*)\)")


def zerlege(s):
    """Liste (Text vor der Gruppe, Noten-Atome) und der Rest hinter der letzten Klammer."""
    paare = [(m[1], [a for a in m[2].split("<m>") if a]) for m in GRUPPE.finditer(s)]
    return paare, GRUPPE.sub("", s)


def pct(w, p):
    return sorted(w)[min(len(w) - 1, int(p * len(w)))]


def main():
    zeilen = [
        json.loads(z)
        for z in (HIER / "daten/systeme.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    tok = AutoTokenizer.from_pretrained(HIER / "models/LightOnOCR-3-1B")
    atome, zeichen = defaultdict(Counter), defaultdict(Counter)
    werte = defaultdict(lambda: defaultdict(list))
    mehr = Counter()
    pro_quelle = defaultdict(list)
    for z in zeilen:
        q, s = z["quelle"], z["ziel"]
        pro_quelle[q].append(z)
        paare, rest = zerlege(s)
        for text, a in paare:
            zeichen[q].update(text)
            atome[q].update(a)
            mehr.update(x for x in a if len(x) > 1)
        kompakt = s.replace("<m>", "")
        w = werte[q]
        w["zeichen"].append(len(s))
        w["token"].append(len(tok(s, add_special_tokens=False).input_ids))
        w["token_kompakt"].append(len(tok(kompakt, add_special_tokens=False).input_ids))
        w["gruppen"].append(len(paare))
        w["atome"].append(sum(len(a) for _, a in paare))
        w["rest"].append(len(rest.strip()))
        # Leerzeichen zwischen zwei Silben mit Text: Anteil zeigt, ob Wortgrenzen da sind
        for i in range(1, len(paare)):
            if paare[i][0].strip() and paare[i - 1][0].strip():
                w["leer_vor_silbe"].append(int(paare[i][0].startswith(" ")))
        w["klammer_fehler"].append(int(s.count("(") != s.count(")")))
        w["leer"].append(int(not paare))
    bericht = {}
    for q, w in werte.items():
        bericht[q] = {
            "systeme": len(pro_quelle[q]),
            "token": {
                "median": st.median(w["token"]),
                "p99": pct(w["token"], 0.99),
                "max": max(w["token"]),
            },
            "token_kompakt": {
                "median": st.median(w["token_kompakt"]),
                "p99": pct(w["token_kompakt"], 0.99),
                "max": max(w["token_kompakt"]),
            },
            "zeichen_median": st.median(w["zeichen"]),
            "gruppen_median": st.median(w["gruppen"]),
            "atome_median": st.median(w["atome"]),
            "ziele_mit_rest": sum(1 for x in w["rest"] if x),
            "anteil_leer_vor_silbe": round(st.mean(w["leer_vor_silbe"]), 3),
            "klammer_fehler": sum(w["klammer_fehler"]),
            "ohne_gruppen": sum(w["leer"]),
            "atome": dict(atome[q].most_common()),
            "textzeichen": dict(zeichen[q].most_common()),
        }
    bericht["mehrzeichen_atome"] = dict(mehr.most_common())
    # Wie der Tokenizer ein typisches Ziel schneidet
    probe = pro_quelle["Einsiedeln"][0]["ziel"][:90]
    for form in (probe, probe.replace("<m>", "")):
        ids = tok(form, add_special_tokens=False).input_ids
        print(len(ids), [tok.decode([i]) for i in ids][:45])
    print("eos", tok.eos_token, "pad", tok.pad_token)
    (HIER / "bericht_daten.json").write_text(
        json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    for q in pro_quelle:
        r = bericht[q]
        print(q, {k: v for k, v in r.items() if k not in ("atome", "textzeichen")})
        print(" atome", len(r["atome"]), "".join(sorted(r["atome"])))
        print(" text ", len(r["textzeichen"]), "".join(sorted(r["textzeichen"])))
    print("mehrzeichen", bericht["mehrzeichen_atome"])


if __name__ == "__main__":
    assert zerlege("(<m>c<m>4) de(<m>g<m>h) x") == (
        [("", ["c", "4"]), (" de", ["g", "h"])],
        " x",
    )
    main()
