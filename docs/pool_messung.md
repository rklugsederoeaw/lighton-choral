# Pool-Messung

Checkpoint: `runs/s4t/checkpoint-53092`, Epoche 4; endgültige Auswahl des Projektleiters. Auf AMNLT-validation: Tonlagen-SER 1,80 %, Schlüssel-SER 1,42 %, Text-CER 2,29 %.

Die Tabellen gewichten Ton- und Zeichenfehler nach der Zahl der Referenzzeichen. Anfangsschlüssel werden nur bewertet, wenn ein Anfangsschlüssel in der GT steht; alternative Schlüssel gelten jeweils als richtig. Fehlerfreie Systeme haben eine identische Tonfolge. Schleifen und Abbrüche bleiben in den Tonlagenwerten enthalten und werden für die Text-CER ausgelassen.

Die Text-CER vergleicht die erkannten Textzeichen ohne Leerraum mit den korrigierten PAGE-Texten im Bereich `korr_text_rk`. Normalisiert werden nur die Buchstaben a–z nach Kleinschreibung und Gleichsetzung von u/v und i/j verglichen. Textsysteme mit als angeschnitten markierter Textzeile werden ausgelassen.

Die automatische Zuschnittprüfung markiert konservativ mögliche Anschnitte anhand der Textregionen und des Tintenprofils; fremde obere Regionen über geometrische Überlappung, fremde untere Linien über Linienprofile. Der obere Rand beruht, wo sicher erkannt, auf dem Profil roter oder dunkler Notenlinien und der höchsten GT-Tonlage; bei unklarer Liniensuche bleibt die bisherige Grenze. Als sauber gelten Systeme ohne die Merkmale fremd_unten und text_angeschnitten. Diese Heuristiken ersetzen keine vollständige manuelle Prüfung und können Fehler übersehen oder unbedenkliche Zuschnitte markieren.

## Alle gemessenen Systeme

| Quelle / Gruppe | Systeme | Tonlagen-SER % | Tonfolge fehlerfrei | Anfangsschlüssel richtig / bewertet (%) | Schleifen | Abbrüche | Textsysteme | CER genau % | CER normalisiert % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| brixen7 | 297 | 1,65 | 230 | 294 / 297 (98,99) | 0 | 0 | 0 | – | – |
| brlm33 | 268 | 1,00 | 243 | 267 / 268 (99,63) | 0 | 0 | 228 | 5,45 | 4,41 |
| brlm34 | 270 | 0,90 | 234 | 269 / 270 (99,63) | 0 | 0 | 181 | 4,74 | 3,95 |
| brz | 273 | 1,78 | 184 | 272 / 273 (99,63) | 0 | 0 | 0 | – | – |
| geras6 | 670 | 1,35 | 570 | 636 / 670 (94,93) | 0 | 0 | 181 | 7,78 | 6,25 |
| gf6722 | 112 | 1,54 | 83 | 112 / 112 (100,00) | 0 | 0 | 0 | – | – |
| gf6723 | 117 | 0,92 | 105 | 113 / 114 (99,12) | 0 | 0 | 0 | – | – |
| gf6727 | 113 | 1,67 | 107 | 69 / 70 (98,57) | 0 | 0 | 0 | – | – |
| gf6741 | 116 | 1,90 | 99 | 114 / 114 (100,00) | 0 | 0 | 0 | – | – |
| gf6742 | 120 | 1,80 | 96 | 118 / 120 (98,33) | 0 | 0 | 0 | – | – |
| gf6743 | 145 | 1,80 | 102 | 143 / 145 (98,62) | 0 | 0 | 6 | 17,32 | 13,71 |
| gfs122 | 129 | 86,18 | 2 | 122 / 129 (94,57) | 1 | 1 | 0 | – | – |
| gfs128 | 113 | 5,62 | 57 | 102 / 106 (96,23) | 0 | 0 | 0 | – | – |
| gfs129 | 129 | 12,56 | 56 | 125 / 129 (96,90) | 0 | 0 | 0 | – | – |
| gfs140a | 145 | 2,75 | 114 | 145 / 145 (100,00) | 0 | 0 | 0 | – | – |
| gfs145 | 84 | 2,32 | 71 | 83 / 84 (98,81) | 0 | 0 | 0 | – | – |
| gfs158 | 120 | 2,07 | 108 | 117 / 120 (97,50) | 0 | 0 | 0 | – | – |
| gu17 | 270 | 2,32 | 182 | 258 / 269 (95,91) | 0 | 0 | 217 | 6,42 | 4,75 |
| kn65 | 647 | 4,44 | 404 | 608 / 645 (94,26) | 1 | 1 | 287 | 18,22 | 16,60 |
| liktu13 | 269 | 6,23 | 127 | 202 / 259 (77,99) | 0 | 0 | 0 | – | – |
| mb2 | 516 | 1,25 | 425 | 493 / 515 (95,73) | 0 | 0 | 226 | 5,09 | 4,35 |
| salzburg3 | 360 | 3,34 | 272 | 338 / 354 (95,48) | 1 | 1 | 0 | – | – |
| sf409 | 194 | 2,18 | 156 | 191 / 192 (99,48) | 0 | 0 | 0 | – | – |
| taisten | 308 | 0,81 | 262 | 292 / 308 (94,81) | 0 | 0 | 175 | 6,55 | 5,12 |
| vor254 | 279 | 1,99 | 219 | 239 / 278 (85,97) | 0 | 0 | 109 | 10,32 | 7,97 |
| vor259 | 206 | 0,67 | 188 | 199 / 201 (99,00) | 0 | 0 | 71 | 6,24 | 4,99 |
| wn15484 | 494 | 1,32 | 452 | 419 / 494 (84,82) | 0 | 0 | 438 | 15,01 | 12,80 |
| gruppe:neu | 3144 | 4,38 | 2231 | 2952 / 3071 (96,13) | 2 | 2 | 181 | 6,84 | 5,35 |
| gruppe:neu_ohne_gfs122 | 3015 | 2,62 | 2229 | 2830 / 2942 (96,19) | 1 | 1 | 181 | 6,84 | 5,35 |
| gruppe:alt | 2360 | 2,27 | 1827 | 2160 / 2356 (91,68) | 1 | 1 | 1232 | 13,01 | 11,11 |
| gruppe:training | 1260 | 1,06 | 1090 | 1228 / 1254 (97,93) | 0 | 0 | 706 | 5,22 | 4,33 |

