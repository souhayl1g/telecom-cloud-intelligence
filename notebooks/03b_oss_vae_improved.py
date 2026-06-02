"""
OSS VAE Anomaly Detection — IMPROVED training (v3.1).

Targets a lift from F1=0.49 -> F1>=0.65 by:
  1. Deeper architecture (10->64->32->Latent(12)->32->64->10)    was: 10->16->8->Latent(4)->8->16->10
  2. RobustScaler instead of StandardScaler                       (telecom KPIs are heavy-tailed)
  3. KL annealing: beta linearly 0->1 across first 30 epochs      (improves reconstruction)
  4. More training: 200 epochs max, patience=20                   (was: 50, patience=10)
  5. Bigger batch (1024)                                          (was: 512)
  6. F1-optimal threshold via percentile sweep                    (more numerically stable)
  7. LayerNorm + GELU activations                                 (was: plain ReLU)
  8. Cosine annealing LR schedule + AdamW + grad clip

Run from notebooks/ directory:
    python 03b_oss_vae_improved.py

Outputs:
    models/oss_vae_v3_1.pt
    models/vae_scaler_v3_1.joblib
    data/vae_v3_1_evaluation.png
"""
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score, roc_curve,
)
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

warnings.filterwarnings("ignore")
sns.set_style("whitegrid")

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(SEED)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
NB_DIR = Path(__file__).parent
ARTIFACT_DIR = NB_DIR / "data"
MODEL_DIR = NB_DIR / "models"
ARTIFACT_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

print(f"[{datetime.now():%H:%M:%S}] VAE v3.1 Improved Training")
print(f"PyTorch: {torch.__version__}, Device: {DEVICE}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")


# 1. Load data
data = np.load(ARTIFACT_DIR / "anomaly_training_mar2026.npz", allow_pickle=True)
X = data["X"].astype(np.float32)
y = data["y"].astype(np.int64)
feature_names = list(data["feature_names"])
print(f"\nDataset: X={X.shape}, anomaly rate={y.mean()*100:.2f}%, features={len(feature_names)}")

# 2. Stratified split
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.30, random_state=SEED, stratify=y)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.50, random_state=SEED, stratify=y_temp)
print(f"Train: {len(y_train):,}  Val: {len(y_val):,}  Test: {len(y_test):,}")

# 3. RobustScaler (resists telecom outliers)
scaler = RobustScaler()
X_train_s = scaler.fit_transform(X_train).astype(np.float32)
X_val_s = scaler.transform(X_val).astype(np.float32)
X_test_s = scaler.transform(X_test).astype(np.float32)
joblib.dump(scaler, MODEL_DIR / "vae_scaler_v3_1.joblib")


# 4. Deeper VAE architecture
class ExperienceVAE(nn.Module):
    def __init__(self, input_dim, latent_dim=12, hidden_dim=64):
        super().__init__()
        self.latent_dim = latent_dim
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim // 2), nn.LayerNorm(hidden_dim // 2), nn.GELU(),
        )
        self.fc_mu = nn.Linear(hidden_dim // 2, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim // 2, latent_dim)
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim // 2), nn.LayerNorm(hidden_dim // 2), nn.GELU(),
            nn.Linear(hidden_dim // 2, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, log_var):
        std = torch.exp(0.5 * log_var)
        return mu + torch.randn_like(std) * std

    def forward(self, x):
        mu, log_var = self.encode(x)
        z = self.reparameterize(mu, log_var)
        return self.decoder(z), mu, log_var

    def reconstruction_error(self, x):
        self.train(False)  # inference mode
        with torch.no_grad():
            recon, _, _ = self.forward(x)
            return F.mse_loss(recon, x, reduction="none").mean(dim=1).cpu().numpy()


INPUT_DIM = X_train_s.shape[1]
LATENT_DIM = 12
HIDDEN_DIM = 64
model = ExperienceVAE(INPUT_DIM, LATENT_DIM, HIDDEN_DIM).to(DEVICE)
print(f"\nArch: {INPUT_DIM} -> {HIDDEN_DIM} -> {HIDDEN_DIM//2} -> Latent({LATENT_DIM}) -> ...")
print(f"Params: {sum(p.numel() for p in model.parameters()):,}")


# 5. KL-annealed training
def vae_loss(recon, x, mu, log_var, beta):
    rec = F.mse_loss(recon, x, reduction="sum")
    kl = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())
    return rec + beta * kl


X_train_normal = X_train_s[y_train == 0]
BATCH_SIZE = 1024
EPOCHS = 200
KL_ANNEAL = 30
PATIENCE = 20

train_loader = DataLoader(
    TensorDataset(torch.tensor(X_train_normal)),
    batch_size=BATCH_SIZE, shuffle=True, num_workers=0,
)

optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-6)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-5)

