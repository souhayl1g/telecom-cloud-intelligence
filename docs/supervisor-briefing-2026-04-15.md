# Technical Briefing — Supervisor Meeting
**Date:** April 15, 2026 — 3:00 PM  
**Project:** Cloud-Native AI Operations Agent for CEM-CVM Intelligence  
**Context:** Huawei Tunisia Internship (Cloud IT / Sales-Solution) — ESPRIT PFE  
**Souhayl Guenichi**

---

## 1. What I Built So Far

A fully containerized AI operations platform with **10 Docker microservices** running locally, designed as a 1:1 blueprint for Huawei Cloud Stack (HCS) deployment.

| Layer | What's Running | Technology |
|-------|---------------|------------|
| **API Gateway** | REST API (JWT-protected, 14 endpoints) | FastAPI, Python 3.11 |
| **AI Service** | 3 ML models served via inference endpoints | scikit-learn, FastAPI |
| **Auth Service** | JWT + Google/GitHub OAuth | bcrypt, OAuth2 |
| **Pipeline Worker** | 22-step ETL pipeline (2-min cycles) | Python daemon |
| **Dashboard** | 15+ pages, real-time visualization | Next.js 14, React 18, TypeScript |
| **Data Lake** | 3-layer architecture (raw → processed → curated) | MinIO (S3-compatible) |
| **Database** | 8 tables, JSONB for ML explanations | PostgreSQL 16 |
| **Observability** | Metrics collection + dashboards | Prometheus + Grafana |
| **LLM Agent** | ADN L4 autonomous operations agent | Ollama + Qwen2.5:7b |

### ML Models Currently Running (v2.0 — trained on synthetic data)

| Model | Algorithm | What It Does | Performance |
|-------|-----------|-------------|-------------|
| SLA Risk Predictor | GradientBoostingRegressor | Predicts SLA breach probability (0→1) | R² = 0.979, MAE = 0.018 |
| OSS Anomaly Detector | IsolationForest | Flags abnormal network patterns | F1 = 0.877, ROC-AUC = 1.0 |
| BSS Revenue Anomaly | IsolationForest | Flags revenue pattern anomalies | F1 = 1.0, ROC-AUC = 1.0 |

### ADN L4 Autonomous Agent

The dashboard includes a Level 4 Autonomous Driving Network agent that:
- Generates actions from live platform data (anomalies, SLA scores, correlations)
- **Auto-approves** safe actions (informational, predictions)
- **Requires human approval** for risky remediations (critical/warning severity)
- Executes real backend playbooks (model reload, anomaly triage, capacity analysis)
- All actions persisted in PostgreSQL with full audit trail

This follows Huawei's ADN L0→L5 maturity framework where L4 = system acts autonomously with human oversight for high-risk decisions.

### CI/CD Pipeline

6-stage GitHub Actions: lint (Ruff) → test (pytest) → build (Docker) → integration → security (pip-audit) → deploy. All images pushed to GHCR.

---

## 2. What Just Happened — Real BSS Data from Tunisie Telecom

I received the first batch of **real production data** from Tunisie Telecom:

| Property | Value |
|----------|-------|
| Source | Tunisie Telecom BSS (MCC 605, MNC 02) |
| Volume | 500,000 subscriber records |
| Period | March 2026 (1 month) |
| Features | 26 columns |
| Nature | CEM subscriber profiles (usage, device, network quality, geography) |

### What's In the Data — 4 Dimensions

**Device Ecosystem (7 features):**  
Brand, model, terminal type (SmartPhone 70%, FeaturePhone 21%), network generation the device supports, SIM slot config, VoLTE capability, USIM flag. This tells me exactly what each subscriber's device CAN do.

**Usage Behavior (7 features):**  
Total data consumption (dou_total in bytes), data broken down by RAT (traffic_2g, traffic_3g, traffic_4g, traffic_5g), voice duration, voice registration time split by 2G/3G. This tells me what each subscriber actually DOES.

**Network Quality Per Subscriber (4 features):**  
s1_mme_sr (4G/LTE attach success rate), iu_attach_sr (3G attach success rate), gb_attach_sr (2G attach success rate), highest_rat (the best RAT actually used). This tells me HOW WELL the network serves each subscriber.

**Geography (2 features):**  
Governorate (all 24 Tunisian governorates) + delegation (~200 sub-regions). This tells me WHERE.

### Key Findings from My Analysis

1. **71% are Data Users**, 18% Voice-only, 12% Silent (zero usage = churn risk)
2. **4G dominates total traffic volume** (~4.15 PB) but 5G already carries ~1.84 PB — real 5G adoption is happening
3. **23% of devices are 2G-only** — significant legacy population
4. **74% don't have USIM** — this is critical: even if a subscriber has a 4G-capable phone, a legacy 2G SIM blocks them from accessing 3G/4G. This is a concrete CVM action target.
5. **Network attach rates are binary** — subscribers either fully succeed (1.0) or fully fail (0.0) at connecting to each RAT. Very few partial values.
6. The **gap between device capability and actual RAT used** is a direct measure of subscriber underservice. Example: device supports 5G but highest_rat = 2G → that subscriber is being underserved.

