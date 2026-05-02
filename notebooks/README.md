# NeXoligence Notebooks — Complete Guide

> Last updated: 2026-04-29

## Overview

These notebooks and scripts form the **ML training, evaluation, and data engineering pipeline** for the Telecom NeXoligence platform. They process real Tunisie Telecom OSS/BSS data, engineer features, train 6 production ML models, and perform temporal causality analysis.

---

## Notebook Inventory

### Phase 1: Data Foundation

| # | File | Type | Purpose | Outputs |
|---|------|------|---------|---------|
| **05** | `05_etl_feature_engineering.ipynb` | `.ipynb` | **Real-data ETL + feature engineering**. Derives missing OSS fields from real Huawei U2000 exports, builds subscriber-level features, constructs area-level aggregates, creates training datasets for v3.0 models. | 3 `.npz` training matrices + EDA plots |

**What it does:**
- Loads real BSS subscribers (Mar 2026, ~500K) and real OSS cell KPIs (Mar 2026, ~2.49M)
- Derives `latency_ms`, `packet_loss_rate`, `jitter_ms`, `cell_load_pct` from domain transforms (real OSS CSVs lack these)
- Computes `subscriber_features`: `rat_gap_score`, `usim_bottleneck`, `data_intensity`, `network_experience_index`, `cem_score`
- Joins OSS per-area with BSS subscriber density → `area_network_health`
- Outputs training matrices:
  - `cem_training_mar2026.npz` (500K, 13 features, target=`cem_score`)
  - `anomaly_training_mar2026.npz` (200K, 10 features, target=`anomaly_flag`)
  - `rat_underservice_mar2026.npz` (500K, 10 features, target=`rat_underserved`)

---

### Phase 2: Individual Model Training

| # | File | Type | Model Trained | Algorithm | Data Used |
|---|------|------|---------------|-----------|-----------|
| **06** | `06_cem_score_training.ipynb` | `.ipynb` | **CEM Experience Score v3.0** | LightGBM (DART) vs GBR baseline | `cem_training_mar2026.npz` (500K real Mar BSS) |
| **07** | `07_oss_vae_anomaly_training.ipynb` | `.ipynb` | **OSS Anomaly Detection v3.0** | PyTorch VAE | `anomaly_training_mar2026.npz` (200K real Mar OSS) |
| **08** | `08_rat_underservice_training.ipynb` | `.ipynb` | **RAT Underservice v3.0** | XGBoost (GPU) vs baseline | `rat_underservice_mar2026.npz` (500K real Mar BSS) |

**Notebook 06 — CEM Score Training:**
- Compares GBR baseline vs LightGBM with hyperparameter tuning
- LightGBM wins with R² = 0.9933, MAE = 0.0129
- SHAP explainability analysis
- Saves: `cem_v3_lightgbm.joblib`, `cem_v3_gbr_baseline.joblib`, `cem_v3_feature_names.joblib`

**Notebook 07 — OSS VAE Anomaly Training:**
- Trains on normal-only data (anomaly_flag == 0)
- Architecture: 10→16→8→4 latent→8→16→10
- Threshold selected via PR-curve targeting 70% recall → 0.23654
- Performance: ROC-AUC = 0.9307, Accuracy = 0.9574
- Saves: `oss_vae_v3.pt`, `vae_scaler.joblib`

**Notebook 08 — RAT Underservice Training:**
- Compares baseline vs tuned XGBoost with RandomizedSearchCV
- Tuned model wins with ROC-AUC = 0.9605
- Feature importances: `dou_total` (0.52), `network_experience_index` (0.35), `iu_attach_sr` (0.08)
- Saves: `rat_underservice_v3_xgb.joblib`, `rat_v3_feature_names.joblib`

---

### Phase 3: Master Combined Training

| # | File | Type | Purpose | Data |
|---|------|------|---------|------|
| **09** | `09_master_v3_combined_training.py` | `.py` | **Master v3.0 training** — trains CEM + VAE + RAT on ALL months (real + simulated, 1.5M+ records) with GPU acceleration | Jan-May 2026 combined |

**What it does:**
- CEM: Queries `subscriber_features` + `bss_subscribers` + `area_network_health` for months 2026-01 through 2026-05 → **2,468,026 subscribers**
- Anomaly: Proportional sample from `oss_cell_kpis` across Jan-Jun → **499,729 records** (2.92% anomaly rate)
- RAT: Same 2,468,026 subscribers, 9.20% underserved rate
- Trains all 3 models with GPU acceleration (LightGBM CPU, XGBoost GPU, PyTorch VAE GPU)
- Splits: 85/15 train/test, stratified

**Saved models (deployed in production):**
- `cem_v3_lightgbm_gpu.joblib` (18.6 MB) — LightGBM DART, 1000 rounds
- `oss_vae_v3_gpu.pt` (14.8 KB) — Deeper VAE: 9→32→16→8 latent
- `rat_v3_xgb_gpu.joblib` (4.2 MB) — XGBoost GPU, tuned

---

### Phase 4: Temporal Causality Analysis

| # | File | Type | Purpose | Data |
|---|------|------|---------|------|
| **10** | `10_oss_bss_granger_causality.py` | `.py` | **OSS↔BSS Granger causality** — tests temporal causal relationships | `area_network_health` Jan-Sep 2026 |

