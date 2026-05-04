import os
import pandas as pd
import scanpy as sc
import numpy as np

from src.DeepSEM_cell_type_non_specific_GRN_model import non_celltype_GRN_model


class Opt:
    pass


def build_opt(data_file, save_dir):
    opt = Opt()

    opt.task = "non_celltype_GRN"
    opt.setting = "default"

    opt.data_file = data_file
    opt.net_file = None
    opt.save_name = save_dir

    opt.n_epochs = 10

    opt.beta = 1
    opt.alpha = 100
    opt.K = 1
    opt.K1 = 1
    opt.K2 = 2
    opt.n_hidden = 128
    opt.gamma = 0.95
    opt.lr = 1e-4
    opt.lr_step_size = 0.99
    opt.batch_size = 64

    return opt


def main():
    expr_path = "/usr/working_dir/ExpressionData.csv"
    output_path = "/usr/working_dir/outFile.txt"
    save_dir = "/usr/working_dir/tmp"

    opt = build_opt(expr_path, save_dir)

    model = non_celltype_GRN_model(opt)
    model.train_model()

    # ---- Read DeepSEM output ----
    result_path = os.path.join(save_dir, "GRN_inference_result.tsv")

    df = pd.read_csv(result_path, sep="\t")

    # Normalize to BEELINE format
    df = df.rename(columns={
        "TF": "Gene1",
        "Target": "Gene2",
        "EdgeWeight": "EdgeWeight"
    })

    df["EdgeWeight"] = df["EdgeWeight"].abs()

    df.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
