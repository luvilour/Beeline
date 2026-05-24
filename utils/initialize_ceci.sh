#!/bin/bash
# =============================================================================
# initialize_ceci.sh
# CECI-adapted version of initialize.sh for Beeline.
# - Custom algorithms: built from Apptainer .def files (no Docker needed)
# - DockerHub algorithms: pulled directly via apptainer pull docker://...
#
# Usage: bash initialize_ceci.sh [OPTIONS]
#   -b, --build                  Build custom algorithm images from .def files
#   -v, --verbose                Enable verbose output
#   -h, --help                   Show this help message
#   --remove-local-images        Remove locally built .sif images
#   --remove-grnbeeline-images   Remove DockerHub-pulled .sif images
#
# Requirements:
#   apptainer, git
# =============================================================================

set -e

BASEDIR="$(dirname "$(readlink -f "$0")")"
ROOTDIR="$(dirname "$BASEDIR")"

# Directory where all .sif images will be stored
SIF_DIR="$BASEDIR/sif_images"
# Directory where the .def files live (next to this script)
DEF_DIR="$BASEDIR/apptainer_defs"

BUILD=false
HELP=false
REMOVE_LOCAL=false
REMOVE_GRNBEELINE=false
VERBOSE_VALUE="--quiet"

# --- Speed up Apptainer with in-memory filesystems (if available) ------------
if [ -n "$XDG_RUNTIME_DIR" ]; then
    export APPTAINER_TMPDIR=$XDG_RUNTIME_DIR
    export APPTAINER_CACHEDIR=$XDG_RUNTIME_DIR
fi

# --- Image lists -------------------------------------------------------------

# Images pulled from DockerHub (grnbeeline organisation)
DOCKERHUB_IMAGES=(
    grnbeeline/arboreto:base
    grnbeeline/grisli:base
    grnbeeline/grnvbem:base
    grnbeeline/leap:base
    grnbeeline/pidc:base
    grnbeeline/ppcor:base
    grnbeeline/scinge:base
    grnbeeline/scns:base
    grnbeeline/scode:base
    grnbeeline/scribe:base
    grnbeeline/sincerities:base
    grnbeeline/singe:0.4.1
)

# Custom algorithms: maps .def filename (no extension) -> output .sif name
# The .def files must be in $DEF_DIR and the source files in the matching
# Algorithms/ subdirectory (used as the build context for %files sections).
declare -A LOCAL_DEF_MAP=(
    [lassonet]="lassonet_base"
    [lassonetprob]="lassonetprob_base"
    [lassonetprobmoy]="lassonetprobmoy_base"
    [scgenerai]="scgenerai_base"
    [tabnet]="tabnet_base"
    [deepsem]="deepsem_base"
)

# Map def name -> Algorithms/ subdirectory (used as the build context,
# so Apptainer finds the files referenced in %files sections)
declare -A DEF_CONTEXT_MAP=(
    [lassonet]="LassoNet"
    [lassonetprob]="LassoNetProb"
    [lassonetprobmoy]="LassoNetProbNorm"
    [scgenerai]="scGeneRAI"
    [tabnet]="TabNet"
    [deepsem]="DeepSEM"
)

# --- Helpers -----------------------------------------------------------------

# Convert "org/name:tag" or "name:tag" to a safe .sif filename
image_to_sif() {
    local image="$1"
    local base="${image##*/}"          # strip org prefix
    echo "$SIF_DIR/${base/:/_}.sif"   # replace : with _
}

show_help() {
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo "CECI-adapted Beeline setup: builds custom algorithm containers as"
    echo "Apptainer .sif images from .def files, and pulls DockerHub images."
    echo ""
    echo "Options:"
    echo "  -h, --help                   Display this help message and exit."
    echo "  -b, --build                  Build custom algorithm images from .def files."
    echo "  -v, --verbose                Enable verbose output."
    echo "  --remove-local-images        Remove locally built .sif images."
    echo "  --remove-grnbeeline-images   Remove DockerHub-pulled .sif images."
    echo ""
    echo "  .def files are expected in: $DEF_DIR"
    echo "  .sif images are stored in:  $SIF_DIR"
}

