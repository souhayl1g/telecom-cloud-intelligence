---
name: Health Check & Model Accuracy Snapshot — 2026-04-06
description: Service health check results and model performance metrics from 2026-04-06 session
type: project
---

## [2026-04-06 15:20] — Health Verification & Model Accuracy Audit

**Status:** PASS — all services healthy after restart

### Service Health
| Service | Status | Notes |
|---------|--------|-------|
| ai-service (:8001) | ✅ OK | model_version: v2.0 |
| api-gateway (:8000) | ✅ OK | serving |
| auth-service (:8002) | ✅ OK | serving |
| pipeline-worker | ✅ Running | 2-min cycles active |
| PostgreSQL | ✅ Healthy | clean shutdown at 11:19 UTC |
| MinIO | ✅ Healthy | — |

**Shutdown cause:** Clean `docker compose down` at ~11:20 UTC (not a crash). Services restarted cleanly.

### Model Registry
All 3 models registered as v2.0, first registered 2026-03-25.
No accuracy_score or metrics column in model_registry — quality tracked via pipeline output.

### SLA Risk Model (GradientBoostingRegressor, 200 est, depth=4)
- **Last 5 scores:** 0.8864, 0.8299, 0.8194, 0.8276, 0.8007 (range ~0.80–0.89)
- **Top feature driver:** `mean_latency_ms` (importance: 0.6947 — dominant)
- **Feature importances:**
  - mean_latency_ms: 69.47%
  - max_latency_ms: 12.39%
  - mean_throughput_mbps: 9.29%
  - mean_packet_loss_pct: 8.02%
  - max_packet_loss_pct: 0.60%
  - std_throughput_mbps: 0.07%
  - std_latency_ms: 0.06%
  - mean_active_users: 0.05%
  - mean_signal_rsrp_dbm: 0.05%
- **Observation:** mean_latency_ms is heavily dominant (69%). Other features have very low importance. Consider re-weighting the training label function or adjusting feature engineering.

### OSS Anomaly Model (IsolationForest, 150 est, contamination=0.05)
- **Total anomalies detected:** 5,501 across 497 runs
- **Avg anomalies/run:** ~11.07 records per run (of 200)
- **Observed rate:** ~5.5% (slightly above 5% contamination target — acceptable)
- **Avg severity score:** 0.8954 (high confidence detections)
- **Last detection:** 2026-04-06 15:11 UTC

### BSS Revenue Anomaly Model (IsolationForest, 150 est, contamination=0.05)
- **Total anomalies detected:** 683 across 382 runs
- **Avg anomalies/run:** ~1.79 records (of 200)
- **Observed rate:** ~0.9% (well below 5% target — potentially under-detecting)
- **Avg severity score:** 0.9717 (very high confidence when detected)
- **Last detection:** 2026-04-06 15:11 UTC

### Key Correlations (from latest run)
- packet_loss ↔ churn_risk: Pearson r=+0.87 (p=0.001) ✅ highly significant
- latency ↔ churn_risk: Pearson r=+0.88 (p=0.0007) ✅ highly significant
- throughput ↔ data_used_gb: Pearson r=+0.67 (p=0.034) ✅ significant

### Next Steps
1. Investigate BSS anomaly under-detection rate (0.9% vs 5% target)
2. Review SLA feature importance imbalance — latency alone drives 69% of predictions
3. Await real Tunisie Telecom data for Phase 3.5 retraining

**Why:** BSS model was trained on data skewed toward high-revenue fraud anomalies; at inference time, synthetic BSS data may not trigger enough outlier scores above the threshold calibrated during training.
**How to apply:** When retraining on real TT data, verify BSS anomaly rate is within 3–7% range.
