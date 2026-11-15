# Ganze Seiten statt Systemausschnitte

Worker „seiten“, 12. und 13. November 2026. Frage: Kann LightOnOCR (Lauf `s4t`, `checkpoint-53092`) ganze Chorbuchseiten lesen oder lernen, die Systeme in Lesereihenfolge hintereinander auszugeben? Stand 13.11. abends: seiten_a (Abschnitte 4 bis 6), Eingabekante und weitere Trainingsseiten (7, 8) und Neutraining seiten_b (9) ausgewertet. Abschnitt 5 ist mit den Zielen vom 12.11. gerechnet; Abschnitt 9 rechnet alle Modelle mit den berichtigten Zielen neu.

Code (Branch `worker/seiten`): `seiten.py` (Inventar, Auflösung, Lückenprüfung, Prüfmenge, Trainingsdaten: `python seiten.py inventar | aufloesung | probe | probe_abschnitte | train [Ordner [Abschnitte]]`), `seiten_messen.py` (Messung einer Lesung), `seiten_vergleich.py` (vorher/nachher), `lesen.py --kante` (größere Eingabekante; schreibt Bildtoken, Ausgabetoken und Sekunden je Lesung), `metriken.py` (Schlüssel `c5`/`f5`). Jobskripte für MUSICA: `cluster/lesen_seiten.sh` (Lesetest, `SPECS` für einzelne Formen), `cluster/train_seiten.sh` (seiten_a), `cluster/train_seiten_b.sh` (seiten_b), `cluster/kante.sh` (Eingabekante); `cluster/manifest_seiten.txt` (Größen aller hochgeladenen Code- und Datendateien). Daten unter `daten/seiten/` (nicht im Repository): `seiten.jsonl`, `inventar.json`, `aufloesung.json`, `probe/` (Prüfmenge), `train/` (seiten_a), `train2/` (seiten_b), `aus/` (Lesungen); Checkpoints unter `runs/seiten_a/` (lokal) und `$DATA/lighton_choral_seiten/laeufe/` (MUSICA).

## Ergebnis in Kürze

Ohne Seitentraining liest s4t eine ganze Seite nicht: etwa ein System, keine Zeilenumbrüche, 94 % Tonlage-SER auf den val/test-Seiten. Schon eine Epoche Weitertraining mit 13 % Mehrsystem-Beispielen (seiten_a) ändert das grundlegend. Das Neutraining aus dem Basismodell mit 26 % Mehrsystem-Beispielen (seiten_b, 4 Epochen) liest ganze Seiten der fünf nie trainierten Prüfhandschriften mit 2,1 % Tonlage-SER, genauso gut wie Systemausschnitte an bekannten Kästen (2,1 %), und CantusDB-Seiten der Trainingsquellen mit 2,9 % (val) bzw. 5,4 % (test); die Systemlesung bleibt dabei gleich oder wird besser (AMNLT 1,80 → 1,71 %). Damit kann das Modell Seiten ohne Systemerkennung und Zuschnitt lesen. Bei sehr kleiner Auflösung (CantusDB, ~7 px je Tonschritt) bleiben Abschnitte mit 2 bis 4 Systemen etwas genauer; eine größere Eingabekante hilft ohne Training nicht (Abschnitt 7). Gewählt ist seiten_b Epoche 4 (`checkpoint-71296`). Schwächen (Abschnitt 10): Der Anfangsschlüssel der Prüfhandschriften fällt von 92,5 auf 87,0 %, weil seiten_b F-Schlüssel öfter als C-Schlüssel liest (echter Nachteil, vermutlich durch den C-lastigen Seitenanteil); der höhere Transkribus-Text-CER (4,9 → 5,5 %) ist überwiegend Rauschen.

## 1. Seiten mit vollständigen Zielen

Eine Seite gilt als vollständig, wenn jedes Notensystem der Seite eine GABC-Zeile mit `status` voll hat, keine Initiale unsicher ist und kein System als „leer“ markiert ist (auf sbe-0611 112r trägt ein solches System Noten). Seitenziel = Zeilenziele in Lesereihenfolge, getrennt durch einen Zeilenumbruch; Kästen derselben Notenzeile (links und rechts einer Initiale) von links nach rechts. Systemliste: bei Transkribus die Notationsregionen der PAGE-XML, bei sbe-0611, fcc-0002, d-ka-aug-lx und Addendum die Kästen des Ganzseitendetektors (`review/results_<quelle>.json`).

| Quelle | Seiten | vollständig | Systeme je Seite (Median) | Ziel-Token Median / Max |
| --- | ---: | ---: | ---: | --- |
| brlm33 | 30 | 3 | 9 | 1.150 / 1.223 |
| brlm34 | 30 | 2 | 9 | 1.191 / 1.210 |
| mb2 | 31 | 3 | 10 | 1.294 / 1.298 |
| vor259 | 27 | 6 | 8 | 637 / 734 |
| sbe-0611 | 523 | 83 | 15 | 2.379 / 2.980 |
| fcc-0002 | 484 | 58 | 13 | 1.890 / 2.349 |
| d-ka-aug-lx | 390 | 5 | 14 | 2.851 / 3.359 |
| d-ka-aug-lx-addendum | 57 | 6 | 8 | 805 / 893 |
| zusammen | | 166 (141 train, 9 val, 16 test) | | |

Ausgeschlossen sind die sieben CantusDB-Quellen, deren Systemkästen nur aus `lage.jsonl` kommen (a-kn-1010, a-kn-1012, a-kn-1018, a-wn-1799, ch-p-18, d-knd-1161, f-pn-lat-12044). `lage.jsonl` kennt nur Systeme mit Zuschnitt; die Sichtprüfung zeigt auf vielen Seiten fehlende Systeme. Formal wären dort 789 Seiten vollständig; nutzbar erst mit eigener Systemerkennung.

Auch der Ganzseitendetektor verfehlt Systeme, und zwar so, dass sie gar nicht in der Liste stehen (d-ka-aug-lx 017r: 6 Kästen, etwa 14 Systeme). Das fiel erst im Prüfbogen der Trainingsabschnitte auf (ein Abschnitt mit etwa 9 Systemen im Bild und 2 im Ziel); der erste Trainingslauf wurde deshalb nach 16 s abgebrochen. Seither prüft `luecken()` jede Review-Seite unabhängig: Vier-Linien-Kamm im Linienabstand der Seite über einen Grat-Filter (jede der vier Linien muss vorhanden sein, sonst greifen Seitenkanten), Treffer außerhalb aller Kästen gelten als fehlendes System; dazu ein Sprung im Zeilenabstand über das 1,6-fache des Medians. Blasse Systeme rutschen durch (017r: 2 von etwa 8 gefunden), deshalb schließt jeder Hinweis die ganze Seite aus. Das traf 94 Review-Seiten (fcc-0002 41, d-ka-aug-lx 37, sbe-0611 15, Addendum 1), darunter 11 der 141 vollständigen Trainingsseiten. Bei einem Teil der fcc- und sbe-Fälle ist der Sprung ein Textblock ohne Noten; diese Seiten sind vorsichtshalber mit ausgeschlossen (Prüfbogen `daten/seiten/train/pruefbogen_luecken.jpg`). Die 25 val/test-Seiten des Lesetests haben keine Hinweise.

## 2. Auflösung

Seiten werden auf 1.540 px längste Kante skaliert. Pixel je Tonschritt = Linienabstand / 2 nach der Skalierung (Linienabstand bei Transkribus Höhe der Notationsregion / 3,5, bei den Review-Quellen der Linienabstand der Seite aus dem Detektor).

| Quelle | Linienabstand im Original | ganze Seite | obere/untere Hälfte | Systemausschnitt |
| --- | ---: | ---: | ---: | ---: |
| brlm33 | 45 | 11,7 | 16,9 | 24,4 |
| brlm34 | 41 | 10,4 | 15,2 | 21,8 |
| mb2 | 61 | 10,6 | 16,4 | 30,4 |
| vor259 | 85 | 13,0 | 19,4 | 42,3 |
| sbe-0611 | 20 | 7,2 | 9,6 | 13,2 |
| fcc-0002 | 20 | 7,2 | 9,6 | 14,1 |
| d-ka-aug-lx | 22 | 7,6 | 10,6 | 14,7 |
| d-ka-aug-lx-addendum | 28 | 9,7 | 13,5 | 18,1 |

Eine ganze Seite liegt überall unter dem 14-px-Patch des Bildencoders, bei den CantusDB-Quellen bei etwa der Hälfte. Hälften reichen für Transkribus, nicht für CantusDB: Die Seitenbilder sind dort nur etwa 1.600 px hoch, der Linienabstand im Original beträgt 20 px, mehr als 10 px je Tonschritt gibt das Original nicht her. Abschnitte mit 2 bis 4 Systemen bleiben auf der Breite der Ausschnitte und damit bei etwa 13 px. Höhe/3,5 überschätzt den Linienabstand bei manchen Transkribus-Quellen um bis zu 25 % (vor254: 87 statt 67 px gemessen). Eine Seite ergibt etwa 2.000 bis 2.300 Bildtoken.

## 3. Lesetest ohne Seitentraining

