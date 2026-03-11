# PFE PROJECT — MASTER SNAPSHOT v2.0
**Date: 2026-03-11**

---

## 0. Operating Mode

Absolute Mode.
No filler, no padding, no motivational language.
All state assertions below are evidence-backed against the running repository.

---

## 1. Student Context

- Engineering student at ESPRIT
- 6-month internship at Huawei Tunisia (Cloud IT / Sales-Solution side)
- Strong networking + AI background
- No access to real production OSS/BSS — synthetic data only

Goals:
- Graduate with excellence
- Impress Huawei Cloud team
- Deliver runnable cloud-native AI platform
- Demonstrate Huawei Cloud Stack architectural maturity

---

## 2. Locked Project Direction

**Project Title:** Cloud-Native Telecom Intelligence Platform with AI Operations Agent (HCS-Ready)

Direction locked. No pivoting.

System objective: cloud-native telecom intelligence platform linking network KPIs (OSS) to business impact (BSS) using AI-driven analytics and REST APIs.

---

## 3. Core System Concept

| Responsibility | Implementation |
|---|---|
| OSS ingestion | Synthetic KPI generator (200 records/run, 10 cells, fault injection) |
| BSS ingestion | Synthetic subscriber/revenue generator (TND, 3 Tunisian operators, 80% prepaid / 20% postpaid) |
| Data lake — raw layer | MinIO bucket `raw`, JSON objects per run |
| Data lake — processed layer | MinIO bucket `processed`, enriched with severity/category/qos fields |
| Data lake — curated layer | MinIO bucket `curated`, joined OSS+BSS+AI dataset per run |
| Metadata/serving store | PostgreSQL 16 — 7 tables, fully populated |
| Pipeline orchestration | pipeline-worker service (22-step execution) |
| AI — SLA risk | GradientBoostingRegressor v2.0, 9 KPI features |
| AI — anomaly detection | IsolationForest v2.0, per-record composite KPI scoring |
| AI — revenue anomaly | IsolationForest v2.0, per-subscriber BSS anomaly detection |
| AI — OSS-BSS correlation | Pearson + Spearman on 5 metric pairs (10 results/run) |
| REST access | API gateway, FastAPI, 7 endpoints |
| Local execution | Docker Compose, 5 containers |
| Cloud portability | Architecture mapped to HCS (OBS/RDS/ECS) — deployment pending Phase 6 |

---

## 4. Runtime Architecture — Actual Running Stack

### Services (docker compose ps verified)

| Service | Image | Port | Status |
|---|---|---|---|
| postgres | postgres:16 | 5432 | healthy |
| minio | minio/minio:latest | 9000/9001 | healthy |
| api-gateway | telecom-cloud-intelligence-api-gateway | 8000 | running |
| ai-service | telecom-cloud-intelligence-ai-service | 8001 | running |
| pipeline-worker | telecom-cloud-intelligence-pipeline-worker | — | run-once |

### API Endpoints (7 total)

| Method | Path | Function |
|---|---|---|
| GET | /health | Service liveness |
| GET | /sla-risk | Latest SLA risk score from GBR model |
| GET | /sla-risk/history | Last N scores, newest first |
| GET | /anomalies | Latest N OSS anomaly records with cell_id, severity |
| GET | /pipeline-runs | Last N pipeline execution records |
| GET | /revenue-anomalies | Latest N BSS revenue anomalies with operator, line_type, plan |
| GET | /correlation | Latest N OSS↔BSS Pearson/Spearman correlations |

### AI Service Endpoints (4 total)

| Method | Path | Model |
|---|---|---|
| GET | /health | Returns model_version (v2.0) |
| POST | /infer/sla-risk | GradientBoostingRegressor v2.0 |
| POST | /infer/anomaly | IsolationForest v2.0 (OSS) |
| POST | /infer/revenue-anomaly | IsolationForest v2.0 (BSS) |

---

## 5. Documentation State

### Artifacts produced

| Artifact | Status |
|---|---|
| Proposal document (12 chapters) | Complete |
| Supervisor presentation (15 slides) | Complete |
| System Context Diagram (C4 L1) | Complete |
| Container Diagram (C4 L2) | Complete |
| Sequence Diagram | Complete |
| Data Lake Architecture diagram | Complete |
| ER Diagram | Complete |
| Local Deployment Diagram | Complete |
| Use Case Diagram | Complete |
| `docs/db/schema.sql` | Complete — matches actual DB structure (7 tables) |
| `docs/architecture/ml-models.md` | Complete — full ML model documentation (586 lines) |
| Complete technical reference PDF | Complete — 23-page reference with verified Tunisian forfait data |

---

## 6. Execution Status

### Completed

#### Repository
- Git repo initialized, `dev` branch in use
- Structured commits maintained

#### Infrastructure
- Docker Compose 5-service stack operational
- Named volumes: `pgdata`, `miniodata`, `aimodels`

#### Database
- Schema applied: 7 tables (`pipeline_runs`, `dataset_registry`, `model_registry`, `anomalies`, `sla_risk_scores`, `revenue_anomalies`, `correlation_insights`)
- All tables populated

#### Data Pipeline (22-step execution)

