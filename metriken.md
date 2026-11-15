# Messungen und Benchmarks aus dem AMNLT-Paper

Gesammelte Datensatz-Statistiken, Metrik-Definitionen und alle berichteten Messergebnisse aus:
Eliseo Fuentes-Martínez, Antonio Ríos-Vila, Juan C. Martinez-Sevilla, David Rizo, Jorge Calvo-Zaragoza: *„Aligned music notation and lyrics transcription“*, *Pattern Recognition* 170 (2026) 112094 ([Aligned_Music_Notation_Lyrics_transcription.md](Aligned_Music_Notation_Lyrics_transcription.md)).

> **Hinweis zu den Einheiten:** Im Paper werden **MER**, **CER**, **SylER** und **AMLER** in **Prozent (%)** angegeben, **AlER** dagegen als **Anteil in `[0, 1]`** (niedriger ist bei allen fünf Metriken besser). In [metriken.py](metriken.py) gibt `messe()` sämtliche Fehlerraten inklusive `amler` und `bwer` als Anteil in `[0, 1]` zurück (`2,93 %` im Paper entspricht `0.0293` in `metriken.py`).

---

## 1. Datensätze und Splits (Tabelle 1 & Abschnitt 5)

| Datensatz      | Systeme | Eindeutige Tokens | Typ                                      | Original-Notation | Adaptierte Zielkodierung   | Split (Train / Val / Test) |
| -------------- | -------:| -----------------:| ---------------------------------------- | ----------------- | -------------------------- | -------------------------- |
| **GregoSynth** | 126.579 | 399               | Hybrid (reale GT, GregorioTex-Render)    | `gabc`            | music-aware `gabc` (`<m>`) | 80 % / 15 % / 5 %          |
| **Solesmes**   | 854     | 137               | Real                                     | `s-gabc`          | music-aware `gabc` (`<m>`) | 70 % / 20 % / 10 %         |
| **Einsiedeln** | 1.816   | 177               | Real (14. Jh., Antiphonar)               | `MEI`             | `pseudo gabc`              | 70 % / 20 % / 10 %         |
| **Salzinnes**  | 2.965   | 183               | Real (16. Jh., Zisterzienser-Antiphonar) | `MEI`             | `pseudo gabc`              | 70 % / 20 % / 10 %         |

- **GregoSynth-Ursprung:** abgeleitet aus nahezu 20.000 Partiturseiten der *Gregorian Chant Database* (GregoBase), zerlegt in Einzelsysteme.

---

## 2. Verwendete Metriken (Abschnitt 6)

| Metrik             | Bedeutung                         | Berechnung im Paper                                                                                     | Entsprechung in [metriken.py](metriken.py)                       |
| ------------------ | --------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **MER** (%)        | Music Error Rate                  | Edit-Distanz auf Musik-Tokens (Character-Level bei `gabc`/`s-gabc`, Token/Word-Level bei `pseudo gabc`) | `noten_ser` × 100 (bzw. `tonlage_ser` ohne Schlüssel/Neumenform) |
| **CER** (%)        | Character Error Rate              | Zeichen-Edit-Distanz auf den extrahierten Lyrics                                                        | `text_cer` × 100                                                 |
| **SylER** (%)      | Syllable Error Rate               | Wort-/Silben-Edit-Distanz auf den extrahierten Lyrics                                                   | `silben_ser` × 100                                               |
| **AMLER** (%)      | Aligned Music & Lyrics Error Rate | Normalisierte Edit-Distanz (Macro-Mittel) auf der gemeinsamen Tokenfolge                                | `amler` × 100                                                    |
| **bWER** (%)       | Baseline Word Error Rate          | Bag-of-Words-Edit-Distanz derselben Tokenfolge (ohne Reihenfolge)                                       | `bwer` × 100                                                     |
| **AlER** (`[0,1]`) | Alignment Error Rate              | `(AMLER - bWER) / AMLER` (Anteil des Fehlers durch falsche Zuordnung)                                   | `aler`                                                           |

---

## 3. Hauptergebnisse: GregoSynth und Solesmes (Tabelle 2)

Fettdruck kennzeichnet den Bestwert pro Spalte (wie in Tabelle 2 des Papers). Bei *Divide & Conquer* teilen sich beide Post-Alignment-Varianten dieselben Transkriptionsfehler (MER, CER, SylER).

