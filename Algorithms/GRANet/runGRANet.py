import os
import warnings
import random

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.optim import Adam
from torch.optim.lr_scheduler import StepLR
from torch.utils.data import DataLoader
from tqdm import tqdm

from src.Model import GRANet, vae_loss, VAE
from src.Tools import Evaluation, SavaBestModel
from src.preprocessing import scRNADataset, load_data, adj2saprse_tensor, Feature_discretization_data

warnings.filterwarnings(action='ignore', category=FutureWarning)

# ── Reproducibility ──────────────────────────────────────────────────────────
SEED = 40
os.environ['PYTHONHASHSEED'] = str(SEED)
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.enabled = False

# ── Hyperparameters ──────────────────────────────────────────────────────────
LR = 4e-4
EPOCHS = 95
ALPHA = 0.2
BATCH_SIZE = 256
LOOP = False
VAE_EPOCHS = 350
VAE_LR = 0.0005


def build_tf_target_indices(net_df, gene_list):  # net_df may be None
    """
    Return integer index arrays for TFs and target genes
    based on the ground truth network and the expression gene list.
    """
    gene_index = {g: i for i, g in enumerate(gene_list)}

    if net_df is None:
        print("No network file found: using all genes as TFs and targets.")
        all_idx = np.arange(len(gene_list), dtype=np.int64)
        return all_idx, all_idx, gene_list, gene_list

    tfs = sorted(set(net_df['Gene1']) & set(gene_index))
    targets = sorted(set(net_df['Gene2']) & set(gene_index))

    # Fall back to all genes if ground truth has no overlap
    if not tfs:
        tfs = gene_list
    if not targets:
        targets = gene_list

    tf_idx = np.array([gene_index[g] for g in tfs],     dtype=np.int64)
    target_idx = np.array([gene_index[g] for g in targets], dtype=np.int64)
    return tf_idx, target_idx, tfs, targets


