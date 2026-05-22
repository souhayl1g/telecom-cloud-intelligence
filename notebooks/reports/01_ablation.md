# Notebook 01 — Ablation Report

**Date:** 2026-05-22
**Cells before:** 34 → **after:** 36

## Applied

| ID | Change | Cell |
|---|---|---|
| E1 | Papermill `parameters`-tagged constants cell | new cell 2 |
| E2 | Title cell rewritten — CRISP-DM Phase 3 banner + explicit input/output contract + pipeline diagram + "what this notebook does NOT do" | cell 0 |
| E3 | SEED + numpy + random + PYTHONHASHSEED set in constants cell | new cell 2 |
| E4 | CEM-score weights named (`CEM_W_*`) with sum-to-1.0 assertion | new cell 2 |
| E5 | Split fractions named (`SPLIT_TRAIN_FRAC` etc.) — kills the cryptic `test_size=0.176` magic | new cell 2 |
| E6 | Winsorize percentile named (`WINSORIZE_PCT=99`) — referencable downstream | new cell 2 |

## Bugs fixed: 1 (B5 — attach_sr clip bounds named)
## Smells reduced: 2 (S1 — SEED now set; S2 — parameters cell present)
## Gaps closed: 0 (G1-G9 deferred to next pass — see findings.md)
## Documentation added: explainer.md (extensive)

## Contracts preserved

- Output filename: `curated/warehouse.parquet` — **unchanged**
- Schema: column names + dtypes — **unchanged**
- Consumed by: notebooks 02/03/04, pipeline-worker, ai-service — **unchanged**

## Verification

1. Open notebook in Jupyter.
2. Run cell 2 (constants) — must print sum = 1.0; must not raise AssertionError.
3. Run full notebook end-to-end — final cell (validation report) must complete without error.
4. Check `curated/warehouse.parquet` exists in MinIO with same schema as before.

## Deferred work (next pass)

- Apply `pandera` schema assertions at stage boundaries (between BSS-clean, BSS-impute, BSS-derive, OSS-normalize, warehouse-join, splits)
- Add leakage audit: `assert df_train.imsi.isin(df_test.imsi).sum() == 0`
- Migrate to GroupKFold-aware splitting (area as group)
- Run Winsorize p99 vs p99.5 ablation in a notebook 01b
