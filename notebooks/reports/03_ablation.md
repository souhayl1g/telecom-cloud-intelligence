# Notebook 03 — Ablation Report

**Date:** 2026-05-23
**Cells before:** 20 → **after:** 21

## Applied

| ID | Change | Cell |
|---|---|---|
| E1 | Papermill `parameters`-tagged constants cell (SEED + torch/numpy/random seeding + all hyperparams + artifact fnames) | new cell 3 |
| E2 | Title rewritten — CRISP-DM Phase 4 banner + I/O contract + pipeline diagram + "does NOT do" | cell 0 |
| E3 | Split cell: `0.8`→`VAE_TRAIN_FRAC`, `RandomState(42)`→`RandomState(SEED)` | split cell |
| E4 | Model instantiation passes `hidden=VAE_HIDDEN_DIM, mid=VAE_MID_DIM, latent=VAE_LATENT_DIM` | VAE-instantiation cell |
| E5 | Training loop: dropped inline `EPOCHS=30; BATCH=256; LR=1e-3; KL_BETA=0.001`, now reads constants | training cell |
| E6 | Checkpoint: `8/32/16`→constants; 4 artifact filenames→constants | save cell |

## Bugs fixed: 0 (training logic untouched — weights identical given same seed)
## Smells reduced: 2 (S1 — full SEED now set; S2 — parameters cell present)
## Gaps closed: 0 (G1–G8 deferred — see findings.md)
## Documentation added: explainer.md (extensive)

## Contracts preserved

- `models/oss_vae_v3.pt` — filename **unchanged** (`services/ai-service/model_cache.py`)
- `models/vae_v3_scaler.joblib` — **unchanged**
- `models/vae_v3_feature_names.joblib` — **unchanged**
- `models/oss_vae_v3_model_card.md` — **unchanged**
- MinIO `curated/models/` mirror — **unchanged**
- Checkpoint dict keys (`model_state_dict`, `input_dim`, `latent_dim`, `hidden_dim`, `mid_dim`, `roc_auc`, `features`) — **unchanged** (ai-service loads by key)

## Verification

1. Open notebook in Jupyter.
2. Run constants cell — prints `SEED=42 | arch=32->16->latent(8) | epochs=30 ...`, no error.
3. Run full notebook — final cell saves `.pt` + scaler to same paths, same checkpoint keys.
4. `POST /models/reload` to ai-service → log shows VAE reloaded (mtime changed).
5. `POST /infer/vae-anomaly` with a sample cell → returns anomaly score.

## Deferred work (next pass)

- KL annealing: ramp `β` 0→`VAE_KL_BETA` over first 10 epochs.
- β-sweep: train {0.0005, 0.001, 0.005, 0.01}, plot ROC-AUC vs β, pick best.
- Early stopping on val reconstruction error + restore best epoch.
- Latent UMAP colored by anomaly label (interpretability demo).
- Persist anomaly threshold (p99 of normal recon error) into the checkpoint.
- Annotated PR curve with chosen operating point.
