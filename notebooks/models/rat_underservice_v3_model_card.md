# RAT Underservice v3 Model Card

## Purpose
Predict subscriber RAT-underservice (4G-capable but stuck on 2G/3G traffic) from behavioral / device features when the formula inputs (`is_4g_capable`, `traffic_share_4g`) are unavailable, stale, or for newly-onboarded subscribers. Used by `pb-churn-prevention`.

## Anti-leakage policy
- Excluded label inputs: `is_4g_capable`, `traffic_share_4g`.
- Excluded proxies: other `traffic_share_*`, raw `traffic_{2,3,4,5}g`, `data_intensity`, `usim_bottleneck`, `highest_rat`.
- Features retained (19): ['volte_flag', 'usim_flag', 'dou_total', 'duration', 'voice_onlinetime_3g', 'voice_onlinetime_2g', 's1_mme_sr', 'iu_attach_sr', 'gb_attach_sr', 'session_flag', 'attach_gap', 'avg_integrity_area', 'avg_cdr_area', 'avg_throughput_area', 'avg_users_area', 'avg_latency_area', 'avg_loss_area', 'cell_count_area', 'anomaly_count_area']

## Training
- XGBoost: ≤800 rounds, depth=6, lr=0.05, subsample=0.8, colsample=0.8, reg_lambda=1.0, gamma=0.1, scale_pos_weight=1.52.
- Early stopping at best val AUC; `best_iteration=799`, `best_val_auc=0.9418500571689761`.

## Random split
- ROC-AUC: 0.9419
- F1@0.5: 0.8418

## Temporal hold-out (2026-09, n=954,760)
- ROC-AUC: 0.9203
- F1@0.5: 0.8927

## 5-fold stratified CV (honesty check, n=200,000)
- Mean ROC-AUC: 0.9352 ± 0.0007
- Mean PR-AUC:  0.8912

## Caveat
If random / temporal / CV all report ROC-AUC > 0.995, residual leakage is almost certain — re-inspect the feature set against the label formula.
