# Data Augmentation Module — Bootstrap Simulation, Subordinate to Real Data

> Reframing rationale: experts asked whether the "generator engine" is an
> independent component or a model-completion mechanism.
> **Answer: it is a Data Augmentation Module subordinate to the real data.**
> It only fills months for which TT did not provide a real dump, and it
> preserves the joint distribution of the real data via stratified bootstrap
> with controlled temporal drift.

---

## 1. Why we need it

| Data | Real coverage | Augmented coverage |
|---|---|---|
| BSS (subscriber CEM) | Feb 2026 (468K rows) + Mar 2026 (500K rows) — **968K real** | Jan + Apr + May 2026 — **1.5M simulated** |
| OSS (cell KPIs) | Mar 2026 (2.49M) + Apr 2026 (16.32M) — **18.81M real** | Jan + Feb + May + Jun 2026 — **200K simulated** |

The temporal models (LSTM Churn, monthly Granger) require contiguous
history. Without augmentation, the panel has gaps that break stationarity
and prevent month-over-month drift modeling. Augmentation closes those gaps
**without claiming the synthetic months are real measurements** — every
synthetic record is identifiable in the database via its `month_year` value
and the simulator's identity-replacement IMSI prefix.

## 2. Method (BSS — `services/data-ingest/generate_bss_months.py`)

1. **Stratified bootstrap.** Sample 500K rows with replacement from the 968K
   real Feb+Mar dump. Strata are `(area, generation, usertype)` — preserves
   the joint categorical distribution exactly.
2. **Log-normal perturbation.** Numerical columns multiplied by
   `exp(N(0, 0.06))`. Prevents exact duplicates while keeping moments stable.
3. **Per-month drift.** Applied as multiplicative factors on DOU and 5G
   traffic plus categorical migration rules:

   | Month | DOU factor | 5G traffic factor | Behavior shift |
   |---|---|---|---|
   | Jan 2026 | ×0.88 | ×0.65 | 8% 5G→4G demotion · -3% silent users |
   | Apr 2026 | ×1.18 | ×1.35 | 12% 4G→5G promotion · +4% silent |
   | May 2026 | ×1.35 | ×1.65 | 12% 4G→5G promotion · +8% silent |

4. **Identity replacement.** Every record receives a fresh IMSI
   (`60502` + 10 digits) and TAC (15 digits). Real identities never appear.
5. **Consistency guard.** If the sum of traffic_2g/3g/4g/5g exceeds
   `1.5 × dou_total`, DOU is bumped up to maintain physical plausibility.

## 3. Method (OSS — `services/data-ingest/simulate_oss_bootstrap.py`)

* Reservoir of 200K real records (sampled from 18.8M).
* Resample with replacement, add Gaussian noise on numerical columns, apply
  per-month load/latency drift.
* Cell IDs are remapped to a synthetic prefix to keep them distinct from
  real IDs.

## 4. Validation

The notebook `notebooks/00_data_understanding_eda.py` (Section 9) overlays
real-month vs simulated-month distributions and runs a Kolmogorov–Smirnov
two-sample test on `dou_total`. Results land in
`notebooks/data/eda/summary.json` under `9_generator`.

**Expected reading:** the KS test rejects equality (drift is intentional).
The accompanying KDE overlay shows the simulated distribution sits within
1.5× of the real envelope — close enough to preserve correlations, far
enough to introduce realistic month-over-month dynamics.

## 5. Defense Q&A

| Question | Answer |
|---|---|
| Is the generator a separate model? | No. It is a **subordinate Data Augmentation Module**. Models train on real + simulated combined; the simulator does not output predictions. |
| Why not train only on real data? | Two months are not enough for LSTM Churn (needs sequence length ≥ 4) or monthly Granger (needs at least 4 panel rows per area). Augmentation buys the temporal horizon at the cost of carefully bounded synthesis. |
| What if reviewers ask whether models overfit on synthesis? | Hold-out evaluation always uses a real month (Mar 2026 for BSS, Apr 2026 for OSS). Reported metrics in `docs/v3_real_data_training_report.md` are real-month metrics, not real+sim. |
| Could this be removed? | Yes, if TT supplies 4+ months of real data. The module is data-driven (one CSV in, one CSV out) and does not change model architecture. |
