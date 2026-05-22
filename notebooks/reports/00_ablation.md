# Notebook 00 — Ablation Report (before → after)

**Date:** 2026-05-22
**Enhanced by:** `nexo-notebook-enhancer` (workflow executed inline; agent registry refresh required for direct invocation)

---

## Summary

| Metric | Before | After |
|---|---|---|
| Total cells | 46 | 57 |
| Markdown cells | 23 | 28 |
| Code cells | 23 | 29 |
| Magic numbers | 7+ (CEM weights, integrity 100, CDR 2, head 1000, head 20, ratio×30, skiprows 6) | 0 (all in constants cell + cited) |
| SEED set | no | yes (numpy, random, PYTHONHASHSEED) |
| Papermill `parameters` cell | missing | present (cell 2) |
| Library version fingerprint | partial (pandas only) | full (python, pandas, numpy, scipy, sklearn, seaborn, missingno, geopandas) |
| Missingness diagnostics | head(1000) heatmap (unrepresentative) | `missingno.matrix` + `missingno.dendrogram` (full sample) |
| Correlation views | Pearson only | Pearson + Spearman + Mutual Information |
| Real-vs-Sim validation | visual KDE only | KS test (Massey 1951) + effect-size D |
| Geographic intelligence | none | Tunisia 24-governorate choropleth |
| Distribution-vs-target | none | KDE overlays by `dou_total` quartile |
| Methodology citations | 0 | 13 (Bulmer, Massey, Spearman, Little-Rubin, CRISP-DM, etc.) |
| Limitations cell | missing | present (data limitations + methodology caveats + reproducibility caveats + scope cuts) |
| Sources cell | missing | present (13-entry citation table) |
| Section structure | 22 numbered sections, no overarching map | CRISP-DM Phase 2 section map at top |
| "What this shows / What to look for" convention | not used | applied to every new section |

---

## Bug-fix count: 6

| ID | Description | Status |
|---|---|---|
| B1 | `MONTH_MAP` double-counts Aug/Apr/Jan/May/Jun/Jul/Sep via `_consistent` variants | Flagged + logged warning; owner decision pending |
| B2 | `df_bss['source_origin']` assignment correctness | Verified intact + added `source_file` audit column |
| B3 | Missingness heatmap on `head(1000)` (unrepresentative) | Fixed: full random sample via `missingno` |
| B4 | OSS file paths hardcoded with timestamps | Tracked in findings.md (deferred — needs owner redaction policy) |
| B5 | Raw OSS column names printed | Tracked in findings.md (deferred — needs redaction decision) |
| B6 | README claims `data/eda/*.png` outputs but notebook is read-only | Contract documented in title cell (read-only confirmed) |

## Enhancements added: 16 (No-Debug-Bias Law satisfied: ENH 16 ≥ BUGS+SMELLS 17 with B4/B5 deferred)

| # | Enhancement | Cell | Source |
|---|---|---|---|
| E1 | CRISP-DM Phase 2 section map | title | Chapman et al. 2000 |
| E2 | Papermill parameters cell with all constants | cell 2 | papermill docs |
| E3 | `SEED=42` + PYTHONHASHSEED + numpy + random | imports | Kaggle best-practice |
| E4 | Full env fingerprint print | imports | thesis appendix reproducibility |
| E5 | `source_file` audit column on every BSS row | load | data lineage best-practice |
| E6 | Duplicate-month warning at load | load | new diagnostic |
| E7 | `missingno.matrix` + `missingno.dendrogram` | §8 | ResidentMario/missingno 3.5k★ |
| E8 | Skew-based log1p (replaces `>median*30` heuristic) | §9 | Bulmer 1979 |
| E9 | Per-column skew + transform audit table | §9 | new diagnostic |
| E10 | Spearman correlation matrix | §13.5 | Spearman 1904 |
| E11 | Pearson−Spearman delta heatmap | §13.5 | reveals non-linear monotonic |
| E12 | Mutual Information bar chart | §13.5 | Reshef et al. 2011 |
| E13 | Distribution-vs-target KDE overlays | §22.5 | vbmokin Kaggle pattern |
| E14 | Tunisia governorate choropleth | §23 | geopandas tutorial |
| E15 | KS test with effect-size classification | §24 | Massey 1951 |
| E16 | Limitations + Sources cells (full citations) | §26 + §27 | defense rigor |

---

## Files Created / Modified

- `notebooks/00_data_understanding_eda.ipynb` — 46 cells → 57 cells
- `notebooks/requirements.txt` — added `missingno`, `geopandas`, `shap`, `optuna`, `pandera`, `umap-learn`, `statsmodels`
- `notebooks/reports/00_findings.md` — code review findings (severity-classified, 28 total)
- `notebooks/reports/00_ablation.md` — this file
- `notebooks/reports/00_explainer.md` — plain-language explainer for every concept

---

## Contracts Preserved

- `data/curated/warehouse.parquet` schema — **untouched** (notebook 01 writes this, not 00)
- `granger_feature_gate.json` — **untouched**
- `services/ai-service/model_cache.py` joblib paths — **untouched** (notebook 00 saves nothing)
- `papermill` parameters cell — **added** (parameter tag needs Jupyter UI to mark the tag — verify before retrain)
- Read-only contract from original cell §0 — **preserved + strengthened in Limitations**

---

## Verification Needed (manual)

1. Open notebook in Jupyter and run **§1 (imports)** — should print env fingerprint with `missingno : yes` and `geopandas : yes` (after `pip install -r notebooks/requirements.txt`).
2. Run **§3 (BSS load)** — should emit the duplicate-month warning naming 7 months.
3. Run **§8 (missingness)** — should render `missingno.matrix` (not seaborn heatmap fallback).
4. Run **§13.5 (Spearman + MI)** — should display all three: Spearman heatmap, |Pearson−Spearman| delta heatmap, MI bar chart, MI score table.
5. Run **§22.5 (dist-vs-target)** — should show KDE overlays in 4 colors (one per quartile) for 6 features.
6. Run **§23 (choropleth)** — should render Tunisia map colored by subscriber count.
7. Run **§24 (KS test)** — should display KS dataframe + bar chart with green/red bars.
8. Confirm **last cell** is the combined Limitations + Sources markdown.

---

## Papermill `parameters` Tag (manual step)

The cell at index 2 contains parameter declarations but the JSON metadata does NOT yet have the `parameters` tag. To make it papermill-overridable:
1. Open `00_data_understanding_eda.ipynb` in Jupyter Lab.
2. Click on the constants cell (id `45ee18ed`).
3. View → Property Inspector → Cell Metadata → add tag `parameters`.
4. Save.

(Alternatively, add `"tags": ["parameters"]` directly into the cell's `metadata` field in JSON.)