best_val = float("inf")
best_state = None
patience_ctr = 0

print(f"\n{'Epoch':>6} {'Beta':>6} {'Train':>12} {'Val':>12} {'LR':>10}")
print("-" * 55)

for epoch in range(1, EPOCHS + 1):
    beta = min(1.0, epoch / KL_ANNEAL)
    model.train(True)
    total = 0.0
    for (xb,) in train_loader:
        xb = xb.to(DEVICE)
        optimizer.zero_grad()
        recon, mu, lv = model(xb)
        loss = vae_loss(recon, xb, mu, lv, beta)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        total += loss.item()
    train_loss = total / len(X_train_normal)

    model.train(False)
    with torch.no_grad():
        Xvn = torch.tensor(X_val_s[y_val == 0]).to(DEVICE)
        rv, mv, lvv = model(Xvn)
        val_loss = vae_loss(rv, Xvn, mv, lvv, beta).item() / len(Xvn)

    scheduler.step()
    lr = optimizer.param_groups[0]["lr"]
    if epoch <= 5 or epoch % 5 == 0:
        print(f"{epoch:>6} {beta:>6.3f} {train_loss:>12.6f} {val_loss:>12.6f} {lr:>10.6f}")

    if val_loss < best_val:
        best_val = val_loss
        best_state = {k: v.clone() for k, v in model.state_dict().items()}
        patience_ctr = 0
    else:
        patience_ctr += 1
        if patience_ctr >= PATIENCE:
            print(f"Early stop @ epoch {epoch}")
            break

model.load_state_dict(best_state)
print(f"\nBest val loss: {best_val:.6f}")


# 6. Threshold via percentile sweep
val_errors = model.reconstruction_error(torch.tensor(X_val_s).to(DEVICE))
best_f1 = 0.0
best_thresh = float(np.median(val_errors))
for p in np.linspace(50, 99.9, 500):
    t = float(np.percentile(val_errors, p))
    preds = (val_errors > t).astype(int)
    f = f1_score(y_val, preds)
    if f > best_f1:
        best_f1 = f
        best_thresh = t
print(f"\nOptimal threshold: {best_thresh:.6f}  (val F1 = {best_f1:.4f})")


# 7. Test evaluation
test_errors = model.reconstruction_error(torch.tensor(X_test_s).to(DEVICE))
y_pred = (test_errors > best_thresh).astype(int)
acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred)
rec = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
auc = roc_auc_score(y_test, test_errors)

print("\n" + "=" * 60)
print(f"VAE v3.1 - TEST METRICS")
print("=" * 60)
print(f"  Accuracy:  {acc:.4f}")
print(f"  Precision: {prec:.4f}")
print(f"  Recall:    {rec:.4f}")
print(f"  F1:        {f1:.4f}    (was 0.4901 v3.0)")
print(f"  ROC-AUC:   {auc:.4f}    (was 0.9307 v3.0)")
print("=" * 60)
print(classification_report(y_test, y_pred, target_names=["Normal", "Anomaly"]))


# 8. Save plots + model
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=axes[0],
            xticklabels=["Normal", "Anomaly"], yticklabels=["Normal", "Anomaly"])
axes[0].set_title(f"VAE v3.1  -  F1={f1:.4f}")
fpr, tpr, _ = roc_curve(y_test, test_errors)
axes[1].plot(fpr, tpr, color="steelblue", lw=2, label=f"AUC = {auc:.4f}")
axes[1].plot([0, 1], [0, 1], "r--", lw=1)
axes[1].set_xlabel("FPR"); axes[1].set_ylabel("TPR"); axes[1].set_title("ROC")
axes[1].legend(); axes[1].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(ARTIFACT_DIR / "vae_v3_1_evaluation.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\nSaved: {ARTIFACT_DIR / 'vae_v3_1_evaluation.png'}")

torch.save({
    "model_state_dict": model.state_dict(),
    "input_dim": INPUT_DIM,
    "latent_dim": LATENT_DIM,
    "hidden_dim": HIDDEN_DIM,
    "threshold": best_thresh,
    "scaler_path": str(MODEL_DIR / "vae_scaler_v3_1.joblib"),
    "feature_names": feature_names,
    "test_metrics": {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "roc_auc": auc},
    "version": "v3.1",
}, MODEL_DIR / "oss_vae_v3_1.pt")
print(f"Saved: {MODEL_DIR / 'oss_vae_v3_1.pt'}")
print(f"\n[{datetime.now():%H:%M:%S}] Done.")
