# Advanced AI Architecture — From Lightweight to Research-Grade

> The goal: A 6-month Huawei internship should produce AI that makes experts take notice.
> Not heavy for the sake of heavy — heavy because the PROBLEM demands it.

---

## What Changes With More Months of Data

This is the single most important thing to understand: **one month of data limits you to point-in-time analysis. Multiple months unlock temporal AI.**

| Data | What You Can Do | What You Can't Do |
|------|----------------|-------------------|
| **1 month (current)** | Static segmentation, point anomaly detection | Real temporal patterns, true churn prediction, seasonal analysis, real drift detection |
| **3 months** | Short-term trends, month-over-month deltas, RAT migration tracking, device upgrade detection | Full seasonal patterns, long-range prediction |
| **6 months** | Full lifecycle analysis, seasonal decomposition, robust churn trajectories, concept drift measurement, statistically significant O+B causality | - |
| **12 months** | Complete annual patterns, year-over-year comparison, robust Granger causality with seasonal correction | - |

### Concrete example — why 1 month is not enough:

With 1 month: "This subscriber is Silent." That's all you know. Maybe they went on vacation. Maybe they switched to Orange. You can't tell.

With 6 months: "This subscriber went Data→Data→Data→Voice→Voice→Silent over 6 months." That's a TRAJECTORY. The LSTM sees a pattern. And it's a REAL pattern, not a simulated one.

**Request to TT: Ask for the same 500K subscribers across 6 consecutive months (October 2025 → March 2026). Same IMSI set, same 26 features, monthly snapshots.**

What this gives you:
- 500K × 6 = **3 million records**
- Real temporal sequences per subscriber (6 timesteps)
- Real month-over-month feature changes (not simulated perturbations)
- Real churn events (subscribers who were Data Users in October and Silent in March)
- Real device upgrades (TAC changes between months)
- Real RAT migration (highest_rat shifts from 3G to 4G)
- Real seasonal patterns (Ramadan usage shifts, summer patterns)

---

## The Advanced AI Stack

### Current (lightweight — to be replaced)

```
GBR (30 sec) + IsolationForest (10 sec) + basic IsolationForest (10 sec)
Total training: ~1 minute. No GPU. No feature engineering depth.
```

### Proposed (research-grade)

```
┌────────────────────────────────────────────────────────────────────┐
│                    ADVANCED AI PIPELINE                             │
│                                                                    │
│  Layer 1: DEEP FEATURE ENGINEERING                                 │
│    - Temporal features (6-month sequences)                         │
│    - Graph features (subscriber-area-device topology)              │
│    - Statistical features (seasonal decomposition, spectral)       │
│    ~50K engineered features before dimensionality reduction        │
│                                                                    │
│  Layer 2: REPRESENTATION LEARNING                                  │
│    - Contrastive Learning encoder (subscriber embeddings)          │
│    - Graph Neural Network (topology-aware representations)         │
│    Training: ~2-4 hours on GPU                                     │
│                                                                    │
│  Layer 3: TASK-SPECIFIC MODELS                                     │
│    - Temporal Fusion Transformer (CEM forecasting)                 │
│    - Multi-task LSTM (joint churn + anomaly + underservice)        │
│    - GBR ensemble with learned features (interpretable scoring)    │
│    Training: ~1-3 hours on GPU                                     │
│                                                                    │
│  Layer 4: O+B CONVERGENCE                                          │
│    - Granger Causality with seasonal correction                    │
│    - Transfer Entropy (nonlinear causal discovery)                 │
│    - Cross-correlation at multiple lags                            │
│                                                                    │
│  Total training: 4-8 hours (GPU) or 24-48 hours (CPU)             │
│  Model parameters: ~5-10M total                                   │
│  Feature space: 26 raw → 200+ engineered → 64-dim embeddings      │
└────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Deep Feature Engineering

### 1.1 Temporal Features (requires multi-month data)

For each subscriber across 6 months:

**Velocity features:**
```
Δ_dou_monthly     = (dou_month_t - dou_month_{t-1}) / dou_month_{t-1}
Δ_attach_monthly  = attach_composite_t - attach_composite_{t-1}
Δ_rat_gap_monthly = rat_gap_t - rat_gap_{t-1}
```

**Acceleration features (rate of change of rate of change):**
```
Δ²_dou = Δ_dou_t - Δ_dou_{t-1}
```
Acceleration tells you if degradation is speeding up or slowing down. A subscriber losing 10% per month (constant velocity) is different from one losing 5%, then 10%, then 20% (accelerating).

**Trend features:**
```
dou_trend_slope     = linear_regression_slope(dou across 6 months)
dou_trend_r2        = R² of the linear fit (how linear is the trend?)
attach_trend_slope  = same for attach rates
```

**Volatility features:**
```
dou_cv              = std(dou across months) / mean(dou)
dou_max_drawdown    = (peak_dou - current_dou) / peak_dou
dou_streak_down     = consecutive months of decline
```

**Lifecycle stage features:**
```
months_active       = count of months where usertype != "Silent"
months_as_data_user = count where usertype = "Data User"
lifecycle_stage     = classify based on pattern:
  - "New" (appeared in recent months)
  - "Stable" (consistent usage)
  - "Growing" (increasing usage)
  - "Declining" (decreasing usage)
  - "Churning" (trajectory toward Silent)
  - "Churned" (Silent for 2+ months)
  - "Resurrected" (was Silent, came back)
