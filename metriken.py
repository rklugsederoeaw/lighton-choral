"""Zerlegen des gabc-artigen Ziels und getrennte Messung von Noten und Text.

Alle Noten-Atome sind Einzelzeichen, deshalb liest zerlege() das Ziel mit und ohne <m> gleich.
Tonlage: Buchstaben a-m (Großbuchstabe nur andere Notenform), ohne Schlüssel, Custos, Vorzeichen.
"""

import re

from rapidfuzz.distance import Levenshtein as lev

GRUPPE = re.compile(r"([^()]*)\(([^()]*)\)")
TON = set("abcdefghijklm")


def zerlege(s):
    """Liste (Text vor der Gruppe, Noten-Atome) und der Text hinter der letzten Klammer."""
    paare = [(m[1], list(m[2].replace("<m>", ""))) for m in GRUPPE.finditer(s)]
    return paare, GRUPPE.sub("", s)


def noten_token(atome):
    """Fasst Schlüssel (c4), Custos (f+), Vorzeichen (gx) und Taktstrich mit Ziffer (;6) zusammen."""
    aus, i = [], 0
    while i < len(atome):
        a, n = atome[i], atome[i + 1] if i + 1 < len(atome) else ""
        if (a in "cf" and n in tuple("1234")) or (a == ";" and n.isdigit()):
            aus.append(a + n)
            i += 2
        elif a.lower() in TON and n in tuple("+xy"):
            aus.append(a + n)
            i += 2
        else:
            aus.append(a)
            i += 1
    return aus


def ist_ton(t):
    return len(t) == 1 and t.lower() in TON


def ist_schluessel(t):
    return len(t) == 2 and t[0] in "cf" and t[1].isdigit()


def sicht(s):
    """Noten-Token, Töne, Schlüssel, Grenzen (Tonzahl am Gruppenende und an !), Silben, Text."""
    paare, rest = zerlege(s)
    token, toene, schl, grenzen, silben = [], [], [], set(), []
    for text, atome in paare:
        if text.strip():
            silben.append(text.strip())
        for t in noten_token(atome):
            token.append(t)
            if t == "!":
                grenzen.add(len(toene))
            elif ist_ton(t):
                toene.append(t.lower())
            elif ist_schluessel(t):
                schl.append(t)
        grenzen.add(len(toene))
    if rest.strip():
        silben.append(rest.strip())
    grenzen.discard(0)
    grenzen.discard(len(toene))
    text = "".join(t for t, _ in paare) + rest
    return {
        "token": token,
        "toene": toene,
        "schl": schl,
        "grenzen": grenzen,
        "silben": silben,
        "zeichen": re.sub(r"\s+", "", text),
        "woerter": text.split(),
        "kompakt": s.replace("<m>", ""),
    }


def schleife(s, min_wdh=6, max_periode=60):
    """Endet s mit einer Zeichenfolge, die sich mindestens min_wdh-mal direkt wiederholt?"""
    s = s.rstrip()  # 116 Referenzen enden auf Leerzeichen
    for p in range(1, max_periode + 1):
        if len(s) >= p * min_wdh and all(
            s[-p:] == s[-p * (k + 1) : -p * k or None] for k in range(min_wdh)
        ):
            return True
    return False


def grenz_treffer(r, h):
    """Treffer, Falsche, Fehlende der Grenzen, über die Ausrichtung der Tonfolgen abgebildet."""
    h_nach_r = {}
    for op in lev.opcodes(h["toene"], r["toene"]):
        if op.tag in ("equal", "replace"):  # falscher Ton: Position bleibt vergleichbar
            for k in range(op.src_end - op.src_start):
                h_nach_r[op.src_start + k + 1] = op.dest_start + k + 1
    abgebildet = {h_nach_r.get(g) for g in h["grenzen"]}
    tp = len(abgebildet & r["grenzen"])
    return tp, len(h["grenzen"]) - tp, len(r["grenzen"]) - tp