| Ansatz / Implementierung                          | GregoSynth MER | GregoSynth CER | GregoSynth SylER | GregoSynth AMLER | GregoSynth AlER | Solesmes MER | Solesmes CER | Solesmes SylER | Solesmes AMLER | Solesmes AlER |
| ------------------------------------------------- | --------------:| --------------:| ----------------:| ----------------:| ---------------:| ------------:| ------------:| --------------:| --------------:| -------------:|
| **Divide & Conquer (CRNN-CTC) — Syllable**        | 2,79           | **4,54**       | **8,66**         | 13,40            | 0,59            | **17,72**    | **8,86**     | **20,84**      | 23,08          | 0,53          |
| **Divide & Conquer (CRNN-CTC) — CTC frames**      | 2,79           | **4,54**       | **8,66**         | 22,29            | 0,30            | **17,72**    | **8,86**     | **20,84**      | 57,48          | 0,19          |
| **Base Holistic — CRNN-CTC**                      | 59,99          | 89,29          | 98,91            | 62,47            | 0,10            | 24,91        | 38,36        | 73,59          | 29,71          | 0,28          |
| **Unfolding — FCN**                               | 3,82           | 16,05          | 37,44            | 8,64             | 0,09            | 25,14        | 40,51        | 88,62          | 21,08          | 0,38          |
| **Unfolding — CRNN**                              | 4,00           | 10,77          | 25,11            | 5,85             | 0,04            | 18,20        | 19,11        | 38,88          | **20,98**      | 0,38          |
| **Unfolding — CNNT2D**                            | 22,70          | 50,03          | 89,93            | 31,28            | 0,13            | 64,42        | 88,97        | 97,32          | 71,82          | 0,08          |
| **Unfolding — VAN**                               | 71,08          | 92,18          | 99,28            | 55,47            | 0,09            | 63,15        | 66,04        | 100,00         | 62,62          | 0,19          |
| **Unfolding — OrigamiNet**                        | 51,42          | 81,96          | 99,34            | 49,85            | 0,12            | 62,03        | 64,83        | 100,00         | 58,86          | 0,22          |
| **Language Modeling (Img2Seq) — SMT**             | **2,26**       | 6,39           | 15,82            | **2,93**         | 0,09            | 35,37        | 52,87        | 91,00          | 41,19          | 0,39          |
| **Language Modeling (Img2Seq) — DAN**             | 9,05           | 11,74          | 25,00            | 9,52             | 0,16            | 21,87        | 17,94        | 30,19          | 23,17          | 0,39          |
| **Language Modeling (Img2Seq) — TrOCR**           | 100,00         | 97,30          | 99,88            | 77,81            | 0,00            | 100,00       | 100,00       | 100,00         | 100,00         | 0,00          |
| **Language Modeling (VLM) — PaliGemma 2 w/ LoRA** | 80,85          | 64,92          | 99,94            | 60,67            | 0,12            | 59,87        | 51,93        | 100,00         | 70,20          | 0,39          |

---

## 4. Hauptergebnisse: Einsiedeln und Salzinnes (Tabelle 3)

Fettdruck kennzeichnet den Bestwert pro Spalte (wie in Tabelle 3 des Papers).

