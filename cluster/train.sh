#!/bin/bash
#
# Lauf 3 (s4g): AMNLT plus CantusDB-GABC-Korpus (daten/korpus_gabc/train.jsonl, 8.781 Systeme mit Textzeile),
# danach je Checkpoint: AMNLT-validation, Korpus-validation und die fünf Prüfhandschriften (daten/gt).
# Auswahl des Checkpoints nach Tonlagen-SER auf AMNLT-validation (wie s4 und s4k).
#
#   ssh musica 'cd $DATA/lighton_choral && SMOKE=1 sbatch --qos=dev_zen4_0768_h100x4 --time=00:10:00 musica/train_v3.sh'
#   ssh musica 'cd $DATA/lighton_choral && sbatch musica/train_v3.sh'

#SBATCH --job-name=lighton_choral3
#SBATCH --account=<your-account>
#SBATCH --gres=gpu:1
#SBATCH --partition=zen4_0768_h100x4
#SBATCH --qos=zen4_0768_h100x4
#SBATCH --time=20:00:00
#SBATCH --output=musica/%x_%j.log
#SBATCH --error=musica/%x_%j.err

set -u
export ROOT="$DATA/lighton_choral"
export WORK="$SCRATCH/lighton_choral_train"
export RUN="${RUN:-s4g}"
export BILD="${BILD:-streifen}"
export EPOCHS="${EPOCHS:-4}"
export ZUSATZ="${ZUSATZ:-daten/korpus_gabc/train.jsonl}"
export SYSTEME="${SYSTEME:-daten/systeme.jsonl}"   # daten/systeme_wg.jsonl: AMNLT mit Wortgrenzen
export ARGS="${ARGS:-}"
export SMOKE="${SMOKE:-0}"
CONTAINER="$SCRATCH/containers/pytorch-25.04.sif"

echo "=== lighton_choral3 $RUN | $BILD | zusatz $ZUSATZ | systeme $SYSTEME | $(date) | $(hostname) | job $SLURM_JOB_ID | smoke $SMOKE ==="
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
[ -f "$CONTAINER" ] || { echo "ABBRUCH: Container fehlt: $CONTAINER"; exit 1; }

cd "$ROOT" || exit 1
bad=0
while read -r size name; do
    [ "$(stat -Lc%s "$name" 2>/dev/null || echo 0)" = "$size" ] || { bad=$((bad + 1)); echo "falsch: $name"; }
done < musica/manifest_v3.txt
[ "$bad" = 0 ] || { echo "ABBRUCH: $bad Dateien fehlen oder sind unvollstaendig"; exit 1; }
echo "Upload vollstaendig ($(wc -l < musica/manifest_v3.txt) Dateien), Zusatz $(cat $ZUSATZ | wc -l) Systeme"
mkdir -p "$WORK" runs

apptainer exec --nv --bind "$DATA:$DATA" --bind "$SCRATCH:$SCRATCH" "$CONTAINER" bash -c '
    set -e
    export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1
    grep -vE "^(dill|regex|safetensors|click)==" /etc/pip/constraint.txt > /tmp/constraint.txt
    export PIP_CONSTRAINT=/tmp/constraint.txt
    export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
    export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE CURL_CA_BUNDLE=$SSL_CERT_FILE
    export TRITON_LIBCUDA_PATH=/.singularity.d/libs
    python -m venv --system-site-packages "$WORK/venv"
    source "$WORK/venv/bin/activate"
    pip install --quiet "transformers==5.22.1" rapidfuzz
    python -c "import torch, transformers; print(\"torch\", torch.__version__, \"| transformers\", transformers.__version__)"

    cd "$ROOT"
    python metriken.py
    python bildform.py
    python vergleich_gt.py
    out="runs/$RUN"; extra=""; gt="daten/gt/systeme.jsonl"
    if [ "$SMOKE" = 1 ]; then
        out="runs/${RUN}_smoke"; extra="--n 2"
        head -3 daten/gt/systeme.jsonl > "$WORK/gt_klein.jsonl"; gt="$WORK/gt_klein.jsonl"
        python train.py --bild "$BILD" --epochs "$EPOCHS" --ckpt-per-epoch 1 --out "$out" --zusatz $ZUSATZ $ARGS --max-n 16 --val-n 8
    else
        python train.py --bild "$BILD" --epochs "$EPOCHS" --ckpt-per-epoch 1 --out "$out" --zusatz $ZUSATZ $ARGS
    fi
    echo "=== lese mit: $(ls -d "$out"/checkpoint-* | sort -V | tr "\n" " ") ==="
    set +e
    rc=0
    pids=""; logs=""; offen=0
    for ck in $(ls -d "$out"/checkpoint-* | sort -V); do
        if [ "$offen" -ge 2 ]; then for p in $pids; do wait "$p" || rc=1; done; pids=""; offen=0; fi
        offen=$((offen + 1))
        python auswertung.py --model "$ck" --split validation --bild "$BILD" $extra > "$ck/lesung_validation.log" 2>&1 &
        pids="$pids $!"; logs="$logs $ck/lesung_validation.log"
        python auswertung.py --model "$ck" --split validation --bild "$BILD" --liste daten/korpus_gabc/validation.jsonl $extra > "$ck/lesung_korpus_validation.log" 2>&1 &
        pids="$pids $!"; logs="$logs $ck/lesung_korpus_validation.log"
        if [ -f daten/korpus_transkribus/validation.jsonl ]; then
            python auswertung.py --model "$ck" --split validation --bild "$BILD" --liste daten/korpus_transkribus/validation.jsonl $extra > "$ck/lesung_transkribus_validation.log" 2>&1 &
            pids="$pids $!"; logs="$logs $ck/lesung_transkribus_validation.log"
        fi
        ( python lesen.py --model "$ck" --device cuda --bild "$BILD" --liste "$gt" --aus "$ck/lesung_gt.jsonl" && python vergleich_gt.py "$ck/lesung_gt.jsonl" ) > "$ck/lesung_gt.log" 2>&1 &
        pids="$pids $!"; logs="$logs $ck/lesung_gt.log"
    done
    for p in $pids; do wait "$p" || rc=1; done
    tail -n 12 $logs
    exit $rc
'
RC=$?
echo "=== Exit-Code: $RC | Ende $(date) ==="
exit $RC
