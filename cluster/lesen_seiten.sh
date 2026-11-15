#!/bin/bash
#
# Lesetest ganze Seiten (Worker „seiten“): ein Checkpoint liest die Prüfmenge daten/seiten/probe als
# ganze Seite, als obere/untere Hälfte und als Systemausschnitte. Mehrere Leseprozesse teilen sich die GPU.
# Eigenes Verzeichnis $DATA/lighton_choral_seiten (models, runs als Symlink, nur gelesen).
#
#   ssh musica 'cd $DATA/lighton_choral_seiten && SMOKE=1 sbatch --qos=dev_zen4_0768_h100x4 --time=00:10:00 cluster/lesen_seiten.sh'
#   ssh musica 'cd $DATA/lighton_choral_seiten && CKPT=runs/s4t/checkpoint-53092 sbatch cluster/lesen_seiten.sh'

#SBATCH --job-name=seiten_lesen
#SBATCH --account=<your-account>
#SBATCH --gres=gpu:1
#SBATCH --partition=zen4_0768_h100x4
#SBATCH --qos=zen4_0768_h100x4
#SBATCH --time=01:00:00
#SBATCH --output=cluster/%x_%j.log
#SBATCH --error=cluster/%x_%j.err

set -u
export ROOT="$DATA/lighton_choral_seiten"
export WORK="$SCRATCH/lighton_choral_seiten"
export CKPT="${CKPT:-runs/s4t/checkpoint-53092}"
export SMOKE="${SMOKE:-0}"
export SPECS="${SPECS:-}"   # z. B. SPECS="abschnitte:2048:4": Art:max_tokens:Prozesse, durch Leerzeichen getrennt
export TAG="${TAG:-$(basename "$(dirname "$CKPT")")_$(basename "$CKPT")}"
CONTAINER="$SCRATCH/containers/pytorch-25.04.sif"

echo "=== seiten_lesen $CKPT | $(date) | $(hostname) | job $SLURM_JOB_ID | smoke $SMOKE ==="
[ -f "$CONTAINER" ] || { echo "ABBRUCH: Container fehlt"; exit 1; }
cd "$ROOT" || exit 1
bad=0
while read -r size name; do
    [ "$(stat -Lc%s "$name" 2>/dev/null || echo 0)" = "$size" ] || { bad=$((bad + 1)); echo "falsch: $name"; }
done < cluster/manifest_seiten.txt
[ "$bad" = 0 ] || { echo "ABBRUCH: $bad Dateien fehlen oder sind unvollstaendig"; exit 1; }
[ -f "$CKPT/model.safetensors" ] || { echo "ABBRUCH: $CKPT fehlt"; exit 1; }
echo "Upload vollstaendig ($(wc -l < cluster/manifest_seiten.txt) Dateien)"
mkdir -p "$WORK" aus

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
    out="aus/$TAG"; mkdir -p "$out" "$WORK/teile"
    set +e
    pids=""
    # art max_tokens prozesse
    for spec in ${SPECS:-seiten:4096:5 haelften:3072:6 systeme:600:3}; do
        set -- ${spec//:/ }
        art=$1; mt=$2; np=$3
        liste="daten/seiten/probe/$art.jsonl"
        if [ "$SMOKE" = 1 ]; then head -2 "$liste" > "$WORK/teile/$art.jsonl"; liste="$WORK/teile/$art.jsonl"; mt=40; np=1; fi
        # reihum aufteilen, damit lange Seiten nicht in einem Teil landen
        for i in $(seq 0 $((np - 1))); do
            awk -v n="$np" -v i="$i" "NR % n == i" "$liste" > "$WORK/teile/${art}_$i.jsonl"
            python lesen.py --model "$CKPT" --device cuda --bild streifen --max-tokens "$mt" \
                --liste "$WORK/teile/${art}_$i.jsonl" --aus "$out/${art}_$i.jsonl" > "$out/${art}_$i.log" 2>&1 &
            pids="$pids $!"
        done
    done
    rc=0
    for p in $pids; do wait "$p" || rc=1; done
    for spec in ${SPECS:-seiten haelften systeme}; do art=${spec%%:*}; cat "$out"/${art}_?.jsonl > "$out/$art.jsonl"; wc -l "$out/$art.jsonl"; done
    exit $rc
'
RC=$?
echo "=== Exit-Code: $RC | Ende $(date) ==="
exit $RC
