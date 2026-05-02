# OSS Experience Anomaly v3.0 — Model Card

## Overview
| Attribute | Value |
|-----------|-------|
| **Model Name** | OSS Experience Anomaly v3.0 |
| **Algorithm** | PyTorch Variational Autoencoder (VAE) |
| **Task** | Anomaly Detection (unsupervised) |
| **Version** | v3.0-gpu |
| **Date** | 2026-04-28 |

## Training Data
| Attribute | Value |
|-----------|-------|
| **Total samples** | 499,729 OSS records |
| **Real samples** | 299,729 (Mar 100K + Apr 200K) |
| **Simulated samples** | 200,000 (Jan 50K + Feb 50K + May 50K + Jun 50K) |
| **Normal-only training** | 424,769 samples (95.7% of training set) |
| **Anomaly rate** | 4.43% |
| **Time span** | 2026-01 to 2026-06 |

## Features (9)
1. throughput_mbps
2. latency_ms
3. packet_loss_rate
4. jitter_ms
5. cell_load_pct
6. rsrp_dbm
7. active_users
8. integrity
9. call_drop_rate

## Architecture
```
Input(9) → Linear(32) → ReLU → Dropout(0.1)
         → Linear(16) → ReLU → Dropout(0.1)
         → μ(8), logvar(8)  [reparameterization]
         → Linear(16) → ReLU → Dropout(0.1)
         → Linear(32) → ReLU → Dropout(0.1)
         → Output(9)
```
- **Total parameters:** 2,057
- **Latent dimensions:** 8

## Hyperparameters
| Parameter | Value |
|-----------|-------|
| epochs | 100 (early stopping at 15) |
| batch_size | 1024 |
| learning_rate | 0.001 |
| weight_decay | 1e-5 |
| optimizer | Adam |
| scheduler | ReduceLROnPlateau (factor=0.5, patience=10) |
| loss | MSE(recon, x) + 0.5 * KL(μ, σ) |

## Threshold Selection
- **Method:** PR-curve optimization
- **Target:** 70% recall
- **Selected threshold:** 0.23654

## Performance
| Metric | Value |
|--------|-------|
| ROC-AUC | 0.9307 |
| Accuracy | 0.9574 |
| Precision | 0.3769 |
| Recall | 0.7003 |
| F1 | 0.4901 |

## Limitations
- Low precision (0.377) by design — optimized for 70% recall
- In telecom ops, missing anomalies is worse than false alarms
- May flag distribution shifts as anomalies (expected behavior)

## Artifacts
- `oss_vae_v3_gpu.pt` (14.8 KB — state dict + metadata)
- `vae_v3_scaler.joblib` (815 B — StandardScaler)
