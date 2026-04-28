import numpy as np
import pandas as pd
import scGeneRAI
import os
import torch

def main():
    expr_path = "/usr/working_dir/ExpressionData.csv"
    output_path = "/usr/working_dir/outFile.txt"

    data_gene_line = pd.read_csv(expr_path, sep=',', index_col=0)
    data = data_gene_line.transpose()
    data = data.reset_index(drop=True)
    data.index.name = 'cell_id'
    genes = data.columns.tolist()

    print(f"Shape of expression matrix (cells x genes): {data.shape}.")

    # Split first, normalize after - using train statistics only.
    train_data = data.sample(frac=0.9).copy()
    test_data = data.drop(train_data.index).copy()

    col_min = data.min(axis=0)
    col_max = data.max(axis=0)
    col_range = (col_max - col_min).replace(0, 1)  # avoid division by zero

    train_data = (train_data - col_min) / col_range
    # Clip test data to [0,1] in case it falls outside the training range
    test_data = ((test_data - col_min) / col_range).clip(0, 1)

    nepochs = 1500
    model_depth = 2
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Fit and predict — same as your original code
    model = scGeneRAI.scGeneRAI()
    model.fit(
        train_data,
        nepochs=nepochs,
        model_depth=model_depth,
        early_stopping=True,
        device_name=device,
    )

    results_path = "usr/working_dir/RESULTS/"
    model.predict_networks(train_data, PATH=results_path)

    # Read results — same logic as your original code
    results_dir = os.path.join(results_path, "results")
    files = [f for f in os.listdir(results_dir) if f.endswith(".csv")]

    cell_frames = []
    for file in files:
        df = pd.read_csv(os.path.join(results_dir, file))

        df = df[df['source_gene'] != df['target_gene']]
        cell_frames.append(df)

    network_data = pd.concat(cell_frames, ignore_index=True)

    # Build LRPau per cell: for each (cell, gene_A, gene_B) pair compute the
    # undirected score by averaging the two directed absolute values.
    # Assumes the results files contain a 'cell_id' column (or one file per
    # cell).  Adjust the groupby key if your version uses a different column.
    if 'cell_id' in network_data.columns:
        group_keys = ['cell_id', 'source_gene', 'target_gene']
    else:
        # If there is no cell_id, each file is one cell — add it from filename
        cell_frames2 = []
        for i, f in enumerate(files):
            df = pd.read_csv(os.path.join(results_dir, f))
            df = df[df['source_gene'] != df['target_gene']]
            df['cell_id'] = i
            cell_frames2.append(df)
        network_data = pd.concat(cell_frames2, ignore_index=True)
        group_keys = ['cell_id', 'source_gene', 'target_gene']

    # For every ordered (A→B) entry, find its mirror (B→A) in the same cell
    # and compute LRPau = 0.5*(|LRPr(A→B)| + |LRPr(B→A)|).
    # A safe and vectorised approach: create a canonical unordered pair key,
    # then average abs values within each (cell, unordered_pair).
    network_data['gene_pair'] = network_data.apply(
        lambda r: tuple(sorted([r['source_gene'], r['target_gene']])), axis=1
    )
    network_data['abs_LRP'] = network_data['LRP'].abs()
 
    # LRPau per cell per gene-pair  (averages the two directed abs values)
    lrpau_per_cell = (
        network_data
        .groupby(['cell_id', 'gene_pair'])['abs_LRP']
        .mean()          # mean of |A→B| and |B→A| = LRPau
        .reset_index()
        .rename(columns={'abs_LRP': 'LRPau'})
    )
 
    # Average LRPau across cells (population-level network)
    average_network = (
        lrpau_per_cell
        .groupby('gene_pair')['LRPau']
        .mean()
        .reset_index()
    )
 
    # Expand the tuple back into two gene columns
    average_network[['Gene1', 'Gene2']] = pd.DataFrame(
        average_network['gene_pair'].tolist(), index=average_network.index
    )
    output_df = (
        average_network[['Gene1', 'Gene2', 'LRPau']]
        .rename(columns={'LRPau': 'EdgeWeight'})
        .sort_values('EdgeWeight', ascending=False)
        .reset_index(drop=True)
    )
 
    output_df.to_csv(output_path, index=False)
    print(f"Done. {len(output_df)} undirected gene pairs written to {output_path}")
 
if __name__ == "__main__":
    main()
