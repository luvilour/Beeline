import os
import pandas as pd
import scanpy as sc
import numpy as np

from src.DeepSEM_cell_type_specific_GRN_model import celltype_GRN_model


class Opt:
    pass


def build_opt(data_file, net_file, save_dir):
    opt = Opt()

    opt.task = "celltype_GRN"
    opt.setting = "default"

    opt.data_file = data_file
    opt.net_file = net_file   # ⚠️ REQUIRED by DeepSEM
    opt.save_name = save_dir

    # Hyperparameters (reduced for BEELINE speed)
    opt.n_epochs = 100
    opt.beta = 0.01
    opt.alpha = 1
    opt.K1 = 1
    opt.K2 = 2
    opt.n_hidden = 128
    opt.gamma = 0.95
    opt.lr = 1e-4
    opt.lr_step_size = 1
    opt.batch_size = 64
    opt.K = 1

    return opt


def convert_csv_to_h5ad(expr_path, out_path):
    """
    BEELINE gives: genes x cells CSV
    DeepSEM expects: AnnData (cells x genes)
    """
    df = pd.read_csv(expr_path, index_col=0)

    # transpose: genes x cells → cells x genes
    adata = sc.AnnData(df.T)

    adata.write(out_path)


def main():
    expr_path = "/usr/working_dir/ExpressionData.csv"
    output_path = "/usr/working_dir/outFile.txt"
    save_dir = "/usr/working_dir/deepsem_out"

    os.makedirs(save_dir, exist_ok=True)

    # ---- Convert input ----
    h5ad_path = os.path.join(save_dir, "input.h5ad")
    convert_csv_to_h5ad(expr_path, h5ad_path)

    # ---- Dummy network file (REQUIRED) ----
    # DeepSEM crashes if net_file is missing
    expr_df = pd.read_csv(expr_path, index_col=0)
    genes = expr_df.index.tolist()

    net_file = os.path.join(save_dir, "dummy_net.csv")

    dummy_edges = []
    for g in genes[:min(10, len(genes))]:  # small fake TF set
        for g2 in genes[:min(10, len(genes))]:
            if g != g2:
                dummy_edges.append({"Gene1": g, "Gene2": g2})

    pd.DataFrame(dummy_edges).to_csv(net_file, index=False)

    # ---- Run DeepSEM ----
    opt = build_opt(h5ad_path, net_file, save_dir)

    model = celltype_GRN_model(opt)
    model.train_model()

    # ---- Read DeepSEM output ----
    result_path = os.path.join(save_dir, "GRN_inference_result.tsv")

    df = pd.read_csv(result_path, sep="\t")

    # Normalize to BEELINE format
    df = df.rename(columns={
        "Gene1": "Gene1",
        "Gene2": "Gene2",
        "EdgeWeight": "EdgeWeight"
    })

    df["EdgeWeight"] = df["EdgeWeight"].abs()

    df.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
