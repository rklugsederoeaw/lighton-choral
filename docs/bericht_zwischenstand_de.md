# LightOnOCR-3-1B für Choral: Zwischenstand

Stand: 2026-11-09. Schritte 1 bis 3 stehen in `BERICHT_Schritt1-3.md`. Schlussmessung, CRNN-Vergleich und Text-Messung stehen weiter unten.

## Ergebnis in Kürze

- Lauf `s4` (nur AMNLT) liest AMNLT-validation mit 1,77 % Tonlagen-SER, die fünf ungesehenen Prüfhandschriften aber mit 24,92 %.
- Lauf `s4k` (AMNLT plus 2.160 Systeme aus der CantusDB) senkt die Prüfhandschriften auf 9,55 %, AMNLT bleibt bei 1,79 %.
- Eine fremde Notenzeile im Ausschnitt schadet dem Modell stark. Deshalb werden solche Systeme aussortiert.

## Läufe

Beide auf einer H100 (MUSICA), Bildform Streifen, 4 Epochen, Lernraten 1e-4 (Bild) und 5e-5 (Decoder), Ziel `transcription` mit `<m>`, Basis `models/LightOnOCR-3-1B-konvertiert`. Checkpoints wurden auf AMNLT-validation nach Tonlagen-SER gewählt. Die Prüfhandschriften gingen nicht in die Auswahl ein.

| Lauf | Job | Daten | Systeme | Trainingsdauer | ausgewählt | AMNLT-val Tonlagen-SER | Noten-SER | Text-CER |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `s4` | 1925296 | AMNLT | 3.923 | 182 min | Epoche 3 | 1,77 % | 5,60 % | 2,43 % |
| `s4k` | 1926046 | AMNLT + Korpus | 6.083 | 216 min | Epoche 4 | 1,79 % | 5,51 % | 2,28 % |

### Prüfhandschriften

Je 40 geprüfte Systeme aus Transkribus-Exporten, die nicht im Training des LightOnOCR-Modells waren. Tonlagen-SER, gelesen mit `lesen.py`, verglichen mit `vergleich_gt.py`. In allen fünf Quellen liegt das Minimum beim Versatz 0, die Abbildung auf gabc stimmt also.

| Handschrift | Notation | `s4` Epoche 3 | `s4k` Epoche 2 | `s4k` Epoche 3 | `s4k` Epoche 4 (ausgewählt) |
| --- | --- | --- | --- | --- | --- |
| A-Wn 15484 | Quadrat | 0,72 % | 1,72 % | 1,00 % | 1,43 % |
| A-Geras 6 | deutsch-gotisch | 18,75 % | 5,18 % | 5,92 % | 4,03 % |
| A-KN 65 | böhmisch-gotisch | 10,79 % | 5,33 % | 12,44 % | 8,25 % |
| A-Gu 17 | deutsch-gotisch | 46,36 % | 18,57 % | 11,93 % | 10,01 % |
| A-VOR 254 | deutsch-gotisch | 34,41 % | 12,62 % | 22,76 % | 23,41 % |
| alle | | 24,92 % | 9,55 % | 11,01 % | 9,55 % |

Anfangsschlüssel richtig: `s4` 80,5 %, `s4k` Epoche 4 89,5 %. Schleifen: 10 gegen 2.

Grenzen: 40 Systeme je Quelle, die Werte schwanken zwischen den Epochen stark. Systeme mit durch eine Initiale geteilter Notenzeile fehlen. Bei A-KN 65 stammen die Seiten 53 bis 82 der GT aus korrigierten Lesungen. Bei A-Gu 17 und A-VOR 254 fehlten in `s4` vor allem Töne (25,8 und 18,4 Punkte), nicht falsche Lagen.

## Fehlerarten von `s4` auf AMNLT

Skript `fehlerarten.py`, Epoche 3, validation.