## Nur automatisch als sauber markierte Systeme

| Quelle / Gruppe | Systeme | Tonlagen-SER % | Tonfolge fehlerfrei | Anfangsschlüssel richtig / bewertet (%) | Schleifen | Abbrüche | Textsysteme | CER genau % | CER normalisiert % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| brixen7:sauber | 103 | 1,78 | 83 | 101 / 103 (98,06) | 0 | 0 | 0 | – | – |
| brlm33:sauber | 229 | 1,05 | 210 | 228 / 229 (99,56) | 0 | 0 | 228 | 5,45 | 4,41 |
| brlm34:sauber | 179 | 0,85 | 158 | 178 / 179 (99,44) | 0 | 0 | 179 | 4,79 | 3,99 |
| brz:sauber | 92 | 1,54 | 65 | 92 / 92 (100,00) | 0 | 0 | 0 | – | – |
| geras6:sauber | 387 | 1,11 | 335 | 366 / 387 (94,57) | 0 | 0 | 181 | 7,78 | 6,25 |
| gf6722:sauber | 78 | 1,56 | 57 | 78 / 78 (100,00) | 0 | 0 | 0 | – | – |
| gf6723:sauber | 92 | 0,68 | 84 | 89 / 89 (100,00) | 0 | 0 | 0 | – | – |
| gf6727:sauber | 85 | 2,10 | 80 | 52 / 53 (98,11) | 0 | 0 | 0 | – | – |
| gf6741:sauber | 91 | 1,78 | 79 | 89 / 89 (100,00) | 0 | 0 | 0 | – | – |
| gf6742:sauber | 81 | 1,90 | 64 | 80 / 81 (98,77) | 0 | 0 | 0 | – | – |
| gf6743:sauber | 100 | 1,88 | 71 | 98 / 100 (98,00) | 0 | 0 | 6 | 17,32 | 13,71 |
| gfs122:sauber | 102 | 82,32 | 1 | 97 / 102 (95,10) | 1 | 1 | 0 | – | – |
| gfs128:sauber | 97 | 5,89 | 46 | 88 / 92 (95,65) | 0 | 0 | 0 | – | – |
| gfs129:sauber | 124 | 12,58 | 54 | 120 / 124 (96,77) | 0 | 0 | 0 | – | – |
| gfs140a:sauber | 132 | 2,86 | 103 | 132 / 132 (100,00) | 0 | 0 | 0 | – | – |
| gfs145:sauber | 57 | 2,38 | 48 | 56 / 57 (98,25) | 0 | 0 | 0 | – | – |
| gfs158:sauber | 99 | 2,08 | 90 | 96 / 99 (96,97) | 0 | 0 | 0 | – | – |
| gu17:sauber | 217 | 2,25 | 148 | 208 / 216 (96,30) | 0 | 0 | 216 | 6,29 | 4,61 |
| kn65:sauber | 455 | 3,57 | 285 | 431 / 454 (94,93) | 0 | 0 | 285 | 18,07 | 16,46 |
| liktu13:sauber | 95 | 5,03 | 53 | 76 / 90 (84,44) | 0 | 0 | 0 | – | – |
| mb2:sauber | 375 | 0,95 | 316 | 355 / 374 (94,92) | 0 | 0 | 226 | 5,09 | 4,35 |
| salzburg3:sauber | 242 | 4,08 | 189 | 226 / 237 (95,36) | 1 | 1 | 0 | – | – |
| sf409:sauber | 123 | 2,85 | 92 | 120 / 121 (99,17) | 0 | 0 | 0 | – | – |
| taisten:sauber | 175 | 0,76 | 151 | 170 / 175 (97,14) | 0 | 0 | 175 | 6,55 | 5,12 |
| vor254:sauber | 110 | 1,72 | 92 | 90 / 110 (81,82) | 0 | 0 | 109 | 10,32 | 7,97 |
| vor259:sauber | 72 | 0,38 | 68 | 69 / 70 (98,57) | 0 | 0 | 71 | 6,24 | 4,99 |
| wn15484:sauber | 437 | 1,32 | 402 | 369 / 437 (84,44) | 0 | 0 | 437 | 14,97 | 12,76 |
| gruppe:neu:sauber | 1968 | 5,18 | 1410 | 1860 / 1914 (97,18) | 2 | 2 | 181 | 6,84 | 5,35 |
| gruppe:neu_ohne_gfs122:sauber | 1866 | 2,83 | 1409 | 1763 / 1812 (97,30) | 1 | 1 | 181 | 6,84 | 5,35 |
| gruppe:alt:sauber | 1606 | 1,99 | 1262 | 1464 / 1604 (91,27) | 0 | 0 | 1228 | 12,94 | 11,04 |
| gruppe:training:sauber | 855 | 0,93 | 752 | 830 / 852 (97,42) | 0 | 0 | 704 | 5,23 | 4,34 |