```

**RAT migration features:**
```
rat_improved     = 1 if highest_rat_t > highest_rat_{t-1}
rat_degraded     = 1 if highest_rat_t < highest_rat_{t-1}
months_on_best_rat = count where highest_rat matches device capability
device_upgraded  = 1 if tac_t != tac_{t-1} (subscriber changed phone)
sim_upgraded     = 1 if usim_flag changed from 0 to 1
```

**Seasonal features:**
```
month_sin = sin(2π × month / 12)    — captures annual cyclicity
month_cos = cos(2π × month / 12)
is_ramadan = 1 if month falls in Ramadan period
is_summer  = 1 if month in {6, 7, 8}
```

### 1.2 Statistical Features

**Per-subscriber distributional features (across months):**
```
dou_skewness     = skew of usage distribution (asymmetry)
dou_kurtosis     = kurtosis (tail heaviness — spiky usage?)
attach_entropy   = -Σ p(x) log p(x)  of attach rate distribution
                   (high entropy = unpredictable attach quality)
```

**Spectral features (frequency domain):**
```
dou_dominant_frequency = FFT of 6-month usage → dominant cycle
                        (e.g., subscriber has weekly pattern vs monthly pattern)
```

### 1.3 Peer-Relative Features (cross-subscriber)

```
dou_percentile_in_area         = percentile rank within governorate
dou_percentile_in_device_tier  = percentile within device tier
attach_percentile_in_area      = network quality vs geographic peers
trend_percentile_in_area       = is this subscriber declining faster than peers?
```

### 1.4 Graph Features (topology-aware)

Build a heterogeneous graph:
```
Nodes:
  - 500K subscriber nodes (features: usage, device, behavior)
  - 24 area nodes (features: aggregated area KPIs)
  - ~200 delegation nodes (features: aggregated delegation KPIs)
  - ~50 brand nodes (features: aggregated brand stats)
  - 6 RAT nodes (2G, 3G, 4G, 5G, Unknown, NULL)

Edges:
  - subscriber → delegation (lives here)
  - subscriber → brand (uses this brand)
  - subscriber → RAT (highest_rat used)
  - delegation → area (belongs to)
  - delegation ↔ delegation (geographically adjacent)
```

Graph features per subscriber:
```
area_neighbor_avg_cem    = mean CEM score of adjacent delegations
brand_peer_avg_usage     = mean usage of same-brand subscribers
rat_cohort_churn_rate    = churn rate among subscribers on same RAT
local_anomaly_density    = fraction of anomalous subscribers in same delegation
```

**Total engineered features: ~200+** (before dimensionality reduction)

---

## Layer 2: Representation Learning

### 2.1 Contrastive Learning — Subscriber Embeddings

**Why:** With 200+ features, models struggle with the curse of dimensionality. We need to compress 200 features into a dense, meaningful 64-dimensional embedding where similar subscribers are close and different subscribers are far.

**Why contrastive learning and not just PCA or a basic Autoencoder?**

PCA assumes linear relationships. A basic Autoencoder minimizes reconstruction error — it learns to compress and decompress but doesn't explicitly learn SIMILARITY. Contrastive learning learns representations where the STRUCTURE of the data is preserved: subscribers with similar experience profiles end up near each other in embedding space.

**Architecture: Supervised Contrastive Learning (SupCon)**

```
Subscriber features (200+)
        │
        ▼
