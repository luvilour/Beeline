import argparse
import os
import pandas as pd


def select_top_genes(TF_file, gene_ordering_file, top_n, method):
    """
    Select top N genes from GeneOrdering.csv
    """
    if not os.path.exists(gene_ordering_file):
        raise FileNotFoundError(f'Gene ordering file not found: {gene_ordering_file}')

    ordering = pd.read_csv(gene_ordering_file, index_col=0)
    tfs = pd.read_csv(TF_file, index_col=0)

    tfs_genes = tfs.index.tolist()

    if method == 'rank':
        top_genes = ordering.index.tolist()

    elif method == 'variance':
        if 'Variance' not in ordering.columns:
            raise ValueError("Column 'Variance' not found in GeneOrdering.csv")
        top_genes = ordering.sort_values(by=["Variance"]).index.tolist()
    else:
        raise ValueError("method must be 'rank' or 'variance'")

    i = 0
    top_gene_n = []
    for g in top_genes:
        if i == top_n:
            break
        if not g in tfs_genes:
            top_gene_n.append(g)
            i += 1
    top_genes = top_gene_n

    for g in tfs_genes:
        top_genes.append(g)

    print(f'[GT filter] Selected {len(top_genes)} genes (top {top_n}, method={method})')
    return set(top_genes)


def detect_gene_columns(df):
    """
    Detect gene columns in ground truth file
    """
    cols = df.columns.tolist()

    if 'Gene1' in cols and 'Gene2' in cols:
        return 'Gene1', 'Gene2'

    print(f'[GT filter] WARNING: Using first two columns as gene columns: {cols[:2]}')
    return cols[0], cols[1]


def filter_ground_truth(gt_file, gene_set, output_file):
    """
    Filter ground truth to keep only edges between selected genes
    """
    if not os.path.exists(gt_file):
        raise FileNotFoundError(f'Ground truth file not found: {gt_file}')

    gt = pd.read_csv(gt_file)
    g1, g2 = detect_gene_columns(gt)

    initial_edges = len(gt)

    gt_filtered = gt[
        (gt[g1].isin(gene_set)) &
        (gt[g2].isin(gene_set))
    ]

    print(f'[GT filter] Edges: {initial_edges} → {len(gt_filtered)}')

    gt_filtered.to_csv(output_file, index=False)
    print(f'[GT filter] Saved to: {output_file}')


def main():
    parser = argparse.ArgumentParser(
        description='Filter ground truth using top N genes from GeneOrdering.csv'
    )

    parser.add_argument('--gene_ordering_file', required=True,
                        help='Path to GeneOrdering.csv')

    parser.add_argument('--tfs_genes', required=True,
                        help='Path to GeneTFs.csv')

    parser.add_argument('--gt_file', required=True,
                        help='Path to ground truth CSV')

    parser.add_argument('--top_n', type=int, default=500,
                        help='Number of genes to keep')

    parser.add_argument('--method', choices=['rank', 'variance'], default='rank',
                        help='Gene selection method')

    parser.add_argument('--output_file', required=True,
                        help='Output filtered ground truth file')

    args = parser.parse_args()

    gene_set = select_top_genes(
        args.tfs_genes,
        args.gene_ordering_file,
        args.top_n,
        args.method
    )

    filter_ground_truth(
        args.gt_file,
        gene_set,
        args.output_file
    )


if __name__ == '__main__':
    main()
