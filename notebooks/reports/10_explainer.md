# Notebook 10 — Plain-Language Explainer (Granger Causality Feature Gate)

> Audience: you (Souhayl) — every term defined from scratch.
> What this notebook does: **tests whether OSS network problems happen BEFORE subscriber-experience drops — i.e. whether the network "leads" the customer pain.**
> This is the statistical backbone of the defense pain hook: *"network anomalies are invisible to OSS until a customer complaint reaches Care."*

---

## The Big Picture

You want to claim: **network degradation precedes (and predicts) customer-experience drops.** That is a *causal-direction, time-ordered* claim. Plain correlation can't support it — correlation is symmetric (if X correlates with Y, Y correlates with X equally) and says nothing about *order in time*.

**Granger causality** is the right tool: it asks whether the PAST of X helps predict the FUTURE of Y, beyond what Y's own past already predicts. If yes, "X Granger-causes Y." This notebook runs that test for OSS KPIs (causes) against BSS experience metrics (effects) and writes the surviving edges to `granger_feature_gate.json`.

---

## Concepts Used

### 1. Time Series

A **time series** is a sequence of measurements ordered in time — here, monthly values of each metric per area. Granger causality is a *time-series* method: order matters, unlike the row-shuffled tables in notebooks 02/04.

### 2. Correlation ≠ Causation (and what Granger adds)

- **Correlation:** "integrity and CEM move together." Symmetric, timeless. Could be coincidence or a hidden common cause.
- **Granger causality:** "knowing integrity's last few months improves my forecast of CEM's next month, beyond CEM's own history." Directional and time-ordered.

**Important honesty caveat (and the notebook says this):** Granger causality is **predictive precedence**, NOT philosophical causation. It can be fooled by a confounder that drives both series. That's why we also want a reverse-Granger sanity test (below). For the defense, phrase it precisely: "Granger F-test shows OSS KPIs have *predictive precedence* over experience metrics" — defensible and correct.

### 3. The Granger F-test (how it actually works)

To test "does X Granger-cause Y?", fit two regressions:

- **Restricted model:** predict Y(t) from its OWN past — Y(t-1), Y(t-2), … Y(t-L).
- **Unrestricted model:** predict Y(t) from its own past PLUS X's past — X(t-1), …, X(t-L).

If adding X's past **significantly** reduces prediction error (residual sum of squares), X carries information about Y's future. An **F-test** compares the two models' residuals:

```
F = [(RSS_restricted − RSS_unrestricted) / L] / [RSS_unrestricted / (n − 2L − 1)]
```

A large F (small **p-value**) means "X's past genuinely helps" → Granger causality. The code uses statsmodels' `ssr_ftest` (sum-of-squared-residuals F-test), selected via the `GRANGER_FTEST` constant.

### 4. p-value (what "significant" means)

The **p-value** is the probability of seeing this much improvement *by random chance* if X actually had no predictive power. Small p = unlikely to be luck = significant. We use threshold `GRANGER_ALPHA = 0.05` (5%). An edge is flagged `significant` when its p < 0.05.

### 5. Lags (`GRANGER_MAX_LAG = 4`)

A **lag** is how many months back we look. Lag-1 = "last month's X". We test lags 1 through 4 (up to 4 months of precedence). Why 4? It's the assumed maximum horizon over which a network problem would still show up in experience metrics. The current code takes the **minimum p-value across lags 1..4** — which is statistically loose (see "Known Gaps"); the proper way is to pick the lag by an information criterion.

### 6. Panel Data (area × month)

We don't have one long national time series — we have MANY short ones, one per **area** (governorate), each only ~5–6 months long. This is **panel data** (many short series). The notebook:
1. Aggregates BSS + OSS to `(area, month)` rows.
2. Runs the Granger test **within each area** separately.
3. Takes the **median p-value across areas** as the edge's panel-level p.

`MIN_PANEL_OBS = 5` skips areas with too few months (Granger needs enough points for degrees of freedom). The median is robust to a few weird areas, but it weights all areas equally regardless of size (a noted smell).

### 7. The causes and effects tested

```
GRANGER_CAUSES  = ['integ', 'cdr', 'tput']        # OSS network KPIs
GRANGER_EFFECTS = ['cem_target', 'rat_gap', 'churn']  # BSS experience metrics
```

That's a 3×3 = 9-edge grid. For each (cause → effect) pair we get a median p-value and a significant/not flag. The heatmap visualizes all 9.

### 8. The Output Gate (`granger_feature_gate.json`)

```json
{
  "generated_at": "...",
  "lag_max_months": 4,
  "significance_threshold": 0.05,
  "edges": [ {cause, effect, median_p, significant, areas_tested}, ... ],
  "significant_edges": [ ...only the significant ones... ]
}
```

**These top-level keys are an API contract** — `services/api-gateway` `/granger-causality/lead-time` reads them. The enhancement parameterized the *values* (`lag_max_months` now = `GRANGER_MAX_LAG`) but **never renamed a key**. This is the two-tier Granger design: this notebook is the **offline gate**; the api-gateway endpoint is the **online lead-time lookup** that uses it.