| Ansatz / Implementierung                          | Einsiedeln MER | Einsiedeln CER | Einsiedeln SylER | Einsiedeln AMLER | Einsiedeln AlER | Salzinnes MER | Salzinnes CER | Salzinnes SylER | Salzinnes AMLER | Salzinnes AlER |
| ------------------------------------------------- | --------------:| --------------:| ----------------:| ----------------:| ---------------:| -------------:| -------------:| ---------------:| ---------------:| --------------:|
| **Divide & Conquer (CRNN-CTC) — Syllable**        | 11,36          | 5,47           | 12,68            | 35,08            | 0,54            | 22,44         | **2,84**      | 7,98            | 14,70           | 0,33           |
| **Divide & Conquer (CRNN-CTC) — CTC frames**      | 11,36          | 5,47           | 12,68            | 90,94            | 0,11            | 22,44         | **2,84**      | 7,98            | 87,76           | 0,17           |
| **Base Holistic — CRNN-CTC**                      | 11,82          | 9,95           | 23,06            | 10,21            | 0,15            | 19,90         | 5,88          | 13,93           | 10,89           | 0,13           |
| **Unfolding — FCN**                               | 30,41          | 31,96          | 65,28            | 26,74            | 0,20            | 67,25         | 62,83         | 98,35           | 54,49           | 0,24           |
| **Unfolding — CRNN**                              | 14,26          | 7,96           | 18,60            | 10,43            | 0,17            | 20,37         | 6,23          | 14,59           | 11,12           | 0,14           |
| **Unfolding — CNNT2D**                            | 79,60          | 61,54          | 98,90            | 56,18            | 0,10            | 80,24         | 16,33         | 39,65           | 43,49           | 0,12           |
| **Unfolding — VAN**                               | 92,75          | 94,56          | 98,21            | 67,45            | 0,10            | 52,82         | 60,78         | 98,05           | 46,01           | 0,26           |
| **Unfolding — OrigamiNet**                        | 76,79          | 61,39          | 97,35            | 56,22            | 0,14            | 88,15         | 69,35         | 100,00          | 61,33           | 0,08           |
| **Language Modeling (Img2Seq) — SMT**             | 14,05          | 8,45           | 15,84            | 10,78            | 0,21            | **13,73**     | 3,69          | **7,80**        | **7,32**        | 0,14           |
| **Language Modeling (Img2Seq) — DAN**             | **7,23**       | **3,44**       | **7,19**         | **5,14**         | 0,17            | 29,46         | 12,34         | 21,08           | 18,73           | 0,25           |
| **Language Modeling (Img2Seq) — TrOCR**           | 93,32          | 98,71          | 100,00           | 95,76            | 0,00            | 80,88         | 99,49         | 100,00          | 88,16           | 0,01           |
| **Language Modeling (VLM) — PaliGemma 2 w/ LoRA** | 91,05          | 50,40          | 89,20            | 55,28            | 0,31            | 96,93         | 47,59         | 93,72           | 47,14           | 0,24           |

---

## 5. Im Text berichtete aggregierte Vergleiche & Einzelfall-Messungen (Abschnitt 8)

### Aggregierte relative Verbesserungen

- **SMT vs. beste Divide-&-Conquer-Variante (Syllable post-alignment), Durchschnitt über die vier Datensätze:**
  - **AMLER:** **27,86 %** relative Verbesserung
  - **AlER:** **58,29 %** relative Verbesserung
- **Unfolding-CRNN auf Einsiedeln (Abschnitt 8, Vergleich gegen die Divide-&-Conquer-Syllable-Baseline `35,08 %` AMLER / `0,54` AlER):**
  - **AMLER:** **70,27 %** Verbesserung (`35,08` → `10,43`)
  - **AlER:** **68,52 %** Verbesserung (`0,54` → `0,17`)

### Qualitative Einzelbeispiele (Abschnitt 8.1, Fig. 14 & Fig. 15)

- **Fig. 14 — DAN-Fehlerbeispiel** (perfekter Text, Versagen bei Noten):
  - `CER = 0,00 %` · `MER = 93,75 %` · `AMLER = 45,55 %`
- **Fig. 15 — SMT-Vorhersagebeispiel** (ausgeglichene Fehlerverteilung über beide Modalitäten):
  - `CER = 19,64 %` · `MER = 11,76 %` · `AMLER = 15,29 %`

---

## 6. Kompakter Zielkorridor für eigene Benchmarks

| Datensatz                  | Bestes AMLER im Paper | Modell         | Zugehöriges AlER | MER / CER / SylER dieses Modells |
| -------------------------- | ---------------------:| -------------- | ----------------:| -------------------------------- |
| **GregoSynth**             | **2,93 %**            | SMT            | 0,09             | 2,26 % / 6,39 % / 15,82 %        |
| **Solesmes** (854 Systeme) | **20,98 %**           | Unfolding CRNN | 0,38             | 18,20 % / 19,11 % / 38,88 %      |
| **Einsiedeln**             | **5,14 %**            | DAN            | 0,17             | 7,23 % / 3,44 % / 7,19 %         |
| **Salzinnes**              | **7,32 %**            | SMT            | 0,14             | 13,73 % / 3,69 % / 7,80 %        |

*(Hinweis zur Interpretation von `AlER`: Bei `TrOCR` oder `Unfolding CNNT2D` treten teils sehr niedrige `AlER`-Werte wie `0,00`–`0,10` auf, weil bei `77–100 % AMLER` fast ausschließlich Inhaltsfehler vorliegen. Aussagekräftig ist `AlER` daher immer nur gemeinsam mit `AMLER`.)*

