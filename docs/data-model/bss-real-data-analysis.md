# BSS Real Data Analysis — CEM-Oriented Architecture Plan

> Analysis date: 2026-04-15 | Dataset: TT BSS 1-month 500K subscribers (March 2026)
> Status: Waiting for OSS data before implementation — O+B convergence is the backbone

---

## 1. Dataset Overview

| Property | Value |
|----------|-------|
| Records | 500,000 subscribers |
| Features | 26 |
| Period | March 2026 (single month) |
| Operator | Tunisie Telecom (MCC 605, MNC 02) |
| Format | Pipe-delimited → converted to CSV |
| Granularity | One row per subscriber per month |

---

## 2. Feature Categories

### 2.1 Subscriber Identity (2 features)

| Feature | Description |
|---------|-------------|
| `imsi` | International Mobile Subscriber Identity — unique SIM ID. MCC=605 (Tunisia), MNC=02 (Tunisie Telecom). Primary key for all subscriber-level analysis. |
| `tac` | Type Allocation Code — first 8 digits of IMEI, identifies the device model globally. Links to GSMA TAC database for full device specifications. |

### 2.2 Device Ecosystem (5 features)

| Feature | Description | Distribution |
|---------|-------------|--------------|
| `model` | Exact device model name (e.g., IPHONE 16 PRO MAX, REDMI 14C). High cardinality — hundreds of models. | Group into families for ML |
| `brand` | Manufacturer. SAMSUNG(21%), XIAOMI(12%), INFINIX(10%), NOKIA(10%), APPLE(6%), OPPO(6%). 24K NULL. | ~50+ brands |
| `tertype` | Terminal type: SmartPhone, FeaturePhone, CPE, Tablet, Wireless Module, WiFi Router. | SmartPhone(70%), FeaturePhone(21%) |
| `generation` | Max network generation the DEVICE supports (hardware capability, NOT actual usage). | 2G/3G/LTE(58%), 2G-only(23%), 5G-capable(12%) |
| `sim_slot` | SIM configuration: Dual, Single, eDual (eSIM+physical), NA. | NA(48%), Dual(33%), eDual(11%) |

### 2.3 SIM/Network Capability (2 features)

| Feature | Description | Distribution |
|---------|-------------|--------------|
| `volte_flag` | VoLTE capability. 1=capable, 0=not, NULL=unknown. | 0(49%), NULL(45%), 1(6%) |
| `usim_flag` | USIM presence. 1=3G/4G-capable SIM, 0=legacy 2G SIM. **Critical:** usim_flag=0 means subscriber CANNOT access 3G/4G even with a capable device. | 0(74%), 1(26%) |

### 2.4 Geography (2 features)

| Feature | Description | Distribution |
|---------|-------------|--------------|
| `area` | Governorate (wilaya) — all 24 Tunisian governorates. | Top: Tunis(12%), Sfax(8%), Nabeul(6%) |
| `area_delegation` | Delegation — sub-region within governorate. ~200+ values. | Finer granularity for localized CEM scoring |

### 2.5 Subscriber Behavior (2 features)

| Feature | Description | Distribution |
|---------|-------------|--------------|
| `usertype` | Monthly behavior classification. | Data User(71%), Voice User(18%), Silent User(12%) |
| `session_flag` | Active data session indicator. | 0(93%), 1(7%) — likely tracks specific session type |

### 2.6 Usage Metrics (7 features)

| Feature | Description | Key Stats |
|---------|-------------|-----------|
| `dou_total` | Total data consumption in bytes (sum of all RAT traffic). | Mean ~17.7 GB for active users. Max ~3.4 TB |
| `traffic_2g` | Data over 2G (GPRS/EDGE) in bytes. | 240K users. Total: ~3.1 TB |
| `traffic_3g` | Data over 3G (UMTS/HSPA) in bytes. | 300K users. Total: ~250 TB |
| `traffic_4g` | Data over 4G (LTE) in bytes. **Dominant.** | 292K users. Total: ~4.15 PB |
| `traffic_5g` | Data over 5G (NR) in bytes. **Significant adoption.** | 191K users. Total: ~1.84 PB |
| `duration` | Total voice call duration in seconds. | 385K users. Mean ~3.6 hrs |
| `voice_onlinetime_3g` / `voice_onlinetime_2g` | Voice registration time split by network. | FeaturePhone users → mostly 2G |