## Linienprofil: Systeme mit und ohne Rückfall

| Quelle / Gruppe | Systeme | Tonlagen-SER % | Tonfolge fehlerfrei | Anfangsschlüssel richtig / bewertet (%) | Schleifen | Abbrüche | Textsysteme | CER genau % | CER normalisiert % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| brixen7:mit_rueckfall | 114 | 2,48 | 88 | 114 / 114 (100,00) | 0 | 0 | 0 | – | – |
| brixen7:ohne_rueckfall | 183 | 1,08 | 142 | 180 / 183 (98,36) | 0 | 0 | 0 | – | – |
| brlm33:mit_rueckfall | 2 | 0,00 | 2 | 2 / 2 (100,00) | 0 | 0 | 2 | 0,00 | 0,00 |
| brlm33:ohne_rueckfall | 266 | 1,01 | 241 | 265 / 266 (99,62) | 0 | 0 | 226 | 5,48 | 4,44 |
| brlm34:mit_rueckfall | 37 | 1,58 | 32 | 37 / 37 (100,00) | 0 | 0 | 13 | 4,11 | 3,42 |
| brlm34:ohne_rueckfall | 233 | 0,79 | 202 | 232 / 233 (99,57) | 0 | 0 | 168 | 4,79 | 3,99 |
| brz:mit_rueckfall | 43 | 2,40 | 30 | 43 / 43 (100,00) | 0 | 0 | 0 | – | – |
| brz:ohne_rueckfall | 230 | 1,67 | 154 | 229 / 230 (99,57) | 0 | 0 | 0 | – | – |
| geras6:mit_rueckfall | 128 | 2,31 | 100 | 119 / 128 (92,97) | 0 | 0 | 9 | 16,29 | 16,29 |
| geras6:ohne_rueckfall | 542 | 1,12 | 470 | 517 / 542 (95,39) | 0 | 0 | 172 | 7,38 | 5,79 |
| gf6722:mit_rueckfall | 2 | 2,38 | 1 | 2 / 2 (100,00) | 0 | 0 | 0 | – | – |
| gf6722:ohne_rueckfall | 110 | 1,53 | 82 | 110 / 110 (100,00) | 0 | 0 | 0 | – | – |
| gf6723:ohne_rueckfall | 117 | 0,92 | 105 | 113 / 114 (99,12) | 0 | 0 | 0 | – | – |
| gf6727:ohne_rueckfall | 113 | 1,67 | 107 | 69 / 70 (98,57) | 0 | 0 | 0 | – | – |
| gf6741:ohne_rueckfall | 116 | 1,90 | 99 | 114 / 114 (100,00) | 0 | 0 | 0 | – | – |
| gf6742:mit_rueckfall | 2 | 0,00 | 2 | 2 / 2 (100,00) | 0 | 0 | 0 | – | – |
| gf6742:ohne_rueckfall | 118 | 1,84 | 94 | 116 / 118 (98,31) | 0 | 0 | 0 | – | – |
| gf6743:mit_rueckfall | 1 | 5,56 | 0 | 1 / 1 (100,00) | 0 | 0 | 0 | – | – |
| gf6743:ohne_rueckfall | 144 | 1,78 | 102 | 142 / 144 (98,61) | 0 | 0 | 6 | 17,32 | 13,71 |
| gfs122:mit_rueckfall | 21 | 140,85 | 0 | 20 / 21 (95,24) | 1 | 1 | 0 | – | – |
| gfs122:ohne_rueckfall | 108 | 76,51 | 2 | 102 / 108 (94,44) | 0 | 0 | 0 | – | – |
| gfs128:mit_rueckfall | 26 | 6,36 | 15 | 24 / 26 (92,31) | 0 | 0 | 0 | – | – |
| gfs128:ohne_rueckfall | 87 | 5,39 | 42 | 78 / 80 (97,50) | 0 | 0 | 0 | – | – |
| gfs129:mit_rueckfall | 2 | 0,00 | 2 | 2 / 2 (100,00) | 0 | 0 | 0 | – | – |
| gfs129:ohne_rueckfall | 127 | 12,77 | 54 | 123 / 127 (96,85) | 0 | 0 | 0 | – | – |
| gfs140a:mit_rueckfall | 15 | 0,56 | 14 | 15 / 15 (100,00) | 0 | 0 | 0 | – | – |
| gfs140a:ohne_rueckfall | 130 | 3,02 | 100 | 130 / 130 (100,00) | 0 | 0 | 0 | – | – |
| gfs145:mit_rueckfall | 2 | 7,69 | 1 | 2 / 2 (100,00) | 0 | 0 | 0 | – | – |
| gfs145:ohne_rueckfall | 82 | 2,24 | 70 | 81 / 82 (98,78) | 0 | 0 | 0 | – | – |
| gfs158:mit_rueckfall | 1 | 0,00 | 1 | 1 / 1 (100,00) | 0 | 0 | 0 | – | – |
| gfs158:ohne_rueckfall | 119 | 2,10 | 107 | 116 / 119 (97,48) | 0 | 0 | 0 | – | – |
| gu17:mit_rueckfall | 269 | 2,17 | 182 | 257 / 268 (95,90) | 0 | 0 | 216 | 6,34 | 4,70 |
| gu17:ohne_rueckfall | 1 | 50,00 | 0 | 1 / 1 (100,00) | 0 | 0 | 1 | 25,00 | 15,00 |
| kn65:mit_rueckfall | 645 | 4,39 | 403 | 606 / 643 (94,25) | 1 | 1 | 286 | 18,23 | 16,60 |
| kn65:ohne_rueckfall | 2 | 23,08 | 1 | 2 / 2 (100,00) | 0 | 0 | 1 | 16,67 | 16,67 |
| liktu13:mit_rueckfall | 57 | 8,71 | 21 | 40 / 55 (72,73) | 0 | 0 | 0 | – | – |
| liktu13:ohne_rueckfall | 212 | 5,50 | 106 | 162 / 204 (79,41) | 0 | 0 | 0 | – | – |
| mb2:mit_rueckfall | 402 | 1,11 | 333 | 387 / 402 (96,27) | 0 | 0 | 166 | 5,15 | 4,44 |
| mb2:ohne_rueckfall | 114 | 1,77 | 92 | 106 / 113 (93,81) | 0 | 0 | 60 | 4,95 | 4,11 |
| salzburg3:mit_rueckfall | 56 | 2,08 | 41 | 51 / 55 (92,73) | 0 | 0 | 0 | – | – |
| salzburg3:ohne_rueckfall | 304 | 3,59 | 231 | 287 / 299 (95,99) | 1 | 1 | 0 | – | – |
| sf409:mit_rueckfall | 60 | 2,65 | 44 | 58 / 59 (98,31) | 0 | 0 | 0 | – | – |
| sf409:ohne_rueckfall | 134 | 1,92 | 112 | 133 / 133 (100,00) | 0 | 0 | 0 | – | – |
| taisten:mit_rueckfall | 2 | 6,25 | 1 | 1 / 2 (50,00) | 0 | 0 | 1 | 5,71 | 0,00 |
| taisten:ohne_rueckfall | 306 | 0,77 | 261 | 291 / 306 (95,10) | 0 | 0 | 174 | 6,56 | 5,16 |
| vor254:mit_rueckfall | 274 | 1,93 | 216 | 235 / 273 (86,08) | 0 | 0 | 109 | 10,32 | 7,97 |
| vor254:ohne_rueckfall | 5 | 5,45 | 3 | 4 / 5 (80,00) | 0 | 0 | 0 | – | – |
| vor259:mit_rueckfall | 28 | 0,39 | 26 | 27 / 27 (100,00) | 0 | 0 | 6 | 6,48 | 5,61 |
| vor259:ohne_rueckfall | 178 | 0,72 | 162 | 172 / 174 (98,85) | 0 | 0 | 65 | 6,22 | 4,93 |
| wn15484:mit_rueckfall | 1 | 0,00 | 1 | 1 / 1 (100,00) | 0 | 0 | 1 | 8,70 | 8,70 |
| wn15484:ohne_rueckfall | 493 | 1,32 | 451 | 418 / 493 (84,79) | 0 | 0 | 437 | 15,03 | 12,80 |