---

## 3. Strategic Decision: CEM Orientation

### What is CEM?

CEM (Customer Experience Management) is Huawei's SmartCare framework for measuring and improving the quality of experience each individual subscriber gets from the network. It's distinct from billing/revenue analytics.

### Why CEM, Not Revenue

The real TT data I received is **not billing data** — there are no revenue columns, no ARPU, no plan information. It's a subscriber experience profile: what device they have, how they use the network, and how well the network serves them.

I made the strategic decision to orient the entire platform around CEM because:

| Factor | CEM Orientation | Revenue/Billing Orientation |
|--------|----------------|---------------------------|
| **Data fit** | Perfect — all 26 features map to CEM dimensions | Would require a separate billing extract I don't have |
| **Huawei alignment** | SmartCare IS CEM. This makes the HCS story airtight | Revenue analytics is a different product line |
| **ML richness** | 26 features with nonlinear interactions across device/usage/network | Would reduce to single-variable anomaly detection |
| **ADN L4 value** | "Subscriber X has degraded experience → auto-remediate" is compelling | "Revenue dipped" is less actionable at network level |
| **O+B convergence** | BSS subscriber quality + OSS network quality = full picture | Revenue doesn't directly correlate with network state |

---

## 4. The Backbone: O+B Convergence

### Why This Project Exists

The core thesis is **OSS+BSS convergence** — the idea that you can only truly understand telecom operations when you join network-side data (OSS: what's happening in the infrastructure) with business-side data (BSS: what's happening to subscribers).

Most telecom operators run OSS and BSS as separate silos. Network teams look at cell KPIs. Business teams look at subscriber metrics. Nobody connects "Cell X in Sfax had 40% throughput degradation last Tuesday" with "4,200 subscribers in Sfax experienced failed 4G attach and shifted to 3G for voice."

My platform makes that connection automatically.

### What BSS Brings to the Convergence

```
BSS (what I have now):
  WHO    → 500K subscriber profiles (IMSI, device, behavior)
  WHAT   → Per-subscriber usage (data by RAT, voice, sessions)
  HOW    → Per-subscriber network quality (attach success rates)
  WHERE  → Governorate + delegation (geographic anchor)
```

### What OSS Will Bring (waiting for data)

```
OSS (what I need):
  WHICH  → Cell-level KPIs (throughput, latency, drops, interference)
  WHEN   → Time-series network events and alarms
  WHY    → Root cause indicators (hardware faults, congestion, coverage)
```

### The Join

The convergence happens through **geography** (BSS area/delegation ↔ OSS site/cell location) and **RAT type** (BSS highest_rat ↔ OSS cell RAT). This produces paired time series where I can compute not just correlation (Pearson, Spearman) but **Granger causality** — proving that network degradation CAUSES subscriber experience degradation, not just correlates with it.

```
OSS: cell throughput drops 40% in Sfax Medina
         ↓ (Granger causal link)
BSS: 4,200 subscribers → s1_mme_sr drops to 0 → highest_rat falls from 4G to 2G
         ↓
CEM Score: experience degradation detected
         ↓
L4 Agent: auto-generates remediation action → human approves → playbook executes
```

This closed loop — detect → correlate → predict → act — running on real data, is what makes this an ADN L4 system, not just a dashboard.

---

## 5. What Changes Next — The Technical Plan

### 5.1 Rolling Window Engine (replaces synthetic data generation)

**Problem:** I have 500K static records for one month. The platform needs continuous real-time ingestion to feed temporal models and simulate production behavior.

**Why not just batch-process all 500K at once?**  
Three reasons:
1. **The LSTM needs sequences.** If I process all 500K in one shot, each subscriber has exactly one observation — a sequence of length 1. The LSTM collapses into a feedforward network and its temporal power is wasted. The rolling window creates W observations per subscriber across W pipeline cycles.
2. **Production simulation.** In a real deployment on HCS, data arrives as a stream — not as a monthly CSV dump. The rolling window engine mirrors how the platform would actually run in production: continuous 2-minute cycles processing batches. This validates the architecture end-to-end.
3. **The correlation engine needs paired time series.** Pearson/Spearman/Granger require multiple time points to compute. One batch = one data point = no correlation possible. W batches = W data points = statistically meaningful correlation.

**Solution:** A rolling window engine that simulates real-time by:
- Sampling batches of subscribers per pipeline cycle (200-500 per 2-min tick)
- **Stratified sampling** by area, usertype, and RAT to maintain representativeness — why? Because random sampling could accidentally produce a batch that's 100% Tunis Data Users, which would skew the window features. Stratification ensures every batch mirrors the real population structure.
- Computing **temporal features** across a sliding window of W cycles — differences, trends, volatility across windows
- Injecting **controlled variation** to simulate daily usage patterns — why? Because in reality, a subscriber's usage fluctuates day to day. A static value repeated W times gives the LSTM nothing to learn from. Small perturbations (±10-20% on usage metrics) create realistic variation while preserving the subscriber's baseline profile.

