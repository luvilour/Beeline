#!/bin/bash
# =============================================================================
# setup_beeline_container.sh
# Sets up a portable Apptainer container for Beeline on CECI clusters.
# Usage: bash setup_beeline_container.sh [path/to/environment.yml]
# =============================================================================

set -ex

# --- Configuration -----------------------------------------------------------
BASEDIR="$(dirname "$(readlink -f "$0")")"
ENV_YML="${1:-$BASEDIR/environment.yml}" # default: environment.yml next to this script
BASE_IMAGE="miniconda3_latest.sif"
SANDBOX_DIR="beeline.sandbox"
FINAL_IMAGE="beeline.sif"

# --- Checks ------------------------------------------------------------------
if [ ! -f "$ENV_YML" ]; then
    echo "ERROR: environment.yml not found at '$ENV_YML'."
    echo "Usage: bash setup_beeline_container.sh [path/to/environment.yml]"
    exit 1
fi

# --- Speed up Apptainer with in-memory filesystems (if available) ------------
if [ -n "$XDG_RUNTIME_DIR" ]; then
    echo "Using in-memory filesystem for Apptainer cache and tmp..."
    export APPTAINER_TMPDIR=$XDG_RUNTIME_DIR
    export APPTAINER_CACHEDIR=$XDG_RUNTIME_DIR
else
    echo "WARNING: XDG_RUNTIME_DIR not set, skipping Apptainer speed-up."
fi

# --- Step 1: Pull base image (skip if already present) -----------------------
if [ ! -f "$BASE_IMAGE" ]; then
    echo "Pulling base miniconda3 image..."
    apptainer pull docker://continuumio/miniconda3
else
    echo "Base image '$BASE_IMAGE' already exists, skipping pull."
fi

# --- Step 2: Build writable sandbox ------------------------------------------
if [ -d "$SANDBOX_DIR" ]; then
    echo "Sandbox '$SANDBOX_DIR' already exists, removing it first..."
    rm -rf "$SANDBOX_DIR"
fi

echo "Building writable sandbox from base image..."
apptainer build --sandbox "$SANDBOX_DIR" "$BASE_IMAGE"

# --- Step 3: Install Beeline conda environment into sandbox ------------------
echo "Installing Beeline conda environment from '$ENV_YML'..."
apptainer exec --writable "$SANDBOX_DIR" conda env create --file="$ENV_YML"

# --- Step 4: Build final .sif image ------------------------------------------
echo "Building final Apptainer image '$FINAL_IMAGE'..."
apptainer build "$FINAL_IMAGE" "$SANDBOX_DIR"

# --- Step 5: Clean up sandbox ------------------------------------------------
echo "Cleaning up sandbox..."
rm -rf "$SANDBOX_DIR"

# --- Done --------------------------------------------------------------------
echo ""
echo "============================================================"
echo " SUCCESS: Beeline container ready -> $FINAL_IMAGE"
echo "============================================================"
echo ""
echo "To run Beeline in your SLURM script, use:"
echo "  apptainer exec $FINAL_IMAGE conda run -n BEELINE python BLRun.py [args]"
echo ""
