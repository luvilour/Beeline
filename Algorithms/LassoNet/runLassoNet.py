import numpy as np
import pandas as pd
from lassonet import LassoNetRegressor
import torch
import argparse

def importances_filling(importances, expr_df, gene_being_regressed):
    # Replaces your Helper.make_X_y_from_tsv call
    # expr_df is the full expression matrix (genes x cells)
    genes = expr_df.index.tolist()
    n_genes = len(genes)

    # Build X (all genes except the one being regressed) and y (target gene)
    target_gene = genes[gene_being_regressed - 1]
    other_genes = [g for g in genes if g != target_gene]

    X_train = expr_df.loc[other_genes].T.to_numpy()
    y_train = expr_df.loc[target_gene].to_numpy()

    model = LassoNetRegressor(hidden_dims=(5, 5))
    oracle, order, wrong, paths, prob = model.stability_selection(X_train, y_train)

    probs = torch.sum(prob, dim1)/prob.shape[0]

    cnt = order.size(dim=0)
    
    '''
    Method by dividing the sum of the mean to every values
    '''

    sum_of_mean = torch.sum(probs)
    probs = probs/sum_of_mean

    i = 0
    for cnt in range(importances.shape[1]):
        if cnt == gene_being_regressed - 1:
            importances[gene_being_regressed-1][cnt] = -200
        else:
            importances[gene_being_regressed-1][cnt] = probs[i]

            i += 1

    return importances


def main():
    # Input/output paths are fixed to the Docker mounted volume
    expr_path = "/usr/working_dir/ExpressionData.csv"
    output_path = "/usr/working_dir/outFile.txt"

    expr_df = pd.read_csv(expr_path, index_col=0)
    n_genes = expr_df.shape[0]
    genes = expr_df.index.tolist()

    importances = np.zeros((n_genes, n_genes))

    for i in range(1, n_genes + 1):
        importances = importances_filling(importances, expr_df, i)

    # Convert importance matrix to ranked edge list
    # This replaces your aupr_roc/adjacency matrix logic — BEELINE handles eval
    rows = []
    for i, g1 in enumerate(genes):
        for j, g2 in enumerate(genes):
            if i != j and importances[i][j] != -200:
                rows.append({'Gene1': g1, 'Gene2': g2, 'EdgeWeight': importances[i][j]})

    output_df = pd.DataFrame(rows, columns=['Gene1', 'Gene2', 'EdgeWeight'])
    output_df.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
