"""Schritt 2: Pixel je Tonschritt nach der Skalierung, je Quelle und Bildform.

Der Linienabstand wird aus Zeilenprofilen in schmalen Spalten geschätzt (Median je Zeile, damit
Noten und Text wegfallen; Grünkanal, damit rote Linien dunkel erscheinen).
"""

import json
import random
import statistics as st
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from bildform import MAX_KANTE, bildform, streifen_zahl

HIER = Path(__file__).resolve().parent
N_JE_QUELLE = 100
SPALTEN = 9


def profil(g, x0, x1, h):
    p = np.median(255.0 - g[:, x0:x1], axis=1)
    k = max(3, h // 6) | 1
    return p - np.convolve(p, np.ones(k) / k, mode="same")


def abstand_spalte(p, h):
    lo, hi = max(8, h // 25), h // 3
    p = p - p.mean()
    ac = np.correlate(p, p, mode="full")[len(p) - 1 :]
    if ac[0] <= 0:
        return None
    ac = ac / ac[0]
    spitzen = [
        i
        for i in range(lo, min(hi, len(ac) - 1))
        if ac[i] > ac[i - 1] and ac[i] >= ac[i + 1] and ac[i] > 0.1
    ]
    if not spitzen:
        return None
    grenze = 0.7 * max(ac[i] for i in spitzen)
    return next(i for i in spitzen if ac[i] >= grenze)  # kleinster starker Abstand


def linienabstand(im):
    """(Abstand in Originalpixeln, Anteil der Spalten, die ihn bestätigen, Beispiel-Zeilen)"""
    g = np.asarray(im.convert("RGB"), dtype=np.uint8)[:, :, 1]
    h, w = g.shape
    breite = max(60, w // 10)
    werte, profile = [], []
    for i in range(SPALTEN):
        x0 = int((w - breite) * (i + 0.5) / SPALTEN)
        p = profil(g, x0, x0 + breite, h)
        d = abstand_spalte(p, h)
        if d:
            werte.append(d)
            profile.append(p)
    if not werte:
        return None, 0.0, []
    d = st.median(werte)
    guete = sum(abs(v - d) <= 0.1 * d for v in werte) / SPALTEN
    p = profile[len(profile) // 2]
    d_i = int(round(d))
    letzte = h - 3 * d_i
    if letzte <= 0:
        return d, guete, []
    t = max(range(letzte), key=lambda t: sum(p[t + k * d_i] for k in range(4)))
    return d, guete, [t + k * d_i for k in range(4)]


def massstab(b, h):
    return min(1.0, MAX_KANTE / max(b, h))


def beispiel(im, quelle, ordner):
    """Eingabe nach der Skalierung, darunter 3fach vergrößert mit 14- und 28-px-Raster."""
    for form in ("ganz", "stauchen", "streifen"):
        x = bildform(im, form)
        s = massstab(*x.size)
        y = x.resize(
            (round(x.width * s), round(x.height * s)), Image.Resampling.BICUBIC
        )
        b, h = 420, min(y.height, 252)
        x0 = y.width // 3
        z = y.crop((x0, 0, x0 + b, h)).resize((b * 3, h * 3), Image.Resampling.NEAREST)
        dr = ImageDraw.Draw(z)
        for t in range(0, max(z.size), 42):
            farbe = (0, 90, 255) if t % 84 == 0 else (170, 200, 255)
            dr.line([(t, 0), (t, z.height)], fill=farbe)
            dr.line([(0, t), (z.width, t)], fill=farbe)
        o = Image.new("RGB", (max(y.width, z.width), y.height + z.height + 10), "white")
        o.paste(y, (0, 0))
        o.paste(z, (0, y.height + 10))
        o.save(ordner / f"beispiel_{quelle}_{form}.jpg", quality=88)


def main():
    zeilen = [
        json.loads(z)
        for z in (HIER / "daten/systeme.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rng = random.Random(0)
    ordner = HIER / "bilder_aufloesung"
    ordner.mkdir(exist_ok=True)
    ergebnis, kontrolle, beispiele = {}, [], set()
    for quelle in ("Einsiedeln", "Salzinnes", "Solesmes"):
        auswahl = rng.sample([z for z in zeilen if z["quelle"] == quelle], N_JE_QUELLE)
        reihen = {"ganz": [], "stauchen": [], "streifen": []}
        abstaende, verworfen, n_streifen, tok = [], 0, [], {k: [] for k in reihen}
        for j, z in enumerate(auswahl):
            im = Image.open(HIER / z["bild"]).convert("RGB")
            d, guete, linien = linienabstand(im)
            if d is None or guete < 0.6:
                verworfen += 1
                continue
            abstaende.append(d)
            b, h = im.size
            n = streifen_zahl(b, h)
            n_streifen.append(n)
            for form in reihen:
                bb, hh = bildform(im, form).size
                s = massstab(bb, hh)
                senk = s * hh / h if form == "stauchen" else s
                reihen[form].append(d / 2 * senk)
                sb, sh = bb * s, hh * s
                tok[form].append(int(np.ceil(sb / 28)) * int(np.ceil(sh / 28)))
            if quelle not in beispiele:
                beispiele.add(quelle)
                beispiel(im, quelle, ordner)
            if j < 6:
                x = im.copy()
                dr = ImageDraw.Draw(x)
                for y in linien:
                    dr.line([(0, y), (b, y)], fill=(0, 200, 0), width=2)
                k = 1500 / b
                kontrolle.append((quelle, x.resize((1500, int(h * k)))))
        ergebnis[quelle] = {
            "gemessen": len(abstaende),
            "verworfen": verworfen,
            "linienabstand_median": st.median(abstaende),
            "linienabstand_p10_p90": [
                float(np.percentile(abstaende, 10)),
                float(np.percentile(abstaende, 90)),
            ],
            "streifen_haeufigkeit": {
                str(n): n_streifen.count(n) for n in sorted(set(n_streifen))
            },
            **{
                f"tonschritt_{form}": {
                    "median": round(st.median(v), 1),
                    "p10": round(float(np.percentile(v, 10)), 1),
                    "anteil_unter_14": round(float(np.mean(np.array(v) < 14)), 2),
                    "bildtoken_median": st.median(tok[form]),
                }
                for form, v in reihen.items()
            },
        }
        print(quelle, json.dumps(ergebnis[quelle], ensure_ascii=False), flush=True)
    (HIER / "bericht_aufloesung.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    hoehe = sum(x.height + 8 for _, x in kontrolle)
    o = Image.new("RGB", (1500, hoehe), "white")
    y = 0
    for _, x in kontrolle:
        o.paste(x, (0, y))
        y += x.height + 8
    o.save(ordner / "kontrolle_linien.jpg", quality=85)


if __name__ == "__main__":
    main()