45 Seiten: die 25 vollständigen val/test-Seiten (brlm33 1, vor259 1, sbe-0611 16, fcc-0002 4, d-ka-aug-lx 2, Addendum 1) und je 4 ganze Seiten der Prüfhandschriften geras6, kn65, wn15484, gu17, vor254 aus der PAGE-XML (nur Notations-GT, dort nur Tonlage). Jede Seite wurde dreifach gelesen: ganz (`--max-tokens 4096`), als obere und untere Hälfte (Schnitt zwischen zwei Systemen unter der Textzeile, 3072) und als Systemausschnitte aller Systeme ohne Filter (Zuschnitt wie im Korpus an den bekannten Kästen, 600). Hälften und Ausschnitte werden je Seite in Lesereihenfolge zusammengesetzt. Tonlagen-SER über die ganze Seite mit Levenshtein-Ausrichtung; ein System gilt als erkannt, wenn mindestens die Hälfte seiner Töne gleich ausgerichtet ist. Job 1938492, Lesungen in `daten/seiten/aus/s4t_checkpoint-53092/`.

| Form | val/test Tonlage-SER | val/test Systeme erkannt | val/test Text-CER | Prüfseiten Tonlage-SER | Prüfseiten Systeme erkannt |
| --- | ---: | ---: | ---: | ---: | ---: |
| ganze Seite | 94,2 % | 6,6 % | 106,8 % | 65,5 % | 24,4 % |
| Hälften | 68,6 % | 19,1 % | 66,6 % | 41,1 % | 59,5 % |
| Systemausschnitte | 2,2 % | 99,1 % | 1,6 % | 2,9 % | 99,4 % |

Gemessen mit der korrigierten Metrik (Schlüssel `c5`/`f5` als Schlüssel, nicht als Ton; Hinweis von pool_codex); die Werte vor der Korrektur wichen höchstens um 0,3 Punkte ab.

Das Modell schreibt nie einen Zeilenumbruch. Auf der ganzen Seite liest es meist etwa ein System an Tönen (Median rund 80 von 400) und hört dann auf; dabei springt es zwischen Zeilen (sbe-0611 223r: Silben aus System 1 und 2 gemischt). Bei Hälften liest es einige Systeme hintereinander, lässt andere aus und setzt an den Übergängen erfundene Schlüsselwechsel (`c5`, `c3`). Schleifen sind selten (1 von 45 Seiten); 6 Seiten laufen bis 4.096 Token mit erfundenem Text weiter. Die Erwartung „nur das erste System oder Schleifen“ trifft damit halb zu: kurzer Abbruch nach etwa einem System, kaum Schleifen.

Ausnahme wn15484 (Quadratnotation, 5 Systeme je Seite, rund 19 px je Tonschritt schon auf der ganzen Seite): ganze Seite 20,5 % Tonlage-SER und 75 % der Systeme, Hälften 1,5 % und 100 %. Das Modell kann also ohne Seitentraining mehrere Systeme hintereinander lesen, wenn die Auflösung reicht.

Systemausschnitte an bekannten Kästen sind auf diesen Seiten mit rund 2 bis 3 % sehr gut, auch ungefiltert. Der Gewinn eines Seitenmodells läge also im Wegfall von Systemerkennung und Zuschnitt, nicht in einer besseren Lesung gut geschnittener Systeme.

## 4. Trainingsversuch seiten_a

Freigegeben vom Projektleiter: Weitertraining von `s4t/checkpoint-53092`, eine Epoche, Lernraten halbiert (Bild 5e-5, Decoder 2,5e-5), sonst wie s4t (Bildform `streifen`, Gradientenakkumulation 8). Trainingsdaten: die 13.273 Systeme von s4t (AMNLT mit Wortgrenzen, CantusDB-Korpus, Transkribus-Korpus) und 2.390 Mehrsystem-Beispiele (13 %) aus `daten/seiten/train/train.jsonl`, nur aus train-Systemen:

| Art | Beispiele | Systeme | Ziel-Token Median / Max |
| --- | ---: | ---: | --- |
| Abschnitte mit 2 bis 4 aufeinanderfolgenden vollen Systemen (je Lauf voller Systeme einer, ab 6 Systemen zwei) | 2.000 | 5.535 | 446 / 1.110 |
| Hälften vollständiger Seiten | 260 | 1.750 | 1.081 / 1.687 |
| vollständige Seiten | 130 | 1.750 | 2.202 / 3.359 |

Abschnitte schneiden zwischen zwei Notenzeilen unter der Textzeile der oberen: bei den Review-Quellen über die gemessenen Notenlinien (Grat-Filter im mittleren Drittel; die Detektorkästen beginnen an der Textzeile darüber, die oberste Linie liegt etwa 2,5 Linienabstände unter der Kante), bei Transkribus zwischen der Unterkante der Textregion und der nächsten Notationsregion. Nie zwischen zwei Kästen derselben Notenzeile. Am Seitenrand enden Abschnitte unter der letzten Textzeile bzw. beginnen über der ersten Notenzeile (vor der Korrektur reichten 282 Abschnitte bis an den unteren Seitenrand, 190 davon zu mehr als der Hälfte leeres Pergament); Hälften und Seiten behalten den Rand wie im Lesetest. Prüfbogen mit Rand- und Mittelabschnitten: `daten/seiten/train/pruefbogen_abschnitte.jpg`, 10 von 10 passend. Rauchtest (Job 1938560): 16 Beispiele mit den vier längsten Seiten, Speicherspitze 26,1 GB, Speichern, Laden und Lesen in Ordnung.

Gemessen wird auf denselben 45 Seiten in allen Formen, dazu neu die Form „Abschnitte zu 3 Systemen“ (175 Bilder, Randschnitt und 1.540 px wie im Training), die auch s4t liest; als Regressionstest AMNLT-validation, Korpus-validation, Transkribus-validation und die 200 Systeme der Prüfhandschriften.

## 5. Ergebnis seiten_a

Job 1938581, 3:16 h (Training 15.663 Beispiele mit 0,39 s je Beispiel, dann Lesen), Speicherspitze 26,8 GB, val_loss (AMNLT) 0,1044 vorher bzw. 0,1043 nach halber und 0,1049 nach ganzer Epoche. Gelesen und verglichen wird der letzte Checkpoint `checkpoint-15663` (lokal gesichert unter `runs/seiten_a/`); der Zwischenstand `checkpoint-7832` liegt auf MUSICA und ist nicht gelesen. Alle Werte aus den Lesungen mit der korrigierten Metrik neu gerechnet (`seiten_vergleich.py`); vorher = s4t/checkpoint-53092.

Regressionstest der Systemlesung:

| Menge | Tonlage-SER vorher | nachher | Text-CER vorher | nachher | Anfangsschlüssel vorher | nachher |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AMNLT validation | 1,80 % | 1,89 % | 2,29 % | 2,35 % | 99,37 % | 99,46 % |
| CantusDB-Korpus validation | 5,67 % | 5,76 % | 4,10 % | 4,34 % | 95,63 % | 95,82 % |
| Transkribus validation (89 Systeme, berichtigte Ziele) | 0,62 % | 0,77 % | 4,94 % | 5,90 % | 98,86 % | 97,73 % |
| Prüfhandschriften (200 Systeme) | 2,11 % | 2,28 % | – | – | 92,50 % | 92,00 % |

Transkribus validation mit den am 13.11. berichtigten Zielen aus `daten/korpus_transkribus/validation.jsonl` (Fehler im Zuordnungsskript, gefunden von text_claude: Text zweier val-Zeilen in vertauschter Reihenfolge; Referenz aus der aktuellen Datei, nicht aus der Lesung). Der Text-CER steigt dadurch für beide Modelle um knapp einen Punkt: Bei brlm33 0025_09 steht im Bild „net salvatorem | Celi enarrant gloriam“, beide Modelle lesen aber die alte, vertauschte Folge, vermutlich gelernt aus der Trainingszeile brlm34 0008_10 mit demselben Text in derselben vertauschten Form. Vor der Berichtigung (alte Ziele, 89 Systeme): Tonlage 0,62 → 0,77 %, Text-CER 4,02 → 4,99 %. Die Systemlesung wird leicht schlechter (0,1 bis 0,2 Punkte Tonlage, Transkribus-Text 1 Punkt); das liegt im Rahmen der Schwankung zwischen Epochen (README: etwa ein Punkt bei den Prüfhandschriften), ist aber durchgehend in dieselbe Richtung.

Seitenformen auf denselben 45 Seiten, val/test (25 Seiten):

| Form | Tonlage-SER vorher | nachher | Systeme erkannt vorher | nachher | Text-CER vorher | nachher |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ganze Seite | 94,2 % | 9,6 % | 6,6 % | 95,4 % | 106,8 % | 8,2 % |
| Hälften | 68,6 % | 8,1 % | 19,1 % | 97,4 % | 66,6 % | 9,9 % |
| Abschnitte zu 3 Systemen | 60,9 % | 2,9 % | 32,1 % | 99,4 % | 61,0 % | 2,4 % |
| Systemausschnitte | 2,2 % | 1,9 % | 99,1 % | 99,1 % | 1,6 % | 1,4 % |

Prüfseiten (20 Seiten der fünf Prüfhandschriften, nur Noten):

