#!/bin/bash
#
# Lauf seiten_d (Worker „seiten“, AUFTRAG_2.md): Neutraining aus dem Basismodell, 4 Epochen, Einstellungen wie
# seiten_c. Trainingsdaten: die Listen von seiten_c (daten/seiten/c/) plus daten/seiten/d/ aus seiten_d.py:
# korpus_graz14 train, Silber-Handschriften, Silber-Drucke (Klasse doppelt, höchstens 1.500), Mehrsystem-Beispiele
# aus Graz14, korpus_graz-Handschriften und Silber; mehrsystem_d.jsonl = alte und neue Mehrsystem-Blöcke mit ganzen
# Seiten dreifach und Hälften doppelt (w3:p1R 14.11.). Je Checkpoint lesen wie seiten_c, dazu korpus_graz14 val und test.
#
#   ssh musica 'cd $DATA/lighton_choral_seiten && SMOKE=1 sbatch --qos=dev_zen4_0768_h100x4 --time=00:10:00 cluster/train_seiten_d.sh'
#   ssh musica 'cd $DATA/lighton_choral_seiten && sbatch cluster/train_seiten_d.sh'

#SBATCH --job-name=seiten_train_d
#SBATCH --account=<your-account>
#SBATCH --gres=gpu:1
#SBATCH --partition=zen4_0768_h100x4
#SBATCH --qos=zen4_0768_h100x4
#SBATCH --time=22:00:00
#SBATCH --output=cluster/%x_%j.log
#SBATCH --error=cluster/%x_%j.err

set -u
export ROOT="$DATA/lighton_choral_seiten"
export WORK="$SCRATCH/lighton_choral_seiten"
export INIT="${INIT:-models/LightOnOCR-3-1B-konvertiert}"
export RUN="${RUN:-seiten_d}"
export SMOKE="${SMOKE:-0}"
export SYSTEME="daten/seiten/c/systeme_c.jsonl"   # systeme_wg, F-Schlüssel-Systeme aus train doppelt
CONTAINER="$SCRATCH/containers/pytorch-25.04.sif"

echo "=== seiten_train $RUN | init $INIT | $(date) | $(hostname) | job $SLURM_JOB_ID | smoke $SMOKE ==="
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
[ -f "$CONTAINER" ] || { echo "ABBRUCH: Container fehlt"; exit 1; }
cd "$ROOT" || exit 1
bad=0
while read -r size name; do
    [ "$(stat -Lc%s "$name" 2>/dev/null || echo 0)" = "$size" ] || { bad=$((bad + 1)); echo "falsch: $name"; }
done < cluster/manifest_seiten.txt
[ "$bad" = 0 ] || { echo "ABBRUCH: $bad Dateien fehlen oder sind unvollstaendig"; exit 1; }
[ -f "$INIT/model.safetensors" ] || { echo "ABBRUCH: $INIT fehlt"; exit 1; }
# Bilder der Trainingslisten einzeln prüfen (Symlinks auf die gemeinsamen Daten tauchen im Manifest nicht auf)
fehlt=$(cat daten/seiten/c/gabc_c.jsonl daten/seiten/c/transkribus_c.jsonl daten/seiten/c/graz_c.jsonl daten/seiten/d/graz14.jsonl daten/seiten/d/silber_hs.jsonl daten/seiten/d/silber_druck.jsonl daten/seiten/d/mehrsystem_d.jsonl daten/korpus_graz/validation.jsonl daten/korpus_graz/test.jsonl daten/korpus_graz14/validation.jsonl daten/korpus_graz14/test.jsonl "$SYSTEME" \
    | python3 -c 'import json,sys,os; print(sum(not os.path.exists(json.loads(z)["bild"]) for z in sys.stdin))')
[ "$fehlt" = 0 ] || { echo "ABBRUCH: $fehlt Bilder fehlen"; exit 1; }
echo "Upload vollstaendig ($(wc -l < cluster/manifest_seiten.txt) Dateien), alle Bilder vorhanden"
mkdir -p "$WORK" laeufe