---

## 7. Eigene Messungen auf dem AMNLT-Testsplit (LightOnOCR-Choral)

Gemessen mit `messe()` aus [metriken.py](metriken.py) auf dem Testsplit der drei realen AMNLT-Datensätze (PRAIG `*_staffLevel`, 562 Systeme: Solesmes 86, Einsiedeln 182, Salzinnes 294; das entspricht den 10 % der Tabelle 1). Alle Werte in Prozent außer AlER. Der Testsplit wird nur berichtet und beeinflusst weder Training noch Checkpoint-Wahl. GregoSynth ist nicht gemessen.

| Datensatz | Modell | Systeme | MER | Tonlage-SER | CER | SylER | AMLER | bWER | AMLER − bWER | AlER |
| --- | --- | ---:| ---:| ---:| ---:| ---:| ---:| ---:| ---:| ---:|
| Solesmes | Paper, bestes AMLER (Unfolding CRNN) | – | 18,20 | – | 19,11 | 38,88 | 20,98 | 13,01 | 7,97 | 0,38 |
| Solesmes | Paper, DAN | – | 21,87 | – | 17,94 | 30,19 | 23,17 | 14,13 | 9,04 | 0,39 |
| Solesmes | s4 | 86 | 9,63 | 1,87 | 5,54 | 13,98 | 9,92 | 6,64 | 3,28 | 0,33 |
| Solesmes | s4k | 86 | 11,12 | 2,70 | 6,30 | 16,07 | 11,55 | 8,41 | 3,14 | 0,27 |
| Solesmes | s4t | 86 | 9,58 | 1,50 | 5,26 | 11,50 | 9,35 | 5,91 | 3,44 | 0,36 |
| Solesmes | seiten_b | 86 | 8,77 | 1,34 | 5,26 | 11,76 | 8,76 | 5,56 | 3,20 | 0,36 |
| Solesmes | seiten_c | 86 | 8,82 | 1,52 | 5,70 | 11,82 | 8,89 | 5,90 | 2,99 | 0,33 |
| Solesmes | seiten_d | 86 | 8,92 | 1,23 | 5,10 | 10,91 | 8,80 | 5,61 | 3,19 | 0,36 |
| Einsiedeln | Paper, bestes AMLER (DAN) | – | 7,23 | – | 3,44 | 7,19 | 5,14 | 4,27 | 0,87 | 0,17 |
| Einsiedeln | s4 | 182 | 1,93 | 1,23 | 2,36 | 4,78 | 2,25 | 1,56 | 0,69 | 0,30 |
| Einsiedeln | s4k | 182 | 1,84 | 1,24 | 2,34 | 4,36 | 2,15 | 1,50 | 0,65 | 0,30 |
| Einsiedeln | s4t | 182 | 1,67 | 1,00 | 1,60 | 3,42 | 1,84 | 1,19 | 0,65 | 0,34 |
| Einsiedeln | seiten_b | 182 | 1,59 | 1,01 | 1,35 | 3,18 | 1,82 | 1,21 | 0,61 | 0,33 |
| Einsiedeln | seiten_c | 182 | 1,70 | 1,00 | 1,53 | 3,39 | 2,02 | 1,32 | 0,70 | 0,34 |
| Einsiedeln | seiten_d | 182 | 1,68 | 1,10 | 1,15 | 2,84 | 1,87 | 1,10 | 0,77 | 0,41 |
| Salzinnes | Paper, bestes AMLER (SMT) | – | 13,73 | – | 3,69 | 7,80 | 7,32 | 6,30 | 1,02 | 0,14 |
| Salzinnes | Paper, DAN | – | 29,46 | – | 12,34 | 21,08 | 18,73 | 14,05 | 4,68 | 0,25 |
| Salzinnes | s4 | 294 | 8,12 | 1,63 | 1,56 | 4,06 | 5,31 | 4,47 | 0,84 | 0,15 |
| Salzinnes | s4k | 294 | 8,04 | 1,77 | 1,14 | 3,31 | 4,42 | 3,66 | 0,76 | 0,17 |
| Salzinnes | s4t | 294 | 8,20 | 1,32 | 1,19 | 3,47 | 4,54 | 3,86 | 0,68 | 0,14 |
| Salzinnes | seiten_b | 294 | 8,02 | 1,61 | 1,26 | 3,37 | 4,60 | 3,82 | 0,78 | 0,17 |
| Salzinnes | seiten_c | 294 | 8,26 | 1,54 | 1,36 | 3,69 | 4,57 | 3,66 | 0,91 | 0,19 |
| Salzinnes | seiten_d | 294 | 8,26 | 1,41 | 0,92 | 2,74 | 4,36 | 3,53 | 0,83 | 0,18 |

