# Notebook 00 — Code Review Findings

**Notebook:** `notebooks/00_data_understanding_eda.ipynb`
**Reviewer:** `nexo-notebook-enhancer` (inline review, gsd:code-review pattern)
**Date:** 2026-05-22
**Total cells:** 46 (23 markdown, 23 code)
**Status before edits:** Functional but lacks rigor for defense-grade EDA

---

## Severity Legend

- **BUG** — functional defect or correctness risk
- **SMELL** — code-smell (magic numbers, fragile patterns, missing seeds)
- **GAP** — missing best-practice (CV/SHAP/ADF/etc.); not a defect, but below Kaggle-Grandmaster bar

---

## BUGS

| # | Cell | Severity | Finding |
|---|------|----------|---------|
| B1 | 6 | BUG | `MONTH_MAP` maps both `'aug'` and `'aou'` to `2026-08`. If both English and French Aug CSVs exist, August rows are loaded twice and silently double-counted. |
| B2 | 6 | BUG | `df_bss['source_origin']` assignment truncated in source view — verify cell completes assignment for all rows, not only first match. |
| B3 | 16 | BUG | Missingness heatmap uses `df_bss.head(1000)` — first 1000 rows are January data only (load order = file order), so heatmap is **not representative** of cross-month NaN patterns. |
| B4 | 28 | BUG | OSS file paths are hardcoded with specific timestamp filenames (e.g., `KPI Analysis Result_Query_Result_20260427105204494...csv`). Re-export breaks the notebook. |
| B5 | 30 | BUG | `print(f'\\n=== {rat} ===')` then `print(f'  [{i:2d}] {c}')` — emits raw OSS column names. Schema-only print is permitted, but a "TT_data column-name redaction policy" decision is required before defense submission. Recommendation: redact to generic labels in defense screenshots. |
| B6 | 44 | BUG | README.md claims notebook outputs `data/eda/summary.json` and `data/eda/conclusions.md`. The notebook itself states "Read-only. No files saved." (cell 0) and prints `summary` only. **Documentation/code contract conflict.** |

## SMELLS

| # | Cell | Severity | Finding |
|---|------|----------|---------|
| S1 | 2 | SMELL | No `SEED` constant set. `numpy`, `random`, hash seed unset. Plot order / sampling reproducibility at risk. |
| S2 | 2 | SMELL | No `papermill` `parameters` cell. Retrain container mounts notebooks `:rw` and parameterizes via papermill — top cell must be tagged `parameters`. |
| S3 | 6 | SMELL | `REAL = {'feb','mars'}` and `MONTH_MAP` inlined inside loading loop. Should live in a top-of-file constants block. |
| S4 | 16 | SMELL | `head(1000)` is a magic number. |
| S5 | 18 | SMELL | `s.max()>s.median()*30` heuristic for log1p is magic with no citation. Standard guidance: skewness > 1 (Fisher-Pearson) or max/median ratio > 10. |
| S6 | 22 | SMELL | Categorical column list hardcoded; if a column is renamed upstream, silently drops from analysis. |
| S7 | 24 | SMELL | Outlier visualization column list hardcoded with same fragility. |
| S8 | 28 | SMELL | `skiprows=6` is a magic number — Huawei CSV header offset has no citation comment. |
| S9 | 34 | SMELL | `integ < 100` and `cdr > 2` thresholds inlined. These are SLA constants and belong in a thresholds block with citation. |
| S10 | 42 | SMELL | Same SLA thresholds (`100`, `2`) repeated — DRY violation. |
| S11 | 40 | SMELL | `head(20)` for top-areas hardcoded — should be a named constant. |

## GAPS (best-of-best missing)

| # | Severity | Finding |
|---|----------|---------|
| G1 | GAP | No **missingness matrix** via `missingno` — heatmap on first 1000 rows is a degenerate substitute. Industry standard: `msno.matrix(df)` + `msno.bar(df)` + `msno.dendrogram(df)` for MAR/MCAR diagnosis. |
| G2 | GAP | No **mutual information** computation. Pearson only captures linear relationships. `sklearn.feature_selection.mutual_info_regression` reveals non-linear structure. |
| G3 | GAP | No **Spearman correlation** for comparison against Pearson. Rank-based correlation is robust to outliers and reveals monotonic-non-linear relationships Pearson misses. |
| G4 | GAP | No **geographic visualization**. Project has `dashboard/lib/tunisia-geojson.json` (24 governorates) and `tunisia-areas.ts` mapping. EDA should show CEM-score / anomaly-rate **choropleth** by governorate. |
| G5 | GAP | No **distribution-vs-target overlays**. KDE per CEM-score quartile reveals which features separate high-vs-low experience subscribers. |
| G6 | GAP | No **KS-test** (`scipy.stats.ks_2samp`) for real-vs-simulated distribution drift. Currently only visual KDE overlay — no statistical evidence of generator fidelity. |
| G7 | GAP | No **data dictionary** cell. 26 BSS columns + 30+ OSS columns reviewed without per-column definition + source + units. Defense reviewers will ask. |
| G8 | GAP | No **CRISP-DM Phase 2 structure**. Sections numbered 1..22 but no mapping to Data Understanding sub-tasks (Collect Initial Data, Describe Data, Explore Data, Verify Data Quality). |
| G9 | GAP | No **"What this shows / What to look for"** markdown paragraphs per major chart. Reviewers must guess interpretation. |
| G10 | GAP | No **Limitations** cell at end. Threats to validity (sampling bias, drift caveats, OSS↔BSS join risk) not documented. |
| G11 | GAP | No **citation/sources** cell. Best-of-best methodology references not surfaced. |

---

## Counts

| Category | Count |
|---|---|
| BUGS | 6 |
| SMELLS | 11 |
| GAPS | 11 |
| **Total findings** | **28** |

## No-Debug-Bias Audit

- `BUGS+SMELLS` = 17
- `GAPS` (enhancements) = 11
- After expansion (see ablation): enhancements grow to **16 inserted/replaced cells** to satisfy `ENH >= BUGS+SMELLS` floor.

## Out of Scope for This Pass

- Migrating notebook to read from postgres instead of TT_data CSVs (changes data contract — defer)
- Adding `data/eda/*.png` and `summary.json` saving (cell 0 explicitly says read-only — would contradict the notebook's own contract)
- Removing OSS file-name hardcoding (B4) — owner must decide redaction policy first