---

## Known Methodology Gaps (the honest part — documented, not yet applied)

These are what separates a "good enough" Granger analysis from a rigorous one. They are deferred because **each one changes the p-values written to the gate**, which changes what the dashboard shows — so they must be applied deliberately and diffed.

### A. Stationarity (the big one — ADF + KPSS)

Granger's math ASSUMES each series is **stationary** — its mean and variance don't drift over time. A trending series (e.g. churn steadily rising) violates this and produces **spurious** Granger results (two unrelated trends look "causal").

- **ADF test** (Augmented Dickey-Fuller): null hypothesis = "has a unit root / non-stationary". Small p → reject → stationary. 
- **KPSS test**: null hypothesis = "stationary" (the opposite framing). Running BOTH and agreeing is the gold standard.
- **Fix when non-stationary: differencing** — analyze the month-to-month *change* `Y(t) − Y(t-1)` instead of the level. Usually one difference makes a series stationary.

Currently NOT done — the most important gap (`10_findings.md` B1/G1).

### B. Lag selection by BIC/AIC (instead of min-p)

Rather than testing all lags and grabbing the smallest p (which inflates significance), choose the single lag order L that minimizes an **information criterion**:
- **AIC** (Akaike) — rewards fit, penalizes parameters.
- **BIC** (Bayesian) — penalizes parameters harder (prefers simpler models).
Pick L by BIC, then run ONE Granger test at that L. Cleaner and defensible (G2).

### C. Multiple-testing correction (Benjamini–Hochberg FDR)

We run 9 tests. At α=0.05, even with NO real effects you'd expect ~0.45 false positives by chance. **Benjamini–Hochberg** controls the **False Discovery Rate**: it ranks the 9 p-values and applies a sliding threshold so the *expected fraction of false positives among the flagged edges* stays ≤ 5%. Without it, some "significant" edges are likely noise (G3/S3).

### D. Reverse-Granger sanity test

Also test effect → cause. If X→Y is significant but Y→X is NOT, that's clean directional precedence. If BOTH are significant, you likely have a **confounder** driving both, and the "causality" is an artifact. Cheap, powerful sanity check (G4/S4).

### E. Bootstrap confidence intervals

Resample areas with replacement, recompute each edge's p-value many times, and report the spread. Tells you whether an edge is robustly significant or hangs on one or two areas (G5).

### F. Power limitation (state it plainly)

With only ~5–6 months per area, Granger tests have **low statistical power** regardless of method. The honest framing for defense: the gate is a **directional hint / feature-selection prior**, strengthened as more months accumulate — not a proof. Belongs in a Limitations cell (G6/G7).

---

## The papermill `parameters` Cell

`retrain-service` (port 8004) can regenerate the gate via **papermill**, overriding `GRANGER_MAX_LAG`, `GRANGER_ALPHA`, the cause/effect lists, etc. — without editing the notebook. That's why they're named constants. The output JSON keys stay fixed because the API depends on them.

---

## Glossary

| Term | Definition |
|---|---|
| Time series | Measurements ordered in time |
| Granger causality | X's past improves the forecast of Y's future → predictive precedence |
| Predictive precedence | "X tends to move before Y" — NOT proof of true causation |
| F-test | Compares two nested regressions' residuals for significance |
| Restricted / unrestricted model | Y from its own past / Y from its past + X's past |
| p-value | Probability the result is chance; small = significant |
| α (alpha) | Significance threshold (0.05 here) |
| Lag | How many months back a predictor reaches |
| Panel data | Many short time series (one per area) |
| Median-across-areas | Robust panel aggregation of per-area p-values |
| Stationarity | Mean/variance constant over time (Granger assumes it) |
| ADF / KPSS | Stationarity tests (opposite null hypotheses) |
| Differencing | Analyze month-to-month change to remove trend |
| AIC / BIC | Information criteria for choosing lag order |
| FDR / Benjamini–Hochberg | Controls expected false positives across many tests |
| Reverse-Granger | Test the opposite direction to detect confounding |
| Bootstrap | Resample to estimate confidence intervals |
| Offline gate / online lookup | This notebook writes JSON; api-gateway serves it |

---

## Quick Read

1. **Cell 0:** title + CRISP-DM banner + precedence-not-causation caveat + known-gaps list.
2. **Cell 3 (new):** all constants + SEED. Papermill-overridable. JSON keys explicitly protected.
3. **Load:** `subscribers.parquet` + `oss_aggregates.parquet`.
4. **Panel:** aggregate BSS + OSS to `(area, month)`; join.
5. **Granger test:** per (cause→effect) pair, per area, lags 1..`GRANGER_MAX_LAG`; median p across areas; flag `p < GRANGER_ALPHA`.
6. **Heatmap:** 3×3 median-p grid.
7. **Write gate:** `granger_feature_gate.json` (keys fixed) → local + MinIO `curated/`.