### 2.7 Network Quality — Per-Subscriber (3 features)

These are the **gold mine** for O+B convergence — OSS-grade metrics embedded in BSS data.

| Feature | Description | Distribution |
|---------|-------------|--------------|
| `s1_mme_sr` | S1-MME Success Rate — LTE attach reliability (S1 interface, eNodeB↔MME). | 1.0(60%), 0.0(39%), fractional(1%) |
| `iu_attach_sr` | Iu Attach Success Rate — 3G (UMTS) registration reliability. | 1.0(61%), 0.0(38%) |
| `gb_attach_sr` | Gb Attach Success Rate — 2G (GPRS) registration reliability. | 0.0(57%), 1.0(42%) |

### 2.8 Actual Network Experience (1 feature)

| Feature | Description | Distribution |
|---------|-------------|--------------|
| `highest_rat` | Highest RAT **actually used** during the month (not device capability). | 4G(52%), Unknown(29%), 5G(7%), 3G(6%), 2G(6%) |

### 2.9 Temporal (1 feature)

| Feature | Description |
|---------|-------------|
| `month_year` | Reporting period: `2026-03`. Single-month snapshot. |

---

## 3. Strategic Decision: CEM Over Billing

**Decision:** Platform pivots to CEM (Customer Experience Management) subscriber profiling, NOT billing/revenue anomaly detection.

**Rationale:**
1. **Data-reality alignment** — real TT data is usage/device/network-quality, not billing. Build on what exists.
2. **Huawei SmartCare IS CEM** — this project sits in SmartCare's architectural layer. CEM subscriber profiling is literally what SmartCare does. HCS story becomes airtight.
3. **Richer ML surface** — 26 real features covering device + multi-RAT usage + per-subscriber network quality vs. a single revenue number. More signal for anomaly detection and prediction.
4. **ADN L4 alignment** — "subscriber X has degraded experience → trigger remediation" is more compelling than "revenue dipped."
5. **O+B convergence** — the attach success rates (s1_mme_sr, iu_attach_sr, gb_attach_sr) are OSS-grade metrics inside BSS data. When real OSS data arrives, the convergence layer gains subscriber-level granularity.

---

## 4. O+B Convergence: The Backbone

This platform exists because of OSS+BSS convergence. The BSS data gives us the subscriber dimension. The OSS data (when it arrives) gives us the network dimension. The convergence layer is where the intelligence lives.

### What BSS Brings to O+B

```
BSS Side (this data):
  - WHO: 500K subscriber profiles with device/location/behavior
  - WHAT: Per-subscriber usage patterns (data by RAT, voice, sessions)
  - HOW WELL: Per-subscriber network quality (s1_mme_sr, iu_attach_sr, gb_attach_sr)
  - WHERE: Governorate + delegation (24 regions, 200+ sub-regions)

OSS Side (waiting):
  - WHICH: Cell-level KPIs (throughput, latency, drops, interference)
  - WHEN: Time-series network events and alarms
  - WHY: Root cause indicators (hardware faults, congestion, coverage gaps)
```

### The Convergence Join

```
         BSS (subscriber)              OSS (network)
         ┌──────────────┐              ┌──────────────┐
         │ imsi          │              │ cell_id      │
         │ area          │──── JOIN ────│ site_region  │
         │ area_delegat. │   geography  │ site_name    │
         │ highest_rat   │──── JOIN ────│ rat_type     │
         │ s1_mme_sr     │   quality    │ s1_setup_sr  │
         │ dou_total     │  correlation │ throughput   │
         └──────────────┘              └──────────────┘
                    │                           │
                    └─────────┬─────────────────┘
                              ▼
                    ┌──────────────────┐
                    │  O+B Convergence │
                    │  Engine          │
                    │                  │
                    │  - Correlation   │
                    │    (Pearson +    │
                    │     Spearman)    │
                    │  - Causal link   │
                    │    (cell degrades│
                    │     → subscriber │
                    │     experience   │
                    │     drops)       │
                    │  - Geographic    │
                    │    aggregation   │
                    └──────────────────┘
```