- Salzinnes: `v` fehlt 706-mal und ist 281-mal zu viel, das sind 6,0 von 8,4 Punkten Noten-SER. Echte Lagefehler 0,71 Punkte.
- Solesmes: `v` 2,5 und `!` 2,2 von 8,1 Punkten. Lagefehler 0,63 Punkte. WER 29,6 %, Text-CER 6,5 % (7,9 % mit Leerzeichen).
- `v` steht in den Originalkodierungen für `-s`, vermutlich Noten mit Stiel. Ob das Modell dünne Striche übersieht oder die Referenz uneinheitlich ist, ist am Bild nicht geprüft.

## Fremde Notenzeile im Bild

Skript `bleed_test.py`, 30 Systeme aus A-Wn 15484, Modell `s4` Epoche 3.

| Ausschnitt | Tonlagen-SER | fehlerfrei | gelesene Töne (GT 513) |
| --- | --- | --- | --- |
| sauber | 0,97 % | 27 | 510 |
| bis zur Mitte des nächsten Systems | 12,67 % | 19 | 558 |
| ganzes nächstes System | 60,43 % | 5 | 799 |

Das Modell schreibt die fremden Noten mit. Ein Modell, das mit solchen Bildern trainiert wird, könnte sie ignorieren lernen. Das ist nicht geprüft.

## Korpus aus der CantusDB

Skripte `silben_cantus.py` (Silbentrennung, Prüfung) und `korpus_cantus.py` (Paare).

- Volpiano: `---` trennt Wörter, `--` Silben, `-` Neumen innerhalb einer Silbe, Ziffern 3 und 4 sind Abschnittsstriche.
- Ohne Abtrennung von Differenz und Vers stimmt die Wortzahl nur bei 28,6 % der Gesänge. Mit Abtrennung bei 92,9 % (44.270 von 47.646). Davon haben 74,2 % in allen Wörtern die gleiche Silbenzahl, Wörter einzeln 97,1 %. Die Trennstellen selbst sind nicht geprüft, etwa `in-tro-iv-i`.
- Der Text steht je Abschnitt im Volltext hinter `|`. Einträge mit `~` sind Repetenda ohne Noten.
- Differenzen ohne Text bleiben unzugeordnet. In Zwiefalten steht darunter oft der Psalmanfang, nicht „euouae“.
- Der Projektleiter hat am Prüfbogen bestätigt, dass Text und Melodien in den Zwiefalten-Beispielen stimmen.

| Quelle | Kandidaten | Paare | fremde Linie unten | Text angeschnitten | übrig |
| --- | --- | --- | --- | --- | --- |
| D-KA Aug. LX | 3.759 | 1.544 | 729 | 401 | 414 |
| D-KA Aug. LX, Addendum | 414 | 140 | 97 | 7 | 36 |
| CH-Fco Ms. 2 | 5.678 | 1.868 | 918 | 122 | 828 |
| CH-E 611 | 7.249 | 3.062 | 1.870 | 310 | 882 |
| Summe | 17.100 | 6.614 | 3.614 | 840 | 2.160 |

Parallel ist im Repo `skripte/gabc_zeilen.py` entstanden (Tagebuch 09.11.2026, Ausgabe `daten/cantus_gabc/`), mit demselben Ziel und höherer Ausbeute: 6.357 von 7.413 Zeilen von CH-E 611 vollständig zugeordnet, geprüft gegen AMNLT-Einsiedeln. `korpus_cantus.py` ist unabhängig davon entstanden. Für weitere Quellen sollte die Zuordnung von dort kommen; Bildzuschnitt und Filter stammen von hier.

Eine Zeile bleibt nur, wenn ihre Töne genau der geprüften GT entsprechen. Grenzen:

- Der Text stammt aus der CantusDB und ist nicht diplomatisch. Abkürzungen stehen im Ziel ausgeschrieben.
- Text ohne Noten und Rubriken stehen im Bild, aber nicht im Ziel.
- Die Filter arbeiten nicht perfekt. Einzelne Systeme haben noch angeschnittene Schrift oder Notenspitzen am Rand.
- Der Filter bevorzugt letzte Systeme einer Seite.
- Die Seiten liegen nur mit 1.600 px Breite vor.
- Die Quellen A-KN 1018, A-Wn 1799, CH-P 18, D-KNd 1161 und F-Pn 12044 haben keine `results`-Datei und sind nicht verarbeitet. A-KN 1012 ist auf Wunsch des Projektleiters ausgenommen (alte, schlecht lesbare Notation).
- CH-E 611 ist dieselbe Handschrift wie AMNLT-Einsiedeln und darf nur ins Training.

## Rechenzeit

- MUSICA H100: 0,54 bis 0,70 s je System beim Training.
- Lesen auf der Strix-Halo-GPU des EVO: 4,4 bis 7,3 s je System, Umgebung `~/projects/lighton_choral/.venv` (ROCm-Torch aus `~/ai/venvs/ml`).
- Lesen auf 6 CPU-Kernen: 20 bis 41 s je System. CPU- und GPU-Lesungen sind meist gleich, an schwierigen Stellen wegen der Rundung (32 gegen 16 Bit) aber nicht immer.

## Dateien

| Datei | Zweck |
| --- | --- |
| `konvertieren.py` | benennt die Decoder-Gewichte des Originals um, sonst bleibt der Decoder zufällig |
| `train.py`, `musica/train_streifen.sh`, `musica/train_v2.sh` | Training; `--zusatz` nimmt weitere Listen auf |
| `auswertung.py`, `metriken.py`, `fehlerarten.py` | Messung mit Referenz |
| `lesen.py`, `vergleich_gt.py` | Lesen ohne Referenz, Tonlagen-Vergleich mit Transkribus-GT |
| `systeme_pagexml.py` | Systemausschnitte aus PAGE-XML |
| `silben_cantus.py`, `korpus_cantus.py` | Silbentrennung und Trainingspaare aus der CantusDB |
| `bleed_test.py` | Ausschnitte mit fremder Notenzeile |

Große Dateien liegen außerhalb des Repos (`daten`, `models`, `runs`); `s4` Epochen 3 und 4 und `s4k` Epoche 4 sind dort gesichert. Die übrigen Checkpoints liegen nur auf MUSICA, das kein Backup hat.

## Schlussmessung auf AMNLT-test

`s4k` Epoche 4, 562 Systeme (Job 1927925). Die Splits sind nicht seitenrein, die Werte also zu günstig.

| Messgröße | gesamt | Einsiedeln | Salzinnes | Solesmes |
| --- | --- | --- | --- | --- |
| Tonlagen-SER | 1,77 % | 1,24 % | 1,77 % | 2,70 % |
| Noten-SER | 6,07 % | 1,84 % | 8,04 % | 11,12 % |
| Anfangsschlüssel richtig | 99,47 % | 99,45 % | 99,32 % | 100 % |
| Neumengrenzen F1 | 0,978 | 0,992 | 0,990 | 0,936 |
| Text-CER | 2,67 % | 2,34 % | 1,14 % | 6,30 % |
| Silben-SER | 6,18 % | 4,36 % | 3,31 % | 16,07 % |

WER nur für Solesmes messbar: 27,19 %. Eine Schleife in 562 Systemen.

## Vergleich mit dem CRNN

Skripte `crnn_lesen.py`, `vergleich_modelle.py`, Werte `vergleich_modelle.json`. Modell `hybrid_hybrid_lang`: trainiert nur auf der Volpiano-GT, die fünf Prüfhandschriften sind laut Index nicht darin. Dieselben 200 Systeme, greedy, ohne Beam, Melodiemodell und Konkordanz. Das CRNN hat rund 38.000 Trainingssysteme, `s4k` 6.083.