┌──────────────────────┐
│  Encoder Network     │
│                      │
│  Dense(512, GELU)    │
│  BatchNorm + Drop0.3 │
│  Dense(256, GELU)    │
│  BatchNorm + Drop0.3 │
│  Dense(128, GELU)    │
│  BatchNorm           │
│  Dense(64)           │  ← embedding space
│                      │
│  Projection Head:    │
│  Dense(64, GELU)     │
│  Dense(32)           │  ← contrastive space (training only)
└──────────────────────┘

Loss: SupCon Loss
  - Positive pairs: subscribers in same segment (same usertype, same area, same device tier)
  - Negative pairs: subscribers from different segments
  - L = -log( exp(sim(z_i, z_j)/τ) / Σ exp(sim(z_i, z_k)/τ) )
    where sim = cosine similarity, τ = temperature (0.07)
```

**Training:**
- 500K subscribers × 200 features
- Batch size: 2048 (large batches are critical for contrastive learning — more negatives per positive)
- Epochs: 100-200
- **Training time: ~2-3 hours on GPU, 10-15 hours on CPU**
- Output: 64-dimensional embedding per subscriber

**After training:** The projection head is discarded. The 64-dim embedding from the encoder is used as input for ALL downstream models. Every task model benefits from the learned representation.

```
200+ raw features → Encoder → 64-dim embedding → GBR (CEM score)
                                                → TFT (forecasting)
                                                → LSTM (churn)
                                                → XGBoost (underservice)
```

### 2.2 Graph Neural Network — Topology-Aware Representations

**Why:** Contrastive learning treats each subscriber independently. But subscribers exist in a NETWORK — geographic, device, and RAT relationships matter. A subscriber's experience depends not just on their own features but on their neighborhood.

**Architecture: GraphSAGE (Scalable Graph Neural Network)**

```
Why GraphSAGE and not vanilla GCN?
  - GCN requires the full graph in memory (500K nodes × adjacency = huge)
  - GraphSAGE uses SAMPLING: for each node, sample K neighbors, aggregate
  - Scales to millions of nodes
  - Inductive: can embed new subscribers without retraining

Architecture:
  Layer 1: Sample 10 neighbors → aggregate (mean/attention) → Dense(128)
  Layer 2: Sample 5 neighbors → aggregate → Dense(64)
  Output: 64-dim topology-aware embedding per subscriber

Loss: Link prediction (predict if subscriber is in area X)
      + Node classification (predict usertype)
```

**Training:**
- 500K subscriber nodes + 280 area/delegation/brand/RAT nodes
- ~2M edges
- Epochs: 50-100
- **Training time: ~1-2 hours on GPU**

**Combined embedding:**
```
Contrastive embedding (64-dim) ⊕ Graph embedding (64-dim) = 128-dim combined
```

This 128-dim vector captures BOTH individual subscriber features AND their position in the telecom topology. No other model in this project (or most telecom AI projects) does this.

---

## Layer 3: Task-Specific Models

### 3.1 Temporal Fusion Transformer (TFT) — CEM Forecasting

**Why TFT and not plain LSTM?**

The LSTM I proposed earlier was a basic 2-layer sequence model. It works, but it treats all features equally and all timesteps equally. TFT (Google Research, 2019) is the state-of-the-art for multi-horizon time-series forecasting because:

1. **Variable Selection Networks** — learns which features matter at each timestep (automated feature importance, more powerful than GBR's static importance)
2. **Gated Residual Networks** — skip connections that let the model bypass unnecessary complexity
3. **Multi-head Temporal Attention** — attends to different parts of the sequence for different reasons (one head might focus on recent usage drop, another on long-term trend)
4. **Static + Temporal feature handling** — natively separates features that don't change (brand, area) from features that change monthly (usage, attach rates)
5. **Quantile Regression** — outputs prediction intervals, not just point estimates ("CEM score will be 0.45-0.62 with 90% confidence")

**Architecture:**
```
Static features (brand, area, device_tier, ...)
    │
    ▼