1. Ensure MinIO buckets exist (raw / processed / curated layers)
2. Generate synthetic OSS dataset (200 records, 10 cells, fault injection: 2–3 cells degrade)
3. Generate synthetic BSS dataset (200 records, 80% prepaid / 20% postpaid, correlated dips)
4. Upload OSS raw to MinIO
5. Upload BSS raw to MinIO
6. Insert pipeline_runs record
7. Register raw datasets in dataset_registry
8. Process OSS data → upload to processed bucket (latency_severity, throughput_category, load_factor, qos_score)
9. Process BSS data → upload to processed bucket (arpu_category, data_intensity, churn_bucket)
10. Register processed datasets
11. Compute aggregate KPI features (9 OSS + 6 BSS)
12. Call AI service /infer/sla-risk
13. Call AI service /infer/anomaly (OSS IsolationForest)
14. Call AI service /infer/revenue-anomaly (BSS IsolationForest)
15. Compute OSS↔BSS correlations (5 pairs × 2 methods = 10 results)
16. Build curated dataset (joined OSS+BSS+AI) → upload to curated bucket
17. Register curated dataset
18. Persist SLA risk score
19. Persist OSS anomalies
20. Persist revenue anomalies (with operator, line_type, plan)
21. Register models in model_registry
22. Persist correlation insights + mark pipeline succeeded

#### AI Models (3 models, all v2.0)
- **GradientBoostingRegressor** — trained on 3000 synthetic windows at startup
  - 9 features: mean/std/max latency, mean/max packet loss, mean/std throughput, mean active users, mean RSRP
  - Hyperparameters: n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8
  - Top driver: `mean_latency_ms` (importance 0.69)
  - Models persisted to `/app/models/` via Docker volume, survive restarts
- **IsolationForest (OSS)** — trained on 3000 OSS KPI records, 5% contamination
  - Hyperparameters: n_estimators=150, contamination=0.05
  - Per-record anomaly flag + normalised severity score (0–1)
- **IsolationForest (BSS)** — trained on 3000 BSS revenue/usage records
  - Hyperparameters: n_estimators=150, contamination=0.05
  - Detects: SIM box fraud, dormant SIMs, SMS spam, churn-correlated anomalies

#### BSS Data Model (Tunisian Market)
- **80% prepaid / 20% postpaid** (matches INTT 2023 market statistics)
- Prepaid forfait tiers based on verified 2025 operator pricing:
  - data_1go (3–7 DT), data_4go (8–14 DT), data_6go (12–18 DT)
  - data_25go (25–35 DT), data_45go (42–55 DT), data_100go (65–80 DT)
- Postpaid plan tiers:
  - post_40 (35–45 DT), post_60 (52–68 DT), post_90 (80–100 DT)
- ARPU categories: low (<10 TND), mid (<40 TND), high (≥40 TND)
- Revenue verified against: orange.tn, tunisietelecom.tn, ooredoo.tn, thd.tn

---

## 7. Technical Gaps Remaining

| Gap | Phase | Priority |
|---|---|---|
| Labeled evaluation dataset + precision/recall per model | 4 | High |
| Prometheus + Grafana observability stack | 5 | Medium |
| HCS deployment evidence (OBS + RDS + ECS) | 6 | High (Huawei impression) |
| Report chapters: Evaluation + Cloud Deployment | — | Required for defence |

---

## 8. Phase Roadmap

| Phase | Scope | Status | Effort |
|---|---|---|---|
| 1 | Vertical slice completion | **Done** | — |
| 2 | Real ML inference (GBR + IsolationForest) | **Done** | — |
| 3 | Fault injection, BSS correlation, revenue anomaly, correlation engine, Tunisian prepaid model | **Done** | — |
| 4 | Labeled evaluation + precision/recall metrics per model | Next | ~1 week |
| 5 | Prometheus + Grafana observability | Pending | 3–5 days |
| 6 | HCS deployment (OBS/RDS/ECS) with evidence screenshots | Pending | ~1 week |
| — | Report writing (Evaluation + Cloud Deployment chapters) | Ongoing | 2–3 weeks |

**Priority order if time-constrained:** Phase 4 → Phase 6 → Phase 5

Phase 6 has highest impression-to-effort ratio for a Huawei audience.

---

## 9. Current True State

| Dimension | State |
|---|---|
| Architecture | Complete |
| Documentation | Strong — all major artifacts current |
| Infrastructure | 5 containers running |
| Database | Healthy — 7 tables, all populated |
| Schema file | Committed — matches actual DB |
| APIs | 7 endpoints operational |
| Pipeline | 22-step execution |
| AI inference | Real models — GBR v2.0 + IsolationForest v2.0 × 2 |
| Data lake | 3 layers populated per run (raw/processed/curated) |
| OSS anomaly detection | Operational — IsolationForest on 5 KPIs |
| Revenue anomaly detection | Operational — IsolationForest on BSS metrics |
| Correlation engine | Operational — 10 results per run (5 pairs × 2 methods) |
| BSS market model | Tunisian prepaid/postpaid with verified 2025 forfait data |
| Observability | Not implemented |
| HCS deployment | Not implemented |

---

## 10. Strategic Positioning

Project represents:
- Cloud-native telecom analytics reference architecture
- AI-augmented operational intelligence platform
- Huawei Cloud Stack portability demonstration
- Telecom data engineering + ML integration exercise
- Verified Tunisian market modelling with real operator pricing data

Project intentionally avoids:
- Real OSS/BSS integration
- Vendor-grade telecom assurance capabilities
- Production telecom operational responsibility

---

## 11. Professional Execution Discipline

Mandatory engineering rules (maintained):
- Architecture freeze before implementation — hold
- Docker-first reproducibility — all changes containerised
- No manual scripts outside repository — hold
- Evidence-based progress validation — every step verified with curl + SQL
- Structured commits with descriptive messages
- Architecture drift prohibited — schema.sql matches actual DB
