#!/bin/bash
# =============================================================================
# run_blrunner.slurm
# SLURM submission script to launch BLRunner.py on a CECI cluster.
#
# Usage:
#   sbatch run_blrunner.slurm --config path/to/config.yaml
#
# Adjust the SBATCH directives below to match your needs.
# =============================================================================

#SBATCH --job-name=beeline
#SBATCH --output=logs/beeline_%j.out
#SBATCH --error=logs/beeline_%j.err
#SBATCH --time=24:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
##SBATCH --partition=debug
##SBATCH --gres=gpu:1

set -e

# --- Parse arguments ---------------------------------------------------------
CONFIG=""
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --config) CONFIG="$2"; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
    shift
done

if [ -z "$CONFIG" ]; then
    echo "ERROR: No config file specified. Use: sbatch run_blrunner.slurm --config path/to/config.yaml"
    exit 1
fi

if [ ! -f "$CONFIG" ]; then
    echo "ERROR: Config file not found: $CONFIG"
    exit 1
fi

# --- Paths -------------------------------------------------------------------
BASEDIR="$(dirname "$(readlink -f "$0")")"
CONDA_ENV="BEELINE"
SIF_DIR="$BASEDIR/utils/sif_images"
SHIM_DIR="$BASEDIR/utils/docker_shim"

# --- Environment setup -------------------------------------------------------
mkdir -p "$BASEDIR/logs"

# Speed up Apptainer with in-memory filesystems
if [ -n "$XDG_RUNTIME_DIR" ]; then
    export APPTAINER_TMPDIR=$XDG_RUNTIME_DIR
    export APPTAINER_CACHEDIR=$XDG_RUNTIME_DIR
fi

# Put the docker shim first on PATH so all "docker run" calls in Runners
# are silently intercepted and translated to "apptainer exec"
export PATH="$SHIM_DIR:$PATH"

# Export SIF_DIR so the shim can find the .sif images
export BEELINE_SIF_DIR="$SIF_DIR"

# Activate the BEELINE conda environment
eval "$(conda shell.bash hook)"
conda activate "$CONDA_ENV"

# --- Run BLRunner ------------------------------------------------------------
echo "============================================================"
echo " Job ID     : $SLURM_JOB_ID"
echo " Node       : $SLURMD_NODENAME"
echo " Config     : $CONFIG"
echo " SIF dir    : $SIF_DIR"
echo " Start time : $(date)"
echo "============================================================"

python "$BASEDIR/BLRunner.py" --config "$CONFIG"

echo "============================================================"
echo " End time   : $(date)"
echo " Done."
echo "============================================================"