`s4t` ist `runs/s4t/checkpoint-53092`, `seiten_b` ist `runs/seiten_b/checkpoint-71296` (Epoche 4), beide als Systemlesung gemessen (MUSICA-Job 1943041). Die Zeile für `seiten_c` folgt nach der Checkpoint-Wahl (Stand 14.11.2026).

Lesehinweise:

- **Spalten:** MER ist `noten_ser` (alle Notenzeichen einschließlich Schlüssel und Neumenform), Tonlage-SER nur die Tonhöhen, CER ist `text_cer`, SylER ist `silben_ser`. AMLER und bWER sind Mittel über die Beispiele wie im Skript der Autoren. Die bWER-Werte der Paper-Zeilen sind aus AMLER und AlER zurückgerechnet, `bWER = AMLER · (1 − AlER)`; das Paper weist bWER nicht aus.
- **AMLER − bWER:** der absolute Ausrichtungsfehler in Prozentpunkten. AlER ist ein Anteil am Gesamtfehler und steigt, wenn der Inhaltsfehler sinkt; deshalb beide Spalten zusammen lesen.
- **Solesmes ist direkt vergleichbar:** Die Tokenbildung (Silben, einzelne Klammern, einzelne Notenzeichen) entspricht dem Skript der Autoren bis auf zwei Kleinigkeiten (dort ohne Präfix an den Notenzeichen, Silbentrennung nur an Klammern).
- **Einsiedeln und Salzinnes nur mit Vorbehalt:** Das Paper zerlegt dort die Pseudo-gabc-Kodierung über ein Vokabular in Mehrzeichen-Token (etwa `a2-s`), wir messen auf unserer gabc-artigen Kodierung mit einem Token je Notenzeichen. Der Nenner ist bei uns größer; ein Teil des Abstands kann aus der Zählweise kommen. Dasselbe gilt für MER.
- **Vergleichsmodell:** Der Bauart nach entspricht unserem Ansatz die Gruppe Language Modeling des Papers (DAN, SMT, PaliGemma), also Modelle, die das Bild ohne Zeilenentfaltung in eine Folge übersetzen und grundsätzlich auch ganze Seiten lesen können; Unfolding CRNN liest nur einzelne Systeme. Deshalb steht DAN bei jedem Datensatz als eigene Zeile. Gemessen hat das Paper alle Modelle auf Einzelsystemen, Seitenwerte gibt es dort nicht.
- **Ausgangslage:** Die Modelle des Papers sind je Datensatz trainiert. Unsere Modelle setzen auf dem vortrainierten LightOnOCR auf und sehen zusätzlich die CantusDB-Korpora und Transkribus-GT.
- **Modelle:** `s4` kennt nur die AMNLT-Trainingsdaten, also dieselben Daten wie die Verfahren des Papers, und ist deshalb die sauberste Vergleichszeile (Lesejob 1943368, 14.11.2026, Epoche 3, `checkpoint-11769`); ab `s4k` steckt CH-E 611, dieselbe Handschrift wie Einsiedeln, über das CantusDB-Korpus im Training. `s4k` ist ein früherer Stand des Systemmodells; `s4t` ist das beste Systemmodell (README des Repos), `seiten_b` und `seiten_c` lesen zusätzlich ganze Seiten.

## 8. Ausgelassene Töne und Einheiten (eigene Messgrößen, seit 15.11.2026)

Anlass: Beim Lesen ungesehener Handschriften fehlten Töne an Stellen, an denen auch die Silbe fehlte, meist bei abgekürzten Wörtern (Beobachtung des Projektleiters). Das Modell schreibt Silbe und Notengruppe als Einheit und kann sie als Einheit überspringen. `messe()` in [metriken.py](metriken.py) weist das seither getrennt aus.