## Rückfall-Stichproben

Die zehn zufällig ausgewählten Rückfall-Zuschnitte je Quelle mit den meisten Rückfällen wurden nach dem Lauf gesichtet: `kn65`, `mb2`, `vor254` und `gu17` (jeweils `daten/pool/<quelle>/pruefbogen_rueckfall.jpg`). Bei kn65 und gu17 sind am oberen Rand teils Notenspitzen der vorherigen Zeile sichtbar; einzelne Textzeilen wirken unten angeschnitten, auch bei als sauber markierten Bildern. In mb2 und vor254 reichen in einzelnen Beispielen Text oder Initialen nahe an die Bildkante. Die automatische Sauberkeitsauswahl ist daher keine Garantie für vollständige Textzeilen und bleibt eine Unsicherheitsquelle für die CER.

Die Vergleiche ohne Linien-Rückfall sind bei kn65 (2 Systeme), vor254 (5) und gu17 (1) viel zu klein für eine belastbare Aussage. Die hohen Zahlen von Rückfällen bündeln sich in diesen Quellen und mb2; ein Rückfall ist kein Nachweis für einen falschen Zuschnitt.

## Datenbasis und Grenzen

Die gültigen GT-Indexzeilen wurden zu Systemen zusammengefasst, indem PAGE-Notationsregionen derselben Zeile nach x-Position verbunden wurden. Zuschnitte enden vor der nächsten bekannten Notationsregion; der obere Rand wird aus den erkannten Linien und der höchsten GT-Tonlage bestimmt, bei unsicherer Erkennung aus der ursprünglichen Region. Nicht eindeutig zuordenbare Regionen und Zeilen mit weiteren Regionen ohne gültige GT sind in `daten/pool/probleme.jsonl` dokumentiert und nicht in den Tabellen enthalten.