| Form | Tonlage-SER vorher | nachher | Systeme erkannt vorher | nachher |
| --- | ---: | ---: | ---: | ---: |
| ganze Seite | 65,5 % | 2,4 % | 24,4 % | 99,4 % |
| Hälften | 41,1 % | 3,0 % | 59,5 % | 97,6 % |
| Abschnitte zu 3 Systemen | 32,1 % | 2,7 % | 68,5 % | 98,8 % |
| Systemausschnitte | 2,9 % | 2,4 % | 99,4 % | 99,4 % |

Tonlage-SER je Quelle (nachher = seiten_a):

| Quelle | Seiten | ganze Seite vorher | nachher | Hälften nachher | Abschnitte nachher | Ausschnitte vorher | nachher |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| geras6 | 4 | 78,4 % | 1,0 % | 0,7 % | 0,8 % | 1,5 % | 0,7 % |
| gu17 | 4 | 66,3 % | 2,6 % | 1,0 % | 1,6 % | 2,8 % | 2,1 % |
| kn65 | 4 | 58,6 % | 3,7 % | 11,7 % | 6,9 % | 6,6 % | 8,1 % |
| vor254 | 4 | 68,3 % | 3,5 % | 2,5 % | 3,0 % | 3,2 % | 1,5 % |
| wn15484 | 4 | 20,5 % | 1,8 % | 1,8 % | 3,9 % | 0,9 % | 0,3 % |
| brlm33 | 1 | 64,9 % | 0,7 % | 0,3 % | 1,4 % | 0,7 % | 1,1 % |
| vor259 | 1 | 58,9 % | 6,5 % | 0,0 % | 0,0 % | 0,0 % | 0,9 % |
| sbe-0611 | 16 | 94,1 % | 8,7 % | 9,3 % | 3,0 % | 2,1 % | 1,8 % |
| fcc-0002 | 4 | 96,1 % | 2,7 % | 3,5 % | 1,6 % | 1,2 % | 1,2 % |
| d-ka-aug-lx | 2 | 102,3 % | 26,5 % | 9,3 % | 4,5 % | 2,0 % | 2,4 % |
| d-ka-aug-lx-addendum | 1 | 88,5 % | 13,7 % | 13,7 % | 7,1 % | 20,8 % | 12,6 % |

Die Lesung schreibt jetzt je System eine Zeile (bei 30 von 45 Seiten genau so viele Zeilen wie Systeme; Abweichungen meist dort, wo das Ziel eine Notenzeile in zwei Kästen links und rechts einer Initiale teilt) und übernimmt Schlüsselwechsel innerhalb der Seite. Keine Schleifen und Abbrüche auf ganzen Seiten (vorher 1 Schleife, 6 Abbrüche); eine Schleife bei einer Hälfte.

Bewertung: Wo die Seite genug Auflösung hat (Transkribus-Quellen und Prüfhandschriften, 10 bis 19 px je Tonschritt), ist die ganze Seite so gut wie die Ausschnitte. Bei den CantusDB-Quellen mit rund 7 px je Tonschritt bleibt die ganze Seite zurück (sbe-0611 8,7 %, d-ka-aug-lx 26,5 %), Abschnitte mit 2 bis 4 Systemen holen das fast ganz auf (3,0 % bzw. 4,5 %). kn65 ist die einzige Quelle, bei der Hälften und Abschnitte schlechter sind als die ganze Seite (11,7 % und 6,9 % gegen 3,7 %); dort trifft der Schnitt vermutlich eng stehende Systeme.

Korrektur während der Auswertung: Die Abschnitte der Prüfmenge waren zunächst in voller Breite gespeichert (1.600 px bei CantusDB). Ab 1.540 px zerlegt `bildform` (Form `streifen`) ein so breites Bild in zwei gestapelte Hälften; das Modell las dann erst alle linken, dann alle rechten Systemhälften, und die Form kam auf 41 %. Im Training waren Abschnitte auf 1.540 px gespeichert und liefen als ein Streifen. Die Prüf-Abschnitte sind seither ebenso gespeichert und von beiden Checkpoints neu gelesen (Jobs 1939180, 1939181); die alten Lesungen liegen unter `abschnitte_zwei_streifen/`. Ganze Seiten und Hälften waren nicht betroffen.

## 6. Vorschläge

- Für neue Handschriften mit Seitenbildern ab etwa 10 px je Tonschritt (Transkribus-Exporte) ganze Seiten lesen und gegen Ausschnitte stichprobenartig prüfen; Systemerkennung und Zuschnitt entfallen.
- Für niedrig aufgelöste Seiten (CantusDB-Bilder, ~1.600 px Höhe) eine größere Eingabekante versuchen (z. B. 2.300 px statt 1.540) oder Abschnitte mit 2 bis 4 Systemen lesen; Abschnitte brauchen wieder Schnitte zwischen Systemen, aber nur grobe.
- Die Lückenprüfung der Systemlisten auch auf die sieben `lage.jsonl`-Quellen anwenden (eigene Systemerkennung je Seite), um mehr vollständige Seiten zu gewinnen; derzeit stehen nur 130 Trainingsseiten zur Verfügung.
- Den leichten Rückgang der Systemlesung bei einem Neutraining mit Seitenanteil von Anfang an prüfen; der Zwischenstand `checkpoint-7832` ist dafür ein günstiger erster Vergleich.

## 7. Nachtrag: größere Eingabekante ohne Training

Frage des Projektleiters: Brauchen ganze Seiten höhere Auflösung? Die CantusDB-Ausschnitte stammen aus denselben 1.600-px-Bildern und lesen mit 1 bis 2 %, weil sie auf ~13 px je Tonschritt hochskaliert werden; der Engpass ist also die Eingabekante des Modells (1.540 px), nicht die Quellauflösung. Test (Job 1939203): seiten_a liest die 45 Seiten mit 2.300 und 2.800 px längster Kante (Bilder vorab skaliert, `lesen.py --kante` setzt Prozessor und `vision_config.image_size`, aus dem Pixtral die axialen Positionen berechnet).

| Kante | Bildtoken je Seite | val/test Tonlage-SER | Systeme erkannt | Prüfseiten Tonlage-SER | Systeme erkannt |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1.540 | 2.255 | 9,5 % | 95 % | 2,4 % | 99 % |
| 2.300 | 5.084 | 13,7 % | 87 % | 18,8 % | 80 % |
| 2.800 | 7.500 | 43,9 % | 52 % | 71,6 % | 43 % |

Ohne Training verschlechtert jede größere Kante das Ergebnis; nur sbe-0611 bleibt bei 2.300 px gleich (9,2 gegen 8,7 %). Das Modell kennt aus dem Training nur Positionen bis 110 Patches je Seite und nur den Maßstab der 1.540-px-Bilder. Ob mehr Pixel helfen, lässt sich deshalb nur mit Training auf der größeren Kante beantworten; ohne dieses Training bleibt 1.540 px die richtige Wahl.

Kosten (Einzelprozess, H100, 4 Seiten je Kante): Die Lesezeit hängt fast nur an der Ausgabelänge, rund 17 ms je Ausgabetoken bei allen drei Kanten, also etwa 40 s für eine CantusDB-Seite mit 2.400 Token; die Bildtoken (2,3- bzw. 3,3-fach) fallen beim Lesen kaum ins Gewicht. Speicherspitze im Einzelprozess 5,6 GB. Im Training wäre der Aufwand größer, weil jede Seite 5.000 bis 7.500 Bildtoken durch Bildencoder und Decoder schickt; das wäre im Rauchtest zu messen.

## 8. Nachtrag: mehr Trainingsseiten aus den Erkennungsquellen

Für drei der sieben `lage.jsonl`-Quellen liegen vollständige Ganzseiten-Erkennungen des Arbeitsprojekts vor (`review/kloster_a-kn-1018.json`, `paris_ch-p-18.json`, `paris_f-pn-lat-12044.json`); der Systemindex `i` entspricht der Zeilen-id `<folio>_<i:02d>`. Geprüft wird die Zuordnung über die Kästen der Zuschnitte in `lage.jsonl`: Bei ch-p-18 (38 Seiten) und f-pn-lat-12044 (80 Seiten, z. B. 229v) sind Seiten um ein System versetzt; solche Seiten fallen ganz heraus, Systeme ohne Kasten gelten als ungeprüft. a-kn-1012 bleibt ausgeschlossen (Projektleiter: schlecht lesbare Notation), für a-kn-1010, a-wn-1799 und d-knd-1161 fehlt eine vollständige Erkennung.

Die Lückenprüfung (Abschnitt 1) meldet bei diesen Quellen viele Fehlalarme (rote Rubriken, Linierung unter dem Schriftspiegel). Dort sperren Kamm-Treffer nur ganze Seiten und Hälften; Abschnitte schließen nur Sprünge im Zeilenabstand aus, denn ein fehlendes System innerhalb eines Abschnitts erzeugt immer einen solchen Sprung. Neu ist eine Prüfung auf zu enge Abstände (unter 0,7 × Median): f-pn-lat-12044 042v meldet ein System 8 px unter dem vorigen, der Schnitt verlor dadurch eine Textzeile.

