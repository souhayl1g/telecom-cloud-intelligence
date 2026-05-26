# NeXoligence Notebooks — Complete Guide

> Last updated: 2026-05-12

## Overview

These notebooks form the **ML training, evaluation, and data engineering pipeline** for the Telecom NeXoligence platform. They process real Tunisie Telecom OSS/CEM data, engineer features, train 3 production ML models, perform temporal causality analysis, and audit data quality.

**All notebooks are `.ipynb` format** (run in Jupyter). Legacy `.py` scripts have been converted.

---

## Prerequisites

Before running any notebook, ensure:

1. **Docker stack is running:**
   ```bash
   make start-NeXo
   ```

2. **Real TT data is ingested** (one-time, persists across restarts):
   ```bash
   make ensure-data
   ```
   - If tables are empty, this auto-runs `ingest_bss.py` + `ingest_oss_real.py` + `compute_features.py`
   - Data survives `make stop` and `make restart`
   - **Data is ONLY lost if you run `make nuke` or `make db-reset`**

3. **Jupyter is accessible:**
   ```bash
   make jupyter-token
   # or open http://localhost:8888
   ```

---

## Notebook Run Order

Run them **in this exact order**. Each phase depends on the previous one.

### Phase 0: Data Quality Audit (run once)

| # | File | When to run | Purpose | Outputs |
|---|------|-------------|---------|---------|
| **00** | `00_data_understanding_eda.ipynb` | **Once**, after first data ingestion | CRISP-DM Phase 2 evidence: inventory, missingness, distributions, outliers, correlations, corruption, imbalance, drift, generator validation, conclusions | `data/eda/*.png`, `data/eda/summary.json`, `data/eda/conclusions.md` |

**What it does:**
- Samples 200K rows each from `bss_subscribers`, `oss_cell_kpis`, `subscriber_features`
- Builds the documented evidence reviewers asked for: cleaning rigor, distributions, correlations, corrupted-row report, generator-engine validation against real data
- Safe to re-run anytime (read-only against DB)

---

### Phase 1: Feature Engineering (run once per retraining cycle)

| # | File | When to run | Purpose | Outputs |
|---|------|-------------|---------|---------|
| **01** | `01_etl_feature_engineering.ipynb` | **Once**, before model training, or after schema changes | Real-data ETL + feature engineering. Derives missing OSS fields, builds subscriber-level features, constructs area-level aggregates | `data/*.npz` training matrices |

**What it does:**
- Loads real BSS subscribers and real OSS cell KPIs
- Computes `subscriber_features`: `rat_gap_score`, `usim_bottleneck`, `data_intensity`, `network_experience_index`, `cem_score`
- Joins OSS per-area with BSS subscriber density → `area_network_health`

---

### Phase 2: Individual Model Training (run each when tuning)

| # | File | When to run | Model Trained | Algorithm | Data Used |
|---|------|-------------|---------------|-----------|-----------|
| **02** | `02_cem_score_training.ipynb` | When retraining CEM model | **CEM Experience Score v3.0** | LightGBM (DART) vs GBR baseline | `data/cem_training_*.npz` |
| **03** | `03_oss_vae_anomaly_training.ipynb` | When retraining anomaly model | **OSS Anomaly Detection v3.0** | PyTorch VAE | `data/anomaly_training_*.npz` |
| **04** | `04_rat_underservice_training.ipynb` | When retraining RAT model | **RAT Underservice v3.0** | XGBoost (GPU) vs baseline | `data/rat_underservice_*.npz` |

**Notebook 02 — CEM Score Training:**
- Compares GBR baseline vs LightGBM with hyperparameter tuning
- LightGBM wins with R² = 0.9933, MAE = 0.0129
- SHAP explainability analysis
- Saves: `models/cem_v3_lightgbm_gpu.joblib`

**Notebook 03 — OSS VAE Anomaly Training:**
- Trains on normal-only data (anomaly_flag == 0)
- Architecture: 9→32→16→8 latent→16→32→9
- Threshold selected via PR-curve targeting 70% recall
- Performance: ROC-AUC = 0.9307, Accuracy = 0.9574
- Saves: `models/oss_vae_v3_gpu.pt`, `models/vae_v3_scaler.joblib`

**Notebook 04 — RAT Underservice Training:**
- Compares baseline vs tuned XGBoost with RandomizedSearchCV
- Tuned model wins with ROC-AUC = 0.9605
- Feature importances: `dou_total` (0.52), `network_experience_index` (0.35)
- Saves: `models/rat_v3_xgb_gpu.joblib`

---

