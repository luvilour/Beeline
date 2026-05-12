import numpy as np 
from pytorch_tabnet.tab_model import TabNetRegressor
import torch
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split


def importances_filling(importances, expr_df, gene_being_regressed):
    genes = expr_df.index.tolist()
    n_genes = len(genes)

    target_gene = genes[gene_being_regressed - 1]
    other_genes = [g for g in genes if g != target_gene]

    X = expr_df.loc[other_genes].T.to_numpy()
    y = expr_df.loc[target_gene].to_numpy().reshape(-1, 1)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2
    )

    min_cells = int(0.2 * X_train.shape[0])
    expressed_mask = (X_train != 0).sum(axis=0) >= min_cells
    X_train = X_train[:, expressed_mask]
    expressed_genes = [g for g, keep in zip(other_genes, expressed_mask) if keep]

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0)
    X_test = scaler.transform(X_test)
    X_test = np.nan_to_num(X_test, nan=0.0, posinf=0.0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TabNetRegressor(
        device_name=device,
        lambda_sparse=1e-3,
        n_d=8,
        n_a=8,
        n_steps=10,
    )
    try:
        model.fit(
            X_train=X_train,
            y_train=y_train,
            eval_set=[(X_train, y_train), (X_test, y_test)],
            eval_name=['train', 'test'],

            eval_metric=['rmsle', 'mae', 'rmse', 'mse'],
            patience=100,
            batch_size=1024,
            virtual_batch_size=128,
            num_workers=0,
            drop_last=False,
        )
    except (AssertionError, RuntimeError, ValueError) as e:
        print(f"Skipping gene {target_gene} (index {gene_being_regressed}): {e}")
        return importances

    importances_map = {g: model.feature_importances_[i].item() for i, g in enumerate(expressed_genes)}

    for cnt in range(importances.shape[1]):
        if cnt == gene_being_regressed - 1:
            importances[gene_being_regressed-1][cnt] = -200
        else:
            g = genes[cnt]
            importances[gene_being_regressed-1][cnt] = importances_map.get(g, 0.0)

    return importances


def main():
    expr_path = "usr/working_dir/ExpressionData.csv"
    output_path = "/usr/working_dir/outFile.txt"

    expr_df = pd.read_csv(expr_path, index_col=0)

    n_genes = expr_df.shape[0]
    genes = expr_df.index.tolist()

    importances = np.zeros((n_genes, n_genes))

    for i in range(1, n_genes + 1):
        importances = importances_filling(importances, expr_df, i)

    rows = []
    for i, g1 in enumerate(genes):
        for j, g2 in enumerate(genes):
            if i != j and importances[i][j] != -200:
                rows.append({'Gene1': g1, 'Gene2': g2, 'EdgeWeight': importances[i][j]})

    output_df = pd.DataFrame(rows, columns=['Gene1', 'Gene2', 'EdgeWeight'])
    output_df.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
