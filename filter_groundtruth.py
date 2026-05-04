import argparse
import os
import pandas as pd


def load_gene_list(gene_file, from_expression=False):
    """
    Load list of genes either from:
    - ExpressionData.csv (rows = genes)
    - Simple text file (1 gene per line)
    """
    if not os.path.exists(gene_file):
        raise FileNotFoundError(f'Gene file not found: {gene_file}')

    if from_expression:
        df = pd.read_csv(gene_file, index_col=0)
        genes = df.index.tolist()
    else:
        with open(gene_file, 'r') as f:
            genes = [line.strip() for line in f if line.strip()]

    print(f'[GT filter] Loaded {len(genes)} genes')
    return set(genes)


def detect_gene_columns(df):
    """
    Detect gene columns in ground truth
    """
    cols = df.columns.tolist()

    if 'Gene1' in cols and 'Gene2' in cols:
        return 'Gene1', 'Gene2'

    # fallback: assume first two columns
    print(f'[GT filter] WARNING: Using first two columns as gene columns: {cols[:2]}')
    return cols[0], cols[1]


def filter_ground_truth(gt_file, gene_set, output_file):
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
    parser = argparse.ArgumentParser(description='Filter ground truth network by gene list')

    parser.add_argument(
        '--gt_file', required=True,
        help='Path to ground truth network CSV'
    )

    parser.add_argument(
        '--gene_file', required=True,
        help='Path to gene list OR ExpressionData.csv'
    )

    parser.add_argument(
        '--from_expression', action='store_true',
        help='Set if gene_file is an ExpressionData.csv'
    )

    parser.add_argument(
        '--output_file', required=True,
        help='Output filtered ground truth file'
    )

    args = parser.parse_args()

    gene_set = load_gene_list(args.gene_file, args.from_expression)
    filter_ground_truth(args.gt_file, gene_set, args.output_file)


if __name__ == '__main__':
    main()
