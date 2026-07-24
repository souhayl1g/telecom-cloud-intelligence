# Notebook 03 — Code Review Findings

**Notebook:** `notebooks/03_oss_vae_anomaly_training.ipynb`
**Date:** 2026-05-23

## BUGS

| # | Cell | Finding |
|---|---|---|
| B1 | training | `KL_BETA=0.001` magic number with no β-sweep — controls the whole VAE bias/variance trade-off, chosen blind. |
| B2 | training | `EPOCHS=30` fixed, no early stopping on validation reconstruction error — may under- or over-train run-to-run. |
| B3 | arch | `hidden=32, mid=16, latent=8` hardcoded as class defaults — not reproducible-tunable, not in any constants block. |
| B4 | split | `int(len(Xn)*0.8)` and `RandomState(42)` inline literals — split fraction + seed buried in code. |

## SMELLS

| # | Finding |
|---|---|
| S1 | No global `SEED` — only `RandomState(42)` in one place; torch + numpy + python `random` not jointly seeded → non-reproducible GPU runs. |
| S2 | No papermill `parameters` cell — retrain container can't override epochs/β/arch. |
| S3 | Anomaly threshold never chosen — ROC-AUC reported but no operating point (which recon-error cutoff flags a cell?). |
| S4 | No latent-space visualization — VAE's selling point ("interpretable latent") is claimed but not shown. |
| S5 | Single train/val split — no k-fold; ROC-AUC=0.9821 is on one partition. |
| S6 | KL term uses `.mean()` over batch AND latent dims mixed with MSE `.mean()` — scale of KL vs MSE not normalized per-dimension (works, but β tuning is sensitive to it). |

## GAPS (best-of-best missing)

| # | Finding |
|---|---|
| G1 | No **KL annealing** — β held constant; ramping β from 0→target over epochs prevents posterior collapse. |
| G2 | No **β-sweep ablation** — should train {0.0005, 0.001, 0.005, 0.01} and plot ROC-AUC vs β. |
| G3 | No **early stopping** on val reconstruction error + best-checkpoint restore. |
| G4 | No **latent UMAP/t-SNE** colored by anomaly label — the interpretability claim is undemonstrated. |
| G5 | No **threshold selection** (e.g. Youden-J on ROC, or p99 of normal recon error) saved alongside the model. |
| G6 | No **reconstruction-error PR curve** annotated with the chosen operating point. |
| G7 | No per-KPI reconstruction-error breakdown (which KPI drives a flagged cell's error?). |
| G8 | No "Limitations" markdown cell. |

## Counts

- BUGS: 4
- SMELLS: 6
- GAPS: 8
- TOTAL: 18

## Applied in this pass

- E1: Papermill `parameters`-tagged constants cell — SEED + full torch/numpy/random seeding + every hyperparameter named (`VAE_KL_BETA`, `VAE_EPOCHS`, `VAE_HIDDEN_DIM`, …) + immutable artifact filenames.
- E2: Title rewritten — CRISP-DM Phase 4 banner + input/output contract + pipeline diagram + "what this notebook does NOT do".
- E3: Wired constants into split / model-instantiation / training-loop / checkpoint cells — killed 7 inline literals.

## Deferred (documented in explainer)

- KL annealing (G1), β-sweep (G2, B1), early stopping (G3) — change training dynamics → re-measure metrics in a follow-up pass.
- Latent UMAP (G4), threshold persistence (G5), PR-curve operating point (G6) — additive analysis cells; do not alter the `.pt` artifact.

Rationale: re-tuning β or adding annealing changes the saved weights → changes the ai-service hot-reloaded model. Apply in a dedicated pass after the defense freeze, with before/after ROC-AUC logged.
