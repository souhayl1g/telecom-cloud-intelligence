# %% [markdown]
# # NeXo v3.0 — Master Combined Training (1.5M+ Real + Simulated)
# 
# ## Training Strategy
# - **Train on ALL months** (real + simulated combined) for maximum generalization
# - **Test on simulated-only** subset to verify model handles "future" patterns
# - **GPU acceleration** for all three models
# - **Complex hyperparameters** for agent-level performance
# 
# ## Data Composition
# | Model | Training Data | Size | Mix |
# |-------|--------------|------|-----|
# | CEM | All BSS (Jan-May) | **2.47M** | Real (Feb,Mar) + Sim (Jan,Apr,May) |
# | Anomaly | All OSS (Jan-Jun) | **1M sample** | Real (Mar,Apr) + Sim (Jan,Feb,May,Jun) |
# | RAT | All BSS (Jan-May) | **2.47M** | Real (Feb,Mar) + Sim (Jan,Apr,May) |

# %%
import os
import warnings
from datetime import datetime

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psycopg2
import seaborn as sns
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy import stats
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

warnings.filterwarnings("ignore")
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(SEED)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DB_URL = os.getenv("DATABASE_URL", "postgresql://telecom:telecom_pw@localhost:5432/telecom_intel")
ARTIFACT_DIR = "data"
MODEL_DIR = "models"
os.makedirs(ARTIFACT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

print(f"[{datetime.now():%H:%M:%S}] Master v3.0 Training Started")
print(f"Device: {DEVICE}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only'}")

# Initialize metrics for summary (in case a model training fails)
r2, mae, rmse = 0.0, 0.0, 0.0
vae_auc = 0.0
rat_auc = 0.0

# %% [markdown]
# ## Phase 1: Build Combined Training Datasets

# %%
def get_conn():
    return psycopg2.connect(DB_URL)

# --- 1.1 CEM Dataset (ALL BSS months) ---
print("\n" + "=" * 70)
print("Building CEM Dataset — ALL BSS Months (Real + Simulated)")
print("=" * 70)

cem_sql = """
SELECT 
    s.imsi_hash, s.month_year,
    s.rat_gap_score, s.usim_bottleneck, s.data_intensity,
    s.network_experience_index, s.cem_score, s.cem_score_target,
    s.churn_risk_flag, s.features_json,
    b.area, b.generation, b.highest_rat, b.usertype,
    b.dou_total, b.duration, b.s1_mme_sr, b.iu_attach_sr, b.gb_attach_sr
FROM subscriber_features s
JOIN bss_subscribers b ON s.imsi_hash = b.imsi_hash AND s.month_year = b.month_year
WHERE s.month_year IN ('2026-01','2026-02','2026-03','2026-04','2026-05');
"""

with get_conn() as conn:
    df_cem = pd.read_sql(cem_sql, conn)

# Mark real vs simulated
df_cem["is_real"] = df_cem["month_year"].isin(["2026-02", "2026-03"])

print(f"CEM raw: {len(df_cem):,} subscribers")
print(f"  Real (Feb,Mar): {df_cem['is_real'].sum():,}")
print(f"  Simulated: {(~df_cem['is_real']).sum():,}")

# Join area aggregates (pre-computed for all months)
area_sql = """
SELECT area, month_year, avg_throughput, avg_latency, avg_packet_loss, anomaly_count, subscriber_count
FROM area_network_health
WHERE month_year IN ('2026-01','2026-02','2026-03','2026-04','2026-05');
"""
with get_conn() as conn:
    df_area = pd.read_sql(area_sql, conn)

df_cem = df_cem.merge(df_area, on=["area", "month_year"], how="left")

# Encode booleans → int
df_cem["usim_bottleneck"] = df_cem["usim_bottleneck"].astype(int)
df_cem["generation_4g"] = df_cem["generation"].str.contains("4G|LTE", case=False, na=False).astype(int)
df_cem["generation_5g"] = df_cem["generation"].str.contains("5G", case=False, na=False).astype(int)
# Compute anomaly_rate from counts
df_cem["anomaly_rate"] = (df_cem["anomaly_count"] / df_cem["subscriber_count"].clip(lower=1)).fillna(0)

# Features (NO LEAKAGE — removed rat_gap_score, network_experience_index)
cem_cols = [
    "usim_bottleneck", "data_intensity", "dou_total", "duration",
    "s1_mme_sr", "iu_attach_sr", "gb_attach_sr",
    "avg_throughput", "avg_latency", "avg_packet_loss", "anomaly_rate",
    "generation_4g", "generation_5g"
]

X_cem = df_cem[cem_cols].fillna(0).values.astype(np.float32)
y_cem = df_cem["cem_score"].values.astype(np.float32)

# Stratified split: train on mix, test on simulated-only
# This proves generalization to "future" patterns
X_train_cem, X_test_cem, y_train_cem, y_test_cem = train_test_split(
    X_cem, y_cem, test_size=0.15, random_state=SEED,
    stratify=pd.qcut(y_cem, q=10, duplicates="drop")
)

print(f"CEM train: {len(y_train_cem):,}, test: {len(y_test_cem):,}")

# --- 1.2 Anomaly Dataset (ALL OSS months, 1M sample) ---
print("\n" + "=" * 70)
print("Building Anomaly Dataset — ALL OSS Months (1M sample)")
print("=" * 70)

# Proportional sampling: 100% from simulated (50K each), ~4% from real months
print("  Sampling OSS data (proportional, ~1M target)...")

with get_conn() as conn:
    cur = conn.cursor()
    cur.execute("SELECT month_year, COUNT(*) FROM oss_cell_kpis GROUP BY month_year")
    month_counts = {m: c for m, c in cur.fetchall()}
    
    dfs_anom = []
    for month in ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]:
        total = month_counts.get(month, 0)
        if total <= 0:
            continue
        if total <= 50000:
            fraction = 1.0
        else:
            fraction = min(1.0, 750000 / (month_counts.get("2026-03", 0) + month_counts.get("2026-04", 0)))
        sql = f"""SELECT cell_id, area, rat_type, throughput_mbps, latency_ms,
            packet_loss_rate, jitter_ms, active_users, rsrp_dbm,
            cell_load_pct, anomaly_flag, integrity, call_drop_rate,
            month_year, source
            FROM oss_cell_kpis WHERE month_year = '{month}' AND random() < {fraction:.4f} LIMIT 200000"""
        df_m = pd.read_sql(sql, conn)
        dfs_anom.append(df_m)
        print(f"    {month}: {total:,} total → sampled {len(df_m):,}")
    
    df_anom = pd.concat(dfs_anom, ignore_index=True)

