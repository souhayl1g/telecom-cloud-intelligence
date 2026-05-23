# Notebook 10 — Code Review Findings

**Notebook:** `notebooks/10_granger_feature_selection.ipynb`
**Date:** 2026-05-23

## BUGS

| # | Cell | Finding |
|---|---|---|
| B1 | granger test | **No stationarity check.** `grangercausalitytests` ASSUMES stationary series. Trended/non-stationary KPIs produce spurious significance. Must run ADF (and ideally KPSS) first and difference if needed. |
| B2 | granger test | **`min(p across lags)`** — taking the minimum p-value over lags 1..4 is multiple testing without correction → inflates significance (any one lag passing flags the edge). Should pick lag by an information criterion, or correct. |
| B3 | granger test | `maxlag=min(4, len(ts)-2)` — with only ~5–6 monthly points per area, lag-4 Granger has almost no degrees of freedom → unstable F-stats. |
| B4 | constants | `lag_max=4`, `alpha=0.05` inline literals — no constants block. |

## SMELLS

| # | Finding |
|---|---|
| S1 | No global `SEED` (Granger itself is deterministic, but downstream resampling/bootstrap would need it). |
| S2 | No papermill `parameters` cell — gate can't be regenerated with different lag/alpha by the retrain container. |
| S3 | No **multiple-testing correction** across the 3×3 = 9 (cause,effect) pairs — family-wise error not controlled. |
| S4 | No **reverse-Granger sanity test** — should also test effect→cause; if BOTH directions are "significant", the result is likely confounding, not precedence. |
| S5 | `median p across areas` is a reasonable panel aggregation but unweighted — areas with 5 vs 50 points count equally. |
| S6 | No confidence interval / bootstrap on the edge p-values. |

## GAPS (best-of-best missing)

| # | Finding |
|---|---|
| G1 | No **ADF + KPSS stationarity gate** with automatic differencing pipeline. |
| G2 | No **BIC/AIC lag selection** — lag chosen as a fixed max, not the order that actually minimizes the criterion. |
| G3 | No **Benjamini–Hochberg FDR** correction across the 9 tested edges. |
| G4 | No **reverse-Granger** sanity test (X→Y AND Y→X check for confounding). |
| G5 | No **bootstrap confidence intervals** on edge significance. |
| G6 | No "Limitations" markdown cell stating the stationarity assumption explicitly. |
| G7 | Panel has very few months (≈5–6) — fundamental power limitation; should be stated, and the gate framed as "directional hint", not proof. |

## Counts

- BUGS: 4
- SMELLS: 6
- GAPS: 7
- TOTAL: 17

## Applied in this pass

- E1: Papermill `parameters`-tagged constants cell — SEED + `GRANGER_MAX_LAG`, `GRANGER_ALPHA`, `MIN_PANEL_OBS`, `GRANGER_FTEST`, `GRANGER_CAUSES`, `GRANGER_EFFECTS`, `GATE_FNAME`.
- E2: Title rewritten — CRISP-DM Phase 4 banner + I/O contract + "Granger = predictive precedence not causation" caveat + explicit known-gaps list + "does NOT do".
- E3: Wired constants into the Granger-test cell and the gate-write cell — killed inline `4` / `0.05` / hardcoded cause+effect lists / test key.

## CRITICAL contract note

The output JSON **keys** (`generated_at`, `lag_max_months`, `significance_threshold`, `edges`, `significant_edges`) are consumed by `services/api-gateway` `/granger-causality/lead-time`. They were **NOT renamed** — only their *values* now reference constants. Per-edge record keys (`cause`, `effect`, `median_p`, `significant`, `areas_tested`) likewise unchanged.

## Deferred (documented in explainer)

- ADF/KPSS + differencing (G1, B1), BIC lag selection (G2, B3), BH-FDR (G3, S3), reverse-Granger (G4, S4), bootstrap CIs (G5).

Rationale: every one of these CHANGES the edge p-values written to `granger_feature_gate.json` → changes what the dashboard Convergence panel shows and what api-gateway serves. They are real rigor upgrades but must be applied deliberately, with the old vs new gate diffed, after the defense freeze.