**Window buffer management:**  
The last W batches are kept in memory (or Redis for persistence across restarts). Each new cycle pushes a new batch and drops the oldest — classic sliding window. Why Redis and not just Python memory? Because the pipeline-worker is a Docker container. If it restarts (crash, redeployment, scaling event), in-memory state is lost. Redis persists the window buffer across container lifecycles — essential for cloud-native operation on HCS.

### 5.2 Feature Engineering Layer

**Why engineer features instead of feeding raw columns to the model?**  
Raw features measure individual things. Engineered features encode **relationships** between things — and relationships are where the intelligence lives. The model could theoretically learn that `generation=2G/3G/LTE/NR` combined with `highest_rat=2G` means underservice. But encoding that as `rat_gap=3` makes the signal explicit, reduces the model's learning burden, and makes the output interpretable ("rat_gap contributed 21% to the score" is meaningful to a human; "generation and highest_rat interacted in tree node 847" is not).

16 derived features computed from the 26 raw columns:

| Feature | Formula / Logic | What It Captures | Why It Matters |
|---------|----------------|-----------------|----------------|
| `rat_gap` | rank(generation) - rank(highest_rat) | Gap between device capability and actual network used | Direct underservice measure. rat_gap=0 means subscriber gets what their device supports. rat_gap=3 means 5G device stuck on 2G. |
| `attach_composite` | 0.5×s1_mme + 0.3×iu_attach + 0.2×gb_attach | Single network quality score per subscriber | Combines 3 attach rates into one metric weighted by RAT importance (4G carries 67% of traffic → highest weight). Reduces 3 correlated features to 1 informative signal. |
| `traffic_concentration` | max(t2g,t3g,t4g,t5g) / dou_total | How dependent on a single RAT | Concentration=1.0 means all traffic on one RAT — fragile. If that RAT degrades, subscriber loses 100% of data. Concentration=0.5 means distributed — more resilient. |
| `sim_bottleneck` | 1 if usim=0 AND generation ≥ 3G | Device supports higher RAT but SIM blocks it | Identifies subscribers where the limiting factor is SIM, not network or device. Direct CVM target: SIM upgrade campaign. |
| `area_peer_deviation` | (subscriber_dou - area_mean) / area_std | Z-score of usage relative to local peers | A subscriber using 500MB in Tunis (avg 18GB) is a z=-2.3 anomaly. The same 500MB in a rural area (avg 600MB) is z=-0.2, normal. Context-aware anomaly detection. |
| `voice_data_ratio` | duration / (dou_total/1e9 + ε) | Voice-centric vs data-centric profile shape | High ratio = voice-heavy (FeaturePhone behavior). Low ratio = data-heavy (SmartPhone behavior). A SmartPhone with high voice_data_ratio is anomalous — why isn't this subscriber using data? |
| `dou_gb` | dou_total / 1,073,741,824 | Data usage in human-readable GB | Normalization for model input and interpretability |
| `duration_min` | duration / 60 | Voice in minutes | Same — normalization |
| `traffic_4g_ratio` | traffic_4g / dou_total | Proportion of data on 4G | 4G adoption indicator. Low ratio for a 4G-capable subscriber = something is wrong. |
| `traffic_5g_ratio` | traffic_5g / dou_total | Proportion of data on 5G | 5G adoption tracking. High value = early adopter segment. |
| `voice_3g_ratio` | voice_onlinetime_3g / duration | Voice time on 3G vs total voice | Measures CS-fallback behavior. If voice_3g_ratio is high, subscriber's voice is handled by 3G even though they might have VoLTE capability — VoLTE adoption gap. |
| `device_tier` | ordinal encode(brand × tertype × generation) | Composite device quality score | Groups subscriber into device segments without high-cardinality model/brand features. Tier 1: premium 5G smartphone. Tier 5: basic 2G feature phone. |
| `is_5g_capable` | 1 if "NR" in generation | Binary 5G readiness | Fast filter for 5G-specific analysis. 12% of subscribers are 5G-capable. |
| `is_silent` | 1 if usertype = "Silent User" | Binary churn flag | Direct churn risk indicator. 12% of the base. |
| `is_voice_only` | 1 if usertype = "Voice User" | Voice-centric profile | 18% of base. Potential data upsell target for CVM. |
| `area_attach_deviation` | (attach_composite - area_mean) / area_std | Network quality vs area peers | Same z-score logic as area_peer_deviation but for network quality. Finds subscribers with worse attach rates than their neighbors — likely device or SIM issue, not area-wide network issue. |

These engineered features turn raw measurements into ML-ready signals that encode **telecom domain knowledge** — the kind of relationships a network engineer would reason about, made explicit for the models.

### 5.3 New ML/DL Model Architecture (v3.0)

Overview — 5 models, each with a distinct role in the intelligence pipeline:

| # | Model | Algorithm | What It Replaces |
|---|-------|-----------|-----------------|
| 1 | **CEM Experience Score** | GradientBoosting | SLA Risk |
| 2 | **Experience Anomaly** | Autoencoder (PyTorch) | IsolationForest |
| 3 | **Churn Trajectory** | LSTM/GRU (PyTorch) | Revenue IF (deprecated) |
| 4 | **RAT Underservice** | XGBoost | New |
| 5 | **O+B Correlation** | Pearson + Spearman + Granger | Enhanced |

