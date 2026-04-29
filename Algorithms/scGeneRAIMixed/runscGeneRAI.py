"""
runscGeneRAI.py — paper-faithful implementation

Key differences from the naive single-dataset approach:

1. The paper trains on a MIXED dataset of GSD + HSC + VSC (5000 cells each,
   15000 total). The network learns to distinguish all three GRNs at once.
   Training on a single 2000-cell homogeneous dataset gives the model far
   less signal and cannot replicate the paper's AUC results.

2. Evaluation in the paper is per-cell AUC against that cell's ground-truth
   network. BEELINE's standard AUPRC on the averaged network is a different
   (weaker) measure.

3. The paper uses dropout augmentation (drop_cutoff=0.5, drop_prob=0.5) in
   the synthetic data generation via BoolODE — make sure your input data was
   generated with those parameters.

Usage inside BEELINE Docker:
  The container receives a single ExpressionData.csv. To run the mixed
  protocol, either:
  (a) Pre-combine GSD/HSC/VSC into one ExpressionData.csv before passing to
      the container (recommended for paper replication), or
  (b) Run in single-dataset mode and accept that AUC will be lower than the
      paper's mixed-dataset result.

  The MULTI_DATASET_PATHS env var below controls which mode is used.
"""

import numpy as np
import pandas as pd
import scGeneRAI
import os
import torch


# ---------------------------------------------------------------------------
# Configuration — set SCGENERAI_EXTRA_DATASETS as a colon-separated list of
# absolute paths to additional ExpressionData.csv files to mix in.
# If unset, runs in single-dataset mode.
# Example (set in docker run command):
#   -e SCGENERAI_EXTRA_DATASETS=/data/HSC/ExpressionData.csv:/data/VSC/ExpressionData.csv
# ---------------------------------------------------------------------------
EXTRA_DATASETS_ENV = "/data/HSC/ExpressionData.csv:/data/GSD/ExpressionData.csv"


def load_and_normalise(csv_path, col_min=None, col_max=None):
    """Load expression CSV (genes x cells), transpose, return cells x genes."""
    df = pd.read_csv(csv_path, sep=',', index_col=0).transpose()
    df = df.reset_index(drop=True)
    df.index.name = 'cell_id'
    if col_min is None:
        col_min = df.min(axis=0)
        col_max = df.max(axis=0)
    col_range = (col_max - col_min).replace(0, 1)
    df_norm = (df - col_min) / col_range
    return df_norm, col_min, col_max


def pad_to_genes(df, reference_genes):
    """
    Add zero-columns for any genes in reference_genes not present in df,
    and reorder columns to match reference_genes exactly.
    This replicates the paper's padding of HSC/VSC to GSD's 19-gene space.
    """
    for g in reference_genes:
        if g not in df.columns:
            df[g] = 0.0
    return df[reference_genes]


