# CEM Experience Score v3.0 — Model Card

## Overview
| Attribute | Value |
|-----------|-------|
| **Model Name** | CEM Experience Score v3.0 |
| **Algorithm** | LightGBM (DART boosting) |
| **Task** | Regression |
| **Target** | cem_score (0–1, formula-derived from attach SRs + DOU) |
| **Version** | v3.0-gpu |
| **Date** | 2026-04-28 |

## Training Data
| Attribute | Value |
|-----------|-------|
| **Total samples** | 2,468,026 subscribers |
| **Real samples** | 968,077 (Feb 468K + Mar 500K) |
| **Simulated samples** | 1,499,949 (Jan 500K + Apr 500K + May 500K) |
| **Train split** | 2,097,822 (85%) |
| **Test split** | 370,204 (15%) |
| **Time span** | 2026-01 to 2026-05 |

## Features (13)
1. usim_bottleneck (boolean → int)
2. data_intensity
3. dou_total
4. duration
5. s1_mme_sr
6. iu_attach_sr
7. gb_attach_sr
8. avg_throughput (area aggregate)
9. avg_latency (area aggregate)
10. avg_packet_loss (area aggregate)
11. anomaly_rate (area aggregate)
12. generation_4g (one-hot)
13. generation_5g (one-hot)

## Hyperparameters
| Parameter | Value |
|-----------|-------|
| boosting_type | dart |
| drop_rate | 0.1 |
| skip_drop | 0.5 |
| num_leaves | 256 |
| max_depth | 12 |
| learning_rate | 0.03 |
| feature_fraction | 0.8 |
| bagging_fraction | 0.8 |
| bagging_freq | 5 |
| min_child_samples | 50 |
| reg_alpha | 0.1 |
| reg_lambda | 1.0 |
| num_boost_round | 1000 |
| early_stopping | 50 rounds |

## Performance
| Metric | Value |
|--------|-------|
| R² | 0.9933 |
| MAE | 0.0129 |
| RMSE | 0.0162 |

## Feature Importances (SHAP)
| Feature | Importance |
|---------|-----------|
| s1_mme_sr | 0.1316 |
| dou_total | 0.0570 |
| iu_attach_sr | 0.0467 |
| gb_attach_sr | 0.0359 |
| generation_4g | 0.0024 |
| avg_packet_loss | 0.0018 |
| data_intensity | 0.0012 |

## Limitations
- Target is formula-derived (attach SRs + DOU), not external CEM survey data
- For true predictive modeling, needs external CEM survey or NPS scores
- Very high R² because model learns the domain formula

## Artifacts
- `cem_v3_lightgbm_gpu.joblib` (18.6 MB)
- `cem_v3_gpu_features.joblib`