---

#### Model 1: CEM Experience Score — GradientBoostingRegressor

**What it does:** Takes a subscriber's full profile (26 raw + 16 engineered features) and outputs a single experience quality score between 0 (worst) and 1 (best), plus a ranked list of which features contributed most to the score.

**Why GradientBoosting and not a neural network?**  
This model feeds the L4 Agent. When the agent auto-generates an action like "Subscriber cluster in Sfax Medina experiencing degraded service," it needs to explain WHY. GradientBoosting provides native feature importance — it can say "68% of the degradation is driven by attach_composite, 15% by rat_gap, 12% by traffic_concentration." A neural network would give the same score but as a black box. In ADN L4 operations, an unexplainable action is an unapprovable action. The human operator reviewing the agent's recommendation needs to see the reasoning, not just a number.

**Why not keep the current SLA Risk model as-is?**  
The current model was trained on 6 synthetic OSS features (latency, jitter, packet loss, throughput, call drops). The real BSS data has 26 completely different features across 4 dimensions (device, usage, network quality, geography). The model architecture (GBR) stays because it's the right tool — but the feature space, training data, and target variable all change. It's effectively a new model.

**Input features (key ones):**
- `attach_composite` — weighted quality score from s1_mme_sr (50%), iu_attach_sr (30%), gb_attach_sr (20%). Why these weights? S1 (4G) matters most because 4G carries 67% of total traffic volume in the dataset. 3G carries 4%, 2G carries 0.05%.
- `rat_gap` — difference between what the device supports and what it actually uses. A subscriber with a 5G phone stuck on 2G has rat_gap=3. This directly measures underservice.
- `traffic_concentration` — if 99% of a subscriber's data goes through one RAT, they're fragile. If that RAT degrades, they lose everything.
- `area_peer_deviation` — how a subscriber compares to peers in the same delegation. A subscriber using 500MB in Tunis (where avg is 18GB) is anomalous; 500MB in a rural delegation might be normal.
- `sim_bottleneck` — binary flag: device supports 4G+ but usim_flag=0. This subscriber is being limited by their SIM card, not the network. Different root cause = different remediation.

**Training approach:**  
Semi-supervised. I don't have explicit experience labels (no one labeled 500K subscribers as "good experience" or "bad experience"). Instead, I construct proxy labels from the data itself:
- Subscribers with attach_composite > 0.9, highest_rat matching device generation, dou_total in top 60% for their usertype → score near 1.0
- Silent Users with attach_composite = 0, rat_gap > 2 → score near 0.0
- Everyone else is interpolated based on feature distance from these anchors

**Why this is sound:** In CEM, experience IS the combination of these measurable factors. If a subscriber has a 5G phone, successfully attaches to 5G, and consumes data normally — they have good experience by definition. We're not guessing — we're encoding telecom domain knowledge into the target variable.

**Output:** `{ score: 0.73, explanation: { attach_composite: 0.42, rat_gap: 0.21, traffic_concentration: 0.15, ... } }`

---

#### Model 2: Experience Anomaly Detector — Autoencoder (PyTorch)

**What it does:** Learns what a "normal" subscriber profile looks like, then flags any subscriber whose profile is unusual — not just on one dimension, but across the interaction of ALL dimensions simultaneously.

**Architecture:**
```
Input (N features, normalized [0,1])
    → Dense(128, ReLU, BatchNorm, Dropout 0.2)
    → Dense(64, ReLU, BatchNorm, Dropout 0.2)
    → Dense(32, ReLU)                            ← bottleneck (latent space)
    → Dense(64, ReLU, BatchNorm, Dropout 0.2)
    → Dense(128, ReLU, BatchNorm, Dropout 0.2)
    → Dense(N, Sigmoid)                           ← reconstruction

Loss:     MSE between input and reconstruction
Anomaly:  reconstruction_error > μ + kσ  (k tuned on validation set)
Severity: proportional to how far above threshold
```

**Why Autoencoder and not IsolationForest?**  
This is the most important algorithmic decision in the upgrade, so I want to be precise about the reasoning.

IsolationForest detects anomalies by measuring how easy it is to isolate a data point. It builds random trees, splits on random features, and counts how few splits it takes to separate a point. This works well when anomalies are extreme on individual features. But it has a fundamental limitation: **it doesn't learn feature interactions**.

Real example from the BSS data: Consider a subscriber with `brand=APPLE, model=IPHONE 16 PRO MAX, generation=2G/3G/LTE/NR, dou_total=0, highest_rat=Unknown, usertype=Silent User`. Each feature individually isn't extreme — there are many Apple users, many silent users, many with Unknown RAT. But the **combination** is anomalous: someone with a top-tier 5G device who has zero usage. IsolationForest might miss this because no single feature is an outlier. An Autoencoder, trained on 500K normal profiles, would struggle to reconstruct this combination — the reconstruction error would spike because the model has never seen "premium 5G device + zero usage" in the training distribution.