┌───────────────────────────┐
│ Static Variable Selection │ → static context vectors
└───────────┬───────────────┘
            │
            ▼
Temporal features (per month: usage, attach, rat_gap, ...)
    │
    ▼
┌───────────────────────────┐
│ Temporal Variable Selection│ → selected temporal features
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│ LSTM Encoder              │ → sequence encoding
│ (processes past months)   │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│ LSTM Decoder              │ → future predictions
│ (generates forecasts)     │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│ Multi-head Attention      │ → temporal attention over encoded sequence
│ (4 heads, d_model=128)   │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│ Quantile Output           │ → P10, P50, P90 forecasts
│ (3 quantiles)             │
└───────────────────────────┘

Parameters: ~2-3M
Training: ~1-2 hours on GPU (6 months × 500K)
```

**What it predicts:**
- Next month's CEM score per subscriber (with confidence intervals)
- Next month's churn probability
- Next month's expected data usage

**Why this is heavy:** TFT has ~2-3M parameters, needs GPU for reasonable training time, and the variable selection networks + attention mechanism make it genuinely sophisticated. This is NOT a tutorial model.

### 3.2 Multi-Task LSTM — Joint Prediction

**Why multi-task?**

Training separate models for churn, anomaly, and underservice wastes information. A subscriber who is churning is ALSO likely anomalous and ALSO likely underserved. The signals are correlated. Multi-task learning shares the representation across tasks:

```
Shared encoder learns:
  "Declining usage + degrading attach + widening rat_gap"
    → this representation is useful for ALL tasks

Task heads specialize:
  Churn head: "this pattern → 82% churn probability"
  Anomaly head: "this pattern → reconstruction error 0.12"
  Underservice head: "this pattern → sim_bottleneck (91%)"
```

**Architecture:**
```
Input: 128-dim combined embedding × 6 months
    │
    ▼
┌──────────────────────────────────┐
│  Shared Bi-LSTM Trunk            │
│                                  │
│  BiLSTM(128 units) → 256-dim    │
│  Dropout(0.3)                    │
│  BiLSTM(64 units) → 128-dim     │
│  Attention pooling               │
│                                  │
│  This trunk is trained by ALL    │
│  task losses simultaneously      │
└──────────┬───────────────────────┘
           │
     ┌─────┼─────┬──────────┐
     ▼     ▼     ▼          ▼
  ┌─────┐ ┌─────┐ ┌──────┐ ┌──────────┐
  │Churn│ │Anom.│ │Under.│ │CEM Score │
  │Head │ │Head │ │Head  │ │Head      │
  │     │ │     │ │      │ │          │
  │D(64)│ │D(64)│ │D(64) │ │D(64)    │
  │D(1) │ │D(1) │ │D(5)  │ │D(1)     │
  │sigm.│ │sigm.│ │softmx│ │sigmoid  │
  └──┬──┘ └──┬──┘ └──┬───┘ └────┬────┘
     │       │       │          │
  P(churn) P(anom) class    CEM[0,1]

Combined Loss:
  L = λ₁·BCE(churn) + λ₂·BCE(anomaly) + λ₃·CE(underservice) + λ₄·MSE(cem)
  
  λ weights tuned to balance tasks (uncertainty weighting or grid search)
```

**Why Bi-LSTM (bidirectional)?**
With 6 months of historical data (not a live stream), we can read the sequence both forward AND backward. Forward: "usage is declining." Backward: "this subscriber WAS a heavy user 6 months ago." Both directions inform the prediction.

**Why attention pooling (not just last hidden state)?**
The last hidden state summarizes the whole sequence from one direction. Attention pooling learns which timesteps matter most for each prediction: "month 3 was when the critical event happened" → attention weight is high on month 3.

**Training:**
- 500K sequences × 6 timesteps × 128 features
- Batch size: 512
- Epochs: 50-100
- **Training time: ~1-2 hours on GPU**
- Parameters: ~1.5M

### 3.3 GBR Ensemble with Learned Features

**The interpretable model stays — but it gets WAY better inputs.**

```
Before (current):
  GBR trained on 42 hand-crafted features → R² = 0.979