Neue Trainingsmenge `daten/seiten/train2/` (alle verfügbaren Abschnitte, noch ohne Deckelung): 4.059 Abschnitte (11.161 Systeme; davon ch-p-18 446, f-pn-lat-12044 493, a-kn-1018 350), 328 Hälften und 164 ganze Seiten (neu: ch-p-18 27, f-pn-lat-12044 6, a-kn-1018 1). Prüfbogen der neuen Quellen: `daten/seiten/train2/pruefbogen_abschnitte.jpg`, 11 von 12 passend; der zwölfte (042v) führte zur Prüfung auf enge Abstände. Die Menge `train/` von seiten_a bleibt unverändert.

## 9. Neutraining seiten_b

Freigegeben vom Projektleiter: Neutraining aus dem Basismodell `LightOnOCR-3-1B-konvertiert` mit den Einstellungen von s4t (4 Epochen, Lernraten 1e-4 Bild / 5e-5 Decoder, Bildform `streifen`, Akkumulation 8, AMNLT mit Wortgrenzen), Eingabekante 1.540 px. Trainingsdaten: die 13.273 Systeme von s4t und alle 4.551 Mehrsystem-Beispiele aus `daten/seiten/train2/train.jsonl` (4.059 Abschnitte, 328 Hälften, 164 Seiten; 26 %), weil ganze Seiten das Ziel sind und keine geprüften Daten liegen bleiben sollen.

Checkpoint-Wahl vorab festgelegt (bestätigt 13.11.): Tonlage-SER auf AMNLT-validation und auf den 9 val-Seiten (ganze Seite); die 15 test-Seiten und die 20 Prüfseiten werden nur berichtet. Je Checkpoint lesen: AMNLT-, Korpus- und Transkribus-validation, die 200 Prüfhandschriften-Systeme, ganze Seiten und Abschnitte; Hälften und Ausschnitte beim letzten Checkpoint.

Die 9 val-Seiten stammen nur aus drei CantusDB-Quellen (sbe-0611 6, fcc-0002 2, d-ka-aug-lx 1), keine aus Transkribus; die Wahl hängt damit an wenigen, ähnlichen Seiten und kann zwischen Epochen schwanken, ohne dass sich die Lesung anderer Quellen entsprechend ändert. Zahl der val- und test-Seiten: 9 und 16, nicht 12 und 13, wie in einer frühen Meldung genannt (dort vor dem Ausschluss der Seiten mit „leeren“ Systemen gezählt). Seit der Korpus-Berichtigung vom 13.11. ist brlm33 0029 (test) nicht mehr vollständig (eine Zeile mit unsicherer Initiale), und vor259 0027 (test) hat ein berichtigtes Ziel; Nach der Gegenprobe (ebenfalls 13.11.: 8 vor259-Zeilen entfernt, 3 Ziele mit v-Korrektur) ist auch vor259 0027 nicht mehr vollständig (Zeile 0027_02). `seiten_messen.py` nimmt die Ziele deshalb aus dem aktuellen Inventar und lässt nicht mehr vollständige Seiten weg: 9 val- und 14 test-Seiten; beide Transkribus-Seiten der Prüfmenge fallen damit heraus. Die Ergebnisse von seiten_a in Abschnitt 5 sind noch mit den alten Zielen auf 25 Seiten gerechnet und werden bei der Auswertung von seiten_b neu gerechnet.

Rauchtest Job 1940131 (dev-QoS): 16 Beispiele mit den vier längsten Seiten (bis 3.604 Token), Speicherspitze 26,4 GB, Speichern, Laden und Lesen in Ordnung. Hauptlauf Job 1940137, 13.11. 10:35 bis 23:03 (12:28 h): Training 7:24 h (71.296 Beispiele, 0,37 s je Beispiel, Spitze 26,8 GB), Lesen etwa 72 min je Checkpoint. Checkpoints `checkpoint-17824/35648/53472/71296` (Epoche 1 bis 4) auf MUSICA; 53472 und 71296 lokal unter `runs/seiten_b/`.

Alle Werte mit den Zielen vom 13.11. (berichtigtes Transkribus-Korpus; Seitenziele aus dem aktuellen Inventar, 9 val-, 14 test-Seiten, 20 Prüfseiten), s4t und seiten_a auf derselben Grundlage neu gerechnet.

Je Epoche (Tonlage-SER; Wahlkriterien fett):

| Checkpoint | **AMNLT val** | **val-Seiten (9)** | test-Seiten (14) | Prüfseiten (20) | Abschnitte val | Korpus val | Transkribus val | Prüfhandschriften-Systeme |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| s4t | 1,80 % | 98,7 % | 93,2 % | 65,5 % | 65,5 % | 5,67 % | 0,65 % | 2,11 % |
| seiten_a | 1,89 % | 10,3 % | 9,5 % | 2,4 % | 2,3 % | 5,76 % | 0,81 % | 2,28 % |
| seiten_b Epoche 1 | 3,12 % | 23,4 % | 29,8 % | 27,1 % | 4,2 % | 7,56 % | 3,57 % | 9,41 % |
| seiten_b Epoche 2 | 1,96 % | 11,2 % | 7,0 % | 2,4 % | 2,9 % | 5,77 % | 0,73 % | 1,50 % |
| seiten_b Epoche 3 | **1,65 %** | 5,4 % | 5,4 % | 2,0 % | 1,6 % | 5,36 % | 0,50 % | 1,46 % |
| seiten_b Epoche 4 | 1,71 % | **2,9 %** | 5,4 % | 2,1 % | 1,5 % | 5,66 % | 0,42 % | 1,74 % |

Die beiden festgelegten Kriterien zeigen auf verschiedene Epochen: AMNLT val auf Epoche 3 (1,65 gegen 1,71 %), die val-Seiten auf Epoche 4 (2,9 gegen 5,4 %). Der AMNLT-Unterschied liegt mit 0,06 Punkten innerhalb der üblichen Schwankung zwischen Epochen, der Unterschied auf den val-Seiten nicht; die val-Seiten stammen aber nur aus drei CantusDB-Quellen. **Auswahl (Projektleiter, 14.11.): Epoche 4, `seiten_b/checkpoint-71296`.** Begründung: Der AMNLT-Abstand von 0,06 Punkten liegt im Rauschen, auf den val-Seiten steht 2,9 gegen 5,4 %, und Ziel sind ganze Seiten. Die Tabellen unten zeigen diesen Checkpoint; er liegt lokal unter `runs/seiten_b/checkpoint-71296/` und auf MUSICA.

Vergleich der Systemlesung s4t → seiten_b Epoche 4:

| Menge | Tonlage-SER s4t | seiten_b | Text-CER s4t | seiten_b | Anfangsschlüssel s4t | seiten_b |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AMNLT validation | 1,80 % | 1,71 % | 2,29 % | 2,00 % | 99,37 % | 99,37 % |
| CantusDB-Korpus validation | 5,67 % | 5,66 % | 4,10 % | 3,56 % | 95,63 % | 95,63 % |
| Transkribus validation (85 Systeme) | 0,65 % | 0,42 % | 4,93 % | 5,50 % | 98,81 % | 98,81 % |
| Prüfhandschriften (200 Systeme) | 2,11 % | 1,74 % | – | – | 92,50 % | 87,00 % |

Anders als bei seiten_a wird die Systemlesung nicht schlechter, sondern bei der Tonlage überall gleich oder besser. Ausnahme ist der Anfangsschlüssel auf den Prüfhandschriften (92,5 → 87,0 %, Epoche 3: 87,5 %); das ist zu prüfen. Der Transkribus-Text-CER steigt (4,9 → 5,5 %).

Seitenformen (Tonlage-SER):

| Gruppe | Form | s4t | seiten_a | seiten_b | Systeme erkannt seiten_b | Text-CER seiten_b |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| val (9) | ganze Seite | 98,7 % | 10,3 % | 2,9 % | 99,2 % | 2,2 % |
| val (9) | Hälften | 70,6 % | 3,5 % | 1,3 % | 100,0 % | 2,5 % |
| val (9) | Abschnitte | 65,5 % | 2,3 % | 1,5 % | 100,0 % | 2,1 % |
| val (9) | Ausschnitte | 1,7 % | 1,7 % | 1,1 % | 100,0 % | 1,7 % |
| test (14) | ganze Seite | 93,2 % | 9,5 % | 5,4 % | 98,5 % | 2,5 % |
| test (14) | Hälften | 69,3 % | 11,4 % | 3,5 % | 99,0 % | 3,2 % |
| test (14) | Abschnitte | 60,2 % | 3,4 % | 3,4 % | 98,5 % | 1,4 % |
| test (14) | Ausschnitte | 2,6 % | 2,1 % | 2,1 % | 99,0 % | 0,9 % |
| Prüfseiten (20) | ganze Seite | 65,5 % | 2,4 % | 2,1 % | 98,8 % | – |
| Prüfseiten (20) | Hälften | 41,1 % | 3,0 % | 1,6 % | 99,4 % | – |
| Prüfseiten (20) | Abschnitte | 32,1 % | 2,7 % | 1,6 % | 99,4 % | – |
| Prüfseiten (20) | Ausschnitte | 2,9 % | 2,4 % | 2,1 % | 99,4 % | – |

Je Quelle (Tonlage-SER):

