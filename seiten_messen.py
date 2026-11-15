"""Misst Seitenlesungen gegen das Seitenziel: Tonlage über die ganze Seite, erkannte Systeme, Abbruch.

    python seiten_messen.py aus/s4t_checkpoint-53092

Erwartet seiten.jsonl, haelften.jsonl, systeme.jsonl und wenn vorhanden abschnitte.jsonl (Ausgaben
von lesen.py auf daten/seiten/probe). Hälften, Abschnitte und Systemausschnitte werden je Seite in Lesereihenfolge zusammengesetzt und wie eine
Seitenlesung gemessen. Referenz: Seitenziel (GABC, mit Text) oder Notations-GT der Prüfhandschriften.
Ein System gilt als erkannt, wenn mindestens die Hälfte seiner Töne in der Levenshtein-Ausrichtung
der ganzen Seite gleich gelesen ist; „letztes System“ ist das letzte erkannte.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

from rapidfuzz.distance import Levenshtein as lev

from metriken import amnlt_token, bwer_fehler, schleife, sicht
from vergleich_gt import toene as gt_toene

HIER = Path(__file__).resolve().parent
# GT-Fehler, am Bild bestätigt (14.11.): fcc-0002/238v System 1-2, GT „super tuarum Do- | mine dominus“, im Bild
# „super opera ma- | nuum tuarum“. GT bleibt; die val-Seiten werden zusätzlich ohne diese Systeme ausgewiesen
# (Gruppe validation_ohne_gt_fehler; Zeile i der Lesung = System i, nur wenn die Zeilenzahl stimmt).
GT_FEHLER = {"fcc-0002/238v": {1, 2}}


def ref_systeme(z):
    """Tonfolgen je System und Silbentext der Seite (None ohne Text-GT)."""
    if "ziel" in z:
        zeilen = z["ziel"].split("\n")
        return [sicht(x)["toene"] for x in zeilen], sicht(z["ziel"])["zeichen"]
    return [gt_toene(lab) for lab in z["label"]], None


def miss(ref, hyp_text, text_ref, ziel=None):
    """ref: Tonfolgen je System; hyp_text: Lesung der ganzen Seite; ziel: GABC-Seitenziel für AMLER/bWER
    (amnlt_token übergeht Zeilenumbrüche, die Seite zählt als ein Beispiel)."""
    r = [t for s in ref for t in s]
    v = sicht(hyp_text)
    h = v["toene"]
    gleich = [False] * len(r)
    for op in lev.opcodes(r, h):
        if op.tag == "equal":
            for i in range(op.src_start, op.src_end):
                gleich[i] = True
    erkannt, pos = [], 0
    for s in ref:
        teil = gleich[pos : pos + len(s)]
        erkannt.append(bool(s) and sum(teil) >= 0.5 * len(s))
        pos += len(s)
    return {
        "ton_f": lev.distance(r, h),
        "ton_n": len(r),
        "toene_lesung": len(h),
        "systeme": len(ref),
        "erkannt": sum(erkannt),
        "letztes": max((i + 1 for i, e in enumerate(erkannt) if e), default=0),
        "zeilen_lesung": len([x for x in hyp_text.split("\n") if x.strip()]),
        "schluessel_lesung": len(v["schl"]),
        "cer_f": lev.distance(text_ref, v["zeichen"]) if text_ref is not None else 0,
        "cer_n": len(text_ref) if text_ref is not None else 0,
    } | amnlt(ziel, hyp_text)


def amnlt(ziel, hyp_text):
    """Fehlersummen für AMLER/bWER (Mikro) und je-Seite-Raten (Makro); leer ohne GABC-Ziel."""
    if not ziel:
        return {}
    rt, ht = amnlt_token(ziel), amnlt_token(hyp_text)
    a, b = lev.distance(rt, ht), bwer_fehler(rt, ht)
    return {
        "aml_f": a,
        "bw_f": b,
        "aml_n": len(rt),
        "aml_m": a / len(rt),
        "bw_m": b / len(rt),
        "aml_anz": 1,
    }


def lade(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines()]


def main(ordner):
    ordner = Path(ordner)
    seiten = {z["seite"]: z for z in lade(ordner / "seiten.jsonl")}
    teile = defaultdict(dict)
    if (ordner / "haelften.jsonl").exists():
        for z in lade(ordner / "haelften.jsonl"):
            teile[z["seite"]][z["teil"]] = z
    systeme = defaultdict(dict)
    if (ordner / "systeme.jsonl").exists():
        for z in lade(ordner / "systeme.jsonl"):
            systeme[z["seite"]][z["nr"]] = z
    abschnitte = defaultdict(dict)
    if (ordner / "abschnitte.jsonl").exists():
        for z in lade(ordner / "abschnitte.jsonl"):
            abschnitte[z["seite"]][z["nr"]] = z
    zeilen, gruppen = [], defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    # Ziele aus dem aktuellen Inventar (Korpus-Berichtigungen vom 13.11.); Seiten, die dort nicht mehr
    # vollständig sind, fallen heraus. Alle Formen messen gegen das Seitenziel.
    inventar = {e["id"]: e for e in lade(HIER / "daten/seiten/seiten.jsonl")}
    weg = []
    for sid, z in list(seiten.items()):
        if "ziel" not in z:
            continue
        e = inventar.get(sid)
        if e is None or e["grund"]:
            weg.append(sid)
            del seiten[sid]
        else:
            z["ziel"] = e["ziel"]
    if weg:
        print("nicht mehr vollständig, ausgelassen:", ", ".join(weg))
    for sid, z in seiten.items():
        ref, text = ref_systeme(z)
        gruppe = "pruef" if z["split"] == "pruef" else "valtest"
        formen = {"seite": ([z["lesung"]], [z])}
        if set(teile[sid]) == {"oben", "unten"}:
            t = [teile[sid]["oben"], teile[sid]["unten"]]
            formen["haelften"] = ([x["lesung"] for x in t], t)
        if len(systeme[sid]) == len(ref):
            t = [systeme[sid][i] for i in range(len(ref))]
            formen["systeme"] = ([x["lesung"] for x in t], t)
        t = [abschnitte[sid][i] for i in sorted(abschnitte[sid])]
        if t and t[-1]["bis"] == len(ref) - 1:
            formen["abschnitte"] = ([x["lesung"] for x in t], t)
        for form, (lesungen, roh) in formen.items():
            m = miss(ref, "\n".join(lesungen), text, z.get("ziel"))
            m |= {
                "abgebrochen": sum(x["abgebrochen"] for x in roh),
                "schleife": sum(schleife(x["lesung"]) for x in roh),
                "lesungen": len(roh),
            }
            zeilen.append({"seite": sid, "quelle": z["quelle"], "form": form} | m)
            extra = (
                (z["split"],) if gruppe == "valtest" else ()
            )  # validation / test getrennt
            for g in (f"{gruppe}/{z['quelle']}", gruppe, "alle", *extra):
                for k, v in m.items():
                    gruppen[g][form][k] += v
                gruppen[g][form]["seiten"] += 1
            if z["split"] == "validation":
                h = "\n".join(lesungen).split("\n")
                weg = GT_FEHLER.get(sid, set())
                if weg and len(h) != len(ref):
                    continue  # Zeilen nicht zuordenbar: Seite fehlt in dieser Gruppe
                behalt = [i for i in range(len(ref)) if i not in weg]
                ziel = "\n".join(z["ziel"].split("\n")[i] for i in behalt)
                m2 = miss(
                    [ref[i] for i in behalt],
                    "\n".join(h[i] for i in behalt) if weg else "\n".join(lesungen),
                    sicht(ziel)["zeichen"] if text is not None else None,
                    ziel,
                ) | {k: m[k] for k in ("abgebrochen", "schleife", "lesungen")}
                for k, v in m2.items():
                    gruppen["validation_ohne_gt_fehler"][form][k] += v
                gruppen["validation_ohne_gt_fehler"][form]["seiten"] += 1
    bericht = {}
    for g, fs in sorted(gruppen.items()):
        for form, s in fs.items():
            bericht.setdefault(g, {})[form] = {
                "seiten": s["seiten"],
                "tonlage_ser_pct": round(100 * s["ton_f"] / s["ton_n"], 2),
                "toene_lesung_pct": round(100 * s["toene_lesung"] / s["ton_n"], 1),
                "systeme_erkannt_pct": round(100 * s["erkannt"] / s["systeme"], 1),
                "text_cer_pct": round(100 * s["cer_f"] / s["cer_n"], 2)
                if s["cer_n"]
                else None,
                "abgebrochen": s["abgebrochen"],
                "schleife": s["schleife"],
                "lesungen": s["lesungen"],
            }
            if s[
                "aml_anz"
            ]:  # AMNLT-Paper; Zerlegung und Makro-Mittel sind unsere Lesart (metriken.amnlt_token)
                aml, bw = s["aml_m"] / s["aml_anz"], s["bw_m"] / s["aml_anz"]
                bericht[g][form] |= {
                    "amler_pct": round(100 * aml, 2),
                    "bwer_pct": round(100 * bw, 2),
                    "aler_pct": round(100 * (aml - bw) / aml, 1) if aml else 0.0,
                    "amler_mikro_pct": round(100 * s["aml_f"] / s["aml_n"], 2),
                    "bwer_mikro_pct": round(100 * s["bw_f"] / s["aml_n"], 2),
                }
    (ordner / "messung_seiten.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in zeilen),
        encoding="utf-8",
    )
    (ordner / "messung.json").write_text(
        json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    for g, fs in bericht.items():
        for form, s in fs.items():
            print(g, form, json.dumps(s, ensure_ascii=False))


if __name__ == "__main__":
    ref = [list("cdef"), list("ggaa")]
    m = miss(ref, "(c4) a(cdef)", None)
    assert m["erkannt"] == 1 and m["letztes"] == 1 and m["ton_f"] == 4, m
    m = miss(ref, "(c4) a(cdef)\n(c4) b(ggaa)", None)
    assert m["erkannt"] == 2 and m["ton_f"] == 0 and m["zeilen_lesung"] == 2, m
    if len(sys.argv) > 1:
        main(sys.argv[1])