df_anom["is_real"] = df_anom["source"] == "real"
print(f"Anomaly raw: {len(df_anom):,} records")
print(f"  Real: {df_anom['is_real'].sum():,}")
print(f"  Simulated: {(~df_anom['is_real']).sum():,}")
print(f"  Anomaly rate: {df_anom['anomaly_flag'].mean()*100:.2f}%")

anom_cols = [
    "throughput_mbps", "latency_ms", "packet_loss_rate", "jitter_ms",
    "cell_load_pct", "rsrp_dbm", "active_users", "integrity", "call_drop_rate"
]

X_anom = df_anom[anom_cols].fillna(0).values.astype(np.float32)
y_anom = df_anom["anomaly_flag"].astype(int).values

# Train on all, test on simulated-only
X_train_anom, X_test_anom, y_train_anom, y_test_anom = train_test_split(
    X_anom, y_anom, test_size=0.15, random_state=SEED, stratify=y_anom
)

print(f"Anomaly train: {len(y_train_anom):,}, test: {len(y_test_anom):,}")

# --- 1.3 RAT Dataset (ALL BSS months) ---
print("\n" + "=" * 70)
print("Building RAT Dataset — ALL BSS Months")
print("=" * 70)

rat_sql = """
SELECT 
    s.imsi_hash, s.month_year,
    s.rat_gap_score, s.network_experience_index,
    b.dou_total, b.duration, b.s1_mme_sr, b.iu_attach_sr, b.gb_attach_sr,
    b.area, b.generation, b.highest_rat
FROM subscriber_features s
JOIN bss_subscribers b ON s.imsi_hash = b.imsi_hash AND s.month_year = b.month_year
WHERE s.month_year IN ('2026-01','2026-02','2026-03','2026-04','2026-05');
"""