**What it does:**
- Tests 2 directions × 2 metric pairs across 24 governorates
- Uses lagged Pearson correlation (custom implementation, statsmodels requires N≥8)
- Expanded from 5 months (Jan-May) → 9 months (Jan-Sep) for stronger statistical power
- Found **13 significant relationships** (p < 0.05)
- Top finding: SOUSSE oss→bss throughput→underserved% (lag=1, p=0.0007, r=0.96)

**Why we expanded to 9 months:**
- Statsmodels Granger test requires minimum N=8 time points
- We only had 5 months initially → used custom lagged correlation as workaround
- Expanded to 9 months (Jan-Sep) by generating Jul-Sep BSS data and simulating OSS data
- This gives proper statistical power and confirms 4 original findings + 9 new ones

---

## Model Files (`notebooks/models/`)

### v2.0 Legacy Models (sklearn, synthetic data fallback)

| File | Size | Algorithm | Used By |
|------|------|-----------|---------|
| `sla_risk_model.joblib` | 611 KB | GradientBoostingRegressor (Pipeline+StandardScaler) | `/infer/sla-risk` (v2.0) |
| `anomaly_model.joblib` | 1.75 MB | IsolationForest (Pipeline+StandardScaler) | `/infer/anomaly` (v2.0) |
| `revenue_anomaly_model.joblib` | 1.84 MB | IsolationForest (Pipeline+StandardScaler) | `/infer/revenue-anomaly` (v2.0) |

### v3.0 Production Models (real data, GPU-trained)

| File | Size | Algorithm | Used By |
|------|------|-----------|---------|
| `cem_v3_lightgbm_gpu.joblib` | 18.6 MB | LightGBM DART, 1000 rounds | `/infer/cem` (v3.0) |
| `oss_vae_v3_gpu.pt` | 14.8 KB | PyTorch VAE (9→32→16→8 latent) | `/infer/vae-anomaly` (v3.0) |
| `rat_v3_xgb_gpu.joblib` | 4.2 MB | XGBoost GPU, tuned | `/infer/rat-underservice` (v3.0) |
| `vae_v3_scaler.joblib` | 815 B | StandardScaler | VAE preprocessing |
| `cem_v3_gpu_features.joblib` | 212 B | Feature name list | CEM feature validation |
| `rat_v3_gpu_features.joblib` | 172 B | Feature name list | RAT feature validation |

### Archived/Baseline Models

| File | Size | Algorithm | Notes |
|------|------|-----------|-------|
| `cem_v3_gbr_baseline.joblib` | 679 KB | GradientBoostingRegressor | Notebook 06 baseline |
| `cem_v3_lightgbm.joblib` | 917 KB | LightGBM CPU | Notebook 06 winning model |
| `cem_v3_feature_names.joblib` | 1.2 KB | Feature names | 13 CEM features |
| `oss_vae_v3.pt` | 10.2 KB | PyTorch VAE (original) | Notebook 07 original |
| `vae_scaler.joblib` | 855 B | StandardScaler | Notebook 07 scaler |
| `rat_underservice_v3_xgb.joblib` | 256 KB | XGBClassifier baseline | Notebook 08 baseline |
| `rat_underservice_v3_xgb_baseline.joblib` | 472 KB | XGBClassifier baseline | Notebook 08 duplicate |
| `rat_v3_feature_names.joblib` | 848 B | Feature names | 10 RAT features |

---

## Training Artifacts (`notebooks/data/`)

| File | Size | Description |
|------|------|-------------|
| `cem_training_mar2026.npz` | 56 MB | Notebook 05 CEM arrays (500K, 13 features) |
| `anomaly_training_mar2026.npz` | 17.6 MB | Notebook 05 anomaly arrays (200K, 10 features) |
| `rat_underservice_mar2026.npz` | 40 MB | Notebook 05 RAT arrays (500K, 10 features) |
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

## How to Run

```bash
# Start Jupyter
make jupyter-token
# or
cd notebooks && jupyter notebook

# Run notebooks in order:
# 1. 05_etl_feature_engineering.ipynb  → generates training matrices
# 2. 06_cem_score_training.ipynb       → trains CEM model
# 3. 07_oss_vae_anomaly_training.ipynb → trains VAE model
# 4. 08_rat_underservice_training.ipynb → trains RAT model
# 5. 09_master_v3_combined_training.py  → master training (all months)
# 6. 10_oss_bss_granger_causality.py   → causality analysis

# Run master training
python 09_master_v3_combined_training.py

# Run Granger causality
python 10_oss_bss_granger_causality.py
```

---

## Data Flow

```
Notebook 05 (ETL)
    ├──→ data/cem_training_mar2026.npz ──→ Notebook 06 ──→ models/cem_v3_*.joblib
    ├──→ data/anomaly_training_mar2026.npz ──→ Notebook 07 ──→ models/oss_vae_v3.pt
    └──→ data/rat_underservice_mar2026.npz ──→ Notebook 08 ──→ models/rat_underservice_v3_*.joblib

Notebook 09 (Master) [replaces all v3.0 models]
    ├──→ queries postgres directly (all months Jan-Sep)
    ├──→ saves data/*_combined_v3.npz
    ├──→ models/cem_v3_lightgbm_gpu.joblib  (18.6 MB)
    ├──→ models/oss_vae_v3_gpu.pt           (14.8 KB)
    ├──→ models/rat_v3_xgb_gpu.joblib       (4.2 MB)
    └──→ models/*_gpu_features.joblib + vae_v3_scaler.joblib

Notebook 10 (Granger)
    └──→ queries area_network_health → data/granger_causality_results.csv + .md
```