Another example: `generation=2G/3G/LTE, s1_mme_sr=1.0, traffic_4g=0, traffic_3g=95%_of_dou`. The subscriber successfully attaches to 4G (s1_mme_sr=1.0) but all their data goes through 3G. Each feature alone is normal. The contradiction across features is what makes it anomalous — and that's exactly what reconstruction error captures.

**Why not a Variational Autoencoder (VAE)?**  
VAE adds a KL-divergence term that forces the latent space to follow a Gaussian distribution. This is useful for generation (creating new synthetic subscribers), but we don't need generation — we need detection. A standard AE with MSE loss is simpler, faster to train, and the reconstruction error is more directly interpretable as "how different is this subscriber from normal." Simpler model = easier to debug, faster inference in the pipeline's 2-minute cycle.

**Training strategy:**
- Train ONLY on "healthy" subscribers (Data Users with attach_composite > 0.8, rat_gap ≤ 1, duration > 0). Why? Because we want the model to learn what NORMAL looks like. If we include anomalies in training, the model learns to reconstruct them too, and the error threshold becomes meaningless.
- Validation set: 10% holdout of healthy subscribers + all Silent Users (known anomalous cohort) + manually constructed edge cases.
- Threshold tuning: plot reconstruction error distribution for healthy vs anomalous validation sets, pick k where F1 is maximized.

**Why not just use the CEM Score for anomaly detection?**  
The CEM Score (Model 1) is supervised — it predicts a known target. The Autoencoder is unsupervised — it finds patterns I didn't anticipate. These are complementary, not redundant. A subscriber could have a CEM score of 0.65 (mediocre but not alarming) but an anomaly flag because their specific combination of features has never been seen before. The CEM Score tells you "how good is this subscriber's experience." The Autoencoder tells you "is this subscriber's profile weird." Both are actionable by the L4 Agent.

**Output:** `{ is_anomaly: true, reconstruction_error: 0.0847, severity: "warning", top_reconstruction_gaps: ["traffic_4g", "s1_mme_sr", "rat_gap"] }`

The `top_reconstruction_gaps` field tells which features the model struggled most to reconstruct — pointing directly at what makes this subscriber anomalous.

---

#### Model 3: Churn Trajectory Predictor — LSTM (PyTorch)

**What it does:** Takes a subscriber's experience history across W rolling windows and predicts the probability of churn (going Silent) in the next N windows.

**Why this model exists:**  
The BSS data shows 12% Silent Users — 58,000 subscribers with zero usage in March 2026. These are churned or about to churn. But churn didn't happen overnight. Before going silent, a subscriber likely reduced data usage, switched from 4G to 2G, shortened call duration, maybe had failed attach attempts. These are temporal patterns — sequences of degradation that unfold over time.

Models 1 and 2 (CEM Score and Autoencoder) are point-in-time: they look at a subscriber's current state and say "right now, this is good/bad/weird." But they can't say "this subscriber is on a trajectory toward churn." That requires sequential modeling.

**Why LSTM and not a simpler approach?**

*Why not logistic regression on window deltas?*  
You could compute Δ(dou_total) between windows and use it as a feature. But this only captures one-step change. A subscriber who dropped 20% this window might be fluctuating (recovers next window) or degrading (continues dropping). The difference is in the **shape of the sequence**, and logistic regression on deltas loses that context.

*Why not a 1D CNN?*  
CNNs detect local patterns through fixed-size kernels. An LSTM maintains a hidden state that carries information across the entire sequence. For churn, what matters is the long-range pattern: a subscriber who was stable for 8 windows then dropped for 2 is different from one who gradually declined over 10 windows. LSTM's gating mechanism (forget gate, input gate, output gate) is specifically designed to learn what to remember and what to forget across long sequences.

*Why not Transformer?*  
Transformers excel at very long sequences (hundreds to thousands of steps) where attention over the full sequence matters. Our rolling window produces W=10-20 steps — short enough that LSTM handles it efficiently without the overhead of self-attention. Transformers also need more data to train effectively due to their larger parameter count. With 500K subscribers and ~20 windows each, LSTM is the right scale.

**Architecture:**
```
Input: [batch_size, W, features_per_window]
    W = number of rolling windows (10-20)
    features_per_window = 8 key temporal features

    → LSTM(64 hidden units, return_sequences=True)
    → Dropout(0.3)
    → LSTM(32 hidden units, return_sequences=False)
    → Dropout(0.3)
    → Dense(16, ReLU)
    → Dense(1, Sigmoid)   → churn probability [0, 1]
```

**Why 2 LSTM layers?**  
The first LSTM layer (64 units, return_sequences=True) captures low-level temporal patterns: "usage dropped between window t and t+1." It outputs a hidden state for every timestep. The second LSTM layer (32 units, return_sequences=False) captures higher-level patterns across the full sequence: "the overall trajectory is downward with increasing variance." It outputs a single summary vector. This hierarchical representation is standard for sequence classification — one layer isn't deep enough to capture both local transitions and global trajectory shape.

**Window features per subscriber (8 dimensions per timestep):**
```
1. dou_total_normalized      — data usage relative to subscriber's baseline
2. duration_normalized        — voice usage relative to baseline
3. attach_composite           — network quality composite
4. rat_gap                    — underservice gap
5. traffic_4g_ratio           — proportion of data on 4G
6. traffic_5g_ratio           — proportion of data on 5G
7. usertype_encoded           — Data=2, Voice=1, Silent=0
8. area_peer_deviation        — how subscriber compares to local peers
```