After (advanced):
  GBR trained on:
    - 42 hand-crafted features
    - 64-dim contrastive embedding (compressed from 200+ features)
    - 64-dim graph embedding (topology-aware)
    - 6-month temporal statistics (trend, volatility, acceleration)
    - TFT variable importance scores per feature
  Total: ~250 features → GBR with 500 estimators, depth=6

  Expected: R² > 0.99, with RICHER feature importance explanations
```

**Why keep GBR?** The L4 Agent still needs explainability. GBR tells you "embedding_dim_23 contributed 15% to the score" — and because the embedding dimensions have interpretable meaning (from contrastive learning with segment labels), you can trace back to "this subscriber's network quality relative to their device tier is the primary driver."

---

## Layer 4: Advanced O+B Convergence

### 4.1 Transfer Entropy (beyond Granger)

**Why:** Granger causality assumes LINEAR relationships. Transfer entropy measures INFORMATION FLOW between time series — captures nonlinear causal relationships.

```
TE(X→Y) = Σ p(y_{t+1}, y_t, x_t) × log[ p(y_{t+1} | y_t, x_t) / p(y_{t+1} | y_t) ]

If TE(OSS→BSS) > TE(BSS→OSS):
  → Information flows FROM network TO subscribers (network causes subscriber impact)
  → Stronger evidence than Granger for nonlinear relationships
```

**With 6 months of data:** 6 time points per (area, RAT) pair. Marginal for Granger (needs ~20+ for statistical power). But with the rolling window engine creating sub-monthly time points, you get enough for both Granger and Transfer Entropy.

### 4.2 Causal Discovery with PCMCI

**PCMCI** (Peter-Clark Momentary Conditional Independence) is a state-of-the-art causal discovery algorithm for time series. It goes beyond "X causes Y" to discover the full causal graph:

```
Does throughput → attach_sr?
Does attach_sr → dou_total?
Does dou_total → churn?
Or does throughput → dou_total directly, skipping attach_sr?

PCMCI discovers:
  throughput → attach_sr → dou_total → churn
               ↘ dou_total (also direct effect)
```

This gives the L4 Agent not just "what correlates" but "what is the causal chain" — enabling more targeted remediation.

**Library:** `tigramite` (Python, by Jakob Runge, DLR Germany). Peer-reviewed, production-ready.

---

## What 6 Months of Data Unlocks — Summary

| Capability | 1 Month | 6 Months |
|-----------|---------|----------|
| Feature engineering | 42 point-in-time features | 200+ temporal + statistical + graph features |
| Subscriber embeddings | Not possible (no temporal variation) | Contrastive learning: 64-dim learned embeddings |
| Graph features | Static only | Dynamic (how does the graph evolve?) |
| Churn prediction | Simulated sequences (fake) | Real 6-month trajectories (actual churn events) |
| CEM forecasting | Point estimate only | TFT with quantile regression (confidence intervals) |
| O+B causality | Weak (few time points) | Strong (Granger + Transfer Entropy + PCMCI) |
| Seasonal patterns | Impossible (1 month) | Real monthly seasonality (Ramadan, summer, etc.) |
| Model training time | ~1 minute (CPU) | **4-8 hours (GPU) or 24-48 hours (CPU)** |
| Total parameters | ~50K | **~5-10M** |
| Research novelty | Standard ML pipeline | Contrastive + GNN + TFT + multi-task + causal discovery |

---

## Training Infrastructure

### What Changes

| Aspect | Current | Advanced |
|--------|---------|----------|
| Data size | 500K × 42 features (~80 MB) | 3M × 200+ features (~2.5 GB) |
| Training hardware | Laptop CPU (any) | **GPU recommended** (NVIDIA, 8GB+ VRAM) |
| Training time | 1 minute | **4-8 hours (GPU), 24-48 hours (CPU)** |
| Framework | scikit-learn only | scikit-learn + **PyTorch 2.x** + **PyTorch Geometric** (GNN) + **tigramite** (causal) |
| Memory | 2 GB RAM | **16-32 GB RAM** (graph + embeddings in memory) |
| Model storage | 3 files, ~5 MB total | 8+ files, **~500 MB total** (embeddings + TFT + GNN) |

### Where to Train

**Option 1: Local GPU (if available)**
- WSL2 with CUDA support
- Any NVIDIA GPU with 8GB+ VRAM (RTX 3060 or better)
- Training: 4-8 hours

**Option 2: Google Colab Pro (free/cheap)**
- T4 GPU (16 GB VRAM) — free tier
- A100 GPU (40 GB VRAM) — Colab Pro ($10/month)
- Training: 2-4 hours on A100
- Export models → download → place in ai-service

**Option 3: Huawei ModelArts (HCS-native)**
- This is the ideal option for the HCS story
- ModelArts notebook with GPU instances
- Training artifacts stored in OBS
- Demonstrates real HCS model training workflow
- **This becomes a Phase 6 deliverable: "models trained on ModelArts"**

**Option 4: CPU-only (fallback)**
- Training: 24-48 hours (leave overnight)
- Totally doable — just slower
- The models are the same, just takes longer to converge

### Training Pipeline (Reproducible)

```
notebooks/
  01_data_loading.ipynb           — Load 6 months, validate, merge
  02_feature_engineering.ipynb    — 200+ features, save feature store
  03_contrastive_training.ipynb   — SupCon encoder, save embeddings
  04_graph_construction.ipynb     — Build graph, train GraphSAGE
  05_tft_training.ipynb           — Temporal Fusion Transformer
  06_multitask_lstm.ipynb         — Joint churn/anomaly/underservice
  07_gbr_ensemble.ipynb           — GBR on combined features
  08_ob_causality.ipynb           — Granger + Transfer Entropy + PCMCI
  09_evaluation.ipynb             — All metrics, cross-validation, comparison
  10_model_export.ipynb           — Export to joblib/TorchScript, package