| Handschrift | `s4k` | CRNN Attention | CRNN CTC |
| --- | --- | --- | --- |
| A-Wn 15484 | 1,43 % | 6,58 % | 3,43 % |
| A-Geras 6 | 4,03 % | 2,38 % | 4,77 % |
| A-KN 65 | 8,25 % | 14,97 % | 14,72 % |
| A-Gu 17 | 10,01 % | 24,90 % | 29,06 % |
| A-VOR 254 | 23,41 % | 18,66 % | 24,27 % |
| alle | 9,55 % | 13,88 % | 16,11 % |
| Anfangsschlüssel richtig | 89,5 % | 70,0 % | 43,0 % |

## Plausibel, aber falsch

Bei ersetzten Tönen: Wie oft ist die Lesung nach einem Intervall-Trigramm aus der CantusDB wahrscheinlicher als die Referenz? CRNN CTC 31,2 % (417 Töne), CRNN Attention 46,1 % (284), `s4k` 52,2 % (115), `s4` 61,7 % (313). Die Prüfung nutzt die GT, nicht das Bild, und zählt nur ersetzte Töne.

## Text gegen korrigierte Text-GT

Skript `text_vergleich.py`, Werte `text_vergleich.json`. Die Text-GT der Transkribus-Exporte ist für die Seiten mit Noten-GT korrigiert (`gt_uebersicht.tsv`, `korr_text_rk`); Abkürzungen sind dort wie in unserem Ziel ausgeschrieben. Normalisiert heißt: ohne Groß-/Kleinschreibung, u/v und i/j gleich, nur Buchstaben. Ohne 2 Systeme mit Schleife oder Abbruch.

| Handschrift | Systeme | CER genau | CER normalisiert | Median je System | fehlerfrei |
| --- | --- | --- | --- | --- | --- |
| A-Geras 6 | 15 | 6,84 % | 5,41 % | 3,45 % | 6 |
| A-Gu 17 | 39 | 9,08 % | 6,37 % | 6,25 % | 16 |
| A-VOR 254 | 39 | 11,53 % | 9,04 % | 5,56 % | 17 |
| A-Wn 15484 | 40 | 17,16 % | 15,13 % | 8,71 % | 8 |
| A-KN 65 | 27 | 23,45 % | 22,04 % | 18,18 % | 4 |
| alle `s4k` | 160 | 14,29 % | 12,17 % | 7,41 % | 51 |
| alle `s4` | 154 | 17,56 % | 15,51 % | 11,32 % | 35 |

Die Text-GT lässt Initialen teils weg; ein gelesenes Initial zählt dann als Fehler. Eindruck des Projektleiters an der Ansicht: Der Text wird gelesen, nicht erfunden, und ist teils noch fehlerhaft.

## Nächstes Korpus

`korpus_gabc.py` schneidet den Datensatz `daten/cantus_gabc/datensatz` mit Koordinaten aus `results_*.json` und `lage.jsonl` zu. Stand 09.11., vor dem letzten Sonnet-Durchgang, ohne A-KN 1012:

| Quelle | Zeilen | fremde Linie unten | Text angeschnitten | übrig |
| --- | --- | --- | --- | --- |
| A-Wn 1799 | 2.637 | 685 | 150 | 1.802 |
| A-KN 1018 | 2.398 | 469 | 134 | 1.795 |
| CH-Fco Ms. 2 | 5.337 | 3.201 | 497 | 1.639 |
| F-Pn 12044 | 3.249 | 986 | 712 | 1.551 |
| CH-E 611 | 6.847 | 4.649 | 668 | 1.530 |
| D-KA Aug. LX | 3.118 | 1.712 | 640 | 766 |
| D-KNd 1161 | 1.124 | 308 | 113 | 703 |
| CH-P 18 | 2.385 | 1.005 | 775 | 605 |
| A-KN 1010 | 284 (11 ohne Koordinaten) | 127 | 15 | 131 |
| D-KA Addendum | 376 | 259 | 6 | 111 |
| gesamt | 27.755 | 13.401 | 3.710 | 10.633 |