apptainer exec --nv --bind "$DATA:$DATA" --bind "$SCRATCH:$SCRATCH" "$CONTAINER" bash -c '
    set -e
    export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1
    grep -vE "^(dill|regex|safetensors|click)==" /etc/pip/constraint.txt > /tmp/constraint.txt
    export PIP_CONSTRAINT=/tmp/constraint.txt
    export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
    export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE CURL_CA_BUNDLE=$SSL_CERT_FILE
    export TRITON_LIBCUDA_PATH=/.singularity.d/libs
    [ -d "$WORK/venv" ] || python -m venv --system-site-packages "$WORK/venv"
    source "$WORK/venv/bin/activate"
    pip install --quiet "transformers==5.22.1" rapidfuzz
    python -c "import torch, transformers; print(\"torch\", torch.__version__, \"| transformers\", transformers.__version__)"
    cd "$ROOT"
    python metriken.py
    python seiten_messen.py
    TRAIN_ARGS="--init $INIT --bild streifen --epochs 4"
    if [ "$SMOKE" = 1 ]; then
        # 6 AMNLT-Systeme, je ein Beispiel jedes Blocks (Mehrsystem aus Silber, falls vorhanden; daten/seiten/d/smoke.jsonl),
        # 4 Abschnitte, die 4 längsten Seiten (Speicherspitze)
        out="$WORK/${RUN}_smoke"; rm -rf "$out"; mkdir -p "$WORK/smoke"
        python - <<EOF
import json
lade = lambda p: [json.loads(z) for z in open(p, encoding="utf-8")]
amnlt = lade("$SYSTEME")
tr = [z for z in amnlt if z["split"] == "train"][:6]
val = [z for z in amnlt if z["split"] == "validation"][:8]
with open("$WORK/smoke/systeme.jsonl", "w") as f:
    f.writelines(json.dumps(z, ensure_ascii=False) + "\n" for z in tr + val)
s = lade("daten/seiten/c/mehrsystem_c.jsonl")
ab = [z for z in s if z["art"] == "abschnitt"][:4]
se = sorted((z for z in s if z["art"] == "seite"), key=lambda z: -z["token"])[:4]
print("laengste Seite", se[0]["id"], se[0]["token"], "Token")
zus = lade("daten/korpus_gabc/train.jsonl")[:1] + lade("daten/korpus_graz/train.jsonl")[:1] + lade("daten/seiten/d/smoke.jsonl") + ab + se
with open("$WORK/smoke/zusatz.jsonl", "w") as f:
    f.writelines(json.dumps(z, ensure_ascii=False) + "\n" for z in zus)
EOF
        SYSTEME="$WORK/smoke/systeme.jsonl" python train.py $TRAIN_ARGS --out "$out" --zusatz "$WORK/smoke/zusatz.jsonl" --val-n 8 --accum 8
        ck=$(ls -d "$out"/checkpoint-* | sort -V | tail -1)
        head -2 daten/seiten/probe/seiten.jsonl > "$WORK/smoke/lesen.jsonl"
        head -2 daten/seiten/probe/abschnitte.jsonl >> "$WORK/smoke/lesen.jsonl"
        python lesen.py --model "$ck" --device cuda --bild streifen --max-tokens 300 --liste "$WORK/smoke/lesen.jsonl" --aus "aus/smoke_lesung.jsonl"
        python -c "
