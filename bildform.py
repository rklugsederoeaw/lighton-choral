"""Bildformen für die Eingabe: ganz, gestaucht oder in Streifen untereinander gestapelt.

Das Modell verkleinert isotrop auf 1540 px längste Kante. Lange Systeme verlieren dabei die
senkrechte Auflösung, obwohl die Höhe frei wäre. Beide Alternativen brauchen kein GT je Stück:
Der Decoder liest wie auf einer Seite von oben nach unten und schreibt das ganze Ziel.
"""

import numpy as np
from PIL import Image

MAX_KANTE = 1540
LUECKE = 28  # weißer Abstand zwischen den Streifen, ein Bildtoken
MAX_STREIFEN = 4


def massstab_bei(b, h, n):
    return min(1.0, MAX_KANTE / max(b / n, n * h + (n - 1) * LUECKE))


def streifen_zahl(b, h):
    """Kleinste Streifenzahl mit dem besten Maßstab (auf 1 % gerundet)."""
    return max(
        range(1, MAX_STREIFEN + 1),
        key=lambda n: (round(massstab_bei(b, h, n), 2), -n),
    )


def schnitte(im, n):
    """Schnittstellen nahe den Teilungspunkten, an der Spalte mit der wenigsten Tinte."""
    g = 255.0 - np.asarray(im.convert("L"), dtype=np.float32)
    tinte = np.convolve(g.mean(axis=0), np.ones(15) / 15, mode="same")
    b = im.width
    feld = b // 25
    return [
        (mitte := b * i // n)
        - feld
        + int(np.argmin(tinte[mitte - feld : mitte + feld]))
        for i in range(1, n)
    ]


def bildform(im, form):
    """form: ganz, stauchen oder streifen."""
    b, h = im.size
    if form == "ganz":
        return im
    if form == "stauchen":
        return im.resize((min(b, MAX_KANTE), h), Image.Resampling.BICUBIC)
    if form != "streifen":
        raise ValueError(form)
    n = streifen_zahl(b, h)
    if n == 1:
        if max(b, h) >= MAX_KANTE:
            return im
        # kleine Zuschnitte (CantusDB-Korpus, 1.600-px-Seiten) auf die Eingabegröße bringen:
        # ein Tonschritt hat sonst 9-13 px, weniger als ein 14-px-Patch
        k = MAX_KANTE / max(b, h)
        return im.resize((round(b * k), round(h * k)), Image.Resampling.BICUBIC)
    grenzen = [0, *schnitte(im, n), b]
    teile = [im.crop((x0, 0, x1, h)) for x0, x1 in zip(grenzen, grenzen[1:])]
    o = Image.new(
        "RGB", (max(t.width for t in teile), n * h + (n - 1) * LUECKE), "white"
    )
    for i, t in enumerate(teile):
        o.paste(t, (0, i * (h + LUECKE)))
    return o


if __name__ == "__main__":
    assert streifen_zahl(1000, 300) == 1  # passt schon
    assert streifen_zahl(3335, 362) == 3
    probe = Image.new("RGB", (3000, 300), "white")
    assert bildform(probe, "streifen").height == 628  # zwei Streifen, ein Token Abstand
    assert bildform(probe, "stauchen").size == (1540, 300)
    assert bildform(probe, "ganz").size == (3000, 300)
    klein = Image.new("RGB", (1100, 200), "white")
    assert bildform(klein, "streifen").size == (1540, 280)  # hochskaliert
    assert bildform(klein, "ganz").size == (1100, 200)
