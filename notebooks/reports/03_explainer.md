# Notebook 03 — Plain-Language Explainer (OSS Anomaly · Variational Autoencoder)

> Audience: you (Souhayl) — every term defined from scratch.
> What this notebook does: **flags abnormal network cells without ever being told what "abnormal" looks like.**
> This is **CRISP-DM Phase 4 — Modeling** (unsupervised branch).

---

## The Big Picture

We have OSS KPIs (signal quality, throughput, call-drop, latency…) for hundreds of thousands of cells. Most cells are fine. A few misbehave. We have **no reliable labels** for which cells are "broken" — labeling that by hand at scale is impossible.

**Solution: learn what "normal" looks like, then flag whatever doesn't fit.** That is *unsupervised anomaly detection*. The model studies only normal cells, becomes an expert at reproducing them, and then anything it CAN'T reproduce well is suspicious.

---

## Concepts Used

### 1. Autoencoder (AE) — the foundation

An **autoencoder** is a neural network shaped like an hourglass:

```
input (9 KPIs) → [encoder] → tiny bottleneck → [decoder] → output (9 KPIs)
```

It is trained to make `output ≈ input` (copy itself). The trick: the **bottleneck** is much smaller than the input (8 numbers vs 9 KPIs, and crucially a *compressed* representation). To squeeze 9 KPIs through 8 latent numbers and rebuild them, the network must learn the *structure* of normal data — which KPIs move together, typical ranges, correlations.

**Reconstruction error** = how different output is from input = `mean((output − input)²)`. For a normal cell the network rebuilds it well → low error. For a weird cell it rebuilds badly → **high error = anomaly signal**.

### 2. Why VARIATIONAL (VAE) and not plain AE?

A plain AE maps each input to a single point in latent space. Gaps and holes form; the latent space is not smooth. A **Variational Autoencoder** instead maps each input to a **probability distribution** (a Gaussian with mean `μ` and variance from `log_var`) in latent space, then samples from it.

Benefits here:
- **Smooth, continuous latent space** — similar cells sit near each other → anomaly *types* cluster (you can later UMAP it).
- **Probabilistic** — gives a principled continuous severity score, not a brittle yes/no.
- Robust to the multi-modal traffic mixtures (2G/3G/4G) that trip simpler detectors.

### 3. μ, log_var, and the Reparameterization Trick

The encoder outputs two vectors: `μ` (the center of the latent Gaussian) and `log_var` (its log-variance — we predict the log so it can be any real number and stays positive after `exp`).

To sample a latent point `z` we'd do `z = μ + σ·ε` where `ε ~ N(0,1)` and `σ = exp(0.5·log_var)`. But **random sampling has no gradient** — backprop can't flow through a coin flip. The **reparameterization trick** moves the randomness OUTSIDE the network: draw `ε` from a fixed `N(0,1)`, then compute `z = μ + exp(0.5·log_var)·ε`. Now `μ` and `log_var` are deterministic functions the gradient CAN flow through; only `ε` is random, and it has no parameters. This is the single idea that makes VAEs trainable. (In the code: `mu + torch.exp(0.5*log) * torch.randn_like(log)`.)

### 4. The Loss: Reconstruction + KL

```
loss = MSE(reconstruction)  +  KL_BETA · KL_divergence
```

- **MSE term** — "rebuild the input accurately." Drives the network to be a good copier.
- **KL divergence term** — "keep the latent distribution close to a standard `N(0,1)`." This *regularizes* the latent space so it stays smooth and centered, preventing the encoder from cheating by spreading points arbitrarily far apart.

**KL divergence** measures how far one probability distribution is from another. Here it's the distance between the encoder's Gaussian `N(μ, σ²)` and the target `N(0,1)`. Closed form for that case:
`KL = -0.5 · Σ(1 + log_var − μ² − exp(log_var))`.

### 5. `KL_BETA` — the β in β-VAE (the key magic number)

`KL_BETA=0.001` weights the KL term against reconstruction.

- **High β** → latent space is very clean/Gaussian, but reconstruction suffers → blunter anomaly detector.
- **Low β** (our 0.001) → reconstruction dominates; latent absorbs more signal → sharper reconstruction-error separation between normal and abnormal.

This is **β-VAE**. The value should be chosen by a **β-sweep**: train several β values, plot ROC-AUC vs β, pick the peak. Right now it's a single blind choice — see `03_findings.md` G2. (Code example uses a function named `train_and_score`, not the forbidden built-in.)

### 6. Train on NORMAL ONLY (the central design choice)

In the split cell we separate `Xn = X[y==0]` (normal) from `Xa = X[y==1]` (anomaly). The VAE trains **exclusively on `Xn`**. The anomaly rows `Xa` are touched ONLY at evaluation time to measure how well high reconstruction error separates them.

Why? If the VAE saw anomalies during training, it would learn to reconstruct them too → they'd stop standing out. Keeping training normal-only is what makes the detector work. The weak label `y` is for *scoring*, never for *fitting*.

### 7. Epochs, Batch, Learning Rate

- **Epoch** — one full pass over the training set. `VAE_EPOCHS=30`.
- **Batch** — rows processed before one weight update. `VAE_BATCH=256`. Bigger = smoother gradient, more memory.
- **Learning rate** — Adam optimizer step size. `VAE_LR=1e-3` (the standard Adam default).