Aufteilung: 8.570 train, 1.038 validation, 1.025 test. In `lage.jsonl` fehlen Systeme ohne GT, das nächste System kann näher liegen als der nächste Kasten; das fängt nur der Linienfilter ab. Bei CH-P 18 blieben in der Stichprobe mehr Reste der Nachbarzeile. Zweige `ernte` sind nur vom Modell freigeschaltet.

## Lauf `s4g`: AMNLT plus GABC-Korpus (10.11.2026)

Job 1928540, 12.704 Systeme (3.923 AMNLT + 8.781 Korpus train), 4 Epochen, Streifen, Korpusbilder auf 1.540 px hochskaliert (`bildform.py`), sonst wie `s4k`. Training 326 min, mit Lesen 8:28 h; das Lesen war langsam, weil zwölf Prozesse eine GPU teilten. Auswahl nach Tonlagen-SER auf AMNLT-validation: Epoche 3 (`checkpoint-38112`), 1,86 % gegen 1,91 % bei Epoche 4 und 1,79 % bei `s4k`.

| Messung | `s4k` Ep. 4 | `s4g` Ep. 2 | `s4g` Ep. 3 (ausgewählt) | `s4g` Ep. 4 |
| --- | --- | --- | --- | --- |
| AMNLT-val Tonlagen-SER | 1,79 % | 1,97 % | 1,86 % | 1,91 % |
| AMNLT-val Noten-SER | 5,51 % | 6,71 % | 5,64 % | 5,64 % |
| AMNLT-val Text-CER | 2,28 % | 2,56 % | 2,85 % | 2,85 % |
| Korpus-val Tonlagen-SER (1.060) | – | 7,11 % | 5,77 % | 5,63 % |
| Korpus-val Text-CER | – | 5,83 % | 3,98 % | 4,08 % |
| Prüfhandschriften Tonlagen-SER (200) | 9,55 % | 5,55 % | 5,84 % | 5,55 % |
| Prüfhandschriften Anfangsschlüssel | 89,5 % | 95,0 % | 96,5 % | 95,5 % |
| Prüfhandschriften Schleifen | 2 | 0 | 1 | 0 |
| Text-CER normalisiert gegen Transkribus-GT | 12,17 % | – | 9,57 % | 9,80 % |

Prüfhandschriften je Quelle, Epoche 3 (`s4k` in Klammern): A-Wn 15484 1,29 (1,43), A-Geras 6 1,73 (4,03), A-KN 65 7,36 (8,25), A-Gu 17 8,25 (10,01), A-VOR 254 10,14 (23,41). Korpus-val je Quelle, Epoche 3: CH-Fco 1,01, CH-P 18 1,23, CH-E 611 1,79, Addendum 2,94, F-Pn 12044 3,81, A-Wn 1799 8,50, D-KA Aug. LX 9,73, A-KN 1018 10,71, D-KNd 1161 12,95, A-KN 1010 18,03. Text normalisiert, Epoche 3: A-Geras 6 3,42, A-VOR 254 5,96, A-Gu 17 6,24, A-Wn 15484 13,65, A-KN 65 14,89; fehlerfreier Text in 59 von 161 Systemen (`s4k` 51 von 160). CRNN-Vergleich: 5,84 gegen 13,88 % (Attention). Plausibilität: nur 39 ersetzte Töne vergleichbar, 53,8 % davon wahrscheinlicher als die Referenz.

Grenzen: Die Epochen 2 bis 4 liegen auf den Prüfhandschriften innerhalb der Schwankung (5,55 bis 5,84 %). Auf AMNLT ist `s4g` nicht besser als `s4k`; der Gewinn liegt bei den gotischen Handschriften. CH-E 611 im Training überlappt mit AMNLT-Einsiedeln, die AMNLT-Werte für Einsiedeln sind deshalb nicht unabhängig. Die Ergebnisansicht (Artifact) zeigt jetzt Epoche 3 von `s4g`. Checkpoints Epoche 3 und 4 werden auf D: gesichert.