---

## 5. Rolling Window Engine Architecture

### Why Rolling Window

We have 500K static records for one month. The rolling window engine simulates real-time ingestion by:

- Sampling batches of subscribers per pipeline cycle
- Computing temporal features across a sliding window of W cycles
- Creating the sequential context that DL models need

This makes a static snapshot behave like a live data stream — enabling real-time detection and prediction while using real data.

### Engine Design

```
┌───────────────────────────────────────────────────┐
│              500K Subscriber Records               │
│               (1-month snapshot)                    │
└──────────────────────┬────────────────────────────┘
                       │
              ┌────────▼─────────┐
              │  Rolling Window   │
              │  Engine           │
              │                   │
              │  Batch: 200-500   │
              │  subscribers per  │
              │  2-min cycle      │
              │                   │
              │  Stratified by:   │
              │  - area           │
              │  - usertype       │
              │  - highest_rat    │
              │                   │
              │  Temporal noise:  │
              │  ±variation on    │
              │  usage values     │
              └────────┬─────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    Window t       Window t-1     Window t-2  ...
    (current)      (previous)     (history)
        │              │              │
        └──────────────┼──────────────┘
                       │
              ┌────────▼─────────┐
              │  Feature Computer │
              │                   │
              │  Per-subscriber:  │
              │  - Δ(dou_total)   │
              │  - trend(attach)  │
              │  - RAT migration  │
              │                   │
              │  Per-cohort:      │
              │  - area mean      │
              │  - brand mean     │
              │  - peer deviation │
              │                   │
              │  Cross-feature:   │
              │  - capability vs  │
              │    actual RAT gap │
              │  - traffic_ratio  │
              │    concentration  │
              └────────┬─────────┘
                       │
              ┌────────▼─────────┐
              │   ML / DL Models  │
              └──────────────────┘
```

### Pipeline Transformation

**Current (synthetic):**
```
generate_bss(200) → infer → store → repeat every 2 min
```

**New (real data, rolling window):**
```
1. BOOTSTRAP: Load 500K CSV into staging (PostgreSQL or memory)
2. Each cycle (2 min):
   a. Sample next batch (stratified by area/usertype/rat)
   b. Inject temporal variation (±perturbation)
   c. Compute WINDOW FEATURES across last W batches
   d. Feed to ML/DL models
   e. Store results + update window buffer
   f. O+B convergence computation (when OSS available)
```

---

## 6. ML/DL Model Architecture (April 2026)

### Model Roster

| # | Model | Algorithm | Input | Output | Role |
|---|-------|-----------|-------|--------|------|
| 1 | **CEM Experience Score** | GradientBoosting (interpretable) | 26 BSS features + engineered features | Score 0-1 + feature explanation | Subscriber experience quality — replaces SLA Risk |
| 2 | **Experience Anomaly Detector** | Autoencoder (PyTorch) | All encoded features → latent → reconstructed | Reconstruction error → anomaly flag + severity | Detects abnormal subscriber experience patterns |
| 3 | **Churn Trajectory Predictor** | LSTM / GRU (PyTorch) | Sequence of W windows per subscriber | Churn probability + trajectory class | Predicts experience degradation over time |
| 4 | **RAT Underservice Classifier** | XGBoost or small NN | Device capability + actual RAT + usage + attach rates | Underserved flag + root cause | Detects subscribers not getting the service their device supports |
| 5 | **O+B Correlation Engine** | Pearson + Spearman + Granger Causality | Paired OSS cell KPIs + BSS subscriber aggregates | Correlation strength + causal direction | The convergence brain — links network issues to subscriber impact |