> Missing: **early stopping** (halt when val reconstruction stops improving) — currently fixed at 30 epochs (G3).

### 8. Evaluation: ROC-AUC and PR-AUC

After training, compute reconstruction error for held-out normal (`en`) and anomaly (`ea`) cells, then score how well error separates them:

- **ROC-AUC** — probability that a random anomaly has higher error than a random normal cell. 1.0 = perfect, 0.5 = coin flip. We report **0.931**.
- **PR-AUC** (precision-recall AUC) — better than ROC when anomalies are RARE (class imbalance), because it ignores the easy true-negatives and focuses on how clean the flagged set is.

Both are **threshold-free** — they rank by error and integrate over all cutoffs. To actually USE the model you still must pick ONE threshold (see next).

### 9. The Missing Piece: the Anomaly Threshold

ROC-AUC says "the ranking is good" but production needs a concrete cutoff: *flag any cell with recon error > T*. Common choices:
- **p99 of normal reconstruction error** — flag the worst 1% as anomalous.
- **Youden's J** — the ROC point maximizing `(TPR − FPR)`.

This threshold should be saved INTO the checkpoint so ai-service uses the same `T`. Currently not persisted — `03_findings.md` G5.

### 10. Latent Space Interpretability (the deferred demo)

The VAE's selling point is that its 8-D latent space is *meaningful*. Project it to 2-D with **UMAP** (Uniform Manifold Approximation and Projection — a non-linear dimensionality reducer that preserves local neighborhoods) and color points by anomaly label: normal cells form a dense blob, anomalies scatter at the edges, and distinct anomaly *types* form separate clusters. This is the picture that sells the model in defense — currently not drawn (G4).

### 11. StandardScaler (why scale first)

KPIs live on wildly different scales (throughput in Mbps, drop-rate in %, latency in ms). Neural nets train badly when one input dominates the gradient. **StandardScaler** transforms each column to mean 0, std 1: `(x − mean) / std`. We **fit on train, apply to val** (never fit on val — that leaks). The fitted scaler is saved as `vae_v3_scaler.joblib` so inference applies the identical transform.

---

## The papermill `parameters` Cell

`retrain-service` (port 8004) runs this notebook unattended via **papermill**, which can override any variable in the `parameters`-tagged cell. That's why `VAE_KL_BETA`, `VAE_EPOCHS`, architecture dims, and artifact filenames now live there as named constants — ops can retrain with a different β without editing code.

---

## The Artifact Contract (do not rename)

| File | Consumed by |
|---|---|
| `models/oss_vae_v3.pt` | `services/ai-service/model_cache.py` (mtime hot-reload) |
| `models/vae_v3_scaler.joblib` | ai-service — same StandardScaler at inference |
| `models/vae_v3_feature_names.joblib` | ai-service — KPI column order |
| `models/oss_vae_v3_model_card.md` | docs / defense evidence |

The checkpoint dict keys (`model_state_dict`, `input_dim`, `latent_dim`, `hidden_dim`, `mid_dim`, `roc_auc`, `features`) are read by ai-service to rebuild the architecture before loading weights — keep them stable.

---

## Glossary

| Term | Definition |
|---|---|
| Autoencoder | Hourglass net trained to copy its input through a bottleneck |
| Bottleneck / latent | The compressed middle representation |
| Reconstruction error | `mean((output−input)²)`; high = anomalous |
| VAE | Autoencoder whose latent is a probability distribution |
| μ / log_var | Mean / log-variance of the latent Gaussian |
| Reparameterization trick | `z = μ + exp(0.5·log_var)·ε`; makes sampling differentiable |
| KL divergence | Distance between two distributions; here latent vs `N(0,1)` |
| β-VAE / KL_BETA | Weight on the KL term; trades reconstruction vs latent cleanliness |
| Normal-only training | Fit on normal cells so anomalies stand out |
| Epoch / batch / LR | Full pass / rows per update / optimizer step size |
| ROC-AUC | Ranking quality, threshold-free (1=perfect) |
| PR-AUC | Precision-recall AUC; better under class imbalance |
| Anomaly threshold | Recon-error cutoff that turns the score into a flag |
| UMAP | Non-linear 2-D projection for visualizing latent space |
| StandardScaler | Per-column mean-0/std-1 normalization |
| Early stopping | Halt when validation stops improving |
| KL annealing | Ramp β from 0 → target to avoid posterior collapse |

---

## Quick Read

1. **Cell 0:** title + CRISP-DM Phase 4 banner + contract.
2. **Cell 3 (new):** all constants + SEED + torch/numpy/random seeding. Papermill-overridable.
3. **Load:** read `cells.parquet`, build weak anomaly label `y` (for evaluation only).
4. **Features:** select 9 OSS KPIs.
5. **Split:** normal cells → 80% train / 20% val; anomalies held for eval.
6. **Scale:** StandardScaler fit on train.
7. **Architecture:** VAE class (encoder → μ/log_var → reparam → decoder).
8. **Train:** loop, loss = MSE + `VAE_KL_BETA`·KL.
9. **Evaluate:** reconstruction error → ROC-AUC + PR-AUC.
10. **Plot:** KDE of normal vs anomaly error.
11. **Save:** `.pt` checkpoint + scaler + feature names + card → local + MinIO.