## Lauf `s4w`: AMNLT mit Wortgrenzen plus GABC-Korpus (11.11.2026)

Job 1930646, wie `s4g`, aber AMNLT-Einsiedeln und -Salzinnes mit nachgetragenen Wortgrenzen (`wortgrenzen_amnlt.py`, `daten/systeme_wg.jsonl`: 3.822 von 4.755 Zeilen umgeschrieben, die übrigen unverändert). Training 327 min, mit Lesen 8:27 h. Ausgewählt nach AMNLT-validation: Epoche 4 (`checkpoint-50816`), 1,68 %.

| Messung | `s4g` Ep. 3 | `s4w` Ep. 3 | `s4w` Ep. 4 (ausgewählt) |
| --- | --- | --- | --- |
| AMNLT-val Tonlagen-SER | 1,86 % | 1,71 % | 1,68 % |
| AMNLT-val Noten-SER | 5,64 % | 5,70 % | 5,59 % |
| AMNLT-val Text-CER | 2,85 % | 1,99 % | 1,91 % |
| AMNLT-val WER (mit Wortgrenzen; Ein./Salz./Sol.) | – | 38,8 / 22,4 / 30,7 % | 32,0 / 16,9 / 25,6 % |
| Korpus-val Tonlagen-SER | 5,77 % | 5,82 % | 5,74 % |
| Korpus-val Text-CER | 3,98 % | 6,76 % | 4,11 % |
| Prüfhandschriften Tonlagen-SER | 5,84 % | 4,53 % | 4,67 % |
| Prüfhandschriften Anfangsschlüssel | 96,5 % | 89,0 % | 88,5 % |
| Text-CER normalisiert (Transkribus-GT) | 9,57 % | 9,58 % | 8,34 % |
| Systeme mit Leerzeichen nach jeder Silbe (Prüfmenge) | 46 | – | 9 |

Prüfhandschriften je Quelle, Epoche 4 (`s4g` Ep. 3 in Klammern): A-Wn 15484 1,14 (1,29), A-Geras 6 1,81 (1,73), A-KN 65 6,22 (7,36), A-Gu 17 8,25 (8,25), A-VOR 254 4,96 (10,14). Text normalisiert: A-Geras 6 3,70, A-Gu 17 3,55, A-VOR 254 6,51, A-Wn 15484 9,92, A-KN 65 16,72; fehlerfreier Text 62 von 162.

Die Wortgrenzen wirken: Die silbenweise Ausgabe ist von 46 auf 9 Systeme zurückgegangen, Text-CER auf AMNLT und auf den Prüfhandschriften sinkt. Die WER auf AMNLT bleibt hoch (17 bis 32 %), weil die Wortgrenzen im Training nur für 80 % der Einsiedeln- und Salzinnes-Zeilen vorliegen. Der Anfangsschlüssel ist auf den Prüfhandschriften schlechter als bei `s4g` (88,5 gegen 96,5 %); bei 200 Systemen sind das 16 Fehler mehr, Ursache ungeklärt. In `auswertung.py` war die WER für Einsiedeln und Salzinnes im Job noch abgeschaltet; die Werte oben sind lokal aus den Lesungen nachgerechnet, das Skript ist korrigiert.

## Lauf `s4t`: plus vier gotische Transkribus-Quellen (12.11.2026)

Job 1937605, wie `s4w`, dazu 569 Trainingssysteme aus A-BRlm P33, P34, A-MB Man.Perg. 2 und A-VOR 259/1 (`daten/korpus_transkribus/`, Silben aus der Bildlesung, Initialen aus dem CantusDB-Lexikon ergänzt, 33 unsichere Zeilen ausgeschlossen). Zusammen 13.273 Trainingssysteme. Training 340 min, mit Lesen 8:51 h. Ausgewählt nach AMNLT-validation: Epoche 4 (`checkpoint-53092`). Die Tonlage ist mit Epoche 3 gleichauf (1,80 gegen 1,78 %); Schlüssel-SER (1,42 gegen 1,75 %) und Text-CER (2,29 gegen 2,33 %) auf AMNLT-validation sprechen für Epoche 4.

