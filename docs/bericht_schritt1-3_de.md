# LightOnOCR-3-1B auf AMNLT: Bericht zu Schritt 1 bis 3

Stand: 2026-11-08. Ein Training hat nicht stattgefunden. Alle Zahlen sind Messungen an den Daten oder am Rauchtest. Auf MUSICA wurde nichts eingereicht.

## Ergebnis in Kürze

- Die Ziele passen in die Tokenlänge: längstes Ziel 430 Token, die Modellkarte nennt 1.024.
- Die Auflösung ist bei Einsiedeln knapp: Median 13,8 px je Tonschritt, 60 % der Systeme unter dem 14-px-Raster.
- Wenn das System in Streifen untereinander steht, verdoppelt sich die senkrechte Auflösung ungefähr, ohne GT je Stück.
- Die Kette aus Training, Speichern, Laden, Lesen und Messen läuft.
- Das Original-Modell wird mit der Vorlage aus OKAR nicht vollständig geladen. Der Decoder blieb ohne Fehler zufällig. `konvertieren.py` behebt das und ist auch für MUSICA nötig.

## Schritt 1: Daten

Alle 5.602 Systeme wurden unverändert als Bilddateien nach `daten/` kopiert; die Liste ist `daten/systeme.jsonl`. Details stehen in `bericht_daten.json`.

| Quelle | Systeme | Token Median | Token Maximum | ohne `<m>` Median | ohne `<m>` Maximum | Noten-Atome Median |
| --- | --- | --- | --- | --- | --- | --- |
| Einsiedeln | 1.816 | 209 | 430 | 95 | 221 | 60 |
| Salzinnes | 2.939 | 115 | 270 | 54 | 135 | 30 |
| Solesmes | 847 | 217 | 347 | 91 | 134 | 65 |

Unterschiede der Quellen, die die Messung betreffen:

- Wortgrenzen gibt es nur in Solesmes. In Einsiedeln und Salzinnes steht vor jeder Silbe ein Leerzeichen. Die WER ist deshalb nur für Solesmes messbar; für alle drei wird die Silben-Fehlerrate gemessen.
- Das Zeichen `!` kommt nur in Solesmes vor (5.995-mal). Neumengrenzen innerhalb einer Silbe sind also nur dort kodiert.
- Salzinnes hat weder `:` noch `;`. Einsiedeln hat 10.195-mal `:` und kein `;`. Solesmes hat beide, dazu `;` mit Ziffer.
- Schlüssel am Systemanfang: Einsiedeln 1.034 c4, 548 c3, 160 f3, 65 c2. Salzinnes 1.416 c3, 529 c4, 392 c2, 355 f3, 245 f2. Solesmes 314 c4, 301 c3, 107 f2, 65 f3, 39 c2.
- Solesmes hat 129 Ziele mit Text hinter der letzten Klammer (etwa `V.`, `R.`, `CONT`).
- 116 Referenzen enden auf Leerzeichen. Sie werden für Training und Messung abgeschnitten.

Zerlegung durch den Tokenizer: `<m>` kostet etwa die Hälfte der Token, wird aber unregelmäßig zerlegt (`(<`, `m`, `>c`, `<m`, `>`). Ohne `<m>` halbiert sich die Länge, dafür fasst der Tokenizer mehrere Noten zu einem Token zusammen (`gh`, `ef`). Alle Noten-Atome sind Einzelzeichen, die Form ohne `<m>` ist also verlustfrei. `train.py --kompakt` schaltet sie ein; der Standard bleibt das beauftragte `transcription`.

## Schritt 2: Auflösung

Gemessen wurden je Quelle 100 zufällige Systeme. Der Linienabstand stammt aus Zeilenprofilen in neun schmalen Spalten; verworfen wurde, wo weniger als 60 % der Spalten übereinstimmten. Skript: `aufloesung.py`, Zahlen: `bericht_aufloesung.json`, Kontrolle: `bilder_aufloesung/kontrolle_linien.jpg`, Beispiele: `bilder_aufloesung/beispiel_<Quelle>_<Form>.jpg`.

