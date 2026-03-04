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

1. **Ingests** synthetic OSS (network KPI) and BSS (revenue/usage) data per pipeline run
2. **Stores** raw datasets in a 3-layer MinIO data lake (`raw` → `processed` → `curated`)
3. **Runs AI inference** — SLA breach risk scoring (GradientBoostingRegressor) and per-record anomaly detection (IsolationForest)
4. **Persists all results** to PostgreSQL (6 tables)
5. **Serves** structured insights through a FastAPI REST gateway

The stack is intentionally portable to **Huawei Cloud Stack**: MinIO → OBS, PostgreSQL → RDS, containers → ECS.

---

## Architecture

### Services

| Service | Image | Port | Role |
|---|---|---|---|
| `postgres` | postgres:16 | 5432 | Serving store + run metadata |
| `minio` | minio/minio | 9000 / 9001 | S3-compatible data lake |
| `api-gateway` | custom | 8000 | Public REST API (FastAPI) |
| `ai-service` | custom | 8001 | ML inference engine (scikit-learn) |
| `pipeline-worker` | custom | — | One-shot data pipeline orchestrator |

### Data Flow

```
pipeline-worker (run-once)
  ├── generate 200 OSS records + 200 BSS records
  ├── upload  →  minio  s3://raw/oss/<date>/<run_id>.json
  │                     s3://raw/bss/<date>/<run_id>.json
  ├── POST /infer/sla-risk  →  ai-service  (9-feature GBR vector)
  ├── POST /infer/anomaly   →  ai-service  (200 raw OSS records)
  └── INSERT  →  postgres   pipeline_runs · dataset_registry
                             sla_risk_scores · anomalies

api-gateway (:8000)
  └── SELECT  →  postgres  (serves results to clients)
```

### HCS Deployment Mapping

| Local | Huawei Cloud Stack |
|---|---|
| Docker containers | ECS (Elastic Cloud Server) |
| MinIO volumes | OBS (Object Storage Service) |
| PostgreSQL container | RDS for PostgreSQL |
| Docker network | VPC |
| Env-var secrets | IAM / KMS |

---

## Quick Start

**Prerequisites:** Docker + Docker Compose

```bash
# 1. Clone and start the full 5-container stack
git clone https://github.com/souhayl1g/telecom-cloud-intelligence.git
cd telecom-cloud-intelligence
docker compose up --build -d

# 2. Run one pipeline cycle (generates data, runs AI inference, persists results)
docker compose run --rm pipeline-worker

# 3. Query results
curl http://localhost:8000/sla-risk
curl http://localhost:8000/anomalies
curl http://localhost:8000/pipeline-runs
```

> MinIO console available at **http://localhost:9001** · user: `minio` · password: `minio_pw`

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service liveness check |
| `GET` | `/sla-risk` | Latest SLA risk score with feature importances |
| `GET` | `/sla-risk/history?limit=N` | Last N SLA scores, newest first |
| `GET` | `/anomalies?limit=N` | Last N anomaly records (`cell_id`, `severity`, `value`) |
| `GET` | `/pipeline-runs?limit=N` | Last N pipeline runs with status and timestamps |

**Example — `GET /sla-risk`**