| Quelle | Seiten | ganze Seite s4t | seiten_a | seiten_b | Abschnitte seiten_b | Ausschnitte s4t | seiten_b |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| geras6 | 4 | 78,4 % | 1,0 % | 1,0 % | 0,5 % | 1,5 % | 0,3 % |
| gu17 | 4 | 66,3 % | 2,6 % | 0,9 % | 1,0 % | 2,8 % | 1,8 % |
| kn65 | 4 | 58,6 % | 3,7 % | 5,0 % | 2,2 % | 6,6 % | 6,0 % |
| vor254 | 4 | 68,3 % | 3,5 % | 3,3 % | 2,9 % | 3,2 % | 2,6 % |
| wn15484 | 4 | 20,5 % | 1,8 % | 0,6 % | 2,4 % | 0,9 % | 0,6 % |
| sbe-0611 | 16 | 94,1 % | 8,7 % | 4,9 % | 2,6 % | 2,1 % | 1,7 % |
| fcc-0002 | 4 | 96,1 % | 2,7 % | 2,2 % | 1,0 % | 1,2 % | 0,9 % |
| d-ka-aug-lx | 2 | 102,3 % | 26,5 % | 5,7 % | 3,9 % | 2,0 % | 1,0 % |
| d-ka-aug-lx-addendum | 1 | 88,5 % | 13,7 % | 1,6 % | 13,7 % | 20,8 % | 13,1 % |

Bewertung: Mit dem Seitenanteil von Anfang an liest das Modell ganze Seiten der Prüfhandschriften mit 2,1 % und die CantusDB-Seiten der Trainingsquellen mit 2,9 % (val) bzw. 5,4 % (test), bei 98 bis 99 % erkannten Systemen, keinen Schleifen und keinen Abbrüchen; 39 von 43 Seitenlesungen haben genau so viele Zeilen wie Systeme. Die Lücke zu den Ausschnitten ist auf den Prüfseiten geschlossen (2,1 gegen 2,1 %), auf den CantusDB-Seiten mit ~7 px je Tonschritt bleibt sie (sbe-0611 4,9 gegen 1,7 %), Abschnitte zu 3 Systemen kommen dort bis auf etwa einen Punkt heran. d-ka-aug-lx verbessert sich von 26,5 auf 5,7 %.

## 10. Schwächen von seiten_b: Anfangsschlüssel und Text

Untersucht aus den vorhandenen Lesungen (kein neuer Job): seiten_b Epoche 4 gegen s4t Epoche 4, dazu Epoche 3.

### Anfangsschlüssel der Prüfhandschriften (92,5 → 87,0 %)

Von den 200 Prüfhandschriften-Systemen liest s4t 185 Anfangsschlüssel richtig, seiten_b 174 (Epoche 3: 175). 15 Systeme kippen von richtig zu falsch, 4 von falsch zu richtig (Vorzeichentest p = 0,02). Betroffen sind vor254 (7), kn65 (5), wn15484 (2) und geras6 (1), gu17 gar nicht. 12 der 15 sind dieselbe Verwechslung: F-Schlüssel wird als C-Schlüssel auf derselben Linie gelesen (f3 → c3, f2 → c2); dazu je einmal c4 → c3, c2 → f2 und f3 → c3 in geras6. Über alle F-Schlüssel gerechnet: s4t erkennt 34 von 47, seiten_b 24 von 47; C-Schlüssel beide fast vollständig (151 bzw. 152 von 153).

| System | GT | s4t | seiten_b E3 | seiten_b E4 | Bild |
| --- | --- | --- | --- | --- | --- |
| vor254 0086_03 | f3 | f3 | c3 | c3 | gotischer F-Schlüssel sauber am Zeilenanfang |
| vor254 0110_03 | f3 | f3 | c3 | c3 | sauber |
| vor254 0091_01 | f3 | f3 | c3 | c3 | sauber, Initiale davor |
| kn65 0046_04 | f3 | f3 | c3 | c3 | blasser, umrandeter Schlüssel |
| kn65 0030_07 | f3 | f3 | c3 | c3 | sauber, Initiale davor |
| kn65 0030_01 | c4 | c4 | c4 | c3 | sauber; Linienfehler |
| wn15484 0095_02 | f3 | f3 | c3 | c3 | am Rand im Falz, halb angeschnitten |
| wn15484 0065_04 | f2 | f2 | c2 | c2 | am Rand im Falz, halb angeschnitten |
| geras6 0047_01 | f3 | f3 | f3 | c3 | sauber |
| gu17 0014_04 | f3 | c3 | f3 | f3 | sauber; hier liest seiten_b besser |

Bilder mit Lesungen: `daten/seiten/aus/schluessel_seiten_b.jpg`. Die Schlüssel stehen bis auf die beiden wn15484-Fälle sauber und vollständig im Ausschnitt; es ist kein Zuschnittproblem.

Ganze Seite und Abschnitt helfen nicht: Auf den 20 Prüfseiten (alle Systeme haben Labels) erkennt seiten_b von 32 F-Schlüsseln im Ausschnitt 8, im Abschnitt 6 von 21 und auf der ganzen Seite 6 von 30 (s4t im Ausschnitt 16 von 32); vor254 auf den Prüfseiten: s4t 5 von 11, seiten_b 0 von 11. C-Schlüssel liest seiten_b in allen Formen sicher (98 bis 99 %).

Wahrscheinliche Ursache: Die Mehrsystem-Daten bringen 15.395 zusätzliche Zeilen, die zu 88 % mit C-Schlüssel beginnen (Systemdaten 81 bis 83 %); der Anteil der F-Zeilen am ganzen Training sinkt von etwa 17 auf 14 %, und die gotischen F-Formen von vor254 und kn65 kommen fast nur in den Transkribus-Daten vor (9 % F). seiten_a, das nur eine Epoche weitertrainiert wurde, hielt den Wert (92,0 %). Einschätzung: ein echter Nachteil, kein Rauschen; behebbar vermutlich durch Übergewichtung von Systemen, Abschnitten und Seiten mit F-Schlüssel im Neutraining.

### Text auf Transkribus-validation (4,9 → 5,5 % CER)

Auf den 85 Systemen (1.908 Zeichen) macht seiten_b 105 Textfehler, s4t 94; Epoche 3 ebenfalls 105. Die 11 Mehrfehler verteilen sich breit: 14 Zeilen werden schlechter, 9 besser, 62 bleiben gleich, keine Zeile verliert mehr als 4 Zeichen, keine Schleifen, keine Abbrüche (Vorzeichentest p = 0,4).

| System | GT | s4t | seiten_b |
| --- | --- | --- | --- |
| mb2 0106_03 | nobis domine miserere no | nobis domine miserere no | nobis domine in serere no |
| vor259 0023_08 | in te videbitur. Ori | in te videbitur Ori | in te videbitur in |
| mb2 0106_11 | … domine uirtutum rex … | … domine uirtutum rex … | … domine virtum rex … |
| mb2 0106_04 | bis Iusticie domini | bis nsticie domini | Unus sticie domini |
| vor259 0022_05 | faciem tuam et salui erimus | … salui eribus | … salui erit |
| brlm34 0025_10 | die genuite Letentur | die genuite tenutur | die genuite Letentur |

Zwei schwache Muster: etwas mehr ausgelassene Silben (seiten_b 848 Silben, s4t 852, GT 860; 13 gegen 10 Zeilen mit zu wenigen Silben) und mehr `v` statt `u` (seiten_b 19, s4t 13, GT 8). Letzteres passt zu den Trainingsdaten: In den CantusDB-Ausschnitten und Mehrsystem-Beispielen sind 15,7 % der u/v ein `v`, in den Transkribus-Ausschnitten 7,6 %. Einschätzung: überwiegend Rauschen bei nur 85 Zeilen; die u/v-Verschiebung ist ein kleiner, erklärbarer Effekt der CantusDB-lastigen Mehrsystem-Daten.

## 11. Vorbereitung seiten_d

Auftrag (AUFTRAG_2.md): seiten_c plus Gold der 14 neuen Grazer Bände (`korpus_graz14`, nur train) und Silber (`korpus_silber/train.jsonl` von `text_claude`); Neutraining aus dem Basismodell, 4 Epochen, sonst wie seiten_c. `seiten_d.py` übernimmt die Listen von seiten_c unverändert und schreibt `daten/seiten/d/`: `graz14.jsonl`, `silber_hs.jsonl`, `silber_druck.jsonl`, `mehrsystem/train.jsonl`, `smoke.jsonl`, `bericht.json`. Jobskript `cluster/train_seiten_d.sh` (aus `train_seiten_c.sh`, liest zusätzlich korpus_graz14 val und test je Checkpoint).

Regeln in der Listenbildung:

- Drucke: Silber-Drucke nur Klasse `doppelt`, höchstens 1.500 je Epoche, gleichmäßig über die Drucke (kleine ganz, Rest zu gleichen Teilen), feste Stichprobe mit Seed 0, weil `train.py` die Liste nicht je Epoche neu zieht. Silber-Drucke gehen nicht in Mehrsystem-Beispiele ein.
- Silber-Handschriften: beide Klassen, ungedeckelt; `striche_unsicher` wird gezählt.
- Mehrsystem: Quellen sind Graz14-Gold, die Handschriften des alten korpus_graz (keine Drucke; w3:p1R 14.11.) und die Silber-Handschriften. Seiten werden über das Seitenbild gruppiert (`seitenbild`, aufgelöster Pfad), auch beim Abgleich mit Gold. Die Systemfolge einer Seite kommt aus allen Notationsregionen der PAGE-XML (`zeilen_bilden`), nicht aus der Korpusliste. Ein System gilt als voll, wenn genau ein Trainingssystem auf der Notenzeile liegt. Abschnitte und Hälften entstehen nur aus Läufen voller Systeme, ganze Seiten nur ohne Lücke; Seiten mit Sprung im Zeilenabstand (über 1,6- oder unter 0,7-fach des Medians) fallen ganz weg. `pruefe_mehrsystem` prüft das am Ergebnis.
- PAGE-XML über `imageFilename`, nicht über die Seitennummer der ID (vom Koordinator bestätigt): Bei gf6437 steht Seite 0057 in `page_xml/0055.xml` (27 Gold-Systeme betroffen; ein erster Bau über die Seitennummer war dort falsch und ist ersetzt). Die Zuordnung stimmt für alle 15.891 Silberkandidaten mit der von `text_claude` überein. Für Silber gilt die mitgegebene `pagexml`; die Zuordnung über `imageFilename` dient als Gegenprobe (`pagexml_abweichend`), bei Aldersbach entfällt sie.
- Seiteninfo des Silbers (`notation_box`, `seitenbild`, `pagexml`) kommt aus `korpus_silber/train.jsonl`; fehlt ein Feld, aus den Kandidatenlisten `daten/silber/*liste*.jsonl` (gezählt als `seiteninfo_aus_liste`, wird gemeldet).
- Prüfhandschriften: Assertion über alle Listen der Epoche, auf Quelle und Pfade (auch Bandnamen wie `A-Geras 6`, `A-Wn15484`). val/test: Kein Silber-System von einer Seite, auf der ein val- oder test-System von korpus_graz, korpus_graz14 oder korpus_transkribus liegt, gleich welcher Kasten (w3:p1R 14.11.); Silber auf dem Kasten eines Gold-train-Systems fällt ebenfalls weg (Gold geht vor); danach Assertion. Gold-Drucke (Seiten 3 bis 32) und Silber-Drucke (ab Seite 33) überschneiden sich nicht.
- Zweifelhafte Gold-GT (w3:p1R 14.11., `daten/gold_zweifel_graz14.jsonl`, 119 Indexzeilen, in denen seiten_b und CRNN gleich lesen und von der GT abweichen; Stichprobe am Bild 6 von 6 Mal GT falsch): Ein korpus_graz14-train-System fällt weg, wenn eine seiner Indexzeilen (Regionen im System, wie `korpus_graz14.py`) mit quelle und index_id in der Liste steht; 18 Systeme, darunter das zweiteilige gf6438 0015_07+0015_08. Sie fehlen auch in den Mehrsystem-Seiten (dort Lücke) und werden nicht durch Silber oder die Modelllesung ersetzt. val und test bleiben unverändert.
- Silber mit `training: false` (von `text_claude` nicht vorgesehen) fällt weg und wird gezählt.
- F-Schlüssel: keine Verdopplung der neuen Blöcke; liegt der Anteil der Zeilen mit F-Anfangsschlüssel unter 24 %, werden F-Beispiele von Graz14 und Silber-Handschriften verdoppelt.

Selbsttest (`python seiten_d.py test`): Deckel und Verteilung der Drucke, nur Klasse doppelt, feste Stichprobe; Prüfhandschrift über Quelle und über Pfad bricht ab; Silber auf einer val/test-Seite fällt weg, auch mit anderem Kasten; Rückfall auf die Kandidatenliste wird gezählt; Abschnitt über eine Lücke und ganze Seite mit Lücke werden abgefangen. Sichtprüfung des Prüfbogens (10 Abschnitte): Systemzahl und Ziele passen zum Bild.

Zählung ohne Silber (14.11., mit Mehrsystem aus dem alten korpus_graz):

| Block | Beispiele je Epoche |
| --- | ---: |
| AMNLT (F doppelt, wie seiten_c) | 4.633 |
| CantusDB-Korpus (wie seiten_c) | 10.463 |
| Transkribus-Korpus (wie seiten_c) | 611 |
| korpus_graz (wie seiten_c) | 1.487 |
| Mehrsystem train3 (wie seiten_c) | 5.543 |
| korpus_graz14 train (ohne 18 Zweifels-Systeme) | 390 |
| Mehrsystem aus Graz14 und korpus_graz-Handschriften (302 Abschnitte, 102 Hälften, 51 Seiten) | 455 |
| gesamt | 23.582 |

Mehrsystem-Anteil 25,4 %, Zeilen mit F-Anfangsschlüssel 25,0 % (keine Verdopplung nötig), Drucke 2,9 % (686 aus korpus_graz). Vor dem Zweifels-Ausschluss: 408 und 461 (308 Abschnitte), gesamt 23.606. Von 334 Seiten mit Trainingssystemen sind 52 vollständig; zwei Psalterium-Seiten (gf6437 0063, 0064) haben in der PAGE-XML keine als Notation markierte Region und fallen weg, acht Seiten wegen Abstandssprung. Mit Graz14 allein waren es 110 Mehrsystem-Beispiele (7 Seiten).

Zählung mit vollständigem Silber (14.11., `korpus_silber/train.jsonl` von `text_claude`, Commit a4a2630: 7.551 Ziele, 6.918 mit `training: true`):

| Block | Beispiele je Epoche |
| --- | ---: |
| Blöcke von seiten_c (AMNLT, CantusDB, Transkribus, korpus_graz, Mehrsystem train3) | 22.737 |
| korpus_graz14 train (ohne 18 Zweifels-Systeme) | 390 |
| Silber-Handschriften (822 doppelt, 1.337 modell; Aldersbach 1.234, Graz 925) | 2.159 |
| Silber-Drucke (doppelt, gedeckelt: druck65 703, druck67 703, druck72 94) | 1.500 |
| Mehrsystem neu (696 Abschnitte, 106 Hälften, 53 Seiten; 410 mit Silber-Systemen, Aldersbach 213 Abschnitte) | 855 |
| gesamt | 27.641 |

Mehrsystem-Anteil 23,2 %, Zeilen mit F-Anfangsschlüssel 25,4 % (keine Verdopplung nötig), Drucke 7,9 % (686 korpus_graz, 1.500 Silber). Entfallen: 633 Silber-Systeme mit `training: false`, 3.257 Silber-Drucke über dem Deckel, 2 Silber-Systeme auf Gold-train-Kästen, 18 Graz14-Gold-Systeme aus der Zweifelsliste; kein Silber-System lag auf einer Seite mit val/test-Gold, auf einem Zweifelskasten oder trug `gold_zweifel` (hat `text_claude` schon ausgeschlossen). `striche_unsicher`: 547 der 2.159 Silber-Handschriften (bleiben drin). Aldersbach-Abschnitte sind eng geschnitten: Textunterlängen und die höchsten Noten des nächsten Systems berühren sich fast, der Schnitt nach dem Tintenprofil liegt an derselben Stelle (0283, 0398) oder tiefer (0456); unverändert gelassen.

Upload in `$DATA/lighton_choral_seiten` (14.11., 18:00): Manifest 19.333 Dateien byte-genau, 29.431 Listeneinträge ohne fehlendes Bild. Manifest neu mit `cluster/manifest_seiten.sh`.

Probelauf mit einer nachgebildeten Silberdatei (Kandidatenlisten von `text_claude`, Zufallsauswahl, Platzhalterziele, ohne Seitenfelder, also ganz über den Rückfall): 29.473 Beispiele, Silber-Drucke 1.500 (druck72 113, druck65 693, druck67 694), 1.624 neue Mehrsystem-Beispiele, davon 1.197 mit Silber-Systemen; aussortiert 83 Silber-Systeme auf val/test-Kästen, 102 weitere auf val/test-Seiten und 272 auf Gold-train-Kästen. Die Zahlen gelten nur für den Ablauf, nicht für die echte Silberdatei.

## 12. Frühes Signal zu seiten_c und Seitengewichtung für seiten_d

Vor dem Einreichen von seiten_d sollte ein kurzes Signal zeigen, ob der Aufbau von seiten_c trägt (w3:p1R 14.11.). Eigene Lesejobs (`cluster/lesen_val.sh`, Ausgabe `aus/frueh_*`) parallel zum laufenden Job 1942059, keine Prüfhandschriften.

| Maß | seiten_b E4 | seiten_c E2 | seiten_c E3 | seiten_c E4 |
| --- | ---: | ---: | ---: | ---: |
| Tonlage-SER AMNLT-val | 1,71 % | – | – | 1,77 % |
| Tonlage-SER 9 val-Seiten (Fehler/4.221 Töne) | 2,94 % (124) | 8,36 % (353) | 4,67 % (197) | 3,98 % (168) |
| dieselben ohne GT-Fehler fcc-0002/238v S1–2 | 2,97 % | 8,47 % | 4,73 % | 3,72 % |
| Anfangsschlüssel Transkribus-val F / C | 11/12, 72/72 | – | – | 12/12, 72/72 |
| Text-CER Transkribus-val | 5,50 % | – | – | 3,41 % |
| AMLER AMNLT-val / val-Seiten | 4,45 / 2,68 % | – | – | 4,57 / 3,87 % |