Die 203 geprüften automatischen Wn-15484-Systeme ohne PAGE-Region werden wie vom Projektleiter entschieden nur gezählt und nicht gemessen. Die obere Bildgrenze nutzt die höchste GT-Tonlage und ist daher nicht ohne Weiteres auf ungesehene Bilder ohne GT übertragbar. Die GT-Indizes vereinheitlichen bereits Bearbeiterkonventionen, dennoch können insbesondere Pes-Reihenfolgen und Grazer Strichkonventionen die Vergleichbarkeit beeinflussen. Besonders auffällig ist gfs122 mit 86,18 % Tonlagen-SER: In der GT wird ein gedehnter Rezitationsbalken als eine Note gezählt, während das Modell auf demselben Balken wiederholt silbenbezogene Töne ausgeben kann; der Projektleiter hat dies am Bild 0003_02 bestätigt. Es handelt sich um eine andere Kodierkonvention, nicht um einen Lesefehler. Die Text-GT lässt dekorierte Initialen aus und löst Abkürzungen auf; die CER enthält deshalb auch Unterschiede der Transkriptionskonvention.

Die neue Prüfgruppe enthält die übrigen Quellen; die alte Prüfgruppe umfasst geras6, kn65, wn15484, gu17 und vor254, die Trainingsgruppe brlm33, brlm34, mb2 und vor259. Innerhalb der alten Gruppe wurden früher nur 200 Systeme gemessen. Die Trainingsgruppe ist keine unabhängige Prüfmenge.

Listen, Zuschnitte, Prüfbögen, Lesungen und Fehlerprotokoll liegen unter `daten/pool/`. Die Kategorien `zuschnitt` sind automatisierte Hinweise; mehrere gleichzeitige Hinweise stehen in `zuschnitt_flags`.

## Inventar

