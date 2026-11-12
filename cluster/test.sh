#!/bin/bash
# Schlussmessung des ausgewählten Checkpoints auf AMNLT-test.
#SBATCH --job-name=lighton_test
#SBATCH --account=<your-account>
#SBATCH --gres=gpu:1
#SBATCH --partition=zen4_0768_h100x4
#SBATCH --qos=zen4_0768_h100x4
#SBATCH --time=01:30:00
#SBATCH --output=musica/%x_%j.log
#SBATCH --error=musica/%x_%j.err

set -u
export ROOT="$DATA/lighton_choral" WORK="$SCRATCH/lighton_choral_train"
CONTAINER="$SCRATCH/containers/pytorch-25.04.sif"
cd "$ROOT" || exit 1
apptainer exec --nv --bind "$DATA:$DATA" --bind "$SCRATCH:$SCRATCH" "$CONTAINER" bash -c '
    set -e
    export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRITON_LIBCUDA_PATH=/.singularity.d/libs
    source "$WORK/venv/bin/activate"
    cd "$ROOT"
    python auswertung.py --model runs/s4k/checkpoint-24332 --split test --bild streifen --out runs/s4k/lesung_test.jsonl
'
RC=$?
echo "=== Exit-Code: $RC | Ende $(date) ==="
exit $RC
