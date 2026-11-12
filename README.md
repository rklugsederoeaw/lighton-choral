# LightOnOCR for chant: music notation and lyrics in one pass

This repository fine-tunes the page OCR model [LightOnOCR-3-1B](https://huggingface.co/lightonai/LightOnOCR-3-1B) (Pixtral ViT encoder, Qwen3-0.6B decoder) to read a staff of medieval plainchant together with the lyrics underneath. Input is an image of one staff with its text line; output is one string in the common GABC encoding of [AMNLT](https://huggingface.co/PRAIG), with syllables and neume groups interleaved:

```
(<m>c<m>4) De(<m>g<m>h)us(<m>g<m>V<m>f) (<m>:) me(<m>e<m>f<m>g)us(<m>f)
```

Letters `a`–`m` are staff positions (`d`, `f`, `h`, `j` are lines 1–4 from the bottom), read together with the clef (`c4`, `f3`). They are geometric, not absolute pitches.

Code comments and script names are German; the glossary at the end maps them to English.

## Results

All runs: one H100, 4 epochs, encoder and decoder trained together (learning rates 1e-4 and 5e-5). The checkpoint is chosen by pitch error rate on AMNLT validation only. *Held-out manuscripts* are 200 verified staves from five Transkribus manuscripts that are in no training set (A-Wn 15484 square notation; A-Geras 6, A-Gu 17, A-VOR 254 German Gothic; A-KN 65 Bohemian Gothic).

| Run | Training data | AMNLT val pitch SER | Held-out pitch SER | Held-out initial clef | Held-out lyrics CER (normalised) |
| --- | --- | --- | --- | --- | --- |
| `s4` | AMNLT (3,923 staves) | 1.77 % | 24.92 % | 80.5 % | 15.51 % |
| `s4k` | + 2,160 CantusDB staves (3 manuscripts) | 1.79 % | 9.55 % | 89.5 % | 12.17 % |
| `s4g` | + 8,781 CantusDB staves (10 manuscripts) | 1.86 % | 5.84 % | 96.5 % | 9.57 % |
| `s4w` | as `s4g`, AMNLT with word boundaries | 1.68 % | 4.67 % | 88.5 % | 8.34 % |
| `s4t` | as `s4w`, + 569 staves from 4 Gothic Transkribus manuscripts | running | | | |

For comparison, the project's CRNN hybrid trained only on the Volpiano ground truth (`hybrid_hybrid_lang`, greedy, without beam search, melody model or concordances) reaches 13.88 % pitch SER on the same 200 held-out staves. `s4k` on AMNLT test (562 staves): 1.77 % pitch SER, 2.67 % lyrics CER.

Caveats: AMNLT splits are not page-disjoint, so AMNLT figures are optimistic. Held-out figures rest on 40 staves per manuscript and vary between epochs by about one point. Lyrics are measured against the corrected Transkribus text, which expands abbreviations and leaves out the letter of decorated initials. Details and all numbers: `docs/bericht_zwischenstand_de.md` (German).

## Getting model and data

Both live in private Hugging Face repositories of the organisation `AlicanteViennaConnection`.

```bash
pip install -r requirements.txt
hf auth login
# training and evaluation data (about 2.6 GB), unpacks into ./daten
hf download AlicanteViennaConnection/lighton-choral-data --repo-type dataset --local-dir .
# fine-tuned model
hf download AlicanteViennaConnection/lighton-choral --local-dir runs/lighton-choral
# base model, only needed for training from scratch
hf download lightonai/LightOnOCR-3-1B --local-dir models/LightOnOCR-3-1B
python konvertieren.py
```

`konvertieren.py` is required before training from the base model: the original checkpoint stores the decoder under `language_model.model.*`, while transformers 5.22 expects `model.language_model.*` and otherwise leaves the decoder randomly initialised without an error.

## Reading new images

`lesen.py` reads a JSON lines file; each line needs at least `id`, `quelle` (source name) and `bild` (image path relative to the repository root).

```bash
python lesen.py --model runs/lighton-choral --device cuda --liste my_staves.jsonl --aus my_readings.jsonl
```

Each image must show one staff with its text line and no part of the next staff: a foreign staff in the crop raises the pitch error rate from 1 % to 13 % (half a staff) and 60 % (full staff). `systeme_pagexml.py` cuts such crops from Transkribus PAGE XML (notation and text regions). Long staves are cut into stacked strips (`bildform.py`, form `streifen`), small crops are upscaled to 1,540 px, because a staff step must stay above the 14 px ViT patch.

Speed: H100 0.4–0.7 s per staff (bf16), AMD Strix Halo iGPU (ROCm) 4–7 s, 6 CPU cores 20–40 s. No repetition penalty is used, because repeated notes are normal in chant; repetition loops are detected afterwards (`metriken.schleife`).

## Evaluation

```bash
# AMNLT validation or test, or any list with a reference field "ziel"
python auswertung.py --model runs/lighton-choral --split validation --bild streifen
python auswertung.py --model runs/lighton-choral --split validation --bild streifen --liste daten/korpus_gabc/validation.jsonl
# held-out manuscripts: read, then compare pitches and initial clef with the verified ground truth
python lesen.py --model runs/lighton-choral --device cuda --liste daten/gt/systeme.jsonl --aus daten/gt/readings.jsonl
python vergleich_gt.py daten/gt/readings.jsonl
```

Measures (`metriken.py`): note SER over all music tokens, pitch SER over staff positions only, clef SER, initial clef, neume boundary F1, lyrics CER (without spaces), syllable SER, WER where word boundaries exist, whole-string CER, loops and truncated outputs. `fehlerarten.py` breaks note errors down by kind.

## Training

```bash
SYSTEME=daten/systeme_wg.jsonl python train.py --bild streifen --epochs 4 --out runs/my_run \
    --zusatz daten/korpus_gabc/train.jsonl daten/korpus_transkribus/train.jsonl
```

`SYSTEME` selects the AMNLT list (`systeme_wg.jsonl` has word boundaries restored from CantusDB for Einsiedeln and Salzinnes). `--zusatz` adds further lists to training only. One staff per forward pass with gradient accumulation (8), bf16 autocast, gradient checkpointing, 24 GB peak on an H100; 4 epochs over 13,000 staves take about 5.5 h. `cluster/train.sh` is the SLURM job used on the Austrian MUSICA cluster (Apptainer, NGC PyTorch 25.04, transformers 5.22.1): it checks the upload against a manifest, trains, and reads AMNLT validation, corpus validation, Transkribus validation and the held-out manuscripts with every checkpoint.

## Data

All files in `daten/` use paths relative to the repository root.

| Path | Content | Staves |
| --- | --- | --- |
| `daten/systeme.jsonl`, `daten/bilder/` | AMNLT Einsiedeln, Salzinnes, Solesmes (from `PRAIG/*_staffLevel`, deduplicated), splits as published | 5,602 |
| `daten/systeme_wg.jsonl` | the same with word boundaries for Einsiedeln and Salzinnes | 5,602 |
| `daten/korpus_gabc/` | ten manuscripts with CantusDB melodies: verified OMR notes, lyrics from CantusDB `fulltext_ms`, syllables aligned through Volpiano, partly read from the image; crops with text line | 10,884 |
| `daten/korpus_transkribus/` | A-BRlm P33, P34, A-MB Man.Perg. 2, A-VOR 259/1: Transkribus note and text ground truth, syllables aligned by image reading, missing initial letters restored from a CantusDB lexicon (`unsicher.jsonl`: initial not restorable, not used) | 795 |
| `daten/gt/` | held-out manuscripts with verified notes (no lyrics reference in the file) | 200 |

Fields: `id`, `quelle`, `split`, `bild`, `ziel` (target string). Lyrics follow the transcription rules of the project: abbreviations expanded, words joined, u/v and capitals as in the source.

The repository is shared with the PRAIG/AMNLT colleagues of the joint project. Image rights remain with the holding libraries. AMNLT: PRAIG, University of Alicante.

## Data preparation (documentation)

These scripts document how the training data were built. They need the full working project (verified OMR ground truth, pipeline results, Transkribus exports, CantusDB database) and do not run on their own.

| Script | Step |
| --- | --- |
| `aufbereiten.py` | AMNLT from Hugging Face format to files and `systeme.jsonl` |
| `daten_pruefen.py`, `aufloesung.py` | vocabulary, lengths, pixels per staff step |
| `silben_cantus.py` | Latin syllabification, check against CantusDB Volpiano |
| `wortgrenzen_amnlt.py` | word boundaries for AMNLT from CantusDB lyrics |
| `upstream/gabc_zeilen.py`, `upstream/gabc_transkribus.py` | syllable-to-neume alignment for CantusDB and Transkribus lines (from the working project) |
| `korpus_cantus.py`, `korpus_gabc.py`, `korpus_transkribus.py` | crops with text line; drop crops with a foreign staff line at the bottom or cut text |
| `systeme_pagexml.py` | staff plus text crops from PAGE XML |
| `crnn_lesen.py`, `vergleich_modelle.py`, `text_vergleich.py`, `bleed_test.py` | comparisons and tests behind the numbers above |

## Glossary

| German | English |
| --- | --- |
| `lesen` / Lesung | read / reading |
| `auswertung` | evaluation |
| `metriken` | metrics |
| `bildform`, Streifen | image layout, strips |
| `vergleich_gt` | comparison with ground truth |
| `fehlerarten` | error types |
| `konvertieren` | convert |
| `ziel` | target |
| `quelle` | source (manuscript) |
| `bild` | image |
| Tonlage | staff position (pitch) |
| Schlüssel | clef |
| Silbe | syllable |
| Schleife | repetition loop |
| `daten`, `korpus` | data, corpus |
| `zusatz` | additional (training lists) |

## Licence

Code: to be decided by the project lead. Base model LightOnOCR-3-1B: Apache 2.0.