import json
for z in map(json.loads, open(\"aus/smoke_lesung.jsonl\")):
    print(z[\"id\"], \"| Zeilen:\", z[\"lesung\"].count(chr(10)) + 1, \"| abgebrochen:\", z[\"abgebrochen\"], \"|\", z[\"lesung\"][:160].replace(\"<m>\", \"\").replace(chr(10), \" / \"))
"
        exit 0
    fi
    out="laeufe/$RUN"
    python train.py $TRAIN_ARGS --out "$out" --ckpt-per-epoch 1 \
        --zusatz daten/seiten/c/gabc_c.jsonl daten/seiten/c/transkribus_c.jsonl daten/seiten/c/graz_c.jsonl daten/seiten/d/graz14.jsonl daten/seiten/d/silber_hs.jsonl daten/seiten/d/silber_druck.jsonl daten/seiten/d/mehrsystem_d.jsonl
    set +e
    mkdir -p "$WORK/teile"
    lies() {  # Modell Ausgabeordner Art max_tokens Prozesse
        mkdir -p "$2"
        for i in $(seq 0 $(($5 - 1))); do
            awk -v n="$5" -v i="$i" "NR % n == i" "daten/seiten/probe/$3.jsonl" > "$WORK/teile/$(basename "$2")_$3_$i.jsonl"
            python lesen.py --model "$1" --device cuda --bild streifen --max-tokens "$4" \
                --liste "$WORK/teile/$(basename "$2")_$3_$i.jsonl" --aus "$2/$3_$i.jsonl" > "$2/$3_$i.log" 2>&1 &
            pids="$pids $!"
        done
    }
    rc=0
    letzter=$(ls -d "$out"/checkpoint-* | sort -V | tail -1)
    # je Checkpoint: Regressionsmengen, ganze Seiten und Abschnitte; Hälften und Ausschnitte nur beim letzten
    for ck in $(ls -d "$out"/checkpoint-* | sort -V); do
        echo "=== lese mit $ck $(date +%T) ==="
        pids=""
        python auswertung.py --model "$ck" --split validation --bild streifen > "$ck/lesung_validation.log" 2>&1 & pids="$pids $!"
        python auswertung.py --model "$ck" --split validation --bild streifen --liste daten/korpus_gabc/validation.jsonl > "$ck/lesung_korpus_validation.log" 2>&1 & pids="$pids $!"
        python auswertung.py --model "$ck" --split validation --bild streifen --liste daten/korpus_transkribus/validation.jsonl > "$ck/lesung_transkribus_validation.log" 2>&1 & pids="$pids $!"
        python auswertung.py --model "$ck" --split validation --bild streifen --liste daten/korpus_graz/validation.jsonl > "$ck/lesung_graz_validation.log" 2>&1 & pids="$pids $!"
        python auswertung.py --model "$ck" --split test --bild streifen --liste daten/korpus_graz/test.jsonl > "$ck/lesung_graz_test.log" 2>&1 & pids="$pids $!"
        python auswertung.py --model "$ck" --split validation --bild streifen --liste daten/korpus_graz14/validation.jsonl > "$ck/lesung_graz14_validation.log" 2>&1 & pids="$pids $!"
        python auswertung.py --model "$ck" --split test --bild streifen --liste daten/korpus_graz14/test.jsonl > "$ck/lesung_graz14_test.log" 2>&1 & pids="$pids $!"
        ( python lesen.py --model "$ck" --device cuda --bild streifen --liste daten/gt/systeme.jsonl --aus "$ck/lesung_gt.jsonl" && python vergleich_gt.py "$ck/lesung_gt.jsonl" ) > "$ck/lesung_gt.log" 2>&1 & pids="$pids $!"
        neu="aus/${RUN}_$(basename "$ck")"
        lies "$ck" "$neu" seiten 4096 5
        lies "$ck" "$neu" abschnitte 2048 3
        if [ "$ck" = "$letzter" ]; then
            lies "$ck" "$neu" haelften 3072 4
            lies "$ck" "$neu" systeme 600 2
        fi
        for p in $pids; do wait "$p" || rc=1; done
        for art in seiten haelften abschnitte systeme; do
            ls "$neu"/${art}_?.jsonl > /dev/null 2>&1 && cat "$neu"/${art}_?.jsonl > "$neu/$art.jsonl"
        done
        [ "$ck" = "$letzter" ] && python seiten_messen.py "$neu" | grep "^alle\|^valtest \|^pruef "
        tail -n 3 "$ck"/lesung_gt.log
    done
    exit $rc
'
RC=$?
echo "=== Exit-Code: $RC | Ende $(date) ==="
exit $RC
