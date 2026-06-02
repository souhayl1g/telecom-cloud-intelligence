# MLOps Memory

> ⚠️ Read [REALIGNMENT_2026-05-10.md](REALIGNMENT_2026-05-10.md) first for the post-expert-feedback realignment + cleanup. The content below is pre-realignment context.


> Last updated: 2026-04-29

## Model Registry

| Model | Version | Algorithm | Training Data | Test Performance | File | Size |
|-------|---------|-----------|---------------|------------------|------|------|
| SLA Risk | v2.0 | GradientBoostingRegressor | Synthetic (200/run) | — | `sla_risk_model.joblib` | 611 KB |
| OSS Anomaly | v2.0 | IsolationForest | Synthetic (200/run) | — | `anomaly_model.joblib` | 1.75 MB |
| BSS Revenue | v2.0 | IsolationForest | Synthetic (200/run) | — | `revenue_anomaly_model.joblib` | 1.84 MB |
| CEM Score | v3.0 | LightGBM DART | 2.47M real+simulated BSS | R²=0.9784, MAE=0.0304 | `cem_v3_lightgbm.joblib` | 18.6 MB |
| OSS Anomaly | v3.0 | PyTorch VAE | 500K real+simulated OSS | ROC-AUC=0.9307 | `oss_vae_v3_gpu.pt` | 14.8 KB |
| RAT Underservice | v3.0 | XGBoost GPU | 2.47M real+simulated BSS | ROC-AUC=0.9605 | `rat_v3_xgb_gpu.joblib` | 4.2 MB |

## Training Pipeline

### Notebook Flow

```
05_etl_feature_engineering.ipynb
    ├──→ data/cem_training_mar2026.npz
    ├──→ data/anomaly_training_mar2026.npz
    └──→ data/rat_underservice_mar2026.npz

06_cem_score_training.ipynb → models/cem_v3_lightgbm.joblib
07_oss_vae_anomaly_training.ipynb → models/oss_vae_v3.pt
08_rat_underservice_training.ipynb → models/rat_underservice_v3_xgb.joblib

09_master_v3_combined_training.py (replaces all v3 models)
    ├──→ models/cem_v3_lightgbm_gpu.joblib
    ├──→ models/oss_vae_v3_gpu.pt
    └──→ models/rat_v3_xgb_gpu.joblib
```

### VAE Architecture Evolution

| Version | Architecture | Parameters | Training |
|---------|-------------|------------|----------|
| Legacy | 10→16→8→4 latent→8→16→10 | ~1,500 | Notebook 07, CPU |
| v3 Original | 10→16→8→4 latent→8→16→10 | ~1,500 | Notebook 07, CPU |
| **v3 GPU** | **9→32→16→8 latent→16→32→9** | **2,057** | **Notebook 09, GPU** |

### XGBoost GPU Syntax Note

XGBoost 3.2.0 dropped `gpu_hist`. New syntax:
```python
XGBClassifier(
    tree_method="hist",
    device="cuda",  # NOT gpu_hist
    # ...
)
```

### LightGBM GPU Limitation

LightGBM pip build lacks CUDA/OpenCL support. Runs on CPU despite "gpu" in filename. Uses DART boosting with aggressive regularization for efficiency.

## Model Cache (ai-service)

- Lazy loader with 30-second TTL
- File mtime checking for hot reload
- Loads 6 models: 3 v2.0 + 3 v3.0
- VAE loader tries architectures in order: ExperienceVAEv3 → ExperienceVAELegacy → ExperienceVAE

## CI/CD

GitHub Actions pipeline (`.github/workflows/ci-cd.yml`):
1. Lint (ruff)
2. Test (pytest)
3. Build (Docker)
4. Integration (full stack health check)
5. Security (pip-audit + secret scan)
6. Deploy notification

Registry: `ghcr.io/souhayl1g/telecom-cloud-intelligence/*`