| Quelle | GT-Regionen im Index | Gemessene Systeme | Enthaltene GT-Teile | Mehrteilige Systeme | Textreferenzen | Linien-Rückfälle | Nicht zugeordnete / ausgeschlossene GT-Teile |
|---|---:|---:|---:|---:|---:|---:|---:|
| brixen7 | 361 | 297 | 349 | 52 | 0 | 114 | 12 |
| brlm33 | 333 | 268 | 333 | 65 | 267 | 2 | 0 |
| brlm34 | 331 | 270 | 331 | 61 | 270 | 37 | 0 |
| brz | 282 | 273 | 281 | 8 | 0 | 43 | 1 |
| geras6 | 799 | 670 | 798 | 128 | 339 | 128 | 1 |
| gf6722 | 125 | 112 | 125 | 13 | 0 | 2 | 0 |
| gf6723 | 129 | 117 | 127 | 10 | 0 | 0 | 2 |
| gf6727 | 130 | 113 | 130 | 17 | 0 | 0 | 0 |
| gf6741 | 132 | 116 | 132 | 16 | 0 | 0 | 0 |
| gf6742 | 135 | 120 | 135 | 15 | 0 | 2 | 0 |
| gf6743 | 170 | 145 | 168 | 23 | 7 | 1 | 2 |
| gfs122 | 129 | 129 | 129 | 0 | 0 | 21 | 0 |
| gfs128 | 116 | 113 | 116 | 3 | 0 | 26 | 0 |
| gfs129 | 131 | 129 | 129 | 0 | 0 | 2 | 2 |
| gfs140a | 145 | 145 | 145 | 0 | 0 | 15 | 0 |
| gfs145 | 84 | 84 | 84 | 0 | 0 | 2 | 0 |
| gfs158 | 120 | 120 | 120 | 0 | 0 | 1 | 0 |
| gu17 | 322 | 270 | 322 | 52 | 268 | 269 | 0 |
| kn65 | 753 | 647 | 753 | 106 | 406 | 645 | 0 |
| liktu13 | 336 | 269 | 334 | 65 | 0 | 57 | 2 |
| mb2 | 783 | 516 | 593 | 77 | 309 | 402 | 190 |
| salzburg3 | 433 | 360 | 433 | 73 | 0 | 56 | 0 |
| sf409 | 236 | 194 | 233 | 38 | 0 | 60 | 3 |
| taisten | 378 | 308 | 378 | 70 | 308 | 2 | 0 |
| vor254 | 320 | 279 | 320 | 41 | 277 | 274 | 0 |
| vor259 | 234 | 206 | 234 | 28 | 204 | 28 | 0 |
| wn15484 | 720 | 494 | 516 | 22 | 494 | 1 | 204 |

Einzelne Ausschlussgründe:

- brixen7: Zeile enthält weitere Regionen ohne gültige GT: 12.
- brz: Zuschnitt durch nächste Notenregion begrenzt: 1.
- geras6: Zeile enthält weitere Regionen ohne gültige GT: 1.
- gf6723: Zeile enthält weitere Regionen ohne gültige GT: 2.
- gf6743: Zeile enthält weitere Regionen ohne gültige GT: 2.
- gfs129: Zeile enthält weitere Regionen ohne gültige GT: 2.
- liktu13: Zeile enthält weitere Regionen ohne gültige GT: 2.
- mb2: Zeile enthält weitere Regionen ohne gültige GT: 190.
- sf409: Region nicht eindeutig in PAGE-XML: 1.
- sf409: Zeile enthält weitere Regionen ohne gültige GT: 2.
- wn15484: Zeile enthält weitere Regionen ohne gültige GT: 1.
- wn15484: keine PAGE-Region im Index: 203.

## Untersuchung auffälliger Quellen

Je Quelle wurden fünf Fehlerbeispiele mit fester Zufallsauswahl und verschiedenen Seiten aus den betroffenen Systemen gewählt. Bei mb2 sind dies fünf Beispiele der ursprünglich falsch bewerteten Stichprobe vor der Parserkorrektur. Die Auswahl beschreibt Fehlerfälle und ist keine Zufallsstichprobe aller Systeme. Die Verweise führen zu den tatsächlichen Modellzuschnitten; vollständige GT-Labels und Lesungen stehen in `daten/pool/auffaelligkeiten/*.json`. Bei Tonfolgen stehen die Buchstaben a–m für geometrische Positionen, nicht für absolute Tonhöhen.

Der c5-Befund betraf den Auswerter, nicht das Lesen: `noten_token` erkannte nur c1–c4 und f1–f4. Ein ausgegebenes c5 wurde daher als Ton c und Ziffer 5 zerlegt. Nach Korrektur auf Schlüssel bis Linie 5 werden dieselben Lesungen neu ausgewertet. Für mb2 verbessert sich der bewertete Anfangsschlüssel von 66,02 % auf 95,73 % und die Tonlagen-SER von 2,17 % auf 1,25 %. Die früheren Ergebnisse stehen zur Nachvollziehbarkeit in `daten/pool/ergebnis_vor_c5_korrektur.json`.

Bei wn15484 sind 46 der 75 Schlüsselabweichungen f2→c2 und weitere 20 f3→c3; bei vor254 sind es 32 von 39 f3→c3. Das ist eine systematische F/C-Unterscheidung bei überwiegend unveränderter geometrischer Tonfolge. Ob jeder GT-Schlüssel anhand der historischen Zeichenform richtig kodiert ist, kann diese Stichprobe allein nicht beweisen.

Für gfs129 bestehen 120 der 156 Tonedits aus Einfügungen am Ende (56 von 129 Systemen); in gfs128 sind es 27 von 123 Edits (16 von 113 Systemen). Die GT lässt Kustoden weg. Die Beispiele zeigen zusätzlich echte oder mutmaßliche Einzeltonabweichungen und mindestens einen Fall mit zusätzlicher im Bild sichtbarer Notation außerhalb des GT-Labels. Nicht jede Endeinfügung ist damit automatisch als Kustos erklärt.