# --- Argument parsing --------------------------------------------------------
while [[ "$#" -gt 0 ]]; do
    case "$1" in
    -b | --build)               BUILD=true ;;
    -v | --verbose)             VERBOSE_VALUE="" ;;
    -h | --help)                HELP=true ;;
    --remove-local-images)      REMOVE_LOCAL=true ;;
    --remove-grnbeeline-images) REMOVE_GRNBEELINE=true ;;
    *)
        echo "Unknown option: $1" >&2
        show_help
        exit 1
        ;;
    esac
    shift
done

if [[ "$HELP" = true ]]; then
    show_help
    exit 0
fi

mkdir -p "$SIF_DIR"

# --- Remove DockerHub-pulled .sif images -------------------------------------
if [[ "$REMOVE_GRNBEELINE" = true ]]; then
    echo "Removing grnbeeline DockerHub .sif images..."
    for image in "${DOCKERHUB_IMAGES[@]}"; do
        sif="$(image_to_sif "$image")"
        if [ -f "$sif" ]; then
            rm -f "$sif"
            echo "Removed $sif"
        fi
    done
    echo "Done removing grnbeeline images."
    if [[ "$BUILD" = false ]]; then exit 0; fi
fi

# --- Remove locally built .sif images ----------------------------------------
if [[ "$REMOVE_LOCAL" = true ]]; then
    echo "Removing locally built BEELINE .sif images..."
    for def_name in "${!LOCAL_DEF_MAP[@]}"; do
        sif="$SIF_DIR/${LOCAL_DEF_MAP[$def_name]}.sif"
        if [ -f "$sif" ]; then
            rm -f "$sif"
            echo "Removed $sif"
        fi
    done
    echo "Done removing local images."
    if [[ "$BUILD" = false ]]; then exit 0; fi
fi

# --- Build custom algorithms from .def files ---------------------------------
if [[ "$BUILD" = true ]]; then
    echo "Building custom algorithm images from .def files..."
    echo "This may take a while."
    echo ""

    for def_name in "${!LOCAL_DEF_MAP[@]}"; do
        def_file="$DEF_DIR/${def_name}.def"
        sif_path="$SIF_DIR/${LOCAL_DEF_MAP[$def_name]}.sif"
        context_dir="$ROOTDIR/Algorithms/${DEF_CONTEXT_MAP[$def_name]}"

        echo "-------------------------------------------------------------"
        echo "Building: $def_name -> $sif_path"
        echo "  .def file:   $def_file"
        echo "  context dir: $context_dir"

        if [ ! -f "$def_file" ]; then
            echo "ERROR: .def file not found: $def_file"
            exit 1
        fi
        if [ ! -d "$context_dir" ]; then
            echo "ERROR: Algorithm directory not found: $context_dir"
            exit 1
        fi

        # Build from the algorithm directory so %files paths resolve correctly
        pushd "$context_dir" > /dev/null
        apptainer build $VERBOSE_VALUE "$sif_path" "$def_file"
        popd > /dev/null

        if [ -f "$sif_path" ]; then
            echo "SUCCESS: $sif_path"
        else
            echo "ERROR: Failed to build $sif_path"
            exit 1
        fi
    done

# --- Pull DockerHub images via Apptainer -------------------------------------
else
    echo "Pulling Apptainer images from DockerHub (grnbeeline)..."
    echo ""

    for image in "${DOCKERHUB_IMAGES[@]}"; do
        sif="$(image_to_sif "$image")"
        if [ -f "$sif" ]; then
            echo "Already exists, skipping: $sif"
            continue
        fi
        echo "Pulling docker://$image -> $sif ..."
        apptainer pull $VERBOSE_VALUE "$sif" "docker://$image"
        if [ -f "$sif" ]; then
            echo "SUCCESS: $sif"
        else
            echo "ERROR: Failed to pull $image"
            exit 1
        fi
    done
fi

# --- Summary -----------------------------------------------------------------
echo ""
echo "============================================================"
echo " All done! .sif images stored in:"
echo "   $SIF_DIR"
echo ""
echo " Example usage in a SLURM job:"
echo "   apptainer exec $SIF_DIR/lassonet_base.sif python runLassoNet.py [args]"
echo "============================================================"
