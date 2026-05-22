# Notebook 01 — Plain-Language Explainer (ETL + Feature Engineering)

> Audience: you (Souhayl) — explained from scratch.
> What this notebook does: **transforms raw CSV files into a clean, feature-rich training dataset.**

---

## The Big Picture

Raw data is unusable by ML models. Models need:
- Numeric columns (no strings unless one-hot encoded)
- No NaNs (or they crash / produce nonsense)
- Reasonable value ranges (no `10^12` values dominating gradients)
- A clear target column to predict

**Notebook 01 is the kitchen.** It takes raw ingredients (CSVs) and produces a meal (parquet warehouse) that notebooks 02, 03, 04 can eat directly.

This is **CRISP-DM Phase 3 — Data Preparation.**

---

## Concepts Used

### 1. MinIO (S3-compatible Object Storage)

**MinIO** is an open-source server that speaks the same protocol as Amazon S3. Files are organized into **buckets** (like folders).

We use 3 buckets:
- `raw/` — exact-byte copies of TT_data CSVs (no modification)
- `processed/` — cleaned + normalized parquets
- `curated/` — final training-ready warehouse + cells + splits

Why 3 layers? **Data Lake pattern** (also called "Bronze/Silver/Gold"). It means you can always re-do downstream steps without re-uploading source data.

`boto3` is the Python library to talk to MinIO/S3.

---

### 2. Parquet (Columnar File Format)

CSV is **row-oriented**: every line is one row. Bad for analytics because reading "all values of column X" requires scanning every line.

**Parquet** is **column-oriented**: each column stored separately, compressed. Reading one column is fast. Reading all 8M `dou_total` values from CSV: 10 seconds. From Parquet: 0.3 seconds.

Used by: this notebook, Spark, BigQuery, every modern data lake.

Saved via `df.to_parquet(...)`; loaded via `pd.read_parquet(...)`.

---

### 3. IterativeImputer (MICE-style)

**Problem:** A column has NaNs. You can't feed NaNs to LightGBM/XGBoost (they crash) or to neural networks (they propagate to all weights).

**Simple imputation:** fill NaNs with the column mean / median / mode. Cheap but loses information.

**IterativeImputer (`sklearn.impute.IterativeImputer`):** smarter approach. Treats each NaN column as a **regression problem**:
1. Initialize NaNs with median.
2. For each column with NaN: predict NaN values using OTHER columns as features (Bayesian Ridge regressor).
3. Repeat until values stop changing (convergence).

This is the same idea as **MICE** (Multiple Imputation by Chained Equations) in statistics.

We **save the fitted imputer** as a joblib file. Inference time: use SAME imputer (don't fit a new one on test data — that's leakage).

---

### 4. Winsorize (Outlier Capping)

**Problem:** A single subscriber has `dou_total = 5.8 × 10^12` bytes (5.8 terabytes in a month). Real or sensor glitch? Either way, this one value dominates the mean and breaks ML training.

**Winsorize:** cap values at a percentile. We cap at **p99** = the 99th percentile.

```python
upper_bound = df['col'].quantile(0.99)
df['col'] = df['col'].clip(upper=upper_bound)
```

Now the top 1% of values all become equal to `upper_bound`. The shape of the distribution is preserved; the extreme tail is flattened.

**Bounds saved to joblib** — same reason as imputer: apply same bound at inference.

Why p99 not p99.5 or p95? Industry convention. A formal ablation would compare model metrics under each choice (deferred — see findings.md G3).

---

### 5. CEM Score (The Target)

The CEM score is what notebook 02 LEARNS TO PREDICT. It must be computed in this notebook (01) and saved as a column of `warehouse.parquet`.

**Formula:**
```
CEM = 0.40 · attach_success_rate
    + 0.30 · traffic_4g_share
    + 0.20 · oss_data_integrity
    + 0.10 · (1 - oss_call_drop_rate)
```

Each component is a number in `[0, 1]`. The weighted sum is in `[0, 1]`.

**Why these weights?**
- 0.40 attach: if the subscriber can't connect, nothing else matters → biggest weight
- 0.30 4G share: modern RAT = better experience (Huawei SmartCare convention)
- 0.20 integrity: OSS area-level data quality (good cells → good experience)
- 0.10 CDR-inverse: rare anomaly signal

These weights are **HARDCODED, not learned**. Changing them changes the target → changes the model's behavior. The defense reviewer will ask: "why these weights?" Answer: domain expert (Huawei) + sensitivity analysis (deferred).

The assertion `assert weights sum to 1.0` prevents typo bugs.

---

### 6. Derived Features (Feature Engineering)

Raw columns are not enough. We compute NEW columns that REVEAL patterns invisible to raw values:

| Feature | Formula | Meaning |
|---|---|---|
| `data_intensity` | `dou_total / max(duration, 1)` | bytes per second of session — heavy user signal |
| `traffic_2g_share` | `traffic_2g / dou_total` | % of usage stuck on 2G — underservice signal |
| `traffic_3g_share` | similar | |
| `traffic_4g_share` | similar | |
| `attach_gap` | `1 - mean(s1_mme_sr, iu_attach_sr, gb_attach_sr)` | overall network-attach failure rate |
| `is_4g_capable` | from `generation` column | whether subscriber's SIM supports 4G |
| `usim_bottleneck` | `usim_flag==0 AND is_4g_capable` | has 4G-capable SIM but didn't enable USIM |