### mb2: ursprüngliche c5-Auffälligkeit

| System und Bild | GT | Lesung | Befund |
|---|---|---|---|
| [mb2/0085_10](../daten/pool/mb2/bilder/0085_10.jpg) | c5 | c5 | Parserfehler: c5 ist im Bild und in der Lesung vorhanden; der alte Parser zählte es weder als Schlüssel noch korrekt als Nicht-Ton. |
| [mb2/0093_08](../daten/pool/mb2/bilder/0093_08.jpg) | c5 | c5 | Parserfehler: sichtbares c5 wird vom Modell korrekt ausgegeben; die alte Auswertung übersah es. |
| [mb2/0088_13](../daten/pool/mb2/bilder/0088_13.jpg) | c5 | c5 | Parserfehler: c5 stimmt mit der GT überein, auch die Tonfolge ist identisch. |
| [mb2/0184_02](../daten/pool/mb2/bilder/0184_02.jpg) | c5 | c5 | Parserfehler: Modell und GT geben c5 aus, die Tonfolge stimmt überein. |
| [mb2/0301_06](../daten/pool/mb2/bilder/0301_06.jpg) | c5 | c4 | Verbleibende Schlüsselabweichung: GT c5, Modell c4; der Schlüssel steht im Bild am Fünfliniensystem, die Tonfolge stimmt. |

### wn15484: Anfangsschlüssel

| System und Bild | GT | Lesung | Befund |
|---|---|---|---|
| [wn15484/0065_05](../daten/pool/wn15484/bilder/0065_05.jpg) | f2 | c2 | F/C-Typabweichung bei gleicher Linie; der Schlüssel liegt sehr weit links, die Tonfolge stimmt. |
| [wn15484/0077_02](../daten/pool/wn15484/bilder/0077_02.jpg) | f2 | c2 | F/C-Typabweichung bei gleicher Linie; die Tonfolge stimmt, die Form des Zeichens kann verwechselt werden. |
| [wn15484/0051_05](../daten/pool/wn15484/bilder/0051_05.jpg) | f2 | c2 | F/C-Typabweichung bei gleicher Linie; die Tonfolge stimmt, das Zeichen liegt nahe am linken Rand. |
| [wn15484/0009_05](../daten/pool/wn15484/bilder/0009_05.jpg) | f2 | c2 | F/C-Typabweichung bei gleicher Linie; der linke Seitenrand erschwert die Sicht auf das Zeichen, die Tonfolge stimmt. |
| [wn15484/0071_04+0071_05](../daten/pool/wn15484/bilder/0071_04+0071_05.jpg) | f2 | c2 | F/C-Typabweichung bei gleicher Linie in einer zusammengeführten Zeile; die Tonfolge stimmt. |

### vor254: Anfangsschlüssel

| System und Bild | GT | Lesung | Befund |
|---|---|---|---|
| [vor254/0092_07](../daten/pool/vor254/bilder/0092_07.jpg) | f3 | c3 | F/C-Typabweichung bei gleicher Linie; außerdem eine Tonpositionsabweichung und unten als angeschnitten markierter Text. |
| [vor254/0108_10](../daten/pool/vor254/bilder/0108_10.jpg) | f3 | c3 | F/C-Typabweichung bei gleicher Linie, geometrische Tonfolge stimmt. |
| [vor254/0110_10+0110_11](../daten/pool/vor254/bilder/0110_10+0110_11.jpg) | f3 | c3 | F/C-Typabweichung bei gleicher Linie, trotz Initiale stimmt die Tonfolge. |
| [vor254/0082_01](../daten/pool/vor254/bilder/0082_01.jpg) | f3 | c3 | F/C-Typabweichung bei gleicher Linie; die Tonfolge stimmt, Textanschnitt ist markiert. |
| [vor254/0098_02](../daten/pool/vor254/bilder/0098_02.jpg) | f3 | c4 | GT f3, Modell c4: Typ und Linienposition weichen ab; die Tonfolge stimmt, Textanschnitt ist markiert. |

### liktu13: Anfangsschlüssel