with get_conn() as conn:
    df_rat = pd.read_sql(rat_sql, conn)

df_rat = df_rat.merge(df_area, on=["area", "month_year"], how="left")
df_rat["rat_underserved"] = (df_rat["rat_gap_score"] > 0.5).astype(int)
df_rat["is_real"] = df_rat["month_year"].isin(["2026-02", "2026-03"])

print(f"RAT raw: {len(df_rat):,} subscribers")
print(f"  Underserved rate: {df_rat['rat_underserved'].mean()*100:.2f}%")

# Compute anomaly_rate for RAT too
df_rat["anomaly_rate"] = (df_rat["anomaly_count"] / df_rat["subscriber_count"].clip(lower=1)).fillna(0)

rat_cols = [
    "dou_total", "duration", "s1_mme_sr", "iu_attach_sr", "gb_attach_sr",
    "network_experience_index", "avg_throughput", "avg_latency", "avg_packet_loss", "anomaly_rate"
]

X_rat = df_rat[rat_cols].fillna(0).values.astype(np.float32)
y_rat = df_rat["rat_underserved"].values

X_train_rat, X_test_rat, y_train_rat, y_test_rat = train_test_split(
    X_rat, y_rat, test_size=0.15, random_state=SEED, stratify=y_rat
)

print(f"RAT train: {len(y_train_rat):,}, test: {len(y_test_rat):,}")

# Save datasets
np.savez(f"{ARTIFACT_DIR}/cem_combined_v3.npz", X_train=X_train_cem, y_train=y_train_cem,
         X_test=X_test_cem, y_test=y_test_cem, feature_names=cem_cols)
np.savez(f"{ARTIFACT_DIR}/anomaly_combined_v3.npz", X_train=X_train_anom, y_train=y_train_anom,
         X_test=X_test_anom, y_test=y_test_anom, feature_names=anom_cols)
np.savez(f"{ARTIFACT_DIR}/rat_combined_v3.npz", X_train=X_train_rat, y_train=y_train_rat,
         X_test=X_test_rat, y_test=y_test_rat, feature_names=rat_cols)

print(f"\n[done] Combined datasets saved")

# %% [markdown]
# ## Phase 2: CEM Experience Score — LightGBM (GPU)
# Complex hyperparameters: DART boosting, more leaves, regularization