def build_edge_dataset(net_df, gene_list, tf_idx, target_idx):
    """
    Build a labelled edge dataset (Gene1_idx, Gene2_idx, label).
    Positive edges come from net_df when available; negatives are sampled to balance.
    If net_df is None, all sampled edges are labelled 0 — the model trains without
    positive supervision but can still learn expression-based embeddings for ranking.
    """
    gene_index = {g: i for i, g in enumerate(gene_list)}
    pos_edges = set()
    rows = []

    if net_df is not None:
        for _, row in net_df.iterrows():
            g1, g2 = row['Gene1'], row['Gene2']
            if g1 in gene_index and g2 in gene_index:
                i, j = gene_index[g1], gene_index[g2]
                pos_edges.add((i, j))
                rows.append([i, j, 1])

    # Sample negatives (balanced with positives, or a fixed budget if no network)
    rng = np.random.default_rng(SEED)
    tf_list = tf_idx.tolist()
    tgt_list = target_idx.tolist()
    n_neg = len(rows) if rows else min(5000, len(tf_list) * len(tgt_list) // 2)
    neg_count = 0
    attempts = 0
    while neg_count < n_neg and attempts < n_neg * 20:
        i = int(rng.choice(tf_list))
        j = int(rng.choice(tgt_list))
        if i != j and (i, j) not in pos_edges:
            rows.append([i, j, 0])
            pos_edges.add((i, j))
            neg_count += 1
        attempts += 1

    return np.array(rows, dtype=np.float32)


def train_vae(vae, data_tensor, epochs=VAE_EPOCHS, lr=VAE_LR):
    optimizer = Adam(vae.parameters(), lr=lr)
    for epoch in range(epochs):
        optimizer.zero_grad()
        reconstructed, mu, logvar = vae(data_tensor)
        loss = vae_loss(reconstructed, data_tensor, mu, logvar)
        loss.backward()
        optimizer.step()
        if (epoch + 1) % 50 == 0:
            print(f'  VAE Epoch [{epoch+1}/{epochs}]  loss: {loss.item():.4f}')


def main():
    expr_path = "/usr/working_dir/ExpressionData.csv"
    net_path = "/usr/working_dir/network.csv"          # Gene1,Gene2 ground truth
    output_path = "/usr/working_dir/outFile.txt"
    model_dir = "/usr/working_dir/model"
    os.makedirs(model_dir, exist_ok=True)

    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

    # ── Load data ────────────────────────────────────────────────────────────
    # ExpressionData.csv: genes × cells  (BEELINE convention)
    data_input = pd.read_csv(expr_path, index_col=0)
    gene_list = data_input.index.tolist()
    n_genes = len(gene_list)

    # network.csv is optional — absent when no refNetwork was provided
    net_df = pd.read_csv(net_path) if os.path.exists(net_path) else None

    # ── Build TF / target index arrays ───────────────────────────────────────
    tf_idx, target_idx, tf_genes, target_genes = build_tf_target_indices(net_df, gene_list)
    tf_tensor = torch.from_numpy(tf_idx)

    # ── Build edge dataset and split ─────────────────────────────────────────
    edge_data = build_edge_dataset(net_df, gene_list, tf_idx, target_idx)

    train_val, test  = train_test_split(edge_data, test_size=0.1,  random_state=SEED, stratify=edge_data[:, -1])
    train,     val   = train_test_split(train_val,  test_size=0.1,  random_state=SEED, stratify=train_val[:, -1])

    # ── Feature preparation ──────────────────────────────────────────────────
    loader = load_data(data_input)
    feature_np = loader.exp_data()                     # cells × genes after transpose inside load_data
    smoothed_np = data_input.rolling(window=3, axis=1, min_periods=1).mean().to_numpy()
    discretized = Feature_discretization_data(data_input, 20)

    feature_tensor = torch.from_numpy(feature_np)
    smoothed_tensor = torch.from_numpy(smoothed_np).to(torch.float32)

    # ── VAE reconstruction ───────────────────────────────────────────────────
    print("Reconstructing expression matrix with VAE...")
    n_cells = feature_tensor.size(1)          # expression dim fed into VAE
    vae = VAE(input_dim=n_cells, hidden_dim=256, latent_dim=n_cells)
    data_raw = torch.tensor(data_input.to_numpy(), dtype=torch.float32)
    train_vae(vae, data_raw)

    with torch.no_grad():
        reconstructed, _, _ = vae(data_raw)
    recon_np = reconstructed.detach().numpy()

    data_feature_np = StandardScaler().fit_transform(recon_np)
    recon_df = pd.DataFrame(recon_np)
    discretized = Feature_discretization_data(recon_df, 20)
    smoothed_np = recon_df.rolling(window=3, axis=1, min_periods=1).mean().to_numpy()

    data_feature = torch.from_numpy(data_feature_np).to(device)
    discretized = discretized.to(device)
    smoothed = torch.from_numpy(smoothed_np).to(torch.float32).to(device)

    # ── Adjacency matrix ─────────────────────────────────────────────────────
    train_dataset = scRNADataset(train, n_genes)
    adj = train_dataset.Adj_Generate(tf_tensor, loop=LOOP)
    adj = adj2saprse_tensor(adj).to(device)

    # ── GRANet model ─────────────────────────────────────────────────────────
    model = GRANet(
        input_dim=data_feature.size(1),
        hidden1_dim=128, hidden2_dim=64, hidden3_dim=32,
        output_dim=16, num_head1=3, alpha=ALPHA, device=device,
    ).to(device)

    optimizer = Adam(model.parameters(), lr=LR)
    scheduler = StepLR(optimizer, step_size=20, gamma=0.99)
    loss_BCE = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(1.0))
    best_model = SavaBestModel(model_dir)

    val_tensor = torch.from_numpy(val).to(device)
    test_tensor = torch.from_numpy(test).to(device)

    print("Training GRANet...")
    metrics = []
    for epoch in range(EPOCHS):
        running_loss = 0.0
        loader_loop = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=False)
        pbar = tqdm(loader_loop, total=len(loader_loop))
        for train_x, train_y in pbar:
            model.train()
            optimizer.zero_grad()
            train_y = train_y.to(device).view(-1, 1)
            pred = model(data_feature, smoothed, discretized, adj, train_x)
            loss = loss_BCE(pred, train_y)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            pbar.set_description(f'Epoch [{epoch+1}/{EPOCHS}] loss:[{running_loss:.3f}]')
        scheduler.step()

        with torch.no_grad():
            model.eval()
            score_val = torch.sigmoid(model(data_feature, smoothed, discretized, adj, val_tensor))
            auroc, auprc = Evaluation(y_pred=score_val, y_true=val_tensor[:, -1])
            metrics.append([auroc, auprc])
            best_model(auroc, auprc, model)

    print(f"Best val AUROC: {np.array(metrics)[:,0].max():.3f}  AUPRC: {np.array(metrics)[:,1].max():.3f}")

    # ── Score ALL TF→target pairs for BEELINE ranked edge list ───────────────
    print("Scoring all TF–target pairs for output...")
    model.load_state_dict(torch.load(os.path.join(model_dir, 'best_model.pkl'), map_location=device))
    model.eval()

    all_pairs = np.array(
        [[ti, tj] for ti in tf_idx for tj in target_idx if ti != tj],
        dtype=np.float32
    )

    rows = []
    chunk = 4096
    with torch.no_grad():
        for start in range(0, len(all_pairs), chunk):
            batch = torch.from_numpy(all_pairs[start:start+chunk]).to(device)
            scores = torch.sigmoid(model(data_feature, smoothed, discretized, adj, batch))
            scores = scores.cpu().numpy().flatten()
            for (ti, tj), s in zip(all_pairs[start:start+chunk], scores):
                rows.append({
                    'Gene1': gene_list[int(ti)],
                    'Gene2': gene_list[int(tj)],
                    'EdgeWeight': float(s),
                })

    out_df = pd.DataFrame(rows, columns=['Gene1', 'Gene2', 'EdgeWeight'])
    out_df.sort_values('EdgeWeight', ascending=False, inplace=True)
    out_df.to_csv(output_path, index=False)
    print(f"Saved {len(out_df)} edges to {output_path}")


if __name__ == "__main__":
    main()