| System und Bild | GT | Lesung | Befund |
|---|---|---|---|
| [liktu13/0025_08](../daten/pool/liktu13/bilder/0025_08.jpg) | c4 | c3 | C-Schlüssel eine Linie tiefer ausgegeben; die Tonfolge stimmt. Bild/GT-Linienlage wegen des gebogenen Systems nachprüfen. |
| [liktu13/0005_03](../daten/pool/liktu13/bilder/0005_03.jpg) | c3 | c2 | Referenz c3 stammt aus einer früheren, nicht berichtigten Lesung; Roh-GT und Modell sagen c2. Daher GT-Konflikt, nicht sicher als Modellfehler entscheidbar. |
| [liktu13/0018_10+0018_11](../daten/pool/liktu13/bilder/0018_10+0018_11.jpg) | f2 | c3 | Referenz f2 stammt aus einer früheren, nicht berichtigten Lesung; Roh-GT sagt f3, Modell c3. Zudem 13 Tonedits bei Initialteilung: Referenz und Zuschnitt gemeinsam prüfen. |
| [liktu13/0015_11+0015_12](../daten/pool/liktu13/bilder/0015_11+0015_12.jpg) | c2 | c4 | GT c2, Modell c4 bei Initialteilung; eine Tonabweichung und Warnung fremd_unten. Schlüsselplatzierung im Bild nachprüfen. |
| [liktu13/0011_08+0011_09](../daten/pool/liktu13/bilder/0011_08+0011_09.jpg) | c4 | c3 | GT c4 wurde vom Projektleiter gesetzt, Modell gibt c3; erste Teilregion enthält im Index nur den Schlüssel. Drei Tonedits; Initialteilung und Linienlage prüfen. |

### gfs129: Tonlagenfehler

| System und Bild | GT | Lesung | Befund |
|---|---|---|---|
| [gfs129/0006_05](../daten/pool/gfs129/bilder/0006_05.jpg) | `defdccdfffg` | `defdccdfffgfi` | Zwei zusätzliche Töne am Ende; Roh-GT enthält einen Kustos, der in der Mess-GT entfernt ist. Das Modell markiert die zusätzlichen Endtöne nicht als Kustos: möglicher Kustos-/Rand-Effekt. |
| [gfs129/0015_02](../daten/pool/gfs129/bilder/0015_02.jpg) | `defefeed` | `defedfeed` | Ein zusätzliches d innerhalb der Folge; eng benachbarte quadratische Noten im Bild. Einzeltonlesung beziehungsweise GT-Ausrichtung prüfen. |
| [gfs129/0009_04](../daten/pool/gfs129/bilder/0009_04.jpg) | `fghgfefghihgfg` | `fghgfefghihgfghj` | Zwei zusätzliche Töne am Ende; im Bild befinden sich Korrekturstriche und ein Kustos, der aus der GT entfernt wurde. Ein Einfluss des Randes ist plausibel, aber nicht einzeln bewiesen. |
| [gfs129/0002_03](../daten/pool/gfs129/bilder/0002_03.jpg) | `efhhhhhi` | `efhhhhhhihk` | Drei Einfügungen: ein zusätzliches h in der Wiederholung und zwei Töne am Ende. Roh-GT enthält dort einen entfernten Kustos; Wiederholungs- und Randfehler unterscheiden. |
| [gfs129/0008_06](../daten/pool/gfs129/bilder/0008_06.jpg) | `hfefghighg` | `hefghighgfi` | Ein f fehlt in der Lesung und zwei Töne kommen am Ende hinzu; das Bild hat eine beschädigte Stelle und einen aus der GT entfernten Kustos. |

### gfs128: Tonlagenfehler

| System und Bild | GT | Lesung | Befund |
|---|---|---|---|
| [gfs128/0020_05](../daten/pool/gfs128/bilder/0020_05.jpg) | `ceffhhgfggighfefghgfhhihfeggig` | `ceffhhgfggighfefghgfhhihfegghg` | Eine Positionsersetzung i→h in der Folge; der Kustos wird in der Ausgabe mit + markiert und nicht als Ton gezählt. |
| [gfs128/0004_04](../daten/pool/gfs128/bilder/0004_04.jpg) | `efhhhhgfhfhfhefecde` | `efhhhhhgfhfhfhefeefe` | Ein zusätzliches h und zwei Positionsersetzungen; dicht gesetzte Noten und Korrekturzeichen im Bild. Die Einzelzuordnung ist nachzuprüfen. |
| [gfs128/0013_03](../daten/pool/gfs128/bilder/0013_03.jpg) | `hfeffdhhhhhjjihg` | `hfeffdhhhhjjihg` | Ein h in einer Wiederholung fehlt; die GT enthält einen Binnenschlüsselwechsel. Der Kustos wird als solcher markiert. |
| [gfs128/0016_05](../daten/pool/gfs128/bilder/0016_05.jpg) | `hhhhghfehh` | `hhhhghfehhhh` | Zwei zusätzliche h am Ende: Im Bild folgen bei Lumen weitere Noten, während das GT-Label bereits endet. Bildausschnitt und GT-Abdeckung stimmen dort nicht vollständig überein. |
| [gfs128/0008_06](../daten/pool/gfs128/bilder/0008_06.jpg) | `ehfhgfeeefgfeded` | `ehfhgfeeefffeded` | Eine Positionsersetzung g→f in der Mitte; die GT enthält dort ein b-Vorzeichen, der Kustos am Ende ist korrekt getrennt. |

