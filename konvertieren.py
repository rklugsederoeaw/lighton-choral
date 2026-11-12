"""Benennt die Decoder-Gewichte des Originals um, damit transformers 5.22 sie lädt.

Das Original speichert language_model.model.*; die Klasse erwartet model.language_model.*.
Ohne Umbenennung bleibt der Decoder ohne Fehlermeldung zufällig initialisiert.
"""

import shutil
from pathlib import Path

from safetensors.torch import load_file, save_file

HIER = Path(__file__).resolve().parent
QUELLE = HIER / "models/LightOnOCR-3-1B"
ZIEL = HIER / "models/LightOnOCR-3-1B-konvertiert"
ALT, NEU = "language_model.model.", "model.language_model."


def neu(name):
    return NEU + name[len(ALT) :] if name.startswith(ALT) else name


def main():
    ZIEL.mkdir(exist_ok=True)
    alt = load_file(QUELLE / "model.safetensors")
    gewichte = {neu(k): v for k, v in alt.items()}
    assert len(gewichte) == len(alt) == 532
    assert not any(k.startswith(ALT) for k in gewichte)
    save_file(gewichte, ZIEL / "model.safetensors", metadata={"format": "pt"})
    for name in (
        "config.json",
        "generation_config.json",
        "processor_config.json",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "chat_template.jinja",
    ):
        shutil.copy(QUELLE / name, ZIEL / name)
    print(sum(k.startswith(NEU) for k in gewichte), "umbenannt von", len(gewichte))


if __name__ == "__main__":
    assert neu("language_model.model.norm.weight") == "model.language_model.norm.weight"
    assert neu("model.vision_encoder.x") == "model.vision_encoder.x"
    main()