The model can't easily discover `data_intensity` from `dou_total` + `duration` — it has to learn division, which trees do approximately. Feature engineering hands the model the right ratio directly.

---

### 7. OSS-Derived KPIs (3GPP Formulas)

Real OSS data has only `integrity %` and `call_drop_rate %` per cell. But Anomaly detection needs `latency` and `packet_loss` and `jitter`.

**Deterministic derivation** (from 3GPP RAN engineering practice):
- Base latency per RAT: `{'4G': 18ms, '3G': 55ms, '2G': 95ms}` (typical air-interface latency)
- Real latency = `base_latency × (1 + (100 - integrity) × 0.05)` — higher integrity → closer to baseline
- Packet loss = `(100 - integrity) × 0.5` — direct mapping
- Jitter = `latency × 0.15` — fixed proportion

These are NOT measured — they're **estimated from KPIs we have**. The VAE then learns the joint distribution of (integrity, CDR, latency, loss, jitter, etc.) and flags cells whose combination is anomalous.

Defense talking point: "real Tunisie Telecom OSS doesn't expose latency directly, so we derive it via standard 3GPP formulas — same approach Huawei SmartCare uses internally."

---

### 8. Train / Val / Test Split

**Why split?** To evaluate honestly.
- Train (70%): the model sees this and learns
- Val (15%): used during training for early stopping / hyperparameter tuning
- Test (15%): held out — model never sees it; metrics on test = honest performance estimate

**Stratified split:** ensure each `area` is proportionally represented in all 3 splits (prevents the test set being entirely Tunis).

**Temporal holdout:** the LAST month of data is held back entirely. Even if random split passes, temporal holdout reveals **drift** — does the model still work on data from a future month?

For thesis defense, BOTH numbers matter:
- Random-split metrics = best-case
- Temporal-holdout metrics = production-realistic

The current notebook does both ("dual policy split").

---

### 9. Dual-Mode Splits in Practice

```python
# After 15% test removed, val = 15/85 = 0.176 of the remaining
X_temp, X_test = train_test_split(X, test_size=0.15, stratify=X['area'])
X_train, X_val = train_test_split(X_temp, test_size=0.176, stratify=X_temp['area'])
```

The `0.176` was a code-smell — replaced with `SPLIT_VAL_FRAC / (SPLIT_TRAIN_FRAC + SPLIT_VAL_FRAC)` in the constants cell. Now readable.

---

### 10. What Is Missing (and Why)

**Pandera** is a Python library that lets you DECLARE the expected schema (column names, dtypes, ranges, regex patterns) and `validate(df)` raises if violated. Industry-standard for ETL pipelines. Currently not used → silent breakage risk if upstream CSV columns rename.

Deferred to next pass because adding pandera schemas at every stage boundary is mechanical but tedious.

**GroupKFold by area** is better than stratified random split for geographic data. Random split lets the SAME area appear in both train and test → trivial leakage of spatial patterns. GroupKFold guarantees no `area` overlap.

Deferred because changing splits changes downstream metrics → coordinate with notebooks 02/03/04.

---

## Glossary

| Term | Definition |
|---|---|
| ETL | Extract / Transform / Load — the data pipeline |
| MinIO | S3-compatible object storage server |
| Parquet | Column-oriented file format, fast for analytics |
| Bronze/Silver/Gold | Data lake convention (raw / cleaned / curated) |
| IterativeImputer | sklearn class — fills NaNs via iterative regression |
| MICE | Multiple Imputation by Chained Equations |
| Winsorize | Cap values at a percentile (we use p99) |
| CEM score | Customer Experience Management score ∈ [0,1], our prediction target |
| 3GPP | Standards body for cellular networks; source of latency baselines |
| RAT | Radio Access Technology (2G/3G/4G/5G) |
| Stratified split | Sample proportionally within each group (e.g., area) |
| Temporal holdout | Reserve future months as test → tests for drift |
| Pandera | Schema-assertion library for pandas DataFrames |
| GroupKFold | Cross-validation that keeps each group entirely in one fold |

---

## Quick Read

1. **Cell 0:** title + contract — what comes in, what goes out, what consumes it
2. **Cell 2 (new):** all constants. SEED=42. CEM weights (0.4, 0.3, 0.2, 0.1) sum to 1.0 (asserted).
3. **Cells 3–10:** upload TT_data CSVs to MinIO, read them back, normalize OSS.
4. **Cells 11–13 (clean + impute + winsorize):** drop garbage rows, fill NaNs via MICE, cap p99 outliers.
5. **Cells 14–17:** compute derived features (data_intensity, attach_gap, etc.).
6. **Cells 18–22:** OSS-derived KPIs (latency, loss, jitter via 3GPP) + per-area aggregation.
7. **Cells 23–28:** join BSS × OSS → warehouse.parquet. Compute CEM target via formula.
8. **Cells 29–32:** train/val/test split + temporal holdout + write splits.json.
9. **Cells 33–34:** sanity-check validation report.