### Phase 3: Temporal Causality Analysis (run once, or when adding months)

| # | File | When to run | Purpose | Data |
|---|------|-------------|---------|------|
| **10** | `10_granger_feature_selection.ipynb` | **Once** after `area_network_health` has >=4 months | **OSS↔CEM Granger causality** — tests temporal causal relationships | `area_network_health` |

**What it does:**
- Tests 8 candidate pairs across all areas with >=4 months of data
- Uses lagged Pearson correlation (statsmodels Granger F-test)
- Produces `granger_feature_gate.json` — consumed by retraining notebooks
- Tier 1 (offline gate) of the 2-tier Granger design

**Why we expanded to 9 months:**
- Statsmodels Granger test requires minimum N=8 time points
- Expanded to 9 months (Jan-Sep) for stronger statistical power

---

## How the 2-Tier Granger Design Works

The Granger F-test answers: *do past values of X help predict Y beyond Y's own past?*
It needs enough time points (statsmodels minimum N=8). Running it on every 2-min pipeline cycle is wasteful + statistically meaningless. So the system splits causality work into two tiers:

### Tier 1 — Offline Gate (Notebook 10)

- Runs once per data refresh (when a new month lands in `area_network_health`).
- Exhaustive F-tests across 8 candidate `(OSS metric, CEM metric)` pairs for every area with ≥4 months.
- Writes `granger_feature_gate.json` — the **approved feature list** with `(lag, p-value, pass/fail)` per area.
- Mirror copy at `services/ai-service/models/granger_gate.json` so the inference service can read it without crossing filesystem boundaries.

**Consumption contract:** Notebooks 02 / 03 / 04 read the gate file BEFORE training, drop features that failed Granger (p ≥ 0.05), then train. Prevents spurious "predictive" features from poisoning models.

### Tier 2 — Online Lead-Time (API)

- Endpoint: `GET /granger-causality/lead-time?area=X` (api-gateway router).
- At query time, computes lagged correlation on a sliding `LAG_WINDOW_MINUTES` buffer for already-gated features.
- Cheap, real-time, surface-able in the dashboard's `<LeadTimeHistogram />` component on `/granger-causality`.
- Operates **only on Tier-1-approved features** — never re-runs the F-test live.

### Why Two Tiers (Decision Rationale)

| Concern | Tier 1 (offline) | Tier 2 (online) |
|---|---|---|
| Statistical rigor | F-test with proper N | N/A (uses approved set) |
| Latency tolerance | Minutes (notebook) | <100ms |
| Frequency | Per data refresh (monthly) | Per dashboard query |
| Cost | One-off compute | Sliding window only |

---

## How Each Model Is Trained

Each model has its own notebook (02/03/04) and produces a self-contained artifact reloaded by `ai-service` on `POST /models/reload`.

| Model | Input NPZ | Algorithm | Key Hyperparameters | Output | Reloaded by |
|---|---|---|---|---|---|
| **CEM Score** | `cem_training_*.npz` (13 features, 500K-2.47M rows) | LightGBM DART | 1000 rounds, 256 leaves, depth=12, learning_rate tuned via Optuna | `cem_v3_lightgbm_gpu.joblib` | `/infer/cem` |
| **OSS VAE Anomaly** | `anomaly_training_*.npz` (10 features, normal-only) | PyTorch VAE | 9→32→16→Latent(8)→16→32→9, threshold via PR-curve at 70% recall | `oss_vae_v3_gpu.pt` + `vae_v3_scaler.joblib` | `/infer/vae-anomaly` |
| **RAT Underservice** | `rat_underservice_*.npz` (10 features, 2.47M rows) | XGBoost GPU | 500 trees, depth=8, `scale_pos_weight=9.87` (9.2% class imbalance) | `rat_v3_xgb_gpu.joblib` | `/infer/rat-underservice` |

**Training contract (all three models):**
1. Load NPZ from notebook 01 output.
2. Read `granger_gate.json` — drop features marked `pass: false`.
3. Train/validation/test split (70/15/15, stratified by area).
4. Hyperparameter tuning where applicable (RandomizedSearchCV / Optuna).
5. SHAP analysis on 2K subset for explainability.
6. Save model + scaler + feature names + model card (`*_model_card.md`).
7. Notebook commits artifact to `notebooks/models/` (also mounted into `services/ai-service/models/` volume via compose).

**Hot-reload path:** L4 agent playbook `pb-model-retrain` POSTs to `ai-service:8001/models/reload`, which `joblib.load` / `torch.load` from disk — no service restart needed.

---

## Data Flow

