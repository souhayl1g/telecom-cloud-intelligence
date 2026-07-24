# NeXo Defense Preparation — Drill Q&A

**Activated:** 2026-06-02 | **Advisor Rehearsal:** next week | **Final Defense:** mid-July 2026  
**Method:** Socratic Q&A — I ask → you answer from memory → I score (🔴/🟡/🟢) → repeat until all 🟢.

---

## Priority Pillars

| Priority | Topic | Why It Matters |
|---|---|---|
| **P0** | **Granger Causality** | Null hypothesis, lag selection, F-statistic, causal vs correlation, `granger_feature_gate.json` 2-tier |
| **P0** | **ADN L4 Agent** | Auto-approve logic, action lifecycle, playbook execution, L4 spec, `classifyAction` matrix |
| **P0** | **Data flow end-to-end** | Raw TT CSV → PostgreSQL → subscriber_features → inference → dashboard. Jury will trace one subscriber record |
| **P1** | **3 ML Models** | CEM (why DART? 256 leaves?), VAE (why normal-only? recon error → score), RAT (scale_pos_weight, leakage) |
| **P1** | **Dashboard Architecture** | App Router, `/api/platform-data` SSR proxy, icon-rail, Cmd+K, StatusStrip, TunisiaMap, httpOnly cookies |
| **P1** | **Actuation Layer** | 5 playbooks — real ops, not mocks. Twilio/SMTP/MinIO/fpdf2 |
| **P2** | **MLOps / Pipeline** | 22-step pipeline-worker, daemon mode, data-init sidecar, MinIO 3-layer, hot-reload via mtime |
| **P2** | **Cloud / HCS** | MinIO→OBS, PostgreSQL→RDS, Docker→ECS. Deployment evidence screenshots |

---

## Knowledge Checkpoints

### Granger Causality
1. What is the null hypothesis in a Granger F-test?
2. Why is `LAG_WINDOW_MINUTES = 43200` (30 days) a conversion constant, not a moving-average window?
3. Walk the 2-tier architecture: offline gate vs online lead-time API.
4. What does `p < 0.05` mean in Granger context? What if `p = 0.12`?
5. How do we go from "significant OSS→CEM pair" to `CEM_Y(t) ~ OSS_X(t−best_lag)`?
6. Where does `granger_feature_gate.json` live, who produces it, who consumes it?

### ADN L4 Agent
1. What are the 6 ADN levels (L0–L5)? Where does this project sit and why?
2. Explain `classifyAction(severity, type, confidence)` — auto-approved vs human-gated.
3. Walk action lifecycle: `generateActions()` → POST → PATCH → POST execute → audit trail.
4. Why does L4 agent use `/api/platform-data` instead of calling :8000 directly?
5. What is in the `execution_log` JSONB? Give an example.

### Data Flow
1. A subscriber record enters via `ingest_bss.py` — what happens next? Every table it touches.
2. What is the join key between BSS and OSS? Why not IMSI↔cell?
3. How does `compute_features.py` turn `bss_subscribers` into `subscriber_features`? Name derived columns.
4. What is `features_json` and why is it JSONB?
5. How does pipeline-worker call ai-service? What does `v3_client` pass?

### ML Models
1. CEM: Why is the target formula-derived? Honest limitation? What would make it truly predictive?
2. VAE: Why train on normal-only? How does reconstruction error → anomaly score? Threshold?
3. RAT: Leakage prevention — which features were dropped and why?
4. How does `model_cache.py` hot-reload? What triggers it?

---

## Data & Metrics Integrity

**Single source of truth for every metric: `notebooks/models/metrics.json`** (computed 2026-05-25 by
`scripts/dump_model_metrics.py`, read from the model cards). If any number anywhere in the repo —
dashboard, report, slides, `master_v3_training_summary.md` — disagrees with `metrics.json`,
**`metrics.json` wins.** The old `master_v3_training_summary.md` (dated 2026-04-28) carried
superseded pre-leakage-fix numbers (CEM R²=0.9933, VAE 0.9307, RAT 0.9605) — never quote it.

Honest headline numbers to know cold:

| Model | Metric | Value |
|-------|--------|-------|
| CEM (LightGBM DART, 13 feat) | Test R² | **0.9784** (MAE 0.0304) |
| VAE (PyTorch, 9 feat) | ROC-AUC | **0.9821** (PR-AUC 0.9974) |
| RAT (XGBoost, 19 feat) | ROC-AUC, temporal hold-out | **0.9203** (F1 0.8927) |

Volume: **968,077 real** BSS subscribers (Feb+Mar) + ~1.5M bootstrap-simulated = **2.47M** total
scored rows. **18.8M real** OSS cell-KPI rows (2G/3G/4G).

### The RAT leakage story (jury will probe this — own it)

The first RAT model scored **ROC-AUC ≈ 1.0**. A perfect score is a red flag, not a trophy.
Root cause: two features — `is_4g_capable` and `traffic_share_4g` — were left in the training set,
but the underservice **label is derived from those exact columns** (a subscriber is "underserved"
when device generation exceeds the RAT actually serving them). The model was reading the answer key
— textbook **target leakage**.

**Fix (notebook 04):** dropped the formula-input features and their proxies, added a StratifiedKFold
cross-validation honesty check + early stopping. Honest ROC-AUC settled at **0.9203** (temporal
hold-out). Three independent checks agree it isn't leaked: temporal hold-out 0.9203, random split
0.9419, 5-fold CV 0.9352 — all comfortably below the self-imposed 0.995 leakage alarm.

> Q: *"How do you know THIS number (0.9203) isn't leaked too?"*
> A: The 19-feature set contains no column that defines the label; temporal, random, and CV splits
> land within a tight band; and SHAP shows the top drivers are area-aggregate network KPIs, not
> label-defining device flags.

---

## Defense Pain Hook (memorize verbatim)

> *"Network anomalies invisible to OSS until customer complaint reaches Care."*

This is your opening. OSS↔CEM convergence via Granger F-test → ConvergenceSpirit → ActionSpirit. Every component closes this gap.

---

## Workflow

1. I ask a batch of 3–5 questions on one pillar
2. You answer in your own words (no reading — from memory)
3. I correct gaps, add depth, assign confidence score (🔴/🟡/🟢)
4. Repeat until every pillar is 🟢
5. I generate mock jury questions (hard ones) for final polish