```json
{
  "run_id": "run-a8f5b0809b6c",
  "region": "demo",
  "score": 0.724,
  "model_version": "v1.0",
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
| `POST` | `/infer/sla-risk` | GradientBoostingRegressor — returns `score` (0–1) |
| `POST` | `/infer/anomaly` | IsolationForest — returns per-record `is_anomaly` + `severity` |

---

## Data Model

PostgreSQL database `telecom_intel` — 6 tables:

| Table | Rows/run | Purpose |
|---|---|---|
| `pipeline_runs` | 1 | Run lifecycle: `run_id`, `status`, timestamps |
| `dataset_registry` | 2 | MinIO object metadata: path, type, row count |
| `sla_risk_scores` | 1 | GBR score (0–1), explanation JSONB, model version |
| `anomalies` | 3–15 | Per-record anomalies: `cell_id`, `severity`, `kpi_name`, `value` |
| `correlation_insights` | 0 *(Phase 3)* | OSS–BSS Pearson/Spearman correlations |
| `model_registry` | 0 *(Phase 3)* | Model artifacts, versions, evaluation metrics |

Apply schema (first-time setup):

```bash
docker compose exec postgres psql -U telecom -d telecom_intel -f /dev/stdin < docs/db/schema.sql
```

---

## AI Models

### SLA Risk Scorer — `GradientBoostingRegressor v1.0`

Predicts the probability of an SLA breach in the current 15-minute window.

| Parameter | Value |
|---|---|
| Training samples | 3,000 synthetic windows |
| Input features | 9 aggregated KPIs (mean/std/max latency, packet loss, throughput, active users, RSRP) |
| Output | Risk score 0.0–1.0 |
| Top feature | `mean_latency_ms` (importance ≈ 0.69) |
| Persistence | `/app/models/sla_risk_model.joblib` (Docker volume `aimodels`) |

### Anomaly Detector — `IsolationForest v1.0`

Flags individual OSS KPI records that deviate from learned normal behaviour.

| Parameter | Value |
|---|---|
| Training samples | 3,000 records (95% normal + 5% injected faults) |
| Input features | 5 per-record KPIs (throughput, latency, packet loss, active users, RSRP) |
| Output | `is_anomaly` flag + normalised `severity` (0–1) |
| Typical detection rate | ~3.5% on normal synthetic data |
| Persistence | `/app/models/anomaly_model.joblib` (Docker volume `aimodels`) |

Models are loaded from disk on restart — no retraining required after the first run.

---

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| **1** | Vertical slice: data generation → MinIO → PostgreSQL → REST API | ✅ Complete |
| **2** | Real ML inference: GBR SLA risk + IsolationForest anomaly detection | ✅ Complete |
| **3** | Fault injection · revenue anomaly detection · OSS–BSS correlation engine | 🔄 Next |
| **4** | Labeled evaluation dataset — precision, recall, F1 per model | 🔄 Planned |
| **5** | Prometheus + Grafana observability stack | 🔄 Planned |
| **6** | HCS deployment: OBS + RDS + ECS with evidence | 🔄 Planned |

**Phase 3 immediate targets:**
- Realistic fault patterns (business-hour load curves, timed outages)
- BSS revenue dips correlated to OSS cell degradation events
- Revenue anomaly model (second IsolationForest on BSS data)
- Populate `correlation_insights` and `model_registry` tables
- New endpoints: `/correlation`, `/revenue-anomalies`

---

## Project Structure

```
telecom-cloud-intelligence/
├── docker-compose.yml                    # 5-service stack definition
├── services/
│   ├── api-gateway/                      # FastAPI REST gateway (:8000)
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── ai-service/                       # ML inference engine (:8001)
│   │   ├── main.py                       # GBR + IsolationForest training & serving
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── pipeline-worker/                  # One-shot 12-step pipeline
│       ├── worker/__main__.py
│       ├── requirements.txt
│       └── Dockerfile
├── docs/
│   ├── db/schema.sql                     # PostgreSQL schema (6 tables)
│   ├── overview/project-snapshot.md      # Master state document (v1.4)
│   ├── architecture/architecture-v1.md   # C4 architecture diagrams
│   ├── data-model/                       # Data lake + ER diagrams
│   ├── deployment/local-docker.md        # Local deployment diagram
│   └── generate_pdf.py                   # Documentation PDF generator
└── diagrams/export/                      # PNG exports of all architecture diagrams
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Services | Python 3.11, FastAPI 0.115, Uvicorn |
| ML / AI | scikit-learn 1.5 (GradientBoostingRegressor, IsolationForest), NumPy 2.0, joblib |
| Data pipeline | boto3, psycopg2, NumPy |
| Storage | PostgreSQL 16, MinIO (S3-compatible) |
| Containerisation | Docker, Docker Compose |
| Cloud target | Huawei Cloud Stack (ECS, OBS, RDS, VPC) |

---

## License

[MIT](LICENSE) © 2026 Souhayl — Huawei Tunisia PFE Project
