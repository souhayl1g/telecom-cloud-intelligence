
# NeXo v3.0 Master Training Summary
## Date: 2026-04-28T20:55:43.587409

### Datasets
| Model | Train Size | Test Size | Real % | Simulated % |
|-------|-----------|-----------|--------|-------------|
| CEM | 2,097,822 | 370,204 | 39.2% | 60.8% |
| Anomaly | 424,769 | 74,960 | 60.0% | 40.0% |
| RAT | 2,097,822 | 370,204 | 39.2% | 60.8% |

### Results
| Model | Algorithm | GPU | Key Metric | Value |
|-------|-----------|-----|-----------|-------|
| CEM | LightGBM (DART) | Yes | R² | 0.9933 |
| Anomaly | VAE (8 latent) | Yes | ROC-AUC | 0.9307 |
| RAT | XGBoost | Yes | ROC-AUC | 0.9605 |

### Artifacts
- cem_v3_lightgbm_gpu.joblib
- oss_vae_v3_gpu.pt
- rat_v3_xgb_gpu.joblib