| Quelle | Linienabstand im Original (Median) | gemessen / verworfen |
| --- | --- | --- |
| Einsiedeln | 59 px | 85 / 15 |
| Salzinnes | 96 px | 99 / 1 |
| Solesmes | 55 px (P10–P90: 44–66) | 67 / 33 |

Pixel je Tonschritt nach der Skalierung auf höchstens 1.540 px längste Kante (Median, in Klammern P10; dazu Anteil unter 14 px und Bildtoken im Median):

| Quelle | ganz | gestaucht (Breite 1.540, Höhe bleibt) | Streifen gestapelt |
| --- | --- | --- | --- |
| Einsiedeln | 13,8 (13,0), 60 % unter 14, 385 Token | 29,5 (28,5), 0 %, 715 Token | 29,0 (28,5), 0 %, 1.800 Token |
| Salzinnes | 17,3 (16,1), 0 %, 495 Token | 48,0 (47,0), 0 %, 1.210 Token | 40,2 (36,2), 0 %, 2.420 Token |
| Solesmes | 16,5 (11,1), 13 %, 495 Token | 27,5 (22,0), 0 %, 825 Token | 27,5 (21,5), 0 %, 1.395 Token |

Bei „ganz“ fällt ein Tonschritt in die Größe eines Patches von 14 px und liegt deutlich unter dem Bildtoken von 28 px.

Die beiden Alternativen im Vergleich:

- **Streifen gestapelt** (`bildform.py`): Das System wird an tintenarmen Spalten in zwei bis vier Stücke geschnitten und untereinander gesetzt. Das Modell liest sie wie Zeilen einer Seite und schreibt das ganze Ziel. Ein GT je Stück ist nicht nötig. Waagerecht und senkrecht bleibt das Verhältnis erhalten. Überlappung gibt es keine, weil der Decoder sonst doppelt gelesene Noten erst lernen müsste.
- **Gestaucht:** nur die Breite wird verkleinert, die Höhe bleibt. Das ist am billigsten, verzerrt aber die Notenformen und verengt die Neumen waagerecht.

Grenzen der Messung: Die Tabelle zeigt nur die Geometrie. Ob mehr Pixel die Tonlage verbessern, sagt erst ein Training. Bei Solesmes fehlt ein Drittel der Stichprobe, und die Streuung ist groß. Die Sichtprüfung der Linien war eine grobe Prüfung des Abstands, keine Prüfung jedes Bildes. Die Lage der eingezeichneten Linien weicht bei schrägen Systemen ab, das Maß nicht.

## Schritt 3: Pipeline und Rauchtest

| Datei | Zweck |
| --- | --- |
| `aufbereiten.py` | Export aus AMNLT (Umgebung `ai-base`) |
| `konvertieren.py` | benennt die Decoder-Gewichte um |
| `bildform.py` | ganz, gestaucht, Streifen |
| `train.py` | Feintuning nach der OKAR-Vorlage, Decoder mittrainiert |
| `auswertung.py` | Lesen und Messen je Quelle und gesamt |
| `metriken.py` | Trennung von Noten und Text, Metriken, Selbsttest |
| `daten_pruefen.py`, `aufloesung.py` | Schritt 1 und 2 |

Umgebung: Vorhanden ist `okar-pixtral` (torch 2.11, transformers 5.22). `datasets` braucht nur `aufbereiten.py`. Eine neue Umgebung war nicht nötig, bestehende wurden nicht verändert.

**Fehler beim Laden des Originals:** Das Original speichert den Decoder unter `language_model.model.*`, die Klasse erwartet `model.language_model.*`. transformers meldet das nur als Hinweis und lässt alle 28 Decoder-Schichten zufällig. Die Kopie `models/LightOnOCR-3-1B-konvertiert` trägt die richtigen Namen. Nach dem Laden stimmen alle 532 Gewichte bitgenau mit dem Original überein, und das Modell liest aus einem Solesmes-Bild lesbaren Text.