```
Notebook 00 (Audit)
    └──→ reads postgres directly → EDA plots + summary.json

Notebook 01 (ETL)
    ├──→ data/cem_training_*.npz ──→ Notebook 02 ──→ models/cem_v3_*.joblib
    ├──→ data/anomaly_training_*.npz ──→ Notebook 03 ──→ models/oss_vae_v3*.pt
    └──→ data/rat_underservice_*.npz ──→ Notebook 04 ──→ models/rat_v3_*.joblib

Notebook 10 (Granger Gate)
    └──→ queries area_network_health → granger_feature_gate.json + ai-service/models/granger_gate.json
```

---

## Model Files (`notebooks/models/`)

### v3.0 Production Models (real data, GPU-trained)

| File | Size | Algorithm | Used By |
|------|------|-----------|---------|
| `cem_v3_lightgbm_gpu.joblib` | 18.6 MB | LightGBM DART, 1000 rounds | `/infer/cem` (v3.0) |
| `oss_vae_v3_gpu.pt` | 14.8 KB | PyTorch VAE (9→32→16→8 latent) | `/infer/vae-anomaly` (v3.0) |
| `rat_v3_xgb_gpu.joblib` | 4.2 MB | XGBoost GPU, tuned | `/infer/rat-underservice` (v3.0) |
| `vae_v3_scaler.joblib` | 815 B | StandardScaler | VAE preprocessing |
| `cem_v3_gpu_features.joblib` | 212 B | Feature name list | CEM feature validation |
| `rat_v3_gpu_features.joblib` | 172 B | Feature name list | RAT feature validation |
| `granger_gate.json` | ~2 KB | Granger feature gate | Notebook 02/03/04 feature selection |

### Archived/Baseline Models

| File | Size | Algorithm | Notes |
|------|------|-----------|-------|
| `cem_v3_gbr_baseline.joblib` | 679 KB | GradientBoostingRegressor | Notebook 02 baseline |
| `cem_v3_lightgbm.joblib` | 917 KB | LightGBM CPU | Notebook 02 winning model (older) |
| `cem_v3_feature_names.joblib` | 1.2 KB | Feature names | 13 CEM features |
| `oss_vae_v3.pt` | 10.2 KB | PyTorch VAE (original) | Notebook 03 original |
| `vae_scaler.joblib` | 855 B | StandardScaler | Notebook 03 scaler |
| `rat_underservice_v3_xgb.joblib` | 256 KB | XGBClassifier baseline | Notebook 04 baseline |

---

## Training Artifacts (`notebooks/data/`)

| File | Size | Description |
|------|------|-------------|
| `cem_training_mar2026.npz` | 56 MB | Notebook 01 CEM arrays (500K, 13 features) |
| `anomaly_training_mar2026.npz` | 17.6 MB | Notebook 01 anomaly arrays (200K, 10 features) |
| `rat_underservice_mar2026.npz` | 40 MB | Notebook 01 RAT arrays (500K, 10 features) |
| `cem_combined_v3.npz` | 138 MB | Master CEM training arrays (2.47M subscribers) |
| `anomaly_combined_v3.npz` | 22 MB | Master anomaly training arrays (500K records) |
| `rat_combined_v3.npz` | 118 MB | Master RAT training arrays (2.47M subscribers) |
| `*.png` | various | Evaluation plots (SHAP, confusion matrices, PR curves, etc.) |

---

## Model Cards

- `cem_v3_model_card.md` — Full model card for CEM LightGBM
- `oss_vae_v3_model_card.md` — Full model card for VAE
- `rat_underservice_v3_model_card.md` — Full model card for RAT XGBoost
- `master_v3_training_summary.md` — Aggregated summary of all 3 master models

---

## Quick Commands

```bash
# Start everything
make start-NeXo

# Ensure data is present (safe to run anytime)
make ensure-data

# Get Jupyter token
make jupyter-token

# If you ever need to re-ingest everything (DESTROYS existing data first)
make db-reset && make ingest-data

# Nuclear option: wipe EVERYTHING including DB data
make nuke
```

---

## Data Persistence Cheat Sheet

| Command | Containers | Data volumes | When to use |
|---------|-----------|--------------|-------------|
| `make stop` | Stopped | **Preserved** | Daily shutdown |
| `make restart` | Restarted | **Preserved** | Refresh after config change |
| `make clean` | Removed | **Preserved** | Clean slate, keep data |
| `make nuke` | Removed | **DELETED** | Nuclear option, total reset |
| `make db-reset` | Running | Schema dropped | Reset only DB, keep containers |
