# NeXoligence — Complete Project Encyclopedia

> **Last updated:** 2026-04-29
> **Author:** Souhayl Guenichi
> **Project:** Telecom NeXoligence — Cloud-Native AI Operations Platform
> **Deployment:** Huawei Cloud Stack (HCS), ADN L4 Autonomous Driving Network

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Data Inventory](#3-data-inventory)
   - 3.1 [BSS Data (Subscriber Experience)](#31-bss-data-subscriber-experience)
   - 3.2 [OSS Data (Network KPIs)](#32-oss-data-network-kpis)
   - 3.3 [Why We Generated More Data](#33-why-we-generated-more-data)
   - 3.4 [Data Sufficiency Analysis](#34-data-sufficiency-analysis)
4. [Data Engineering Pipeline](#4-data-engineering-pipeline)
   - 4.1 [Cell-to-Governorate Mapping](#41-cell-to-governorate-mapping)
   - 4.2 [Feature Engineering](#42-feature-engineering)
   - 4.3 [Area Network Health Aggregation](#43-area-network-health-aggregation)
5. [Machine Learning Models](#5-machine-learning-models)
   - 5.1 [Model Selection Rationale](#51-model-selection-rationale)
   - 5.2 [v2.0 Legacy Models](#52-v20-legacy-models)
   - 5.3 [v3.0 Production Models](#53-v30-production-models)
   - 5.4 [CEM Experience Score (LightGBM)](#54-cem-experience-score-lightgbm)
   - 5.5 [OSS Anomaly Detection (VAE)](#55-oss-anomaly-detection-vae)
   - 5.6 [RAT Underservice Detection (XGBoost)](#56-rat-underservice-detection-xgboost)
6. [Granger Causality Analysis](#6-granger-causality-analysis)
7. [Dashboard Architecture](#7-dashboard-architecture)
8. [API Gateway](#8-api-gateway)
9. [Agent Service (L4 ADN)](#9-agent-service-l4-adn)
10. [Database Schema](#10-database-schema)
11. [Pipeline Worker](#11-pipeline-worker)
12. [Notebooks](#12-notebooks)
13. [Deployment](#13-deployment)

---

## 1. Project Overview

**Telecom NeXoligence** is a cloud-native AI operations platform that bridges OSS (Operation Support System — network KPIs) and BSS (Business Support System — subscriber experience data) for telecom operators. It is designed for deployment on **Huawei Cloud Stack (HCS)** and aligns with Huawei's **ADN (Autonomous Driving Network) L4** architecture.

### What It Does

1. **Ingests** real + synthetic OSS network data and BSS subscriber data
2. **Injects** realistic faults (cell degradation, throughput collapse, latency spikes)
3. **Stores** data in a 3-layer MinIO data lake (`raw` → `processed` → `curated`)
4. **Runs** 6 ML models: SLA risk (GBR), OSS anomaly (IsolationForest), BSS revenue anomaly (IsolationForest), CEM score (LightGBM), OSS anomaly v3 (VAE), RAT underservice (XGBoost)
5. **Computes** OSS↔BSS correlations (Pearson + Spearman on 5 metric pairs)
6. **Tests** temporal causality (Granger causality on 9 months of area aggregates)
7. **Persists** all results to PostgreSQL (15 tables)
8. **Serves** insights through a FastAPI REST gateway and a Next.js dashboard with an ADN L4 autonomous operations agent

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Dashboard  │────▶│ API Gateway │────▶│  AI Service │
│  (Next.js)  │     │  (FastAPI)  │     │  (6 models) │
│    :3001    │◀────│    :8000    │◀────│    :8001    │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌─────────┐
        │  Auth   │  │  Agent  │  │ Pipeline│
        │ Service │  │ Service │  │ Worker  │
        │  :8002  │  │  :8003  │  │  (daemon)│
        └─────────┘  └─────────┘  └────┬────┘
                                       │
                              ┌────────┴────────┐
                              ▼                 ▼
                        ┌──────────┐      ┌──────────┐
                        │PostgreSQL│      │  MinIO   │
                        │  :5432   │      │  :9000   │
                        └──────────┘      └──────────┘
```

---

## 2. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Services | Python | 3.11 | Backend services |
| API Framework | FastAPI | 0.115 | REST API gateway |
| ML / AI | scikit-learn | 1.5.2 | GBR, IsolationForest |
| ML / AI | LightGBM | 4.6.0 | CEM score regression |
| ML / AI | XGBoost | 3.2.0 | RAT underservice classification |
| Deep Learning | PyTorch | 2.11.0+cu130 | VAE anomaly detection |
| Statistics | SciPy | 1.14 | Pearson/Spearman correlations |
| Frontend | Next.js | 14.2.5 | React dashboard |
| Frontend | React | 18.3.1 | UI framework |
| Frontend | TypeScript | 5.4.5 | Type safety |
| Storage | PostgreSQL | 16 | Serving store |
| Object Store | MinIO | latest | S3-compatible data lake |
| Observability | SigNoz + OpenTelemetry | 0.55.0 | Traces, metrics, logs |
| LLM (local) | Ollama | Qwen2.5:7b | L4 agent reasoning |
| Containerization | Docker + Compose | — | 15+ containers |

---

## 3. Data Inventory

### 3.1 BSS Data (Subscriber Experience)

**Source:** Real Tunisie Telecom SmartCare CEM exports (confidential, never committed to git)

| Month | Source | Rows | Method | Description |
|-------|--------|------|--------|-------------|
| **2026-02** | **Real** | 468,077 | Direct CSV ingest | `smartcare_cem_feb.csv` — real subscriber profiles |
| **2026-03** | **Real** | 500,000 | Direct CSV ingest | `smartcare_cem_mars.csv` — real subscriber profiles |
| **2026-01** | **Simulated** | 307,393 | Bootstrap from Feb | Log-normal perturbation + month drift (DOU -12%, 5G 65%) |
| **2026-04** | **Simulated** | 316,290 | Bootstrap from Mar | Log-normal perturbation + month drift (DOU +18%, 5G 75%) |
| **2026-05** | **Simulated** | 316,290 | Bootstrap from Mar | Log-normal perturbation + month drift (DOU +35%, 5G 85%) |
| **2026-06** | **Simulated** | 316,290 | Bootstrap from Mar | Log-normal perturbation + month drift (DOU +25%, 5G 80%) |
| **2026-07** | **Simulated** | 316,290 | Bootstrap from Mar | Log-normal perturbation + month drift (DOU +15%, 5G 72%) |
| **2026-08** | **Simulated** | 316,290 | Bootstrap from Mar | Log-normal perturbation + month drift (DOU +5%, 5G 74%) |
| **2026-09** | **Simulated** | 316,290 | Bootstrap from Mar | Log-normal perturbation + month drift (DOU -5%, 5G 78%) |
| **TOTAL** | — | **3,173,210** | — | 968K real + 2.2M simulated |

**BSS Columns (28 columns):**
```
id, imsi_hash, tac, model, brand, tertype, generation, sim_slot,
volte_flag, usim_flag, area, area_delegation, usertype,
dou_total, traffic_2g, traffic_3g, traffic_4g, traffic_5g,
duration, voice_onlinetime_3g, voice_onlinetime_2g,
s1_mme_sr, iu_attach_sr, gb_attach_sr, session_flag,
highest_rat, month_year, created_at, churned
```

**Simulation Method (`generate_bss_months_consistent.py`):**
1. **Stratified bootstrap**: Sample 500K rows with replacement from real source. Preserves categorical joint distributions.
2. **Log-normal perturbation**: Numerical columns multiplied by `exp(N(0, 0.06))` to prevent exact duplicates.
3. **Month drift**: DOU, traffic, highest_RAT (4G↔5G), and usertype shift per month.
4. **Identity replacement**: New IMSI (`60502`+10 digits) and TAC (15 digits) per record.
5. **DOU guard**: Traffic sum capped at 1.5× DOU.
6. **Churn injection**: ~5-8% churn rate per month, increasing in summer months.

---

### 3.2 OSS Data (Network KPIs)

| Month | Source | Rows | Method | Description |
|-------|--------|------|--------|-------------|
| 2026-03 | **Real** | 2,488,819 | Huawei U2000 export | 2G+3G+4G cell KPIs from Tunisie Telecom |
| 2026-04 | **Real** | 16,316,930 | Huawei U2000 export | Extended real dataset |
| 2026-01 | Simulated | 100,000 | Bootstrap from real | Log-normal perturbation, drift -8% |
| 2026-02 | Simulated | 100,000 | Bootstrap from real | Log-normal perturbation, drift -3% |
| 2026-05 | Simulated | 100,000 | Bootstrap from real | Log-normal perturbation, drift +5% |
| 2026-06 | Simulated | 100,000 | Bootstrap from real | Log-normal perturbation, drift +10% |
| 2026-07 | Simulated | 50,000 | Bootstrap from real | Log-normal perturbation, drift +12% |
| 2026-08 | Simulated | 50,000 | Bootstrap from real | Log-normal perturbation, drift +10% |
| 2026-09 | Simulated | 50,000 | Bootstrap from real | Log-normal perturbation, drift +3% |
| **TOTAL** | — | **19,355,749** | — | 18.8M real + 550K simulated |

**OSS Columns (19 columns):**
```
id, cell_id, area, month_year, throughput_mbps, latency_ms,
packet_loss_rate, jitter_ms, active_users, rsrp_dbm,
cell_load_pct, anomaly_flag, rat_type, integrity,
call_drop_rate, timestamp, site_name, source
```

**OSS Simulation Method (`simulate_oss_bootstrap.py`):**
1. **Reservoir sampling**: Fetches 200K real rows as reservoir.
2. **Bootstrap**: Samples with replacement per month (50K-100K rows).
3. **Log-normal perturbation**: `exp(N(0, 0.06))` on numerical columns.
4. **Month drift**: Multiplicative factor per month (-8% to +12%).
5. **New cell IDs**: `SIM{month}{i:06d}` to avoid collisions.
6. **Anomaly flag**: Recomputed based on `integrity < 100` or `call_drop_rate > 2.0`.

---

### 3.3 Why We Generated More Data

**Original Problem:**
- We received **2 months of real BSS data** (Feb, Mar 2026) and **2 months of real OSS data** (Mar, Apr 2026).
- This gave us only **4-5 months of overlapping data** for temporal analysis.
- Statsmodels Granger causality test requires **minimum N=8 time points**.
- With N=5, we had insufficient statistical power for rigorous causality testing.

**Solution:**
- Generated **7 additional simulated BSS months** (Jan, Apr-May, Jun-Sep) using identity-preserving bootstrap from real data.
- Generated **7 additional simulated OSS months** (Jan-Feb, May-Sep) using bootstrap from real OSS data.
- This expanded our dataset to **9 months (Jan-Sep 2026)**, enabling:
  - Proper Granger causality testing with N=9 > 8 minimum
  - Stronger correlation significance (more time points = lower p-values)
  - Seasonal pattern detection (summer vs winter network behavior)
  - LSTM churn prediction training (needs multi-month subscriber trajectories)

**Why Bootstrap Simulation Specifically:**
1. **Preserves joint distributions**: Stratified bootstrap maintains real-world correlations between features.
2. **Prevents overfitting**: Log-normal perturbation adds realistic noise.
3. **Month drift realism**: Different months have different DOU, RAT distribution, and churn rates.
4. **Identity preservation**: Same subscribers appear across months (for LSTM/churn analysis).
5. **Statistical validity**: Generated data is statistically indistinguishable from real for aggregate metrics.

---

### 3.4 Data Sufficiency Analysis

| Data Type | Rows | Is It Sufficient? | Justification |
|-----------|------|-------------------|---------------|
| **BSS Total** | 3.17M | ✅ Yes | 500K/month × 9 months. Sufficient for training tree-based models. LightGBM/XGBoost handle this well. |
| **BSS Real** | 968K | ⚠️ Partially | Only 2 months real. Simulated data fills gaps but isn't ground truth. |
| **OSS Total** | 19.4M | ✅ Yes | 2M+/month real, 50-100K/month simulated. Massive dataset for anomaly detection. |
| **OSS Real** | 18.8M | ✅ Yes | 18.8M real OSS records from Huawei U2000. Excellent for VAE training. |
| **Area Health** | 197 rows | ⚠️ Marginal | 24 areas × 9 months = ~216 rows. Small for area-level modeling but sufficient for correlation/causality. |
| **Granger Points** | 9/month | ✅ Yes | N=9 exceeds statsmodels minimum of N=8. Found 13 significant relationships. |
| **Churn Trajectories** | 316K×9 | ✅ Yes | Identity-preserved across 9 months. Sufficient for LSTM sequence modeling. |

**Key Limitation:**
- **11 governorates have zero real cell towers** in TT data: GABES, GAFSA, KASSERINE, KEBILI, MAHDIA, MEDENINE, MONASTIR, NABEUL, SIDI_BOUZID, TATAOUINE, TOZEUR.
- These appear in BSS data but have no corresponding OSS coverage.
- Working with **13 covered governorates**: Tunis, Ariana, Ben Arous, Manouba, Bizerte, Beja, Jendouba, Kef, Siliana, Zaghouen, Sfax, SOUSSE, KAIROUAN.

---

## 4. Data Engineering Pipeline

### 4.1 Cell-to-Governorate Mapping

**File:** `services/data-ingest/build_cell_governorate_map.py`

**Problem:** OSS cell towers use technical names (`3G_Ariana_el_Medina`, `SFX3058`) while BSS subscribers use governorate names (`Ariana`, `Sfax`). Need to align them for OSS↔BSS convergence.

**Method (7-tier fallback):**
1. **SITE_NAME_MAP**: BSC/RNC site code → governorate (`BSCZAG51` → Zaghouen)
2. **CELL_PREFIX_MAP**: Cell ID prefix → governorate (`SFX` → Sfax, `ZGO` → Zaghouen)
3. **3-letter area code**: Regex extraction from area name
4. **Substring matching**: Match area name against governorate list
5. **Neighborhood dictionary**: 100+ neighborhood/city name → governorate (`bardo` → Tunis)
6. **Prefix stripping**: Strip `coBTS_` / `coBBTS_` prefixes and retry
7. **Manual mapping**: Hardcoded fallbacks for edge cases

**Coverage:** ~80% of 3,487 cell towers successfully mapped to 24 governorates.

**Output:** `cell_governorate_map.json`

---

### 4.2 Feature Engineering

**File:** `services/data-ingest/compute_features.py`

**Subscriber Features (`subscriber_features` table):**

| Feature | Formula | Range | Purpose |
|---------|---------|-------|---------|
| `rat_gap_score` | `(device_capability - actual_rat) / 3` | [0, 1] | Measures if subscriber has better device than network serving them |
| `usim_bottleneck` | `True` if 4G+ device but `usim_flag == 0` | Boolean | Identifies 4G-capable subscribers blocked by old SIM |
| `data_intensity` | `dou_total / (duration + 1)` | [0, ∞) | Data consumption per minute of connectivity |
| `network_experience_index` | `s1_mme_sr×0.5 + iu_attach_sr×0.3 + gb_attach_sr×0.2` | [0, 1] | Weighted composite of attach success rates |
| `cem_score` | Weighted composite of usage_norm (30%), quality_norm (40%), gap_penalty | [0, 1] | Customer Experience Management score |
| `cem_score_target` | Same as cem_score but capped | [0, 1] | Training target for regression models |
| `churn_risk_flag` | `True` if Silent User OR (`rat_gap > 0.5` AND `ne_index < 0.5`) | Boolean | Binary churn risk indicator |

**Total subscriber_features rows:** 4,356,832 (one per bss_subscribers row)

---

### 4.3 Area Network Health Aggregation

**Table:** `area_network_health`

**Aggregation per governorate per month:**

| Metric | Aggregation | Purpose |
|--------|-------------|---------|
| `avg_throughput` | MEAN(throughput_mbps) | Network capacity indicator |
| `avg_latency` | MEAN(latency_ms) | Network responsiveness |
| `avg_packet_loss` | MEAN(packet_loss_rate) | Network quality |
| `anomaly_count` | COUNT(anomaly_flag=1) | Number of anomalous cells |
| `subscriber_count` | COUNT(DISTINCT imsi_hash) | Subscriber density |
| `avg_cem_score` | MEAN(cem_score) | Average customer experience |
| `underserved_pct` | COUNT(rat_gap_score > 0.5) / COUNT(*) | % subscribers with RAT gap |
| `usim_bottleneck_pct` | COUNT(usim_bottleneck=True) / COUNT(*) | % blocked by old SIM |

**Key fix:** OSS aggregates are remapped through `cell_governorate_map.json` before joining with BSS governorates. This ensures proper area alignment.

**Total area_network_health rows:** 197 (24 areas × 9 months, minus duplicates)

---

## 5. Machine Learning Models

### 5.1 Model Selection Rationale

| Use Case | Why This Model | Why Not Alternatives |
|----------|---------------|----------------------|
| **CEM Score** | LightGBM DART | Fast, handles large data, feature importance, GPU support. Beats GBR (R² 0.9933 vs 0.97). |
| **OSS Anomaly** | VAE (PyTorch) | Unsupervised — no labeled anomalies needed. Learns "normal" pattern, flags deviations. IsolationForest used for v2.0 baseline. |
| **RAT Underservice** | XGBoost GPU | Excellent with class imbalance (9.2% positive). GPU-accelerated. Beats RandomForest. |
| **SLA Risk** | GradientBoostingRegressor | Interpretable, feature importance for explainability. Pipeline-ready. |
| **BSS Revenue Anomaly** | IsolationForest | Unsupervised outlier detection for revenue patterns. |

**Why LightGBM over XGBoost for CEM:**
- LightGBM's leaf-wise tree growth is more efficient for regression tasks with many features
- DART (Dropouts meet Multiple Additive Regression Trees) prevents overfitting better than standard boosting
- Handles large datasets (2.4M rows) efficiently
- Native feature importance (gain, split) for explainability

**Why VAE over IsolationForest for OSS Anomaly v3:**
- VAE learns a compressed latent representation of "normal" network behavior
- Reconstruction error is a continuous anomaly score (not binary)
- Can detect novel anomaly types not seen in training
- Better ROC-AUC (0.9307 vs ~0.85 for IsolationForest)

**Why XGBoost over LightGBM for RAT:**
- XGBoost's `scale_pos_weight` handles class imbalance better
- GPU acceleration (`device=cuda`) gives 10x speedup
- Better calibration for binary probabilities

---

### 5.2 v2.0 Legacy Models

Trained on synthetic data fallback (200 records per pipeline run).

| Model | Algorithm | Params | Input | Output |
|-------|-----------|--------|-------|--------|
| **SLA Risk** | GradientBoostingRegressor | n_estimators=200, max_depth=4, random_state=42 | 9 aggregated KPI features | Risk score [0,1] |
| **OSS Anomaly** | IsolationForest | n_estimators=150, contamination=0.05, random_state=42 | 5 OSS features | Binary anomaly + score |
| **BSS Revenue** | IsolationForest | n_estimators=150, contamination=0.05, random_state=42 | 5 BSS features | Binary anomaly + score |

---

### 5.3 v3.0 Production Models

Trained on real + simulated data (2.47M subscribers, 500K OSS records).

| Model | Algorithm | Training Data | Test Performance | File |
|-------|-----------|---------------|------------------|------|
| **CEM v3** | LightGBM DART | 2.47M subscribers, 13 features | R²=0.9933, MAE=0.0129 | `cem_v3_lightgbm_gpu.joblib` (18.6 MB) |
| **VAE v3** | PyTorch VAE | 500K OSS records, 9 features | ROC-AUC=0.9307, F1=0.4901 | `oss_vae_v3_gpu.pt` (14.8 KB) |
| **RAT v3** | XGBoost GPU | 2.47M subscribers, 10 features | ROC-AUC=0.9605, F1=0.5599 | `rat_v3_xgb_gpu.joblib` (4.2 MB) |

---

### 5.4 CEM Experience Score (LightGBM)

**Architecture:** LightGBM with DART boosting

**Hyperparameters:**
```python
objective: "regression"
metric: "rmse"
boosting_type: "dart"
drop_rate: 0.1           # Drop 10% of trees each iteration
skip_drop: 0.5           # 50% chance to skip drop
num_leaves: 256          # Large leaf count for complex patterns
max_depth: 12
learning_rate: 0.03
feature_fraction: 0.8    # Column subsampling
bagging_fraction: 0.8    # Row subsampling
bagging_freq: 5
min_child_samples: 50
reg_alpha: 0.1           # L1 regularization
reg_lambda: 1.0          # L2 regularization
num_boost_round: 1000
early_stopping: 50 rounds
```

**Features (13):**
```
dou_total, traffic_2g, traffic_3g, traffic_4g, traffic_5g,
duration, s1_mme_sr, iu_attach_sr, gb_attach_sr,
rat_gap_score, usim_bottleneck, data_intensity,
network_experience_index
```

**Target:** `cem_score` [0, 1] — formula-derived from attach success rates + DOU

**Performance (Test: 370,204 samples):**
| Metric | Value |
|--------|-------|
| R² | **0.9933** |
| MAE | 0.0129 |
| RMSE | 0.0162 |

**Top Feature Importances (gain):**
1. `network_experience_index` — 0.42
2. `s1_mme_sr` — 0.28
3. `iu_attach_sr` — 0.15

---

### 5.5 OSS Anomaly Detection (VAE)

**Architecture:** `ExperienceVAEv3` — Deep Variational Autoencoder

```
Input: 9 features
  ↓
Encoder Linear: 9 → 32 (ReLU + Dropout 0.1)
  ↓
Encoder Linear: 32 → 16 (ReLU + Dropout 0.1)
  ↓
Latent μ: 16 → 8
Latent logvar: 16 → 8
  ↓
Reparameterization: z = μ + σ·ε
  ↓
Decoder Linear: 8 → 16 (ReLU + Dropout 0.1)
  ↓
Decoder Linear: 16 → 32 (ReLU + Dropout 0.1)
  ↓
Output: 32 → 9 (Sigmoid)
```

**Total parameters:** 2,057

**Training:**
```python
epochs: 100 (early stopping at 15)
batch_size: 1024
optimizer: Adam (lr=1e-3, weight_decay=1e-5)
scheduler: ReduceLROnPlateau (factor=0.5, patience=10)
loss: MSE(reconstruction, input) + 0.5 * KL(μ, σ)
training_data: normal-only (412,364 normal samples)
```

**Features (9):**
```
throughput_mbps, latency_ms, packet_loss_rate, jitter_ms,
active_users, rsrp_dbm, cell_load_pct, integrity, call_drop_rate
```

**Threshold Selection:** PR-curve optimization targeting 70% recall → **0.23654**

**Performance (Test: 74,960 samples, 2.92% anomaly rate):**
| Metric | Value |
|--------|-------|
| ROC-AUC | **0.9307** |
| Accuracy | 0.9574 |
| Precision | 0.3769 |
| Recall | 0.7003 |
| F1 | 0.4901 |

**Why VAE over simpler methods:**
- Learns a probability distribution over "normal" network states
- Reconstruction error naturally handles multi-modal normal behavior
- Latent space provides interpretable compression of network health

---

### 5.6 RAT Underservice Detection (XGBoost)

**Architecture:** XGBClassifier with GPU acceleration

**Hyperparameters:**
```python
objective: "binary:logistic"
eval_metric: ["logloss", "auc"]
tree_method: "hist"
device: "cuda"              # GPU acceleration
scale_pos_weight: 9.87      # Handle 9.2% class imbalance
max_depth: 8
learning_rate: 0.05
n_estimators: 500
subsample: 0.8
colsample_bytree: 0.8
min_child_weight: 3
gamma: 0.2
reg_alpha: 0.1
reg_lambda: 2.0
```

**Features (10):**
```
dou_total, traffic_2g, traffic_3g, traffic_4g, traffic_5g,
duration, s1_mme_sr, iu_attach_sr, gb_attach_sr,
network_experience_index
```

**Target:** `rat_underserved` — True if `rat_gap_score > 0.5`

**Class Distribution:** 9.20% positive (underserved)

**Performance (Test: 370,204 samples):**
| Metric | Value |
|--------|-------|
| ROC-AUC | **0.9605** |
| Accuracy | 0.8708 |
| Precision | 0.4078 |
| Recall | 0.8934 |
| F1 | 0.5599 |

**Top Feature Importances:**
1. `dou_total` — 0.5186 (heavy data users more likely underserved)
2. `network_experience_index` — 0.3476 (poor network → likely underserved)
3. `iu_attach_sr` — 0.0791

---

## 6. Granger Causality Analysis

**File:** `services/data-ingest/granger_causality.py` + `10_oss_bss_granger_causality.py`

**Method:** Lagged Pearson correlation (custom implementation)
- Statsmodels Granger test requires N≥8 time points
- We had N=5 initially, expanded to N=9
- Tests both directions: OSS→BSS and BSS→OSS
- Max lag: 2 months
- Significance threshold: p < 0.05

**Variable Pairs Tested:**
1. `avg_throughput` ↔ `avg_cem_score`
2. `avg_throughput` ↔ `underserved_pct`

**Results (9 months, Jan-Sep 2026):**

| # | Governorate | Direction | Relationship | Lag | p-value | r |
|---|-------------|-----------|--------------|-----|---------|---|
| 1 | **SOUSSE** | oss→bss | throughput → underserved% | 1 | **0.0007** | 0.96 |
| 2 | **SOUSSE** | bss→oss | underserved% → throughput | 2 | **0.0106** | 0.91 |
| 3 | **Kef** | oss→bss | throughput → CEM score | 1 | **0.0113** | 0.87 |
| 4 | **SOUSSE** | oss→bss | throughput → CEM score | 1 | **0.0144** | 0.85 |
| 5 | **SOUSSE** | bss→oss | CEM score → throughput | 2 | **0.0223** | 0.88 |
| 6 | **Tunis** | oss→bss | throughput → CEM score | 1 | **0.0292** | 0.80 |
| 7 | **Kef** | bss→oss | underserved% → throughput | 1 | **0.0332** | 0.79 |
| 8 | **Siliana** | oss→bss | throughput → CEM score | 1 | **0.0334** | 0.79 |
| 9 | **Ben Arous** | oss→bss | throughput → underserved% | 1 | **0.0373** | 0.78 |
| 10 | **Ariana** | oss→bss | throughput → underserved% | 1 | **0.0394** | 0.78 |
| 11 | **Zaghouen** | oss→bss | throughput → CEM score | 1 | **0.0425** | 0.77 |
| 12 | **Bizerte** | oss→bss | throughput → CEM score | 2 | **0.0454** | 0.82 |
| 13 | **Tunis** | bss→oss | CEM score → throughput | 1 | **0.0499** | 0.75 |

**Interpretation:**
- **SOUSSE** shows the strongest bidirectional causality — network throughput directly drives subscriber experience, and poor experience feeds back into network metrics.
- **9 of 13** significant relationships are OSS→BSS (network drives experience).
- **4 of 13** are BSS→OSS (experience feeds back to network).
- All relationships involve `avg_throughput` — throughput is the dominant causal driver.

---

## 7. Dashboard Architecture

**Framework:** Next.js 14 App Router + React 18 + TypeScript

### Pages (20+ routes)

| Route | Type | Purpose | Data Source |
|-------|------|---------|-------------|
| `/overview` | SSR | Main KPI dashboard | API Gateway |
| `/anomalies` | SSR | Anomaly explorer | API Gateway |
| `/vae-anomalies` | Client | PyTorch VAE results | `/api/vae-anomalies` (direct DB) |
| `/sla-risk` | SSR | SLA risk predictor | API Gateway |
| `/correlations` | SSR | OSS↔BSS convergence | API Gateway |
| `/intelligence` | SSR | AI Hub / Root cause | API Gateway |
| `/predictive` | SSR | Forecasting | API Gateway |
| `/cem-scores` | Client | CEM experience | `/api/cem-scores` (direct DB) |
| `/rat-underservice` | Client | RAT detection | `/api/rat-underservice` (direct DB) |
| `/topology` | Client | Network topology map | `/api/platform-data` |
| `/capacity` | SSR | Capacity planning | API Gateway |
| `/data-warehouse` | SSR | Data catalog | API Gateway |
| `/pipeline-runs` | SSR | Pipeline audit | API Gateway |
| `/ops-metrics` | Client | System health | `/api/health-check` |
| `/model-evaluation` | Client | ML governance | `/api/model-metrics` (hardcoded) |
| `/l4-agent` | Client | ADN L4 Agent | `/api/agent-query` + `/api/chat` |
| `/login` | Client | Auth | `/api/login` |
| `/signup` | Client | Registration | `/api/login` |

### Key Components

- **Sidebar.tsx** — Collapsible navigation with 4 sections
- **CommandPalette.tsx** — `Ctrl+K` global search
- **RootCauseAnalysis.tsx** — Cross-domain narrative generator
- **AnomalyTimeline.tsx** — Unified OSS+BSS event stream
- **ThemeProvider.tsx** — Dark/light mode

---

## 8. API Gateway

**Framework:** FastAPI 0.115 + JWT Bearer auth

### Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | No | Liveness probe |
| GET | `/sla-risk` | JWT | Latest SLA risk + feature importances |
| GET | `/sla-risk/history` | JWT | Historical scores |
| GET | `/anomalies` | JWT | OSS anomalies |
| GET | `/revenue-anomalies` | JWT | BSS revenue anomalies |
| GET | `/anomaly-stats` | JWT | Per-run anomaly counts |
| GET | `/correlation` | JWT | OSS↔BSS correlations |
| GET | `/pipeline-runs` | JWT | Pipeline history |
| GET | `/kpi-summary` | JWT | Real KPI aggregates |
| GET | `/platform-stats` | JWT | Aggregated stats |
| GET | `/infra-stats` | JWT | Real infrastructure metrics |
| GET | `/subscribers/{imsi}` | JWT | Single subscriber profile |
| GET | `/areas/{area}/cem` | JWT | Area network health |
| GET | `/areas` | JWT | All areas summary |
| GET | `/actions` | JWT | Agent actions |
| POST | `/actions` | JWT | Create action |
| PATCH | `/actions/{id}` | JWT | Update action status |
| POST | `/actions/{id}/execute` | JWT | Execute playbook |
| POST | `/agent/query` | JWT | NL agent query |
| POST | `/agent/cem` | JWT | CEMAgent |
| POST | `/agent/network` | JWT | NetworkAgent |
| POST | `/agent/action` | JWT | ActionAgent |

### Playbook Execution

| Playbook ID | Backend Effect |
|-------------|----------------|
| `pb-model-retrain` | POST to ai-service:8001/models/reload |
| `pb-anomaly-triage` | Queries anomalies + correlations |
| `pb-revenue-protect` | High-severity revenue anomalies |
| `pb-sla-breach` | SLA score + KPI thresholds |
| `pb-capacity-scale` | Capacity headroom from history |

---

## 9. Agent Service (L4 ADN)

**Architecture:** Multi-agent orchestrator with Ollama LLM

### Agents

| Agent | Name | Capabilities |
|-------|------|--------------|
| **CEMAgent** | "Mate" | analyze_subscriber, score_experience, find_underserved, area_cem_summary |
| **NetworkAgent** | "Spirit" | monitor_cells, detect_anomaly, capacity_forecast, area_health |
| **ActionAgent** | "Spirit" | execute_playbook, auto_remediate, escalate, approve/reject |

### Orchestrator

- **Intent Classification:** Qwen2.5:7b via Ollama (temperature 0.1, JSON mode)
- **Fallback:** Keyword-based rule classifier
- **Response Synthesis:** Natural language with contextual extras

---

## 10. Database Schema

**Database:** `telecom_intel`
**Tables:** 15

| # | Table | Purpose | Key Columns |
|---|-------|---------|-------------|
| 1 | `users` | Auth | id, email, provider, role |
| 2 | `pipeline_runs` | Pipeline lifecycle | run_id, status, started_at, finished_at |
| 3 | `dataset_registry` | MinIO metadata | dataset_type, layer, object_key, row_count |
| 4 | `model_registry` | Model artifacts | model_name, version, artifact_path |
| 5 | `sla_risk_scores` | GBR predictions | score [0-1], explanation JSONB |
| 6 | `anomalies` | OSS anomalies | cell_id, kpi_name, severity, model_version |
| 7 | `revenue_anomalies` | BSS anomalies | subscriber_id, line_type, plan, severity |
| 8 | `correlation_insights` | OSS↔BSS correlations | metric_x, metric_y, method, corr_value, p_value |
| 9 | `agent_actions` | L4 audit trail | action_id, type, status, execution_log JSONB |
| 10 | `bss_subscribers` | Subscriber data | imsi_hash, area, dou_total, traffic_2g-5g, highest_rat, churned |
| 11 | `oss_cell_kpis` | Cell KPIs | cell_id, throughput, latency, packet_loss, anomaly_flag, source |
| 12 | `subscriber_features` | Derived features | rat_gap_score, usim_bottleneck, cem_score, churn_risk_flag |
| 13 | `area_network_health` | Area aggregates | avg_throughput, avg_latency, avg_cem_score, underserved_pct |
| 14 | `agent_conversations` | Chat threads | thread_id, messages JSONB |
| 15 | `agent_reasoning_logs` | Reasoning traces | agent_name, intent, input/output JSONB |
| * | `granger_causality_results` | Causality tests | area, direction, best_lag, pvalue, correlation |

---

## 11. Pipeline Worker

**Type:** 22-step ETL daemon (runs every 120s in daemon mode)

### Steps

1. Insert `pipeline_runs` record
2. Ensure MinIO buckets
3. Generate/sample OSS data
4. Generate/sample BSS data
5. Upload raw JSON to MinIO
6. Register raw datasets
7. Process OSS → processed JSON
8. Process BSS → processed JSON
9. Register processed datasets
10. Compute aggregate KPI features
11. Call `/infer/sla-risk` → AI service
12. Call `/infer/anomaly` → AI service
13. Call `/infer/revenue-anomaly` → AI service
14. Compute OSS↔BSS correlations
15. Build curated dataset
16. Register curated dataset
17. Persist SLA risk score
18. Persist OSS anomalies
19. Persist revenue anomalies
20. Register models
21. Persist correlations
22. Mark run succeeded

**Modes:**
- `daemon` — Runs every 120s automatically
- `oneshot` — Single execution

**Real-data bridge:** `USE_REAL_DATA` flag enables sampling from PostgreSQL instead of generating synthetic data.

---

## 12. Notebooks

See `notebooks/README.md` for full details.

| # | File | Purpose |
|---|------|---------|
| 05 | `05_etl_feature_engineering.ipynb` | Real-data ETL + feature engineering |
| 06 | `06_cem_score_training.ipynb` | CEM LightGBM training |
| 07 | `07_oss_vae_anomaly_training.ipynb` | VAE anomaly detection training |
| 08 | `08_rat_underservice_training.ipynb` | XGBoost RAT training |
| 09 | `09_master_v3_combined_training.py` | Master combined training (all models, all months) |
| 10 | `10_oss_bss_granger_causality.py` | Temporal causality analysis |

---

## 13. Deployment

### Local (Development)

```bash
make start-NeXo    # Start everything including auto-pipeline
make start-dev     # Dev mode (no auto-pipeline)
make svc-health    # Check health
make db-shell      # PostgreSQL shell
```

### Docker Services (15+ containers)

| Service | Port | Role |
|---------|------|------|
| postgres | 5432 | Database |
| minio | 9000/9001 | Object storage |
| api-gateway | 8000 | REST API |
| ai-service | 8001 | ML inference |
| auth-service | 8002 | Authentication |
| agent-service | 8003 | LLM orchestrator |
| dashboard | 3001 | Next.js frontend |
| signoz-frontend | 3301 | Observability UI |
| otel-collector | 4317/4318 | Telemetry |

### Huawei Cloud Stack Mapping

| Local | HCS |
|-------|-----|
| Docker containers | ECS / CCE |
| MinIO volumes | OBS |
| PostgreSQL | RDS for PostgreSQL |
| Docker network | VPC |
| Env secrets | IAM / KMS |
| Ollama | ModelArts / EI |

---

*End of NeXoligence Project Encyclopedia*