**Why these 8 and not all 42 features?**  
Temporal models need features that CHANGE over time. Brand doesn't change. Device model rarely changes. Geography might change but is noisy. The 8 selected features are the ones that reflect subscriber behavior and experience quality — the things that shift as someone moves toward churn. Including static features would add noise without signal.

**Training approach:**
- **Label construction:** A subscriber is labeled "churned" if their usertype transitions to Silent in a later window and stays Silent. A subscriber is "active" if they maintain Data or Voice status.
- **Class imbalance:** 12% Silent Users means ~88/12 imbalance. Handle with weighted loss (positive class weight = 7.3) rather than oversampling. Why? Oversampling (SMOTE etc.) creates synthetic temporal sequences that don't reflect real churn trajectories — the fabricated gradual decline patterns would be artificial. Weighted loss preserves the real distribution while penalizing missed churners.
- **Sequence construction:** Each subscriber gets a sequence of W windows. For subscribers who churn mid-sequence, the label is 1 for windows preceding churn. For active subscribers, all windows are labeled 0.

**Why this model depends on the rolling window engine:**  
Without the engine, I have ONE snapshot per subscriber. An LSTM with sequence length 1 is just a feedforward network — all the temporal power is wasted. The rolling window engine creates the W-step sequences by sampling subscribers across cycles. After 10 pipeline cycles (20 minutes of simulated time), each subscriber has a 10-step history. This is the minimum viable input for the LSTM to learn trajectory patterns.

**Output:** `{ churn_probability: 0.82, trajectory_class: "degrading", windows_to_churn: ~3 }`

---

#### Model 4: RAT Underservice Classifier — XGBoost

**What it does:** For each subscriber, determines if they're receiving a lower quality of service than what their device and SIM can support, and identifies the root cause.

**Why this model exists:**  
This is the model that directly enables CVM (Customer Value Management) actions. In the BSS data, I can see:
- A subscriber's device supports `2G/3G/LTE/NR` (5G-capable)
- Their `highest_rat` is `2G`
- Their `s1_mme_sr` is `0.0` (never attached to 4G)

That subscriber is underserved. But WHY? There are multiple possible causes:
1. **SIM bottleneck** — usim_flag=0, legacy 2G SIM can't authenticate on 3G/4G → CVM action: SIM upgrade campaign
2. **Coverage gap** — their delegation has poor 4G/5G coverage → Network planning action: infrastructure investment
3. **Device misconfiguration** — device supports 4G but settings are wrong → CVM action: push APN configuration
4. **Network congestion** — cell is overloaded, subscriber gets pushed to lower RAT → OSS action: load balancing

A simple rule (if rat_gap > 0 then underserved) catches the obvious cases. But the ROOT CAUSE classification requires a model that considers all factors simultaneously.

**Why XGBoost and not a neural network?**  
This is a classification task with ~15 tabular features and clear decision boundaries. XGBoost dominates tabular classification because it handles feature interactions through gradient-boosted trees (inherently captures "IF usim=0 AND generation=4G THEN sim_bottleneck"), handles mixed feature types (numeric + categorical) natively, and trains fast on 500K rows. A neural network would need careful feature encoding, more tuning, and would likely underperform XGBoost on tabular data — this is well-established in ML literature (Grinsztajn et al., 2022: "Why do tree-based models still outperform deep learning on tabular data?").

**Input features:**
```
- generation_rank          (ordinal: 2G=1, 2G/3G=2, 2G/3G/LTE=3, 2G/3G/LTE/NR=4)
- highest_rat_rank         (ordinal: 2G=1, 3G=2, 4G=3, 5G=4, Unknown=0)
- rat_gap                  (generation_rank - highest_rat_rank)
- usim_flag                (SIM capability)
- volte_flag               (VoLTE capability)
- s1_mme_sr                (4G attach success)
- iu_attach_sr             (3G attach success)
- gb_attach_sr             (2G attach success)
- dou_total_normalized     (usage level)
- traffic_4g_ratio         (4G usage proportion)
- traffic_5g_ratio         (5G usage proportion)
- area_encoded             (governorate — captures regional coverage differences)
- tertype_encoded          (SmartPhone vs FeaturePhone vs CPE)
- brand_encoded            (top 10 brands + "other")
- session_flag             (active data session indicator)
```

**Output:** Multi-class classification:
```
{
  is_underserved: true,
  root_cause: "sim_bottleneck",    // or "coverage_gap", "congestion", "device_config", "not_underserved"
  confidence: 0.91,
  recommended_action: "sim_upgrade_campaign"
}
```

**Why this model is unique to real data:**  
The synthetic pipeline had no device information — no brand, no model, no generation, no USIM flag. It was impossible to detect underservice because there was no way to know what the subscriber's device COULD do. The real TT data has 7 device features. This model could not exist without real data.