| Messung | `s4w` Ep. 4 | `s4t` Ep. 3 | `s4t` Ep. 4 (ausgewählt) |
| --- | --- | --- | --- |
| AMNLT-val Tonlagen-SER | 1,68 % | 1,78 % | 1,80 % |
| AMNLT-val Noten-SER | 5,59 % | 5,80 % | 5,91 % |
| AMNLT-val Text-CER | 1,91 % | 2,33 % | 2,29 % |
| AMNLT-val WER (Ein./Salz./Sol.) | 32,0 / 16,9 / 25,6 % | 32,8 / 20,1 / 27,9 % | 31,6 / 19,1 / 27,2 % |
| Korpus-val Tonlagen-SER | 5,74 % | 5,59 % | 5,67 % |
| Korpus-val Text-CER | 4,11 % | 4,02 % | 4,10 % |
| Transkribus-val Tonlagen-SER (89 Systeme) | – | 0,51 % | 0,62 % |
| Transkribus-val Text-CER | – | 5,14 % | 4,02 % |
| Prüfhandschriften Tonlagen-SER | 4,67 % | 2,36 % | 2,11 % |
| Prüfhandschriften fehlerfreie Systeme | – | 153 von 200 | 157 von 200 |
| Prüfhandschriften Anfangsschlüssel | 88,5 % | 90,5 % | 92,5 % |
| Text-CER normalisiert (Transkribus-GT) | 8,34 % | 8,37 % | 7,90 % |

Prüfhandschriften je Quelle, Epoche 4 (`s4w` Ep. 4 in Klammern): A-Wn 15484 0,86 (1,14), A-Geras 6 1,89 (1,81), A-KN 65 3,68 (6,22), A-Gu 17 2,24 (8,25), A-VOR 254 1,83 (4,96). Text normalisiert: A-Gu 17 3,21, A-Geras 6 3,13, A-VOR 254 5,40, A-Wn 15484 10,12, A-KN 65 15,96; fehlerfreier Text 77 von 162 (`s4w` 62). Keine Schleifen, keine Abbrüche.

Die 569 gotischen Systeme halbieren die Tonlagen-SER auf den ungesehenen Handschriften (4,67 auf 2,11 %), vor allem bei A-Gu 17 und A-VOR 254, die derselben deutsch-gotischen Notation angehören wie die neuen Trainingsquellen (A-VOR 259 liegt wie A-VOR 254 in der Stiftsbibliothek Vorau). AMNLT verliert leicht (1,68 auf 1,80 %), innerhalb der Schwankung zwischen Epochen. Grenzen: 40 Systeme je Prüfhandschrift. Die Pool-Messung über alle 27 Transkribus-Quellen (6.764 Systeme, Worker `pool`, Bericht `docs/pool_messung.md`) bestätigt das Bild: 17 weitere ungesehene Handschriften 2,62 % Tonlagen-SER (3.015 Systeme), die fünf bisherigen Prüfhandschriften 2,28 % (2.360), die vier Trainingsquellen 1,06 % (1.260). Ausgenommen ist gfs122 (Lektionston mit Rezitationsbalken, die GT zählt einen Balken als einen Ton). Werte mit dem korrigierten Parser für `c5` (13.11.2026).

## Offen

- Beim Lesen im Jobskript weniger Prozesse parallel oder weniger Systeme (Lauf 3: 12 Prozesse, 15 s je System). Entscheidung über ganze Seiten statt Zeilenausschnitte (Projektleiter, zur späteren Überlegung).
