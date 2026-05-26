---
status: issues-found
review_date: 2026-05-26
scope: notebooks 00/02/03/04/10 + reports (session commits e5e74c1..45f0083)
reviewer: direct (gsd:code-review is phase-bound; no GSD phase exists, so reviewed inline)
depth: standard
files_reviewed: 6
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
constraints_verified:
  freeze_weights: PASS
  warehouse_parquet_untouched: PASS
  gate_json_untouched: PASS
  no_tt_data_raw_leakage: PASS
---

# Notebook Code Review — 2026-05-26

Reviewed the new EDA viz cells (NB00), per-model eval cells (NB02/03/04), Granger cells (NB10),
and the violin/z-score cell. Focus: correctness, OOM risk, accidental retrain/overwrite, TT_data leakage.

> Note: `/gsd:code-review` is phase-bound and `.planning/phases/` is empty (no GSD phase for this
> ad-hoc notebook work), so it fails-closed. This review was done directly to deliver the intent.

## Constraints verified (the important ones)

- **Freeze-weights HONORED.** Every eval cell loads frozen artifacts (`joblib.load` / `torch.load`);
  none call `.save()`/`.fit()` over `cem_v3*.joblib` / `oss_vae_v3.pt` / `rat_*.joblib`. NB04's CV cell
  trains **throwaway in-memory** models only. `metrics.json` is never rewritten.
- **OOM guards present** throughout: SHAP 5k rows, per-segment SHAP 800, CV subsample 200k,
  PCA plot 5k, violin sample 150k. No full-dataset `.fit()` on millions of rows.
- **No TT_data raw-row leakage.** Outputs are aggregates, SHAP plots, distributions, and per-area/month
  MAE — no IMSI/MSISDN dumps.

## Warnings (4)

### WR-1 — NB03 cell 22: VAE eval hardcodes `mid=16`, ignores checkpoint `mid_dim`
`_VAEEval(_in, hidden=_hid, latent=_lat)` reads `input_dim/hidden_dim/latent_dim` from the checkpoint
but leaves `mid` at its default 16. If a future retrain changes `mid_dim`, `load_state_dict` throws a
shape-mismatch and the whole eval block fails.
**Fix:** `mid=_vae_ckpt.get('mid_dim', 16)` and pass it through.

### WR-2 — NB04 cell 15: CV early-stopping peeks at the scored fold (mild leakage)
Inside each fold, `m.fit(Xtr, ytr, eval_set=[(Xte, yte)])` uses the **test fold** for early stopping,
then scores ROC-AUC on that same `Xte`. Early stopping selects the iteration that looks best on the
data it is then graded on → CV AUC is optimistically biased. In an "honesty check" cell this matters.
**Fix:** split a small validation slice off the **train** fold for `eval_set`; score on the untouched test fold.

### WR-3 — NB02 cell 31: possible `NameError` on `a_mae`
`worst = a_mae.index[0] if len(a_mae)>0 else '—'` references `a_mae`, which is only assigned inside
`if 'area' in seg_df_e.columns`. If `area` is absent, the `worst=` line raises `NameError`.
**Fix:** initialise `a_mae = pd.Series(dtype=float)` before the `if`, or guard the `worst=` line.

### WR-4 — NB02 cell 23: silent feature-set drift risk
`feat_e = [f for f in _cem_features if f in subs_e.columns and f not in DROP_E]` can yield fewer
columns than the model was trained on. LightGBM then predicts on a mismatched column set (errors, or
worse, wrong positional mapping).
**Fix:** assert `feat_e == _cem_features` (order + completeness) before `predict`; fail loudly if not.

## Info (3)

- **IN-1** — Hardcoded MinIO creds (`minio`/`minio_pw`) repeated in eval cells. Dev-only per CLAUDE.md;
  prefer `os.environ` for portability and to avoid creds drifting into committed outputs.
- **IN-2** — NB03 loads the checkpoint with `weights_only=False`, which deserializes arbitrary objects.
  Safe for a local trusted checkpoint; flagged only for awareness (PyTorch 2.6+ defaults to the safe
  `weights_only=True`, which would require allow-listing the custom class).
- **IN-3** — The NB00 violin/z-score cell (§12.5) is **un-executed** (no embedded output). Run the
  notebook (sampled → OOM-safe) to populate the plots before the defense freeze.

## Verdict

No critical issues. The eval cells are well-structured and respect freeze-weights. WR-1 and WR-2 are
worth fixing before any future retrain (WR-2 affects the reported CV honesty number). WR-3/WR-4 are
cheap defensive guards. None block the current committed state.