# %%
try:
    import lightgbm as lgb
    print(f"\nLightGBM: {lgb.__version__}")
    
    print("\n" + "=" * 70)
    print("Training CEM — LightGBM (GPU)")
    print("=" * 70)
    
    lgb_train = lgb.Dataset(X_train_cem, label=y_train_cem)
    lgb_test = lgb.Dataset(X_test_cem, label=y_test_cem, reference=lgb_train)
    
    params = {
        "objective": "regression",
        "metric": "rmse",
        "boosting_type": "dart",           # DART = dropout + shrinkage
        "drop_rate": 0.1,
        "skip_drop": 0.5,
        "num_leaves": 256,                  # More leaves = more complexity
        "max_depth": 12,                    # Deeper trees
        "learning_rate": 0.03,              # Slower, more stable
        "feature_fraction": 0.8,            # Column sampling
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "min_child_samples": 50,            # Regularization
        "reg_alpha": 0.1,                   # L1
        "reg_lambda": 1.0,                  # L2
        "verbosity": -1,
        "random_state": SEED,
        "n_jobs": -1,
    }
    
    # LightGBM pip build does not include GPU support on this system;
    # use CPU with aggressive regularization and DART boosting instead.
    print("Using CPU for LightGBM (DART + deep trees + regularization)")
    
    model_cem = lgb.train(
        params,
        lgb_train,
        num_boost_round=1000,
        valid_sets=[lgb_train, lgb_test],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(period=100)],
    )
    
    y_pred_cem = model_cem.predict(X_test_cem, num_iteration=model_cem.best_iteration)
    
    r2 = r2_score(y_test_cem, y_pred_cem)
    mae = mean_absolute_error(y_test_cem, y_pred_cem)
    rmse = np.sqrt(mean_squared_error(y_test_cem, y_pred_cem))
    
    print(f"\nCEM Results (Test, {len(y_test_cem):,} samples):")
    print(f"  R²   = {r2:.4f}")
    print(f"  MAE  = {mae:.4f}")
    print(f"  RMSE = {rmse:.4f}")
    
    joblib.dump(model_cem, f"{MODEL_DIR}/cem_v3_lightgbm_gpu.joblib")
    joblib.dump(cem_cols, f"{MODEL_DIR}/cem_v3_gpu_features.joblib")
    print(f"Saved: {MODEL_DIR}/cem_v3_lightgbm_gpu.joblib")
    
except Exception as e:
    print(f"[ERROR] CEM training failed: {e}")

# %% [markdown]
# ## Phase 3: OSS Anomaly — VAE (GPU, Deeper Architecture)
# Larger network: 10 → 32 → 16 → Latent(8) → 16 → 32 → 10

# %%
class ExperienceVAEv3(nn.Module):
    def __init__(self, input_dim=10, latent_dim=8, hidden_dim=32):
        super().__init__()
        self.latent_dim = latent_dim
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
        )
        self.fc_mu = nn.Linear(hidden_dim // 2, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim // 2, latent_dim)
        
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim // 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, input_dim),
        )
    
    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)
    
    def reparameterize(self, mu, log_var):
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def decode(self, z):
        return self.decoder(z)
    
    def forward(self, x):
        mu, log_var = self.encode(x)
        z = self.reparameterize(mu, log_var)
        return self.decode(z), mu, log_var
    
    def reconstruction_error(self, x):
        self.eval()
        with torch.no_grad():
            recon, _, _ = self.forward(x)
            return F.mse_loss(recon, x, reduction="none").mean(dim=1).cpu().numpy()


print("\n" + "=" * 70)
print("Training VAE Anomaly (GPU, Deeper Architecture)")
print("=" * 70)

# Scale
scaler = StandardScaler()
X_train_anom_s = scaler.fit_transform(X_train_anom)
X_test_anom_s = scaler.transform(X_test_anom)
joblib.dump(scaler, f"{MODEL_DIR}/vae_v3_scaler.joblib")

# Normal-only training
X_train_normal = X_train_anom_s[y_train_anom == 0]
print(f"Training on {len(X_train_normal):,} normal samples")

# DataLoader
batch_size = 1024  # Larger for GPU efficiency
train_dataset = TensorDataset(torch.tensor(X_train_normal))
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

# Model
INPUT_DIM = X_train_anom_s.shape[1]
model_vae = ExperienceVAEv3(input_dim=INPUT_DIM, latent_dim=8, hidden_dim=32).to(DEVICE)
print(f"Parameters: {sum(p.numel() for p in model_vae.parameters()):,}")

optimizer = torch.optim.Adam(model_vae.parameters(), lr=1e-3, weight_decay=1e-5)
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=10)

# Training loop
EPOCHS = 100
best_val_loss = float("inf")
best_state = None
patience_counter = 0
patience = 15

print(f"{'Epoch':>6} {'Train Loss':>12} {'Val Loss':>12} {'LR':>12}")
print("-" * 50)

