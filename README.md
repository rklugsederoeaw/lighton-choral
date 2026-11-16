# LightOnOCR for chant: music notation and lyrics in one pass

This repository fine-tunes the page OCR model [LightOnOCR-3-1B](https://huggingface.co/lightonai/LightOnOCR-3-1B) (Pixtral ViT encoder, Qwen3-0.6B decoder) to read a staff of medieval plainchant together with the lyrics underneath. The current model, `seiten_d`, also reads whole pages and writes one line per staff. Input is an image of one staff with its text line, or of several staves up to a whole page; output per staff is one string in the common GABC encoding of [AMNLT](https://huggingface.co/PRAIG), with syllables and neume groups interleaved:

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
| `s4t` | as `s4w`, + 569 staves from 4 Gothic Transkribus manuscripts | 1.80 % | 2.11 % | 92.5 % | 7.90 % |

`s4t` (epoch 4) is the best model trained on single staves only; the current standard is the page model `seiten_d` described in the next section. On a wider check `s4t` reads 3,015 staves from 17 further Transkribus manuscripts, none of them in training, with 2.62 % pitch SER; one more source written in lesson tone with long recitation bars is left out, because its ground truth counts a bar as one note while the model writes one note per syllable. The four training sources of `s4t` reach 1.06 % on all their 1,260 staves. Figures per manuscript: `docs/pool_messung.md` (German).

For comparison, the project's CRNN hybrid trained only on the Volpiano ground truth (`hybrid_hybrid_lang`, greedy, without beam search, melody model or concordances) reaches 13.88 % pitch SER on the same 200 held-out staves. `s4k` on AMNLT test (562 staves): 1.77 % pitch SER, 2.67 % lyrics CER.

Caveats: AMNLT splits are not page-disjoint, so AMNLT figures are optimistic. Held-out figures rest on 40 staves per manuscript and vary between epochs by about one point. Until 13 November 2026, `metriken.py` misread a clef on the fifth line (`c5`) as a note; this only affected Transkribus and corpus lists, and the figures above are corrected. Lyrics are measured against the corrected Transkribus text, which expands abbreviations and leaves out the letter of decorated initials. Details and all numbers: `docs/bericht_zwischenstand_de.md` (German).

## Page model `seiten_d`

`seiten_d` (epoch 4, `checkpoint-118508`, 15 November 2026) is the current standard model. It is trained from the base model with the same settings as the runs above, on single staves and on images that show several staves: page sections, half pages and whole pages. For such an image it writes one line per staff, from top to bottom. `train.py` is unchanged; the page model differs only in its training lists.

Training data, 29,627 examples per epoch:

| Block | Examples |
| --- | ---: |
| AMNLT with word boundaries; staves starting with an F clef counted twice | 4,633 |
| CantusDB corpus (ten manuscripts) | 10,463 |
| Transkribus corpus (four Gothic manuscripts) | 611 |
| Graz manuscripts and printed chant books: human notes, corrected text | 1,487 |
| 14 further Graz volumes: human notes, corrected text ("gold") | 463 |
| "Silver" manuscript staves: notes read by the model, kept only where the earlier page model `seiten_b` and the project's CRNN agree exactly; lyrics from the corrected text | 2,446 |
| "Silver" staves from printed chant books, capped | 1,500 |
| Images with several staves: 5,585 sections, 529 half pages and 284 whole pages, half and whole pages counted three times | 8,024 |

Results (pitch SER unless stated; `s4t` cannot read pages, without page training it writes about one staff and stops):

| Measure | `s4t` | `seiten_d` |
| --- | ---: | ---: |
| AMNLT validation | 1.80 % | 1.74 % |
| Held-out manuscripts, 200 staves | 2.11 % | 1.31 % |
| Held-out manuscripts, initial clef | 92.5 % | 91.0 % (F clef 30 of 47, C clef 152 of 153) |
| Transkribus validation, lyrics CER | – | 3.30 % |
| Whole pages, 9 validation pages | – | 3.34 % (all staves found) |
| Whole pages, 14 test pages | – | 3.82 % |
| Whole pages, 20 pages of the held-out manuscripts | – | 1.9 % (99.4 % of staves found) |

The same pages read in other forms with `seiten_d` (validation and test pages / held-out pages): whole page 3.6 % / 1.9 %, two halves 2.3 % / 1.2 %, sections 2.6 % / 1.2 %, single staves cut from known boxes 1.7 % / 2.5 %. No truncated outputs and no repetition loops on pages.

AMNLT test split (562 staves, reported only, never used for selection), AMLER as defined in the AMNLT paper (Fuentes-Martínez et al., Pattern Recognition 170, 2026), measured with `metriken.py`:

| Dataset | `s4` (AMNLT training data only) | `s4t` | `seiten_d` | best value in the paper |
| --- | ---: | ---: | ---: | ---: |
| Solesmes | 9.92 % | 9.35 % | 8.80 % | 20.98 % (unfolding CRNN) |
| Einsiedeln | 2.25 % | 1.84 % | 1.87 % | 5.14 % (DAN) |
| Salzinnes | 5.31 % | 4.54 % | 4.36 % | 7.32 % (SMT) |

Over all 562 staves `seiten_d` has 1.25 % pitch SER and 1.86 % lyrics CER. Read these figures with care: only Solesmes is directly comparable. For Einsiedeln and Salzinnes this repository trains and measures on the common GABC encoding (one character per note sign), the paper on pseudo gabc tokens, so token counts and denominators differ. From `s4k` on, the CantusDB corpus contains CH-E 611, the same manuscript as Einsiedeln; `s4` is the like-for-like row. All tables, MER, CER, SylER, bWER and AlER: `metriken.md` (German).

Limits: the Gothic F clef remains the weakest point (17 of 47 initial F clefs wrong on the held-out manuscripts). With small notation (less than about 14 px per staff step after scaling to 1,540 px) two halves read better than the whole page. Each run has one seed. The validation loss does not select the best epoch (it would have chosen epoch 3); the checkpoint is chosen by pitch SER on AMNLT validation and on the nine validation pages, which agreed. Full report with all epochs and sets: `docs/seiten_versuch.md` (German).

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

The Hugging Face repositories were set up for `s4t`. The page model `seiten_d` and the additional lists and images it was trained on (`daten/seiten/`, the Graz corpora, the silver corpus) are not uploaded yet; until then they are available from the project lead.

`konvertieren.py` is required before training from the base model: the original checkpoint stores the decoder under `language_model.model.*`, while transformers 5.22 expects `model.language_model.*` and otherwise leaves the decoder randomly initialised without an error.

## Reading new images

`lesen.py` reads a JSON lines file; each line needs at least `id`, `quelle` (source name) and `bild` (image path relative to the repository root).

```bash
python lesen.py --model runs/lighton-choral --device cuda --liste my_staves.jsonl --aus my_readings.jsonl
```

Each image must show one staff with its text line and no part of the next staff: a foreign staff in the crop raises the pitch error rate from 1 % to 13 % (half a staff) and 60 % (full staff). `systeme_pagexml.py` cuts such crops from Transkribus PAGE XML (notation and text regions). Long staves are cut into stacked strips (`bildform.py`, form `streifen`), small crops are upscaled to 1,540 px, because a staff step must stay above the 14 px ViT patch.

Whole pages are read the same way with `seiten_d`: one image per line of the list, and a larger output limit.

```bash
python lesen.py --model runs/seiten_d/checkpoint-118508 --device cuda --max-tokens 4096 --liste my_pages.jsonl --aus my_readings.jsonl
```

The reading has one line per staff. Images are scaled to at most 1,540 px on the longest edge; for half pages 3,072 tokens are enough. `seiten_messen.py` measures page readings against page targets (pitch SER over the page, staves found, truncation); `cluster/lesen_seiten.sh` is the SLURM job that reads the test pages as whole pages, halves, sections and single staves. A page takes 45–70 s on an AMD Strix Halo iGPU (ROCm).

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

The page model uses the same `train.py` with more lists. `cluster/train_seiten_d.sh` is the job that trained `seiten_d` (lists under `daten/seiten/c/` and `daten/seiten/d/`, built by `seiten.py` and `seiten_d.py`; 13.4 h training for 4 × 29,627 examples on one H100, 0.41 s per example, 26.8 GB peak; then it reads all validation sets, the held-out manuscripts and the test pages with every checkpoint).

## Data

All files in `daten/` use paths relative to the repository root.

| Path | Content | Staves |
| --- | --- | --- |
| `daten/systeme.jsonl`, `daten/bilder/` | AMNLT Einsiedeln, Salzinnes, Solesmes (from `PRAIG/*_staffLevel`, deduplicated), splits as published | 5,602 |
| `daten/systeme_wg.jsonl` | the same with word boundaries for Einsiedeln and Salzinnes | 5,602 |
| `daten/korpus_gabc/` | ten manuscripts with CantusDB melodies: verified OMR notes, lyrics from CantusDB `fulltext_ms`, syllables aligned through Volpiano, partly read from the image; crops with text line | 10,884 |
| `daten/korpus_transkribus/` | A-BRlm P33, P34, A-MB Man.Perg. 2, A-VOR 259/1: Transkribus note and text ground truth, syllables aligned by image reading, missing initial letters restored from a CantusDB lexicon (`unsicher.jsonl`: initial not restorable, not used) | 795 |
| `daten/gt/` | held-out manuscripts with verified notes (no lyrics reference in the file) | 200 |
| `daten/seiten/` | lists for the page model: images with several staves (sections, half pages, whole pages) from pages on which every staff has a target, test pages, and the training lists of `seiten_c` and `seiten_d`; not uploaded yet | 8,024 multi-staff examples per epoch |
| `daten/korpus_graz/`, `daten/korpus_graz14/` | Graz manuscripts and printed chant books, 14 further Graz volumes: Transkribus note ground truth, corrected text, syllables assigned directly; not uploaded yet | 1,769 and 516 |
| `daten/korpus_silber/` | silver staves: notes from the model where two readers agree, lyrics from the corrected text; not uploaded yet | 7,551 (6,918 used for training lists) |

Fields: `id`, `quelle`, `split`, `bild`, `ziel` (target string). Lyrics follow the transcription rules of the project: abbreviations expanded, words joined, u/v and capitals as in the source.

The repository is shared with the PRAIG/AMNLT colleagues of the joint project. Image rights remain with the holding libraries. AMNLT: PRAIG, University of Alicante.

## Data preparation (documentation)

These scripts document how the training data were built. The tools that built the Graz and silver corpora (pairing of note and text lines, the two-reader filter) stay in the working project. They need the full working project (verified OMR ground truth, pipeline results, Transkribus exports, CantusDB database) and do not run on their own.

| Script | Step |
| --- | --- |
| `aufbereiten.py` | AMNLT from Hugging Face format to files and `systeme.jsonl` |
| `daten_pruefen.py`, `aufloesung.py` | vocabulary, lengths, pixels per staff step |
| `silben_cantus.py` | Latin syllabification, check against CantusDB Volpiano |
| `wortgrenzen_amnlt.py` | word boundaries for AMNLT from CantusDB lyrics |
| `upstream/gabc_zeilen.py`, `upstream/gabc_transkribus.py` | syllable-to-neume alignment for CantusDB and Transkribus lines (from the working project) |
| `korpus_cantus.py`, `korpus_gabc.py`, `korpus_transkribus.py` | crops with text line; drop crops with a foreign staff line at the bottom or cut text |
| `systeme_pagexml.py` | staff plus text crops from PAGE XML |
| `seiten.py`, `seiten_d.py` | page inventory (pages on which every staff has a target), images with several staves, training lists of the page model (need `scipy`) |
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
| `seiten`, Seite | pages, page |
| `haelften`, `abschnitte` | half pages, sections |
| Mehrsystem | several staves in one image |
| Prüfhandschriften | held-out manuscripts |
| `messen` | measure |

## Licence

Code: Apache License 2.0, see `LICENSE`. Base model LightOnOCR-3-1B: Apache 2.0. Fine-tuned weights, if released: CC BY-NC 4.0, because the training data include the AMNLT datasets (CC BY-NC 4.0). The ground truth is not public; its licences are not yet settled.