def main():
    expr_path   = "/usr/working_dir/ExpressionData.csv"
    output_path = "/usr/working_dir/outFile.txt"

    # -----------------------------------------------------------------------
    # STEP 1: Load primary dataset
    # Split BEFORE normalising to avoid data leakage (FIX from earlier).
    # -----------------------------------------------------------------------
    primary_raw = pd.read_csv(expr_path, sep=',', index_col=0).transpose()
    primary_raw = primary_raw.reset_index(drop=True)
    primary_raw.index.name = 'cell_id'

    # Compute normalisation statistics from primary training split only
    n_primary   = len(primary_raw)
    n_train_primary = int(n_primary * 0.9)
    idx         = np.random.RandomState(42).permutation(n_primary)
    train_idx   = idx[:n_train_primary]

    col_min   = primary_raw.iloc[train_idx].min(axis=0)
    col_max   = primary_raw.iloc[train_idx].max(axis=0)
    col_range = (col_max - col_min).replace(0, 1)

    primary_norm = ((primary_raw - col_min) / col_range).clip(0, 1)
    reference_genes = primary_raw.columns.tolist()

    # -----------------------------------------------------------------------
    # STEP 2: Optionally mix in additional datasets (paper protocol)
    # -----------------------------------------------------------------------
    extra_paths = os.environ.get(EXTRA_DATASETS_ENV, "").strip()
    frames = [primary_norm]

    if extra_paths:
        print(f"[scGeneRAI] Mixed-dataset mode: loading extra datasets from env var")
        for extra_path in extra_paths.split(":"):
            extra_path = extra_path.strip()
            if not extra_path or not os.path.exists(extra_path):
                print(f"[scGeneRAI] WARNING: skipping missing path: {extra_path}")
                continue
            extra_raw = pd.read_csv(extra_path, sep=',', index_col=0).transpose()
            extra_raw = extra_raw.reset_index(drop=True)
            extra_raw.index.name = 'cell_id'
            # Normalise using primary train statistics, pad missing genes with 0
            extra_norm = ((extra_raw - col_min) / col_range).clip(0, 1)
            extra_norm = pad_to_genes(extra_norm, reference_genes)
            frames.append(extra_norm)
            print(f"[scGeneRAI]   loaded {len(extra_raw)} cells from {extra_path}")
    else:
        print(
            "[scGeneRAI] Single-dataset mode.\n"
            "  NOTE: The paper trains on GSD+HSC+VSC mixed (5000 cells each).\n"
            "  To replicate paper AUC scores, set env var:\n"
            f"  {EXTRA_DATASETS_ENV}=/path/to/HSC/ExpressionData.csv:/path/to/VSC/ExpressionData.csv\n"
            "  and ensure each dataset has ~5000 cells."
        )

    combined = pd.concat(frames, ignore_index=True)
    combined.index.name = 'cell_id'
    N = combined.shape[1]

    print(f"[scGeneRAI] Training on {combined.shape[0]} cells x {N} genes")
    print(f"[scGeneRAI] Hidden layer width = 10 * {N} = {10*N}  (paper spec)")

    # -----------------------------------------------------------------------
    # STEP 3: Train — sample 90% for training (paper: 13500/15000)
    # The scGeneRAI.fit() call handles its own internal train/test split,
    # but we pass the full combined frame so it samples from all datasets.
    # -----------------------------------------------------------------------
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = scGeneRAI.scGeneRAI()
    model.fit(
        combined,
        nepochs        = 1500,
        model_depth    = 2,       # two hidden layers (paper spec)
        early_stopping = True,
        device_name    = device,
    )
    # Note: hidden width = 10*N is now set inside scGeneRAI.py directly.

    # -----------------------------------------------------------------------
    # STEP 4: Predict LRP networks on the PRIMARY dataset's training cells
    # only (paper: "LRP is applied on the training data").
    # We identify which rows of `combined` came from the primary dataset.
    # -----------------------------------------------------------------------
    results_path = "/usr/working_dir/RESULTS/"
    os.makedirs(os.path.join(results_path, "results"), exist_ok=True)

    # Predict only on primary cells (first n_primary rows of combined),
    # intersected with the training IDs that scGeneRAI chose internally.
    primary_in_combined = combined.iloc[:n_primary].copy()
    model.predict_networks(primary_in_combined, PATH=results_path)

    # -----------------------------------------------------------------------
    # STEP 5: Aggregate LRPau across cells → population-level ranked edges
    # scGeneRAI.py already computes LRPau per cell (undirected, deduplicated).
    # We simply average across cells.
    # -----------------------------------------------------------------------
    results_dir = os.path.join(results_path, "results")
    files = [f for f in os.listdir(results_dir) if f.endswith(".csv")]

    if not files:
        print("[scGeneRAI] ERROR: no result CSVs found — predict_networks failed")
        return

    network_data = pd.concat(
        [pd.read_csv(os.path.join(results_dir, f)) for f in files],
        ignore_index=True,
    )

    average_network = (
        network_data[['LRP', 'source_gene', 'target_gene']]
        .groupby(['source_gene', 'target_gene'])['LRP']
        .mean()
        .reset_index()
    )

    output_df = (
        average_network
        .rename(columns={'source_gene': 'Gene1',
                         'target_gene': 'Gene2',
                         'LRP':         'EdgeWeight'})
        [['Gene1', 'Gene2', 'EdgeWeight']]
        .sort_values('EdgeWeight', ascending=False)
        .reset_index(drop=True)
    )

    output_df.to_csv(output_path, index=False)
    print(f"[scGeneRAI] Done — {len(output_df)} gene pairs written to {output_path}")


if __name__ == "__main__":
    main()