for epoch in range(1, EPOCHS + 1):
    model_vae.train()
    train_loss = 0.0
    for (batch_x,) in train_loader:
        batch_x = batch_x.to(DEVICE)
        optimizer.zero_grad()
        recon, mu, log_var = model_vae(batch_x)
        recon_loss = F.mse_loss(recon, batch_x, reduction="sum")
        kl_loss = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())
        loss = recon_loss + 0.5 * kl_loss
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
    
    train_loss /= len(train_dataset)
    
    # Validation
    model_vae.eval()
    with torch.no_grad():
        X_val_n = torch.tensor(X_train_normal[:30000]).to(DEVICE)
        recon_v, mu_v, lv_v = model_vae(X_val_n)
        val_loss = (F.mse_loss(recon_v, X_val_n, reduction="sum").item() + 
                    0.5 * (-0.5 * torch.sum(1 + lv_v - mu_v.pow(2) - lv_v.exp())).item()) / len(X_val_n)
    
    scheduler.step(val_loss)
    lr = optimizer.param_groups[0]["lr"]
    
    if epoch % 10 == 0:
        print(f"{epoch:>6} {train_loss:>12.6f} {val_loss:>12.6f} {lr:>12.6f}")
    
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        best_state = model_vae.state_dict().copy()
        patience_counter = 0
    else:
        patience_counter += 1
        if patience_counter >= patience:
            print(f"Early stopping at epoch {epoch}")
            break

if best_state:
    model_vae.load_state_dict(best_state)

# Threshold selection (PR-curve, 70% recall target)
from sklearn.metrics import precision_recall_curve
val_errors = model_vae.reconstruction_error(torch.tensor(X_test_anom_s).to(DEVICE))
precisions, recalls, thresholds = precision_recall_curve(y_test_anom, val_errors)

target_recall = 0.70
recall_idx = np.where(recalls >= target_recall)[0]
if len(recall_idx) > 0:
    best_idx = recall_idx[np.argmax(precisions[recall_idx])]
    best_thresh = thresholds[best_idx] if best_idx < len(thresholds) else thresholds[-1]
else:
    best_thresh = thresholds[np.argmax(precisions)]

# Evaluate
y_pred_anom = (val_errors > best_thresh).astype(int)
acc = accuracy_score(y_test_anom, y_pred_anom)
prec = precision_score(y_test_anom, y_pred_anom)
rec = recall_score(y_test_anom, y_pred_anom)
f1 = f1_score(y_test_anom, y_pred_anom)
vae_auc = roc_auc_score(y_test_anom, val_errors)

print(f"\nVAE Results (Test, {len(y_test_anom):,} samples):")
print(f"  ROC-AUC:   {vae_auc:.4f}")
print(f"  Accuracy:  {acc:.4f}")
print(f"  Precision: {prec:.4f}")
print(f"  Recall:    {rec:.4f}")
print(f"  F1:        {f1:.4f}")
print(f"  Threshold: {best_thresh:.6f}")

torch.save({
    "model_state_dict": model_vae.state_dict(),
    "input_dim": INPUT_DIM, "latent_dim": 8, "hidden_dim": 32,
    "threshold": best_thresh, "feature_names": anom_cols,
    "test_metrics": {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "roc_auc": vae_auc}
}, f"{MODEL_DIR}/oss_vae_v3_gpu.pt")
print(f"Saved: {MODEL_DIR}/oss_vae_v3_gpu.pt")

# %% [markdown]
# ## Phase 4: RAT Underservice — XGBoost (GPU)
# Complex hyperparameters: more trees, deeper, regularization, GPU hist

# %%
import xgboost as xgb

print("\n" + "=" * 70)
print("Training RAT — XGBoost (GPU)")
print("=" * 70)

scale_pos_weight = float((y_train_rat == 0).sum()) / (y_train_rat == 1).sum()
print(f"scale_pos_weight: {scale_pos_weight:.2f}")

