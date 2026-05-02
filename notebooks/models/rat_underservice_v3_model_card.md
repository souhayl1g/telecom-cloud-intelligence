# RAT Underservice Detection v3.0 — Model Card

## Overview
| Attribute | Value |
|-----------|-------|
| **Model Name** | RAT Underservice Detection v3.0 |
| **Algorithm** | XGBoost Classifier |
| **Task** | Binary Classification |
| **Target** | rat_gap_score > 0.5 (underserved subscribers) |
| **Version** | v3.0-gpu |
| **Date** | 2026-04-28 |

## Training Data
| Attribute | Value |
|-----------|-------|
| **Total samples** | 2,468,026 subscribers |
| **Real samples** | 968,077 (Feb 468K + Mar 500K) |
| **Simulated samples** | 1,499,949 (Jan 500K + Apr 500K + May 500K) |
| **Positive class** | 226,564 (9.2%) |
| **Negative class** | 2,241,462 (90.8%) |
| **Train split** | 2,097,822 (85%) |
| **Test split** | 370,204 (15%) |
| **Time span** | 2026-01 to 2026-05 |

## Features (10)
1. dou_total
2. duration
3. s1_mme_sr
4. iu_attach_sr
5. gb_attach_sr
6. network_experience_index
7. avg_throughput (area aggregate)
8. avg_latency (area aggregate)
9. avg_packet_loss (area aggregate)
10. anomaly_rate (area aggregate)

## Hyperparameters
| Parameter | Value |
|-----------|-------|
| n_estimators | 500 |
| max_depth | 8 |
| learning_rate | 0.05 |
| subsample | 0.8 |
| colsample_bytree | 0.8 |
| min_child_weight | 3 |
| gamma | 0.2 |
| reg_alpha | 0.1 |
| reg_lambda | 2.0 |
| scale_pos_weight | 9.87 |
| tree_method | hist |
| device | cuda |

## Performance
| Metric | Value |
|--------|-------|
| ROC-AUC | 0.9605 |
| Accuracy | 0.8708 |
| Precision | 0.4078 |
| Recall | 0.8934 |
| F1 | 0.5599 |

## Feature Importances
| Feature | Importance |
|---------|-----------|
| dou_total | 0.5186 |
| network_experience_index | 0.3476 |
| iu_attach_sr | 0.0791 |
| duration | 0.0308 |
| gb_attach_sr | 0.0113 |
| s1_mme_sr | 0.0058 |
| avg_packet_loss | 0.0035 |
| avg_latency | 0.0020 |
| avg_throughput | 0.0013 |
| anomaly_rate | 0.0010 |

## Limitations
- Precision is moderate (0.408) due to class imbalance
- High recall (0.893) ensures most underserved subscribers are caught
- Area aggregates may not capture subscriber-specific network conditions

## Artifacts
- `rat_v3_xgb_gpu.joblib` (4.2 MB)
- `rat_v3_gpu_features.joblib` (172 B)