**Rauchtest** (CPU, Bildform Streifen, 2 Systeme, ein Optimierungsschritt, nur Durchlaufprüfung): Training, Validierung, Speichern (3,8 GB je Checkpoint), Laden und Auswertung sind ohne Fehler gelaufen. Dauer 169 s je System auf 6 Kernen. Der erste Versuch auf einem Kern war nach 23 Minuten nicht fertig und wurde abgebrochen; 6 Kerne hat der Projektleiter freigegeben. Der Rauchtest-Checkpoint ist gelöscht.

Die gemessenen Werte des Rauchtests sagen nichts über die Qualität. Das Modell schreibt nach einem Schritt noch Bildbeschreibungen (`<figure>…`).

Festlegungen in der Auswertung:

- Lesen ohne Wiederholungsstrafe, weil Tonwiederholungen im Choral regulär sind (anders als in OKAR).
- Schleifenerkennung: gleiche Zeichenfolge mindestens sechsmal am Ende. Auf allen 5.602 Referenzen gibt es keinen Fehlalarm.
- Notenfolge: Schlüssel, Custos, Vorzeichen und Strich mit Ziffer zählen als je ein Token. Tonlage: nur die Buchstaben a bis m, Groß- und Kleinschreibung gleich, ohne Schlüssel, Custos und Vorzeichen.
- Neumengrenzen: Enden der Klammergruppen und `!`, über die Ausrichtung der Tonfolgen verglichen.

Noch nicht gebaut: die Prüfung, ob Fehler musikalisch plausibel, aber am Bild falsch sind. Sie braucht echte Lesungen, gehört also zu Schritt 5. `auswertung.py` schreibt dafür jede Lesung mit Referenz in eine Datei.

## Vorbehalte für die Schlussmessung

- Die AMNLT-Splits sind nicht seitenrein. Die Testwerte sind dadurch zu günstig und müssen so berichtet werden.
- Ein Vergleich mit dem CRNN `general_v10` ist auf diesen Testmengen verzerrt, weil Salzinnes und Solesmes in dessen Training waren und CH-E 611 dieselbe Handschrift wie Einsiedeln ist. Welches CRNN und welche Prüfmenge fair sind, ist noch zu klären.

## Vorschlag für den ersten Trainingslauf

| Punkt | Vorschlag |
| --- | --- |
| Basis | `models/LightOnOCR-3-1B-konvertiert` |
| Daten | alle drei Quellen, 3.923 Systeme in train |
| Bildform | Streifen |
| Ziel | `transcription` mit `<m>` |
| Lernraten | Bild 1e-4, Decoder 5e-5, Decoder von Anfang an mittrainiert |
| Umfang | 4 Epochen, 8 Systeme je Schritt, Checkpoint je Epoche |
| Auswahl | auf validation nach Tonlagen-SER |
| Rechner | MUSICA, eine H100 |

Laufzeit, geschätzt aus OKAR (0,74 bis 0,93 s je Seite bei bis zu 3.025 Bildtoken): etwa 3 bis 4 Stunden. Auf MUSICA ist das noch nicht gemessen. Vier Checkpoints belegen etwa 15 GB.

Ein Kontrolllauf mit Bildform „ganz“ würde zeigen, ob die Streifen die Tonlage wirklich verbessern. Ich schlage ihn erst vor, wenn der erste Lauf brauchbar liest.

## Entscheidungen des Projektleiters

1. Freigabe des ersten Laufs mit der Bildform Streifen.
2. Ist die Definition der Neumengrenzen (Klammergruppen und `!`) fachlich richtig? Sie ist in den Quellen unterschiedlich kodiert.
3. Ist es richtig, die Tonlage ohne Custos zu messen?

Vor dem ersten Einsatz auf MUSICA wird die Clusterbetreuung informiert.
