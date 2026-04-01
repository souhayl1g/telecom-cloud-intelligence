# Telecom Cloud Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.5-F7931E?logo=scikitlearn&logoColor=white)
![MinIO](https://img.shields.io/badge/MinIO-S3--compatible-C72E49?logo=minio&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

> Cloud-native telecom analytics and AI-driven operations platform designed for deployment on **Huawei Cloud Stack (HCS)**.
> Links OSS network KPIs to BSS business impact using real ML models, a 3-layer data lake, and a structured REST API.

---

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Data Model](#data-model)
- [AI Models](#ai-models)
- [Roadmap](#roadmap)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)

---

## Overview

Telecom Cloud Intelligence is a fully containerised platform that:

1. **Ingests** synthetic OSS (network KPI) and BSS (revenue/usage) data per pipeline run — 200 OSS records from 10 cell towers + 200 BSS subscriber records from 3 Tunisian operators
2. **Injects realistic faults**: 2–3 random cells degrade (throughput collapse, latency spike) + correlated BSS dips (data usage drops, churn spikes)
3. **Stores** raw datasets in a 3-layer MinIO data lake (`raw` → `processed` → `curated`)
4. **Runs 3 AI models** — SLA breach risk scoring (GradientBoostingRegressor), OSS anomaly detection (IsolationForest), BSS revenue anomaly detection (IsolationForest)
5. **Computes OSS–BSS correlations** — Pearson + Spearman on 5 metric pairs (latency↔revenue, throughput↔data, packet_loss↔churn, etc.)
6. **Persists all results** to PostgreSQL (7 tables)
7. **Serves** structured insights through 7 FastAPI REST endpoints

The stack is intentionally portable to **Huawei Cloud Stack**: MinIO → OBS, PostgreSQL → RDS, containers → ECS.

---

## Architecture

### Services

| Service | Image | Port | Role |
|---|---|---|---|
| `postgres` | postgres:16 | 5432 | Serving store + run metadata |
| `minio` | minio/minio | 9000 / 9001 | S3-compatible data lake |
| `api-gateway` | custom | 8000 | Public REST API (FastAPI) |
| `ai-service` | custom | 8001 | ML inference engine (scikit-learn, 3 models) |
| `pipeline-worker` | custom | — | 22-step pipeline orchestrator (daemon, 2-min cycle) |
| `prometheus` | prom/prometheus | 9090 | Metrics scraper (api-gateway + ai-service) |
| `grafana` | grafana/grafana | 3000 | Observability dashboard |

### Data Flow

```
pipeline-worker (daemon, 22 steps per cycle, repeats every 2 min)
  ├── generate 200 OSS records (with fault injection) + 200 BSS records (80% prepaid / 20% postpaid)
  ├── upload raw JSON    →  minio  s3://raw/oss/<date>/<run_id>.json
  │                                s3://raw/bss/<date>/<run_id>.json
  ├── process + enrich   →  minio  s3://processed/oss/... (latency_severity, qos_score, ...)
  │                                s3://processed/bss/... (arpu_category, churn_bucket, ...)
  ├── POST /infer/sla-risk          →  ai-service  (9-feature GBR vector)
  ├── POST /infer/anomaly           →  ai-service  (200 raw OSS records, IsolationForest)
  ├── POST /infer/revenue-anomaly   →  ai-service  (200 BSS records, IsolationForest)
  ├── compute Pearson + Spearman correlations (5 pairs × 2 methods = 10 results)
  ├── build curated dataset (joined OSS+BSS+AI) → minio s3://curated/...
  └── INSERT  →  postgres   pipeline_runs · dataset_registry · model_registry
                             sla_risk_scores · anomalies · revenue_anomalies · correlation_insights

api-gateway (:8000)
  └── SELECT  →  postgres  (serves results to clients via 7 endpoints)
```

### HCS Deployment Mapping

| Local | Huawei Cloud Stack |
|---|---|
| Docker containers | ECS (Elastic Cloud Server) / CCE (Cloud Container Engine) |
| MinIO volumes | OBS (Object Storage Service) |
| PostgreSQL container | RDS for PostgreSQL |
| Docker network | VPC |
| Env-var secrets | IAM / KMS |

---

## Quick Start

**Prerequisites:** Docker + Docker Compose

```bash
# 1. Clone and start the full 7-container stack
git clone https://github.com/souhayl1g/telecom-cloud-intelligence.git
cd telecom-cloud-intelligence
docker compose up --build -d

# pipeline-worker starts automatically in daemon mode (runs every 2 min)
# Wait ~30 s for the first cycle to complete, then query results:
curl http://localhost:8000/sla-risk
curl http://localhost:8000/anomalies
curl http://localhost:8000/revenue-anomalies
curl http://localhost:8000/correlation
curl http://localhost:8000/pipeline-runs
```

> MinIO console: **http://localhost:9001** · user: `minio` · password: `minio_pw`
> Grafana: **http://localhost:3000** · user: `admin` · password: `admin`
> Prometheus: **http://localhost:9090**

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service liveness check |
| `GET` | `/sla-risk` | Latest SLA risk score with feature importances |
| `GET` | `/sla-risk/history?limit=N` | Last N SLA scores, newest first (default 20, max 200) |
| `GET` | `/anomalies?limit=N` | Last N OSS anomaly records with `cell_id`, `severity`, `value` (default 50, max 500) |
| `GET` | `/pipeline-runs?limit=N` | Last N pipeline runs with status and timestamps (default 10, max 100) |
| `GET` | `/revenue-anomalies?limit=N` | Last N BSS revenue anomalies with `operator`, `line_type`, `plan`, `severity` (default 50, max 500) |
| `GET` | `/correlation?limit=N` | Last N OSS–BSS correlations: Pearson + Spearman (default 50, max 200) |

**Example — `GET /sla-risk`**

```json
{
  "run_id": "run-a8f5b0809b6c",
  "region": "demo",
  "score": 0.724,
  "model_version": "v2.0",
  "explanation": {
    "method": "GradientBoostingRegressor",
    "top_driver": "mean_latency_ms",
    "feature_importances": {
      "mean_latency_ms": 0.69,
      "mean_packet_loss_pct": 0.12,
      "max_latency_ms": 0.08
    }
  }
}
```

### AI Service Internal API (port 8001)

| Method | Endpoint | Model |
|---|---|---|
| `GET` | `/health` | Returns model version |
| `POST` | `/infer/sla-risk` | GradientBoostingRegressor v2.0 — returns `score` (0–1) + feature importances |
| `POST` | `/infer/anomaly` | IsolationForest v2.0 — returns per-record `is_anomaly` + `anomaly_score` (OSS) |
| `POST` | `/infer/revenue-anomaly` | IsolationForest v2.0 — returns per-record `is_anomaly` + `anomaly_score` (BSS) |

---

## Data Model

PostgreSQL database `telecom_intel` — 7 tables:

| Table | Rows/run | Purpose |
|---|---|---|
| `pipeline_runs` | 1 | Run lifecycle: `run_id`, `status`, timestamps |
| `dataset_registry` | 5 | MinIO object metadata: 2 raw + 2 processed + 1 curated |
| `model_registry` | 3 | Model artifacts: sla-risk, anomaly, revenue-anomaly (v2.0) |
| `sla_risk_scores` | 1 | GBR score (0–1), explanation JSONB, model version |
| `anomalies` | 5–30 | Per-record OSS anomalies: `cell_id`, `severity`, `kpi_name`, `value` |
| `revenue_anomalies` | 5–20 | Per-subscriber BSS anomalies: `operator`, `line_type`, `plan`, `severity` |
| `correlation_insights` | 10 | OSS–BSS Pearson/Spearman correlations (5 pairs × 2 methods) |

Apply schema (first-time setup):

```bash
docker compose exec postgres psql -U telecom -d telecom_intel -f /dev/stdin < docs/db/schema.sql
```

---

## AI Models

### Model 1: SLA Risk Scorer — `GradientBoostingRegressor v2.0`

Predicts the probability of an SLA breach in the current 15-minute window.

| Parameter | Value |
|---|---|
| Training samples | 3,000 synthetic windows |
| Input features | 9 aggregated KPIs (mean/std/max latency, mean/max packet loss, mean/std throughput, mean active users, mean RSRP) |
| Hyperparameters | n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8 |
| Output | Risk score 0.0–1.0 + feature importances |
| Top feature | `mean_latency_ms` (importance ≈ 0.69) |
| Persistence | `/app/models/sla_risk_model.joblib` (Docker volume `aimodels`) |

### Model 2: Network Anomaly Detector — `IsolationForest v2.0`

Flags individual OSS KPI records that deviate from learned normal behaviour.

| Parameter | Value |
|---|---|
| Training samples | 3,000 records (95% normal + 5% injected faults) |
| Input features | 5 per-record KPIs (throughput, latency, packet loss, active users, RSRP) |
| Hyperparameters | n_estimators=150, contamination=0.05 |
| Output | `is_anomaly` flag + normalised `severity` (0–1) |
| Persistence | `/app/models/anomaly_model.joblib` (Docker volume `aimodels`) |

### Model 3: Revenue Anomaly Detector — `IsolationForest v2.0`

Detects anomalous BSS subscriber records (SIM box fraud, dormant SIMs, SMS spam).

| Parameter | Value |
|---|---|
| Training samples | 3,000 records (95% normal Tunisian subscriber behaviour, 5% anomalous) |
| Input features | 5 per-record BSS metrics (revenue_tnd, data_used_gb, voice_min, sms_count, churn_risk) |
| Hyperparameters | n_estimators=150, contamination=0.05 |
| Output | `is_anomaly` flag + normalised `severity` (0–1) |
| Persistence | `/app/models/revenue_anomaly_model.joblib` (Docker volume `aimodels`) |

Models are loaded from disk on restart — no retraining required after the first run.

---

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| **1** | Vertical slice: data generation → MinIO → PostgreSQL → REST API | ✅ Complete |
| **2** | Real ML inference: GBR SLA risk + IsolationForest anomaly detection | ✅ Complete |
| **3** | Fault injection · revenue anomaly detection · OSS–BSS correlation engine · Tunisian prepaid market model | ✅ Complete |
| **4** | Labeled evaluation dataset — precision, recall, F1 per model | 🔄 Planned |
| **5** | Prometheus + Grafana observability stack | ✅ Complete |
| **6** | HCS deployment: OBS + RDS + ECS with evidence | 🔄 Planned |

---

## Project Structure

```
telecom-cloud-intelligence/
├── docker-compose.yml                    # 7-service stack definition
├── services/
│   ├── api-gateway/                      # FastAPI REST gateway (:8000, 7 endpoints)
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── ai-service/                       # ML inference engine (:8001, 3 models)
│   │   ├── main.py                       # GBR + 2× IsolationForest training & serving
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── pipeline-worker/                  # One-shot 22-step pipeline
│       ├── worker/__main__.py
│       ├── requirements.txt              # numpy, boto3, psycopg2, requests, scipy
│       └── Dockerfile
├── docs/
│   ├── db/schema.sql                     # PostgreSQL schema (7 tables)
│   ├── overview/project-snapshot.md      # Master state document
│   ├── architecture/architecture-v1.md   # C4 architecture diagrams
│   ├── architecture/ml-models.md         # Complete ML model documentation
│   ├── data-model/                       # Data lake + ER diagrams
│   ├── deployment/local-docker.md        # Local deployment diagram
│   ├── generate_pdf.py                   # Documentation PDF generator
│   ├── generate_knowledge_base.py        # Academic reference PDF (24 IEEE citations)
│   └── generate_reference_pdf.py         # Complete technical & commercial reference PDF
└── diagrams/export/                      # PNG exports of all architecture diagrams
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Services | Python 3.11, FastAPI 0.115, Uvicorn |
| ML / AI | scikit-learn 1.5 (GradientBoostingRegressor, IsolationForest ×2), NumPy 2.0, joblib |
| Statistics | SciPy 1.14 (Pearson/Spearman correlations) |
| Data pipeline | boto3, psycopg2, NumPy, SciPy |
| Storage | PostgreSQL 16, MinIO (S3-compatible) |
| Containerisation | Docker, Docker Compose |
| Cloud target | Huawei Cloud Stack (ECS, OBS, RDS, VPC) |
