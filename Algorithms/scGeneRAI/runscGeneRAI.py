import numpy as np
import pandas as pd
import scGeneRAI
import os
import torch

def main():
    expr_path = "/usr/working_dir/ExpressionData.csv"
    output_path = "/usr/working_dir/outFile.txt"

    data_gene_line = pd.read_csv(expr_path, sep=',', index_col=0)
    data = data_gene_line
    data = data.reset_index(drop=True)
    data.index.name = 'cell_id'
    genes = data.columns.tolist()

    print(f"The data are the following {data}")

    # Same parameters as your original main()
    nepochs = 100
    model_depth = 2
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Fit and predict — same as your original code
    model = scGeneRAI.scGeneRAI()
    model.fit(data, nepochs=nepochs, model_depth=model_depth, early_stopping=True, device_name=device)
    model.predict_networks(data, PATH="/usr/working_dir/RESULTS/")

    # Read results — same logic as your original code
    files = os.listdir("/usr/working_dir/RESULTS/results")
    network_data = pd.concat([
        pd.read_csv("/usr/working_dir/RESULTS/results/" + file) for file in files
    ])

    # Same post-processing as your original code
    network_data['LRP'] = np.abs(network_data['LRP'])
    network_data = network_data[network_data['source_gene'] != network_data['target_gene']]
    average_network = (
        network_data[['LRP', 'source_gene', 'target_gene']]
        .groupby(['source_gene', 'target_gene'])
        .mean()
        .reset_index()
    )

    # Rename to BEELINE's required format and write output
    output_df = average_network.rename(columns={
        'source_gene': 'Gene1',
        'target_gene': 'Gene2',
        'LRP':         'EdgeWeight'
    })[['Gene1', 'Gene2', 'EdgeWeight']]

    output_df.to_csv(output_path, index=False)

if __name__ == "__main__":
    main()