def messe(paare):
    """paare: Liste (Referenz, Lesung, Quelle-mit-Wortgrenzen). Fehlerraten als Anteil."""
    s = dict.fromkeys(
        "ser_f ser_n ton_f ton_n sch_f sch_n sil_f sil_n cer_f cer_n ges_f ges_n "
        "wer_f wer_n tp fp fn start_ok start_n".split(),
        0,
    )
    for ref, hyp, wortgrenzen in paare:
        r, h = sicht(ref), sicht(hyp)
        for f, n, a, b in (
            ("ser_f", "ser_n", r["token"], h["token"]),
            ("ton_f", "ton_n", r["toene"], h["toene"]),
            ("sch_f", "sch_n", r["schl"], h["schl"]),
            ("sil_f", "sil_n", r["silben"], h["silben"]),
            ("cer_f", "cer_n", r["zeichen"], h["zeichen"]),
            ("ges_f", "ges_n", r["kompakt"], h["kompakt"]),
        ):
            s[f] += lev.distance(a, b)
            s[n] += len(a)
        if wortgrenzen:
            s["wer_f"] += lev.distance(r["woerter"], h["woerter"])
            s["wer_n"] += len(r["woerter"])
        tp, fp, fn = grenz_treffer(r, h)
        s["tp"] += tp
        s["fp"] += fp
        s["fn"] += fn
        if r["schl"]:
            s["start_n"] += 1
            s["start_ok"] += h["schl"][:1] == r["schl"][:1]
    anteil = lambda a, b: round(s[a] / s[b], 4) if s[b] else None  # noqa: E731
    nenner = 2 * s["tp"] + s["fp"] + s["fn"]
    return {
        "noten_ser": anteil("ser_f", "ser_n"),
        "tonlage_ser": anteil("ton_f", "ton_n"),
        "schluessel_ser": anteil("sch_f", "sch_n"),
        "anfangsschluessel_richtig": anteil("start_ok", "start_n"),
        "grenzen_f1": round(2 * s["tp"] / nenner, 4) if nenner else None,
        "text_cer": anteil("cer_f", "cer_n"),
        "silben_ser": anteil("sil_f", "sil_n"),
        "text_wer_nur_mit_wortgrenzen": anteil("wer_f", "wer_n"),
        "gesamt_cer": anteil("ges_f", "ges_n"),
        "noten_token": s["ser_n"],
        "toene": s["ton_n"],
    }


if __name__ == "__main__":
    z = "(<m>c<m>4) de(<m>g<m>h) us(<m>g<m>V<m>f) (<m>:) re(<m>e<m>x<m>f<m>+)"
    v = sicht(z)
    assert v["token"] == ["c4", "g", "h", "g", "V", "f", ":", "ex", "f+"], v["token"]
    assert v["toene"] == ["g", "h", "g", "f"], v["toene"]
    assert v["schl"] == ["c4"] and v["silben"] == ["de", "us", "re"]
    assert v["zeichen"] == "deusre" and v["kompakt"].startswith("(c4) de(gh)")
    assert sicht(z.replace("<m>", ""))["token"] == v["token"]  # mit und ohne <m> gleich
    assert sicht("(<m>;<m>6) a(<m>G)")["token"] == [";6", "G"]
    assert sicht("(<m>;<m>6) a(<m>G)")["toene"] == ["g"]
    assert messe([(z, z, True)])["noten_ser"] == 0.0
    m = messe([(z, z.replace("<m>g<m>h", "<m>g<m>i"), False)])
    assert m["tonlage_ser"] == 0.25 and m["text_wer_nur_mit_wortgrenzen"] is None, m
    assert m["grenzen_f1"] == 1.0, m  # ein falscher Ton verschiebt keine Grenze
    assert m["anfangsschluessel_richtig"] == 1.0
    assert schleife("a(f) " * 7) and not schleife("a(f) b(g) " * 2)
    assert not schleife("a(f)" + " " * 30)
    print("ok")
