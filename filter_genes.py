import argparse
import os
import pandas as pd


def filter_expression_by_top_genes(expression_file, gene_ordering_file, top_n, method, output_file):
    """
    Filter an ExpressionData.csv to keep only the top N most variable genes
    based on a GeneOrdering.csv file.

    method='rank'     -> top N genes by p-value rank (pre-sorted in GeneOrdering.csv)
    method='variance' -> top N genes by variance score
    """
    if not os.path.exists(expression_file):
        raise FileNotFoundError(f'Expression file not found: {expression_file}')
    if not os.path.exists(gene_ordering_file):
        raise FileNotFoundError(f'Gene ordering file not found: {gene_ordering_file}')

    expr = pd.read_csv(expression_file, index_col=0)
    ordering = pd.read_csv(gene_ordering_file, index_col=0)

    if method == 'rank':
        top_genes = ordering.head(top_n).index.tolist()
    elif method == 'variance':
        if 'Variance' not in ordering.columns:
            raise ValueError("Column 'Variance' not found in GeneOrdering.csv")
        top_genes = ordering.nlargest(top_n, 'Variance').index.tolist()
    else:
        raise ValueError("method must be 'rank' or 'variance'")

    genes_to_keep = [g for g in top_genes if g in expr.index]
    missing = top_n - len(genes_to_keep)

    print(f'[filter_genes] Dataset : {os.path.dirname(expression_file) or "."}')
    print(f'[filter_genes] Requested: {top_n} | Found: {len(genes_to_keep)} | Missing: {missing}')

    expr_filtered = expr.loc[genes_to_keep]
    expr_filtered.to_csv(output_file)
    print(f'[filter_genes] Saved filtered expression to: {output_file}')

    return expr_filtered


def process_dataset_folder(folder, top_n, method):
    """
    Process a single dataset folder containing ExpressionData.csv and GeneOrdering.csv.
    Writes ExpressionData_filtered.csv in the same folder.
    """
    output_folder = folder + "_filtered"
    try:
        os.mkdir(output_folder)
    except:
        print(f"The directory {output_folder} already exists")

    expression_file  = os.path.join(folder, 'ExpressionData.csv')
    gene_ordering_file = os.path.join(folder, 'GeneOrdering.csv')
    output_file      = os.path.join(output_folder, 'ExpressionData.csv')

    if not os.path.exists(expression_file):
        print(f'[filter_genes] WARNING: No ExpressionData.csv in {folder}, skipping.')
        return
    if not os.path.exists(gene_ordering_file):
        print(f'[filter_genes] WARNING: No GeneOrdering.csv in {folder}, skipping.')
        return

    filter_expression_by_top_genes(expression_file, gene_ordering_file, top_n, method, output_file)


def main():
    parser = argparse.ArgumentParser(
        description='Filter ExpressionData.csv to top N most variable genes using GeneOrdering.csv'
    )
    parser.add_argument(
        '--input_dir', type=str, required=True,
        help='Root input directory. Every subfolder containing ExpressionData.csv + GeneOrdering.csv will be processed.'
    )
    parser.add_argument(
        '--top_n', type=int, default=500,
        help='Number of top genes to keep (default: 500)'
    )
    parser.add_argument(
        '--method', type=str, default='rank', choices=['rank', 'variance'],
        help="Selection method: 'rank' uses p-value order (default), 'variance' uses variance score"
    )
    opt = parser.parse_args()

    # Collect all dataset folders (any subfolder with both required files)
    dataset_folders = []
    for root, dirs, files in os.walk(opt.input_dir):
        if 'ExpressionData.csv' in files and 'GeneOrdering.csv' in files:
            dataset_folders.append(root)

    if not dataset_folders:
        print(f'[filter_genes] No datasets found under {opt.input_dir}')
        return

    print(f'[filter_genes] Found {len(dataset_folders)} dataset(s) to process.')
    for folder in sorted(dataset_folders):
        process_dataset_folder(folder, opt.top_n, opt.method)

    print('[filter_genes] Done.')


if __name__ == '__main__':
    main()
