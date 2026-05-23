# Notebook 10 — Ablation Report

**Date:** 2026-05-23
**Cells before:** 13 → **after:** 14

## Applied

| ID | Change | Cell |
|---|---|---|
| E1 | Papermill `parameters`-tagged constants cell (SEED + `GRANGER_MAX_LAG`, `GRANGER_ALPHA`, `MIN_PANEL_OBS`, `GRANGER_FTEST`, causes, effects, gate fname) | new cell 3 |
| E2 | Title rewritten — CRISP-DM Phase 4 banner + I/O contract + precedence-vs-causation caveat + known-gaps list + "does NOT do" | cell 0 |
| E3 | Granger-test cell: `causes`/`effects`→constants, `<5`→`MIN_PANEL_OBS`, `min(4,…)`→`min(GRANGER_MAX_LAG,…)`, `'ssr_ftest'`→`GRANGER_FTEST`, `mp<0.05`→`mp<GRANGER_ALPHA` | granger cell |
| E4 | Gate-write cell: `4`→`GRANGER_MAX_LAG`, `0.05`→`GRANGER_ALPHA`, fname→`GATE_FNAME` | gate cell |

## Bugs fixed: 0 (test logic + output values byte-identical given same data)
## Smells reduced: 2 (S1 — SEED set; S2 — parameters cell present)
## Gaps closed: 0 (G1–G7 deferred — see findings.md)
## Documentation added: explainer.md (extensive)

## Contracts preserved — VERIFIED

Output JSON **keys** unchanged (consumed by `services/api-gateway` `/granger-causality/lead-time`):

| Key | Status |
|---|---|
| `generated_at` | unchanged |
| `lag_max_months` | unchanged (value now = `GRANGER_MAX_LAG`) |
| `significance_threshold` | unchanged (value now = `GRANGER_ALPHA`) |
| `edges` | unchanged |
| `significant_edges` | unchanged |

Per-edge record keys (`cause`, `effect`, `median_p`, `significant`, `areas_tested`) — unchanged.
Output filename `granger_feature_gate.json` — unchanged. MinIO `curated/` mirror — unchanged.

## Verification

1. Open notebook in Jupyter.
2. Run constants cell — prints `SEED=42 | maxlag=4 | alpha=0.05 | min_obs=5 | causes=[...] effects=[...]`, no error.
3. Run full notebook — writes `granger_feature_gate.json` with the SAME 5 top-level keys as before.
4. `python -c "import json; d=json.load(open('notebooks/granger_feature_gate.json')); print(sorted(d))"` → must list `['edges','generated_at','lag_max_months','significance_threshold','significant_edges']`.
5. Hit `GET /granger-causality/lead-time?area=X` on api-gateway → still parses the gate without KeyError.

## Deferred work (next pass — will change gate numbers)

- ADF + KPSS stationarity gate + automatic differencing before each Granger test.
- BIC/AIC lag-order selection per pair (replace fixed max-lag + min-p).
- Benjamini–Hochberg FDR across the 9 (cause,effect) edges.
- Reverse-Granger sanity test (flag bidirectional = likely confounding).
- Bootstrap confidence intervals on edge p-values.
- Diff old vs new `granger_feature_gate.json` and review before shipping.