| Schlüssel | Bedeutung |
| --- | --- |
| `toene_geloescht`, `toene_eingefuegt`, `toene_ersetzt` | Tonlage-SER nach Fehlerart zerlegt: fehlender, überzähliger, falscher Ton, je als Anteil der Referenztöne; die drei ergeben zusammen `tonlage_ser`. Geht auch gegen reine Noten-GT. |
| `einheit_weg` | Anteil der Einheiten (Silbe mit Tönen), die ganz fehlen: Silbe in der Ausrichtung der Silbenfolgen gestrichen und alle ihre Töne in der Ausrichtung der Tonfolgen gestrichen (`auslassungen()`). Strenge Zählung, also eine untere Grenze: Stehen Nachbartöne falsch, wertet die Ausrichtung einen fehlenden Ton teils als ersetzt. |
| `toene_weg` | Töne dieser Einheiten als Anteil aller Referenztöne. |

Alle Werte in Prozent. `seiten_d` Epoche 4, Systemlesung:

| Menge | fehlend | überzählig | falsch | Tonlage-SER | `einheit_weg` |
| --- | ---:| ---:| ---:| ---:| ---:|
| AMNLT test | 0,40 | 0,35 | 0,50 | 1,25 | 0,03 |
| AMNLT validation | 0,62 | 0,55 | 0,58 | 1,74 | 0,03 |
| CantusDB-Korpus validation | 1,48 | 1,51 | 2,73 | 5,72 | 0,48 |
| Transkribus validation | 0,08 | 0,35 | 0,12 | 0,54 | 0,00 |
| korpus_graz validation | 0,18 | 0,37 | 0,42 | 0,97 | 0,00 |
| korpus_graz14 validation | 0,00 | 1,37 | 0,46 | 1,82 | 0,00 |

Prüfhandschriften (200 Systeme, nur Noten-GT) und ganze Seiten. Achtung bei den Seiten: Diese Zeilen sind über alle 25 val- und test-Seiten mit Textziel gerechnet (9 val, 16 test). Die Standardmessung in `docs/seiten_versuch.md` lässt zwei test-Seiten aus, die nach Berichtigungen der Ziele nicht mehr vollständig sind, und kommt für `seiten_d` auf 3,34 % (9 val) und 3,82 % (14 test); für Vergleiche gelten jene Werte, die Zeilen hier zeigen nur die Zerlegung nach Fehlerart:

| Menge | Modell | fehlend | überzählig | falsch | Tonlage-SER | `einheit_weg` |
| --- | --- | ---:| ---:| ---:| ---:| ---:|
| Prüfhandschriften | `s4t` | 0,47 | 1,00 | 0,64 | 2,11 | – |
| Prüfhandschriften | `seiten_b` | 0,35 | 1,13 | 0,27 | 1,74 | – |
| Prüfhandschriften | `seiten_c` | 0,49 | 0,61 | 0,16 | 1,27 | – |
| Prüfhandschriften | `seiten_d` | 0,72 | 0,49 | 0,10 | 1,31 | – |
| Ganze Seiten | `seiten_b` | 2,03 | 0,77 | 1,51 | 4,32 | 0,31 |
| Ganze Seiten | `seiten_c` | 1,58 | 0,78 | 1,55 | 3,92 | 0,33 |
| Ganze Seiten | `seiten_d` | 1,29 | 0,80 | 1,44 | 3,54 | 0,10 |

`einheit_weg` auf dem AMNLT-Testsplit (alle drei Datensätze): `s4` 0,04, `s4k` 0,00, `s4t` 0,01, `seiten_b` 0,01, `seiten_c` 0,05, `seiten_d` 0,03.

Lesehinweise:

- **Fehlende Töne sind auf Seiten die häufigste Fehlerart nach den falschen** (1,29 von 3,54 % bei `seiten_d`) und auf den Prüfhandschriften die häufigste (0,72 von 1,31 %). Von `seiten_c` zu `seiten_d` sind sie dort gestiegen (0,49 auf 0,72 %), während falsche und überzählige Töne sanken.
- **Ganz ausgelassene Einheiten sind auf den Mengen mit GT selten** (höchstens 0,48 %, auf Seiten 7 von 6.669 bei `seiten_d`). Diese Mengen enthalten aber Handschriften, deren Schrift das Modell aus dem Training kennt. Für ungesehene Handschriften mit vielen Abkürzungen fehlt eine Menge mit Text-GT; dort ist die Rate nach dem Augenschein des Projektleiters höher.
- **Für das nächste Training vorgesehen:** Trainingsbilder, in denen einzelne Wörter der Textzeile abgedeckt sind, mit einem Ziel, das die Noten behält und die Silbe offen lässt.