**Training approach:**  
Label construction from data rules (semi-supervised):
- `rat_gap > 1 AND usim_flag = 0` → label = "sim_bottleneck"
- `rat_gap > 1 AND usim_flag = 1 AND attach_sr = 0` → label = "coverage_gap"
- `rat_gap > 1 AND usim_flag = 1 AND attach_sr > 0 AND traffic on lower RAT` → label = "congestion"
- `rat_gap ≤ 1` → label = "not_underserved"

These rules create initial labels. XGBoost then learns the nuanced decision boundaries — capturing cases the rules miss (e.g., a subscriber with rat_gap=1 but anomalously low traffic_4g_ratio might still be underserved).

---

#### Model 5: O+B Correlation Engine — Pearson + Spearman + Granger Causality

**What it does:** Measures the statistical relationship between OSS network KPIs and BSS subscriber experience metrics, and determines causal direction.

**Why three correlation methods?**

**Pearson** measures linear correlation. If cell throughput drops and subscriber dou_total drops proportionally, Pearson catches it. But Pearson assumes linearity — if the relationship is "throughput drops below a threshold and then dou_total collapses" (nonlinear, step-function), Pearson underestimates the relationship.

**Spearman** measures monotonic correlation (rank-based). It catches nonlinear but monotonic relationships: "when throughput goes down, dou_total goes down, but not proportionally." This handles the threshold effects common in telecom networks.

**Granger Causality** adds something neither Pearson nor Spearman can: **temporal direction**. It tests whether past values of OSS KPIs help predict future values of BSS metrics beyond what BSS metrics' own history predicts. If yes, OSS "Granger-causes" BSS — the network degradation PRECEDES the subscriber impact.

Why this matters for the platform: Correlation alone is descriptive ("cell KPIs and subscriber metrics moved together"). Granger causality is prescriptive ("fixing the cell will fix the subscriber experience, not the other way around"). This directly feeds the L4 Agent's action generation — it can say "remediate cell X because its degradation is CAUSING subscriber experience drops" vs. "cell X and subscriber experience are correlated but we don't know which direction."

**How the join works (when OSS arrives):**
```
BSS aggregation:
  - Group 500K subscribers by (area, area_delegation, highest_rat)
  - Compute per-group: mean CEM score, anomaly rate, mean attach_composite,
    mean dou_total, churn probability distribution

OSS aggregation:
  - Group cell KPIs by (site_region, site_delegation, rat_type)
  - Compute per-group: mean throughput, mean latency, alarm rate,
    packet loss, jitter

Join key:
  BSS (area, area_delegation, highest_rat) ↔ OSS (site_region, site_delegation, rat_type)

Result: paired time series per (region, delegation, RAT) across rolling windows
  → Pearson/Spearman on each pair
  → Granger test on lagged pairs (lag = 1 to 5 windows)
```

**Why join on geography and not on cell ID?**  
The BSS data has no cell ID — it doesn't tell which specific cell served each subscriber. What it has is `area` (governorate) and `area_delegation` (delegation). The OSS data will have cell-level identifiers plus site location. The join happens at the delegation level — aggregating all cells in a delegation and all subscribers in the same delegation. This is coarser than cell-level but it's what the data supports. When we aggregate across multiple cells and subscribers in the same area, the noise averages out and the true OSS↔BSS relationship becomes clearer.

---

### The Full Model Pipeline — How They Work Together

```
Raw BSS Data (500K subscribers, 26 features)
        │
        ▼
Feature Engineering (16 derived features → 42 total)
        │
        ├──→ Model 1: CEM Score  ──→ "How good is this subscriber's experience?"
        │                              → feeds L4 Agent with explainable scores
        │
        ├──→ Model 2: Autoencoder ──→ "Is this subscriber's profile abnormal?"
        │                              → catches patterns Model 1 wasn't trained for
        │
        ├──→ Model 4: RAT Underservice ──→ "Is this subscriber getting less than they should?"
        │                                    → generates CVM action recommendations
        │
        └──→ Rolling Window Buffer
                │
                ▼ (after W windows accumulated)
                │
                ├──→ Model 3: LSTM Churn ──→ "Is this subscriber on a path to churn?"
                │                              → early warning before subscriber goes Silent
                │
                └──→ Model 5: O+B Correlation ──→ "Is network causing experience drops?"
                     (when OSS available)           → root cause attribution for L4 Agent
```

Models 1, 2, and 4 run every pipeline cycle (2 minutes) on each batch.  
Model 3 runs every cycle but only produces meaningful output after W windows of history.  
Model 5 runs every cycle but only when OSS data is available for the join.

**Why this order matters:**  
The CEM Score (Model 1) produces the target variable that the correlation engine (Model 5) uses on the BSS side. The Autoencoder (Model 2) catches anomalies that the CEM Score might rate as "mediocre but not critical" — different detection surfaces for different failure modes. The LSTM (Model 3) watches the CEM Score over time — a stable 0.65 is different from a declining 0.85→0.72→0.65. The Underservice Classifier (Model 4) identifies the root cause for a specific class of low CEM scores. Together, they answer WHAT (score), HOW UNUSUAL (anomaly), WHY (underservice root cause), WHAT'S NEXT (churn trajectory), and WHO'S RESPONSIBLE (O+B correlation).