Fehlerart der großen Ausreißer von E4: fcc-0002/240v System 11 lässt eine Passage aus (Sprung von de-*mo*-nes zu ho-*mo*, 27 Töne), d-ka-aug-lx/214v System 9 ersetzt eine Passage durch erfundenen Text („dominus et gloriam suam eius“ statt „deum ploremus coram domino …“); keine durchgehende Tonverschiebung, keine Streufehler. Die Ausreißer wandern zwischen den Epochen (d-ka-aug-lx/214v: 197, 89, 50 Fehler in E2 bis E4). Einschätzung: instabile Lesung langer Seiten, mit den Epochen abnehmend. Nach der Regel nicht eingereicht.

GT-Fehler: fcc-0002/238v Systeme 1–2 haben in der GT „super tuarum Do- | mine dominus“, im Bild steht „super opera ma- | nuum tuarum“ (seiten_c E4 liest richtig). GT bleibt unverändert; `seiten_messen.py` weist die val-Seiten zusätzlich ohne diese Systeme aus (Gruppe `validation_ohne_gt_fehler`).

Abhilfe in seiten_d (w3:p1R): ganze Seiten dreifach, Hälften doppelt in der Epochenliste, alte und neue Mehrsystem-Blöcke (`daten/seiten/d/mehrsystem_d.jsonl`), Abschnitte einfach. Freigabe nur bei Mehrsystem-Anteil nach Beispielen mindestens 27 %, Training höchstens 16 h und grünen Assertions.

Zeit je Beispielart: Aus dem Log von seiten_c nicht zu trennen (laufender Mittelwert, gerundet; Regression R² 0,01). Gemessen mit derselben Trainingsschleife (`zeit_je_art.py`, Job 1943160, 114 Beispiele): System 0,47 s, Abschnitt 0,29 s, Hälfte 0,79 s, Seite 0,78 s; an seiten_c kalibriert (geschätzt 10.054 s je Epoche, gemessen 8.607 s, Faktor 0,856).

| Gewicht Seiten / Hälften | Beispiele je Epoche | Mehrsystem nach Beispielen | Training hochgerechnet |
| --- | ---: | ---: | ---: |
| 3 / 2 (beschlossen) | 28.738 | 26,1 % | 12,5 h |
| 2 / 2 | 28.454 | 25,3 % | 12,3 h |
| 3 / 3 | 29.267 | 27,4 % | 12,9 h |
| 5 / 2 | 29.306 | 27,5 % | 12,9 h |
| 4 / 3 | 29.551 | 28,1 % | 13,1 h |

Mit 3 / 2: Mehrsystem nach Zielzeichen 60,6 %, F-Zeilen 24,2 %, Drucke 7,6 %. Bedingung „mindestens 27 %“ verfehlt, nicht eingereicht; Entscheidung beim Koordinator.

AMNLT-Testsplit (Berichtsmessung, Job 1943041, 562 Systeme, keine Auswahl): s4t / seiten_b Tonlage-SER 1,23 / 1,32 %, Text-CER 2,18 / 2,11 %, AMLER 4,40 / 4,33 %, AMLER − bWER 1,09 / 1,09 Prozentpunkte; Solesmes AMLER 9,35 / 8,76 %. Dateien `runs/<lauf>/<checkpoint>/lesung_test.*`.

## 13. Ergebnis seiten_c

Job 1942059, 14:51 h (Training 573,8 min, danach Lesen aller vier Checkpoints), Exit 0. Lesungen und Gewichte lokal unter `runs/seiten_c/` und `daten/seiten/aus/seiten_c_checkpoint-*`. Alle Werte mit dem aktuellen `metriken.py` neu gerechnet.

Feste Regel (AMNLT-val Tonlage-SER und 9 val-Seiten; bei Widerspruch und AMNLT-Abstand unter 0,1 Punkten entscheiden die val-Seiten):

| Checkpoint | AMNLT-val Tonlage-SER | AMNLT-val AMLER | 9 val-Seiten Tonlage-SER | ohne GT-Fehler | Systeme erkannt |
| --- | ---: | ---: | ---: | ---: | ---: |
| seiten_b E4 (Vergleich) | 1,71 % | 4,45 % | 2,94 % | 2,97 % | 99,2 % |
| seiten_c E1 (22737) | 2,35 % | 6,49 % | 16,51 % | 15,32 % | 89,2 % |
| seiten_c E2 (45474) | 1,92 % | 4,74 % | 8,36 % | 8,47 % | 97,7 % |
| seiten_c E3 (68211) | 1,79 % | 4,53 % | 4,67 % | 4,73 % | 99,2 % |
| seiten_c E4 (90948) | 1,77 % | 4,57 % | 3,98 % | 3,72 % | 99,2 % |

Beide Kriterien zeigen auf Epoche 4, kein Widerspruch: **gewählt `seiten_c/checkpoint-90948`.** Keine Abbrüche oder Schleifen auf den Seiten.

Vergleich seiten_b E4 → seiten_c E4 (`seiten_vergleich.py`):

| Menge | Tonlage-SER | Text-CER | Anfangsschlüssel | AMLER (Makro) | AMLER − bWER (Pp.) |
| --- | ---: | ---: | ---: | ---: | ---: |
| AMNLT validation | 1,71 → 1,77 % | 2,00 → 2,18 % | 99,37 → 99,28 % | 4,45 → 4,57 % | 1,25 → 1,24 |
| Einsiedeln¹ | 1,33 → 1,38 % | 1,00 → 1,15 % | 99,45 → 99,45 % | 1,95 → 2,24 % | 0,74 → 0,90 |
| Salzinnes¹ | 1,97 → 1,96 % | 1,13 → 1,08 % | 99,15 → 99,15 % | 4,81 → 4,95 % | 1,00 → 0,98 |
| Solesmes | 1,91 → 2,09 % | 5,96 → 6,69 % | 100,00 → 99,40 % | 8,59 → 8,29 % | 3,20 → 2,91 |
| CantusDB-Korpus validation | 5,66 → 6,25 % | 3,56 → 4,11 % | 95,63 → 95,25 % | 5,35 → 8,10 % (Mikro 5,24 → 5,74 %) | 1,35 → 1,38 |
| Transkribus validation | 0,42 → 0,46 % | 5,50 → 3,41 % | 98,81 → 100,00 % | 6,54 → 5,85 % | 3,02 → 2,96 |
| Prüfhandschriften (200 Systeme) | 1,74 → 1,27 % | – | 87,0 → 91,5 % (F 24/47 → 32/47, C 150/153 → 151/153) | – | – |
| korpus_graz val Graz / Drucke | – → 0,63 / 1,04 % | – → 3,35 / 0,67 % | – → 100 / 98,2 % | – → 5,20 / 1,21 % | – → 1,78 / 0,34 |
| korpus_graz test Graz / Drucke | – → 0,37 / 0,37 % | – → 2,49 / 1,20 % | – → 100 / 100 % | – → 2,98 / 0,68 % | – → 0,75 / 0,00 |

¹ wie in Abschnitt 12: AMLER/bWER nicht streng mit dem Paper vergleichbar. seiten_b wurde nicht auf korpus_graz gelesen.

Der Makro-AMLER im CantusDB-Korpus springt durch ein einziges System: a-kn-1010/126r_01_1 (Ziel 39 Zeichen) gerät in eine Schleife („do-mi-ne“ wiederholt, 1.005 Zeichen, AMLER 2.969 %). Ohne dieses System liegt der Makrowert nahe dem Mikrowert. Es ist die einzige Schleife und der einzige Abbruch unter 1.060 Systemen.

Seitenformen (Makro über Seiten, 9 val- und 14 test-Seiten der Prüfmenge zusammen; Prüfhandschriften 20 Seiten):

| Form | valtest Tonlage-SER | valtest AMLER | AMLER − bWER (Pp.) | Prüfhandschriften Tonlage-SER |
| --- | ---: | ---: | ---: | ---: |
| seite | 4,5 → 4,0 % | 3,71 → 3,96 % | 1,69 → 1,93 | 2,1 → 1,9 % |
| haelften | 2,6 → 2,8 % | 3,24 → 3,50 % | 1,24 → 1,28 | 1,6 → 2,1 % |
| abschnitte | 2,6 → 3,6 % | 2,84 → 3,33 % | 1,26 → 1,33 | 1,6 → 1,9 % |
| systeme | 1,7 → 1,8 % | 2,15 → 2,17 % | 1,00 → 1,01 | 2,1 → 2,7 % |

Bewertung: seiten_c bringt die Ziele der Graz-Daten (Prüfhandschriften 1,74 → 1,27 %, F-Schlüssel 24 → 32 von 47, Transkribus-Text 5,50 → 3,41 %), kostet aber auf den AMNLT- und CantusDB-Mengen 0,1 bis 0,6 Punkte Tonlage. Ganze Seiten: val schlechter (2,94 → 3,98 %), test besser (5,39 → 4,06 %), Prüfhandschriften etwa gleich. Seiten werden mit den Epochen stetig besser (16,5 → 8,4 → 4,7 → 4,0 %); die Kurve ist nach Epoche 4 nicht flach, mehr Seitengewicht (seiten_d) oder Epochen dürften helfen.

