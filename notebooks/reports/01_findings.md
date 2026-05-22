# Notebook 01 — Code Review Findings

**Notebook:** `notebooks/01_etl_feature_engineering.ipynb`
**Date:** 2026-05-22

## BUGS

| # | Cell | Finding |
|---|---|---|
| B1 | 26 (warehouse) | CEM-score weights `0.40 / 0.30 / 0.20 / 0.10` hardcoded inline — no sensitivity analysis, no provenance comment, no assertion that they sum to 1.0 |
| B2 | 30 (splits) | `train_test_split test_size=0.176` is a cryptic ratio — actually `0.15 / (0.15+0.70) ≈ 0.176` to produce 15% val from remaining 85% post-test. Easy to misread. |
| B3 | 16 (imputer) | `IterativeImputer` saved to disk but no validation that imputed values stay in physical ranges (e.g., `s1_mme_sr ∈ [0,1]`). Could produce out-of-range imputations. |
| B4 | 16 (winsorize) | p99 cap applied to traffic columns but no before/after ablation justifying the threshold choice. |
| B5 | 14 (clean BSS) | `attach_sr` clip uses `[0, 1]` magic literals inline. |

## SMELLS

| # | Finding |
|---|---|
| S1 | No SEED set globally — train_test_split uses random_state but other ops are non-deterministic |
| S2 | No `papermill` parameters cell — retrain container can't override constants |
| S3 | No `pandera` (or any) schema assertions between stages — silent column-rename or dtype changes will break downstream |
| S4 | No leakage audit — `imsi` not checked against splits to ensure same subscriber doesn't appear in train AND test |
| S5 | OSS file glob hardcoded — re-export with different timestamp filename breaks pipeline |
| S6 | 3GPP base latencies (`{'4G':18.0,'3G':55.0,'2G':95.0}`) inline, no citation |

## GAPS (best-of-best missing)

| # | Finding |
|---|---|
| G1 | No `pandera` schema validation between pipeline stages |
| G2 | No CEM-weight sensitivity analysis (what if 0.35/0.35/0.20/0.10?) |
| G3 | No Winsorize ablation — does p99 vs p99.5 vs p99.9 change training metrics? |
| G4 | No leakage audit between train/val/test (`imsi` overlap check) |
| G5 | No GroupKFold-aware splitting (`area` should be a split group to avoid spatial leakage) |
| G6 | No idempotency hash check (re-running should produce identical parquet) |
| G7 | No data-version registry update — `dataset_registry` table not written from this notebook |
| G8 | No "what this shows" / "what to look for" narrative |
| G9 | No Limitations cell |

## Counts

- BUGS: 5
- SMELLS: 6
- GAPS: 9
- TOTAL: 20

## Applied in this pass

- E1: Constants/Seed papermill cell at top with assertion CEM weights sum to 1.0
- E2: Title cell rewritten with CRISP-DM Phase 3 banner + explicit contract + pipeline diagram

## Deferred (documented in explainer, not applied to avoid breakage)

- Pandera schema (G1) — deferred to next pass (requires touching every stage boundary)
- Leakage audit (G4) — deferred (requires reading `imsi` across all splits, slow)
- GroupKFold splitting (G5) — deferred (changes split policy, downstream impact)
- Winsorize ablation (G3) — deferred (training notebooks own metric measurement)