---

### Why PyTorch and Not TensorFlow

- **Model complexity:** The Autoencoder is ~5 layers, the LSTM is ~4 layers. These are small models. PyTorch's eager execution and simple `nn.Module` class make these trivial to implement, debug, and modify. TensorFlow's graph-based execution adds overhead for no benefit at this scale.
- **Production serving:** Both models export to TorchScript for inference without Python overhead. The ai-service loads TorchScript models via `torch.jit.load()` — same pattern as loading joblib models for scikit-learn.
- **Ecosystem:** PyTorch dominates research and industry for new projects in 2026. Community support, tutorials, and debugging tools are stronger.
- **Container size:** `torch` (CPU-only) adds ~150MB to the ai-service Docker image. `tensorflow` would add ~500MB+. In a cloud-native architecture where every container matters, this is significant.

---

## 6. Architecture: Cloud-Native by Design

Every component is a stateless containerized microservice. State lives in PostgreSQL (relational), MinIO (object storage), or Redis (window buffer — planned).

| Local Component | HCS Equivalent | Status |
|----------------|---------------|--------|
| PostgreSQL 16 (Docker) | **RDS** (Relational Database Service) | 1:1 mapping |
| MinIO (Docker) | **OBS** (Object Storage Service) | S3-compatible, direct migration |
| Docker containers | **ECS** (Elastic Cloud Server) | Each service = 1 ECS instance |
| Ollama + Qwen2.5:7b | **ModelArts / EI** (Enterprise Intelligence) | LLM serving endpoint |
| Prometheus + Grafana | **AOM** (Application Operations Management) | Monitoring migration |
| GitHub Actions CI/CD | **CodeArts** (DevOps pipeline) | Pipeline migration |

The Docker Compose file IS the HCS deployment blueprint. No service has local file dependencies. No monolithic patterns. This is not a local project with cloud aspirations — it's a cloud solution being developed locally.

---

## 7. Implementation Sequence

```
                    NOW (April 2026)
                        │
                        ▼
    ┌──── Phase 3.5: Real Data + Rolling Window Engine ────┐
    │  - BSS CSV loader + PostgreSQL staging                │
    │  - Feature engineering (16 derived features)          │
    │  - Rolling window engine in pipeline-worker           │
    │  - BLOCKED ON: OSS data arrival                       │
    └───────────────────────┬───────────────────────────────┘
                            ▼
    ┌──── Phase 4.5: Model v3.0 (CEM Models) ─────────────┐
    │  - CEM Experience Score (GBR retrained)               │
    │  - Experience Anomaly (Autoencoder, PyTorch)           │
    │  - RAT Underservice Classifier (XGBoost)              │
    │  - O+B Correlation with real paired OSS+BSS           │
    └───────────────────────┬───────────────────────────────┘
                            ▼
    ┌──── Phase DL: Temporal Models ───────────────────────┐
    │  - LSTM Churn Trajectory (needs accumulated windows)  │
    │  - Granger Causality in correlation engine            │
    │  - L4 Agent playbooks updated for new outputs         │
    └───────────────────────┬───────────────────────────────┘
                            ▼
    ┌──── Phase 6: HCS Deployment ─────────────────────────┐
    │  - Huawei Cloud Stack mapping (OBS/RDS/ECS)           │
    │  - Deployment evidence + screenshots                   │
    └───────────────────────┬───────────────────────────────┘
                            ▼
    ┌──── Final: Report + Presentation ────────────────────┐
    │  - PFE report                                         │
    │  - Technical defense + demo                           │
    └──────────────────────────────────────────────────────┘
```

**Current blocker:** OSS data. I've contacted the data provider with exact specifications of what I need (same month, same geography, cell-level KPIs). BSS preprocessing and feature engineering can begin immediately.

---

## 8. What Makes This Project Different

1. **Real operator data** — not synthetic, not simulated. 500K real Tunisie Telecom subscribers.
2. **O+B convergence** — not just OSS dashboards or BSS analytics separately, but the correlation between them with causal inference.
3. **Deep Learning on telecom CEM** — Autoencoder for multivariate anomaly detection, LSTM for temporal churn prediction. Not just classical ML.
4. **ADN L4 autonomy** — the system doesn't just detect and display. It generates actions, auto-approves safe ones, and executes real backend operations. Human stays in the loop for high-risk decisions.
5. **Cloud-native architecture** — 10 containerized microservices, CI/CD pipeline, 3-layer data lake, full observability. Direct mapping to Huawei Cloud Stack.
6. **Production-grade engineering** — JWT + OAuth auth, SSR security patterns, PostgreSQL audit trails, Prometheus metrics, Grafana dashboards. This is not a Jupyter notebook.

---

## Summary

I understand what I'm building (an ADN L4 CEM intelligence platform), why I'm building it this way (O+B convergence on real data, cloud-native for HCS), what the data tells me (500K subscribers across 26 CEM dimensions), what models I need and why each algorithm was chosen (GBR for interpretability, AE for multivariate anomaly, LSTM for temporal churn, XGBoost for classification), and what's blocking me (OSS data for the convergence layer). The moment OSS arrives, I execute.
