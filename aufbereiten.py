"""AMNLT nach daten/: Bilder unverändert als Dateien, dazu daten/systeme.jsonl.

Läuft in der Conda-Umgebung ai-base (datasets); alles Spätere liest nur noch die jsonl-Liste.
"""

import io
import json
import os
from pathlib import Path

from datasets import Image as HfImage
from datasets import load_from_disk
from PIL import Image

HIER = Path(__file__).resolve().parent
AMNLT = Path(os.environ.get("AMNLT", "AMNLT/common_encoding_deduplicated"))  # PRAIG/*_staffLevel, see README
QUELLEN = ["Einsiedeln", "Salzinnes", "Solesmes"]


def main():
    ziel = HIER / "daten"
    zeilen = []
    for quelle in QUELLEN:
        dd = load_from_disk(str(AMNLT / f"{quelle}_staffLevel"))
        for split, d in dd.items():
            ordner = ziel / "bilder" / quelle / split
            ordner.mkdir(parents=True, exist_ok=True)
            d = d.cast_column("image", HfImage(decode=False))
            for i, r in enumerate(d):
                roh = r["image"]["bytes"]
                im = Image.open(io.BytesIO(roh))
                pfad = ordner / f"{i:05d}.{im.format.lower()}"
                if not pfad.exists():
                    pfad.write_bytes(roh)
                zeilen.append(
                    {
                        "id": f"{quelle}/{split}/{i:05d}",
                        "quelle": quelle,
                        "split": split,
                        "bild": str(pfad.relative_to(HIER)),
                        "b": im.width,
                        "h": im.height,
                        "ziel": r["transcription"],
                        "original_index": r["original_index"],
                    }
                )
            print(quelle, split, len(d), flush=True)
    (ziel / "systeme.jsonl").write_text(
        "".join(json.dumps(z, ensure_ascii=False) + "\n" for z in zeilen),
        encoding="utf-8",
    )
    print(len(zeilen), "Systeme")


if __name__ == "__main__":
    main()