## 14. Ergebnis seiten_d

Job 1943174, 18:46 h (Training 803,6 min für 4 × 29.627 Beispiele, 0,407 s je Beispiel, Speicherspitze 26,8 GB; danach Lesen aller vier Checkpoints zu je etwa 75 min), Exit 0. Im Fehlerprotokoll derselbe harmlose Traceback wie bei seiten_c (Kurzzeile von `seiten_messen.py` am Jobende, Seiteninventar nicht auf MUSICA); die Messung ist lokal gerechnet. Lesungen und Gewichte lokal unter `runs/seiten_d/` und `daten/seiten/aus/seiten_d_checkpoint-*`. val_loss (AMNLT) 0,1086 / 0,0918 / 0,0916 / 0,1128.

Feste Regel:

| Checkpoint | AMNLT-val Tonlage-SER | AMNLT-val AMLER | 9 val-Seiten Tonlage-SER | ohne GT-Fehler | Systeme erkannt | Prüfhandschriften 200 Systeme |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| seiten_c E4 (Vergleich) | 1,77 % | 4,57 % | 3,98 % | 3,72 % | 99,2 % | 1,27 % |
| seiten_d E1 (29627) | 2,69 % | 6,42 % | 11,42 % | 11,54 % | 92,3 % | 3,09 % |
| seiten_d E2 (59254) | 1,83 % | 4,77 % | 9,48 % | 9,50 % | 94,6 % | 3,09 % |
| seiten_d E3 (88881) | 1,86 % | 4,57 % | 3,86 % | 3,65 % | 98,5 % | 1,52 % |
| seiten_d E4 (118508) | 1,74 % | 4,30 % | 3,34 % | 3,12 % | 100,0 % | 1,31 % |

Beide Kriterien zeigen auf Epoche 4: **gewählt `seiten_d/checkpoint-118508`.** Keine Abbrüche oder Schleifen auf den Seiten.

Vergleich seiten_c E4 → seiten_d E4 (`seiten_vergleich.py`, jetzt mit korpus_graz14):

| Menge | Tonlage-SER | Text-CER | Anfangsschlüssel | AMLER (Makro) | AMLER − bWER (Pp.) |
| --- | ---: | ---: | ---: | ---: | ---: |
| AMNLT validation | 1,77 → 1,74 % | 2,18 → 2,17 % | 99,28 → 99,37 % | 4,57 → 4,30 % | 1,24 → 1,14 |
| Einsiedeln¹ | 1,38 → 1,36 % | 1,15 → 1,02 % | 99,45 → 99,72 % | 2,24 → 2,02 % | 0,90 → 0,73 |
| Salzinnes¹ | 1,96 → 2,00 % | 1,08 → 0,96 % | 99,15 → 99,15 % | 4,95 → 4,61 % | 0,98 → 0,96 |
| Solesmes | 2,09 → 1,94 % | 6,69 → 7,18 % | 99,40 → 99,40 % | 8,29 → 8,20 % | 2,91 → 2,71 |
| CantusDB-Korpus validation | 6,25 → 5,72 % | 4,11 → 3,82 % | 95,25 → 95,92 % | 8,10 → 5,46 % (Mikro 5,74 → 5,39 %) | 1,38 → 1,33 |
| Transkribus validation | 0,46 → 0,54 % | 3,41 → 3,30 % | 100,00 → 98,81 % | 5,85 → 5,45 % | 2,96 → 2,60 |
| Prüfhandschriften (200 Systeme) | 1,27 → 1,31 % | – | 91,5 → 91,0 % (F 32/47 → 30/47, C 151/153 → 152/153) | – | – |
| korpus_graz val Graz / Drucke | 0,63 / 1,04 → 0,63 / 1,32 % | 3,35 / 0,67 → 2,15 / 0,47 % | 100 / 98,2 → 100 / 98,2 % | 5,20 / 1,21 → 4,78 / 1,55 % | 1,78 / 0,34 → 1,47 / 0,80 |
| korpus_graz test Graz / Drucke | 0,37 / 0,37 → 0,37 / 0,25 % | 2,49 / 1,20 → 1,95 / 0,53 % | 100 / 100 → 100 / 100 % | 2,98 / 0,68 → 3,40 / 0,37 % | 0,75 / 0,00 → 0,72 / 0,06 |
| korpus_graz14 validation (55 von 56) | – → 1,48 % | – → 4,66 % | – → 100 % | – → 4,29 % | – → 0,18 |
| korpus_graz14 test (52) | – → 0,00 % | – → 2,80 % | – → 100 % | – → 3,21 % | – → 0,28 |

¹ wie in Abschnitt 12. seiten_c wurde nicht auf korpus_graz14 gelesen.

korpus_graz14 je Epoche (Tonlage-SER val / test): E1 0,80 / 0,36 %, E2 0,34 / 0,00 %, E3 0,23 / 0,12 %, E4 1,48 / 0,00 %. Der Anstieg in E4 kommt von einem System: gf6438 0007_06 (13 Töne) liest nach dem Ende des Systems weiter und hängt Text und Töne aus der Textzeile darüber an („Dictus qui ue-nit ex-cel-sis Be-ne“; der Ausschnitt zeigt oben die Textzeile „excelsis Benedictus qui ue-“ des vorigen Systems). E3 liest das System bis auf die Schlusssilbe richtig.

Referenzstand korpus_graz14: Die Datei wurde am 14.11. um 20:04 neu gebaut (Worker text), nach dem Hochladen für seiten_d (12:10). Auf MUSICA stehen noch die alten Ziele, damit auch in den Trainingsdaten von seiten_d (`daten/seiten/d/graz14.jsonl`). Gemessen ist gegen die aktuellen Ziele; val hat dort eine Zeile mehr (gf6442 0316_03, nicht gelesen), in 2 val- und 5 test-Zeilen weicht das Ziel ab. Gegen die alten Ziele aus der Lesung: E4 val 1,82 %, test 0,60 %; E3 val 0,57 %, test 0,72 %.

Seitenformen (9 val- und 14 test-Seiten der Prüfmenge; Prüfhandschriften 20 Seiten):

| Form | valtest Tonlage-SER | valtest AMLER | AMLER − bWER (Pp.) | Prüfhandschriften Tonlage-SER |
| --- | ---: | ---: | ---: | ---: |
| seite | 4,0 → 3,6 % | 3,96 → 3,30 % | 1,93 → 1,68 | 1,9 → 1,9 % |
| haelften | 2,8 → 2,3 % | 3,50 → 3,02 % | 1,28 → 1,28 | 2,1 → 1,2 % |
| abschnitte | 3,6 → 2,6 % | 3,33 → 2,81 % | 1,33 → 1,27 | 1,9 → 1,2 % |
| systeme | 1,8 → 1,7 % | 2,17 → 2,11 % | 1,01 → 1,00 | 2,7 → 2,5 % |

Ganze Seiten getrennt: val 3,98 → 3,34 % (ohne GT-Fehler 3,72 → 3,12 %), test 4,06 → 3,82 %; seiten_b E4 hatte val 2,94 %, test 5,39 %. Seiten erkannt val 100 %.

## Grenzen

- Kleine Menge vollständiger Seiten (130 im Training von seiten_a, 164 in train2, 25 in val/test), überwiegend aus sbe-0611 und fcc-0002; Prüfseiten nur mit Noten-GT.
- Die Lückenprüfung findet blasse Systeme nicht sicher; Restfehler in den Review-Quellen sind möglich. Bei den Erkennungsquellen (a-kn-1018, ch-p-18, f-pn-lat-12044) gelten Kamm-Treffer wegen vieler Fehlalarme nur für Seiten und Hälften, für Abschnitte nur Abstandssprünge.
- Die Transkribus-Ziele wurden am 13.11. im Korpus berichtigt (vertauschte Textfolgen, ergänzte Anfangsbuchstaben mitten in der Zeile, falsche Zuordnungen, unsichere Initialen); `zeilen.jsonl` ist unverändert. `seiten.py` nimmt seither das Ziel aus `daten/korpus_transkribus`, wenn die Zeile dort steht, behandelt die dortigen unsicheren Initialen wie die eigenen und schließt die wegen Fehlern entfernten Zeilen aus (`FALSCH`: 7 vertauschte oder falsch zugeordnete, 8 vor259-Zeilen nach der Gegenprobe). `train/` und `train2/` sind vor der Berichtigung gebaut und bleiben als Trainingsstand von seiten_a und seiten_b unverändert (darin u. a. 6 bzw. 7 Mehrsystem-Beispiele mit vertauschtem Text).
- Für a-kn-1010, a-wn-1799 und d-knd-1161 fehlt eine vollständige Systemerkennung; a-kn-1012 ist auf Wunsch des Projektleiters ausgeschlossen.
- Schnitte zwischen eng stehenden Systemen streifen teils Unterlängen oder hohe Noten (gu17, vor254: Textzeile berührt das nächste System).
- Die Systemausschnitte im Vergleich stammen aus bekannten Kästen; im Einsatz bräuchte es dafür eine Systemerkennung, deren Fehler hier nicht enthalten sind.