training/
  train_all.py                    — End-to-end script (runs 01-10 in sequence)
  config.yaml                     — Hyperparameters, paths, GPU settings
  requirements-training.txt       — Training-specific dependencies
```

---

## The Email to Request More Data

You need to ask for 6 months of the same BSS extract. Same 500K IMSIs, same 26 features, monthly snapshots from October 2025 to March 2026. This transforms the project from "static analysis" to "temporal AI."

---

## Model Comparison: Before vs After

| Model | Before (current) | After (advanced) | What Changed |
|-------|------------------|-------------------|-------------|
| CEM Score | GBR, 42 features, 200 trees, 30 sec | GBR, 250 features (incl. embeddings), 500 trees, 5 min | Learned features from contrastive + graph + temporal |
| Anomaly | IsolationForest, 6 features | Contrastive encoder + reconstruction anomaly, 200+ features | Representation learning, not random splits |
| Churn | None (simulated LSTM) | Multi-task BiLSTM on REAL 6-month sequences | Real trajectories, joint training, attention |
| CEM Forecast | None | Temporal Fusion Transformer with quantile regression | State-of-the-art time-series, uncertainty estimation |
| Underservice | XGBoost, 15 features | XGBoost, 250 features + graph embeddings | Topology-aware, temporal root cause |
| O+B Causality | Pearson + Spearman | Granger + Transfer Entropy + PCMCI causal graph | Full causal discovery, nonlinear |

---

## Why This Is Now Breathtaking

1. **Contrastive Learning on telecom subscriber data** — rarely done in industry. Most telecom AI is still basic clustering and rule-based. Learned subscriber embeddings are research-grade.

2. **Graph Neural Networks for telecom topology** — modeling the subscriber-area-device-RAT graph with GraphSAGE. This captures network effects that no tabular model can: "your experience depends on your neighbors."

3. **Temporal Fusion Transformer** — Google's state-of-the-art, applied to telecom CEM forecasting with quantile regression. Uncertainty-aware predictions.

4. **Multi-task learning** — joint training across 4 tasks with shared representations. More data-efficient, better generalization, captures cross-task correlations.

5. **Causal discovery (PCMCI)** — not just "what correlates" but "what causes what." The full causal graph of telecom experience. This is publishable research.

6. **Real operator data** — 3M records from Tunisie Telecom. Not synthetic, not UCI repository, not Kaggle. Real production data from a real operator.

7. **Cloud-native deployment** — all of this running as containerized microservices, trained on GPU (ModelArts on HCS), served via FastAPI, monitored by Prometheus. End-to-end industrial AI.

This is not a student project. This is a research-grade industrial AI system deployed on cloud-native infrastructure with real operator data. That's what a 6-month Huawei internship should produce.