### Model 1: CEM Experience Score (Enhanced GBR)

Replaces the current SLA Risk model. Same interpretable GradientBoosting, but trained on real CEM features.

**Engineered features from real data:**
- `rat_gap` = generation_rank - highest_rat_rank (underservice indicator)
- `attach_composite` = weighted mean of s1_mme_sr, iu_attach_sr, gb_attach_sr
- `traffic_concentration` = max(traffic_2g..5g) / dou_total (single-RAT dependency)
- `device_tier` = encoded from brand + tertype + generation
- `area_peer_deviation` = subscriber usage vs delegation mean
- `voice_data_ratio` = duration / (dou_total + 1) (usage profile shape)

**Why GBR stays:** Feature importance = "why is this subscriber's experience bad?" → critical for L4 Agent explainability. DL is a black box; GBR tells you "attach_composite=42% of the prediction."

### Model 2: Autoencoder — Experience Anomaly

Replaces IsolationForest. Handles 26+ features with nonlinear correlations.

```
Architecture:
  Input (N features, normalized)
      → Dense(128, ReLU, BatchNorm)
      → Dense(64, ReLU, BatchNorm)
      → Dense(32, ReLU)              ← latent space
      → Dense(64, ReLU, BatchNorm)
      → Dense(128, ReLU, BatchNorm)
      → Dense(N, Sigmoid)            ← reconstruction

Loss: MSE reconstruction error
Anomaly: error > μ + kσ (k tuned on validation)
```

**Training strategy:**
- Train on "healthy" subscribers: Data Users with attach_sr > 0.9, highest_rat matching generation
- Anomalies = high reconstruction error = experience pattern the model hasn't seen in normal subscribers
- **Advantage over IsolationForest:** captures cross-feature interactions (e.g., 5G device + high dou_total + low s1_mme_sr is a very specific anomaly pattern that IF would miss)

### Model 3: LSTM Churn Trajectory

**This is where the rolling window engine pays off.** Each tick adds a window position.

```
Architecture:
  Input: [batch, W, features_per_window]
      → LSTM(64 units, return_sequences=True)
      → Dropout(0.3)
      → LSTM(32 units)
      → Dropout(0.3)
      → Dense(16, ReLU)
      → Dense(1, Sigmoid)           ← churn probability

Window features per subscriber:
  - dou_total_normalized
  - duration_normalized
  - attach_sr_composite
  - rat_gap
  - usertype_encoded (Data=2, Voice=1, Silent=0)
```

**Why LSTM over simpler models:** A subscriber going Data→Data→Voice→Silent across windows is a temporal pattern. IsolationForest sees each window independently — LSTM sees the trajectory.

### Model 4: RAT Underservice Classifier

New model enabled entirely by real data.

**Logic:** If device `generation` = "2G/3G/LTE/NR" but `highest_rat` = "2G" → subscriber is underserved. The classifier learns the nuanced version — factoring in area, usim_flag, attach rates, etc.

**Features:**
- generation_rank (ordinal encoding)
- highest_rat_rank (ordinal encoding)
- usim_flag (SIM bottleneck?)
- s1_mme_sr, iu_attach_sr (network bottleneck?)
- area + area_delegation (coverage bottleneck?)

**Output:** Underserved flag + root cause category (SIM limitation, network coverage, device issue)

### Model 5: O+B Correlation Engine (Enhanced)

**Current:** Pearson + Spearman on synthetic data.
**New:** Add Granger Causality to detect if OSS network degradation CAUSES BSS subscriber impact (not just correlates).

```
When OSS arrives:
  - Aggregate BSS by area/delegation → area-level CEM scores
  - Aggregate OSS by site/cell → area-level network KPIs
  - Compute: Pearson, Spearman, Granger on paired time series
  - Output: "Cell throughput drop in Sfax Medina CAUSED 23% experience
    degradation for 4,200 subscribers over 3 windows"
```

---

## 7. Derived Feature Engineering Catalog

Features to compute from the 26 raw columns before feeding to models:

| Feature | Formula | Purpose |
|---------|---------|---------|
| `dou_gb` | dou_total / 1,073,741,824 | Human-readable data usage in GB |
| `duration_min` | duration / 60 | Voice duration in minutes |
| `rat_gap` | encode(generation) - encode(highest_rat) | Underservice score: positive = underserved |
| `attach_composite` | 0.5 × s1_mme + 0.3 × iu_attach + 0.2 × gb_attach | Weighted network quality composite |
| `traffic_4g_ratio` | traffic_4g / max(dou_total, 1) | 4G dependency ratio |
| `traffic_5g_ratio` | traffic_5g / max(dou_total, 1) | 5G adoption ratio |
| `traffic_concentration` | max(t2g,t3g,t4g,t5g) / max(dou_total,1) | Single-RAT dependency |
| `voice_data_ratio` | duration / max(dou_total/1e9, 0.001) | Usage profile shape |
| `voice_3g_ratio` | voice_onlinetime_3g / max(duration, 1) | Voice 3G dependency |
| `device_tier` | encode(brand, tertype, generation) | Ordinal device quality score |
| `is_5g_capable` | 1 if "NR" in generation else 0 | 5G readiness flag |
| `sim_bottleneck` | 1 if usim_flag=0 AND generation supports 3G+ | SIM blocking higher RAT |
| `area_dou_deviation` | (dou_gb - area_mean_dou) / area_std_dou | Peer comparison within governorate |
| `area_attach_deviation` | (attach_composite - area_mean) / area_std | Network quality vs area peers |
| `is_silent` | 1 if usertype = "Silent User" | Binary churn risk flag |
| `is_voice_only` | 1 if usertype = "Voice User" | Voice-centric profile flag |

---

## 8. Technology Stack Changes

| Component | Current | New | Reason |
|-----------|---------|-----|--------|
| DL Framework | None | **PyTorch 2.x** | Lightweight, good for AE + LSTM, production-friendly |
| Feature Store | In-memory per cycle | **PostgreSQL staging + Redis window buffer** | Rolling window needs persistent state across cycles |
| Model Format | joblib (sklearn) | joblib (GBR/XGB) + **TorchScript** (DL) | DL models need separate serialization |
| Training | Notebooks | Notebooks + **training pipeline script** | Reproducible retraining on real data |

---

## 9. Implementation Sequence

### Phase 3.5: Real Data Ingestion + Rolling Window Engine
> Blocked on: OSS data arrival. BSS preprocessing can begin.

1. BSS CSV loader → PostgreSQL staging table
2. Feature engineering layer (derived features from 26 columns)
3. Rolling window engine in pipeline-worker
4. Window buffer management (last W cycles in memory/Redis)

### Phase 4.5: Model v3.0 — CEM Models
> Blocked on: Phase 3.5 + OSS data

5. CEM Experience Score (retrained GBR on real features)
6. Experience Anomaly Autoencoder (PyTorch)
7. RAT Underservice Classifier
8. O+B Correlation Engine with real paired data

### Phase DL: Temporal Models
> Blocked on: Accumulated window history from engine running

9. LSTM Churn Trajectory Predictor
10. Granger Causality in correlation engine
11. L4 Agent playbooks updated for new model outputs

---

## 10. Key Observations from Data

1. **71% Data Users** — Tunisia's network is data-dominant, voice is secondary
2. **4G dominates traffic** (4.15 PB) but 5G already carries 1.84 PB — real 5G adoption
3. **23% of devices are 2G-only** — significant legacy device population
4. **74% don't have USIM** — even 4G-capable devices may be stuck on 2G SIM
5. **29% "Unknown" highest_rat** — measurement gap, likely voice-only users
6. **12% Silent Users** — zero usage, immediate churn risk cohort
7. **Attach success rates are binary-like** (0.0 or 1.0) — subscribers either fully connect or fully fail. This simplifies anomaly detection but limits gradient-based models.
8. **Geographic coverage is national** — all 24 governorates, enabling area-level CEM benchmarking