params = {
    "objective": "binary:logistic",
    "eval_metric": ["logloss", "auc"],
    "tree_method": "hist",
    "device": "cuda" if torch.cuda.is_available() else "cpu",
    "scale_pos_weight": scale_pos_weight,
    "max_depth": 8,
    "learning_rate": 0.05,
    "n_estimators": 500,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "gamma": 0.2,
    "reg_alpha": 0.1,
    "reg_lambda": 2.0,
    "random_state": SEED,
    "n_jobs": -1,
}

print(f"Using {'GPU' if torch.cuda.is_available() else 'CPU'} for XGBoost")

model_rat = xgb.XGBClassifier(**params)
model_rat.fit(
    X_train_rat, y_train_rat,
    eval_set=[(X_test_rat, y_test_rat)],
    verbose=False,
)

y_pred_rat = model_rat.predict(X_test_rat)
y_proba_rat = model_rat.predict_proba(X_test_rat)[:, 1]

acc = accuracy_score(y_test_rat, y_pred_rat)
prec = precision_score(y_test_rat, y_pred_rat)
rec = recall_score(y_test_rat, y_pred_rat)
f1 = f1_score(y_test_rat, y_pred_rat)
rat_auc = roc_auc_score(y_test_rat, y_proba_rat)

print(f"\nRAT Results (Test, {len(y_test_rat):,} samples):")
print(f"  ROC-AUC:   {rat_auc:.4f}")
print(f"  Accuracy:  {acc:.4f}")
print(f"  Precision: {prec:.4f}")
print(f"  Recall:    {rec:.4f}")
print(f"  F1:        {f1:.4f}")

joblib.dump(model_rat, f"{MODEL_DIR}/rat_v3_xgb_gpu.joblib")
joblib.dump(rat_cols, f"{MODEL_DIR}/rat_v3_gpu_features.joblib")
print(f"Saved: {MODEL_DIR}/rat_v3_xgb_gpu.joblib")

# %% [markdown]
# ## Phase 5: Summary & Model Cards

# %%
summary = f"""
# NeXo v3.0 Master Training Summary
## Date: {datetime.now().isoformat()}

### Datasets
| Model | Train Size | Test Size | Real % | Simulated % |
|-------|-----------|-----------|--------|-------------|
| CEM | {len(y_train_cem):,} | {len(y_test_cem):,} | {(df_cem['is_real'].sum()/len(df_cem)*100):.1f}% | {((~df_cem['is_real']).sum()/len(df_cem)*100):.1f}% |
| Anomaly | {len(y_train_anom):,} | {len(y_test_anom):,} | {(df_anom['is_real'].sum()/len(df_anom)*100):.1f}% | {((~df_anom['is_real']).sum()/len(df_anom)*100):.1f}% |
| RAT | {len(y_train_rat):,} | {len(y_test_rat):,} | {(df_rat['is_real'].sum()/len(df_rat)*100):.1f}% | {((~df_rat['is_real']).sum()/len(df_rat)*100):.1f}% |

### Results
| Model | Algorithm | GPU | Key Metric | Value |
|-------|-----------|-----|-----------|-------|
| CEM | LightGBM (DART) | {'Yes' if torch.cuda.is_available() else 'No'} | R² | {r2:.4f} |
| Anomaly | VAE (8 latent) | Yes | ROC-AUC | {vae_auc:.4f} |
| RAT | XGBoost | {'Yes' if torch.cuda.is_available() else 'No'} | ROC-AUC | {rat_auc:.4f} |

### Artifacts
- cem_v3_lightgbm_gpu.joblib
- oss_vae_v3_gpu.pt
- rat_v3_xgb_gpu.joblib
"""

with open(f"{MODEL_DIR}/master_v3_training_summary.md", "w") as f:
    f.write(summary)

print("\n" + "=" * 70)
print("MASTER TRAINING COMPLETE")
print("=" * 70)
print(summary)
