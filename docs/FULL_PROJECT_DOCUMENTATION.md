# Telecom NeXoligence Platform — Full Technical Documentation

> **Version:** 2.0 | **Date:** 2026-04-15 | **Author:** Souhayl Guenichi (ESPRIT / Huawei Tunisia)
> **Branch:** `dev` | **Phase:** 5.5 complete

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Service Catalog](#3-service-catalog)
4. [Data Pipeline](#4-data-pipeline)
5. [Machine Learning Models](#5-machine-learning-models)
6. [Database Schema](#6-database-schema)
7. [API Reference](#7-api-reference)
8. [Dashboard (Frontend)](#8-dashboard-frontend)
9. [ADN L4 Autonomous Agent](#9-adn-l4-autonomous-agent)
10. [Authentication & Authorization](#10-authentication--authorization)
11. [Infrastructure & Deployment](#11-infrastructure--deployment)
12. [Observability](#12-observability)
13. [Development Guide](#13-development-guide)
14. [Known Constraints & Decisions](#14-known-constraints--decisions)

---

## 1. Executive Summary

### What This System Does

The **Telecom NeXoligence Platform** is a cloud-native AI Operations Agent designed for Huawei's CEM-CVM convergence strategy. It bridges **OSS** (Operations Support Systems) network KPIs and **BSS** (Business Support Systems) subscriber/revenue data through three ML models, statistical correlation analysis, and an ADN (Autonomous Driving Network) Level 4 agent that can autonomously execute remediation playbooks.

### Strategic Context

This project implements the intelligence layer in Huawei's ADN architecture for O+B (OSS+BSS) convergence. It is designed as a **Huawei Cloud Stack (HCS)-ready** solution, meaning every infrastructure component maps directly to an HCS service (MinIO -> OBS, PostgreSQL -> RDS, containers -> ECS).

### Core Capabilities

| Capability | Description |
|-----------|-------------|
| **SLA Risk Prediction** | GradientBoostingRegressor predicts SLA breach probability (0-1) from 9 aggregated KPI features |
| **OSS Anomaly Detection** | IsolationForest identifies anomalous network KPI records (throughput, latency, packet loss, users, signal) |
| **BSS Revenue Anomaly Detection** | IsolationForest detects anomalous subscriber revenue/usage patterns |
| **OSS-BSS Correlation** | Pearson + Spearman correlations between network degradation and revenue impact |
| **ADN L4 Operations** | Autonomous agent with 5 real playbooks: model retrain, anomaly triage, revenue protection, SLA breach analysis, capacity scaling |
| **Full Observability** | Prometheus metrics, Grafana dashboards, pipeline execution tracking |

---

## 2. System Architecture

### High-Level Architecture

```
[CEM / SmartCare OSS Data] ----+
                                |
                                v
                    +---[Pipeline Worker]---+
                    |   (22-step ETL/ML)    |
                    |                       |
                    v                       v
              [MinIO S3]            [AI Service]
              (3-layer              (3 ML models:
               data lake)            SLA, OSS, BSS)
                    |                       |
                    v                       v
               [PostgreSQL] <----- Results persisted
                    |
                    v
              [API Gateway]  <--- JWT-protected REST API
                    |
                    v
              [Next.js Dashboard]  <--- 15+ pages, SSR + CSR
                    |
                    v
              [ADN L4 Agent]  <--- Autonomous Ops (Qwen2.5:7b + playbooks)

[CVM / BSS Revenue Data] ------+
```

### Container Topology (10 services)

```
docker-compose.yml
 |
 +-- postgres:16          (data store, schema auto-init)
 +-- minio                (S3-compatible object store, 3 buckets)
 +-- auth-service         (JWT + Google/GitHub OAuth)
 +-- api-gateway          (REST API, 15+ endpoints)
 +-- ai-service           (ML inference, 3 models)
 +-- pipeline-worker      (22-step ETL daemon, 2-min cycles)
 +-- dashboard            (Next.js 14, standalone mode)
 +-- notebooks            (Jupyter, model training)
 +-- prometheus           (metrics scraping)
 +-- grafana              (observability dashboards)
```

### Network Architecture

All services communicate over Docker's internal bridge network. Key routing:

- **Dashboard SSR** -> `api-gateway:8000` (via `NEXT_PUBLIC_API_BASE_URL`)
- **Pipeline Worker** -> `ai-service:8001` (inference calls)
- **API Gateway** -> `ai-service:8001` (model reload for playbooks)
- **All Python services** -> `postgres:5432` (via `DATABASE_URL`)
- **Pipeline Worker** -> `minio:9000` (data lake uploads)

**Important:** `NEXT_PUBLIC_API_BASE_URL` is set at Docker build time as a build arg. Inside Docker, it resolves to `http://api-gateway:8000` (internal network). For local development, it defaults to `http://localhost:8000`.

---

## 3. Service Catalog

### API Gateway (`services/api-gateway/`)
- **Port:** 8000
- **Tech:** FastAPI 0.115, psycopg2, python-jose
- **Purpose:** Central REST API serving all dashboard data. JWT-protected. Direct SQL queries against PostgreSQL (no ORM). Implements 5 real playbook execution handlers for the L4 Agent.
- **Key file:** `main.py` (793 lines, single-module design)

### AI Service (`services/ai-service/`)
- **Port:** 8001
- **Tech:** FastAPI, scikit-learn 1.5, joblib, numpy
- **Purpose:** ML inference engine. Loads 3 pre-trained joblib models with hot-reload (30s TTL cache, mtime-based invalidation). Supports force-reload via `/models/reload` endpoint for the L4 Agent's model-retrain playbook.
- **Key files:** `main.py` (inference), `bootstrap_models.py` (default model generation if none exist)

### Auth Service (`services/auth-service/`)
- **Port:** 8002
- **Tech:** FastAPI, passlib/bcrypt, python-jose, httpx
- **Purpose:** User authentication. Supports local signup/login (email+password with bcrypt), Google OAuth2, and GitHub OAuth2. Issues JWT tokens (24h default expiry). Auto-creates `users` table on startup.
- **Key file:** `main.py` (497 lines)

### Pipeline Worker (`services/pipeline-worker/`)
- **Port:** None (background daemon)
- **Tech:** Python, boto3, numpy, scipy, requests, tenacity
- **Purpose:** 22-step ETL/ML pipeline running on 2-minute cycles. Generates synthetic OSS/BSS data with fault injection, uploads to MinIO (3-layer data lake), calls AI service for inference, computes correlations, persists all results to PostgreSQL.
- **Key file:** `worker/__main__.py` (857 lines)

### Dashboard (`dashboard/`)
- **Port:** 3001
- **Tech:** Next.js 14.2.5, React 18.3.1, TypeScript 5.4, Recharts 2.15.3
- **Purpose:** 15+ page interactive dashboard with SSR data fetching, JWT auth via httpOnly cookies, theme toggle, command palette, and real-time data refresh.
- **Output mode:** Standalone (for Docker deployment)

---

## 4. Data Pipeline

### 22-Step Execution Flow

The pipeline worker executes this sequence every 2 minutes in daemon mode:

| Step | Description | Output |
|------|-------------|--------|
| 1 | Insert `pipeline_runs` record (status='started') | DB row |
| 2 | Ensure MinIO buckets exist (raw, processed, curated) | S3 buckets |
| 3 | Generate 200 synthetic OSS records with fault injection | In-memory |
| 4 | Generate 200 synthetic BSS records with correlated dips | In-memory |
| 5 | Upload OSS raw data to MinIO | `s3://raw/oss/{date}/{run_id}.json` |
| 6 | Upload BSS raw data to MinIO | `s3://raw/bss/{date}/{run_id}.json` |
| 7 | Register raw datasets in `dataset_registry` | DB rows |
| 8 | Process OSS data (add severity, QoS score, load factor) | In-memory |
| 9 | Process BSS data (add ARPU category, data intensity, churn bucket) | In-memory |
| 10 | Register processed datasets | DB rows |
| 11 | Compute 9 aggregate KPI features from OSS records | Feature dict |
| 12 | Call AI service `/infer/sla-risk` with features | SLA score |
| 13 | Call AI service `/infer/anomaly` with OSS records | Anomaly labels |
| 14 | Call AI service `/infer/revenue-anomaly` with BSS records | Anomaly labels |
| 15 | Compute Pearson + Spearman correlations (5 pairs x 2 methods) | 10 correlation values |
| 16 | Build curated dataset (joined OSS+BSS+AI) | `s3://curated/joined/{date}/{run_id}_curated.json` |
| 17 | Register curated dataset | DB row |
| 18 | Persist SLA risk score | `sla_risk_scores` row |
| 19 | Persist OSS anomalies (only flagged records) | `anomalies` rows |
| 20 | Persist BSS revenue anomalies (only flagged records) | `revenue_anomalies` rows |
| 21 | Register models in `model_registry` | DB rows |
| 22 | Persist correlation insights + mark pipeline succeeded | `correlation_insights` rows |

### Fault Injection

The synthetic data generator injects realistic network faults:
- 2-3 randomly selected cells experience degradation for ~15-25% of the time window
- **OSS degradation:** throughput collapses (10-35% of normal), latency spikes (2.5-5x), packet loss surges (+3-8%), signal drops (-15-30 dBm)
- **BSS correlation:** subscribers on faulted cells see reduced data usage (30-60%), fewer voice minutes (40-70%), and increased churn risk (+30-55%)

This creates measurable OSS-BSS correlations that the correlation analysis (step 15) detects.

### Error Handling

If any step fails, the pipeline run is marked with `status='failed'` and the error message is stored in `error_message` (truncated to 500 chars). The daemon continues running and retries on the next cycle.

### Data Lake (MinIO)

Three buckets implementing a standard lakehouse pattern:

| Layer | Bucket | Content |
|-------|--------|---------|
| Raw | `raw` | Unprocessed OSS/BSS JSON records |
| Processed | `processed` | Enriched records (severity labels, QoS scores, ARPU categories) |
| Curated | `curated` | Joined OSS+BSS+AI output per run |

---

## 5. Machine Learning Models

### Model v2.0 — Pre-trained via Jupyter Notebooks

Models are trained in `notebooks/` and saved as `.joblib` files. The AI service loads them dynamically with hot-reload support.

#### SLA Risk Model (GradientBoostingRegressor)

- **Algorithm:** sklearn Pipeline(StandardScaler -> GradientBoostingRegressor(n_estimators=200, max_depth=4))
- **Input:** 9 aggregated KPI features computed from 200 OSS records per run
- **Output:** Risk score 0.0 (safe) to 1.0 (critical)
- **Test R2:** 0.979108
- **Test MAE:** 0.018495
- **Test RMSE:** 0.027222
- **CV R2:** 0.977127 +/- 0.002773
- **Top features:** mean_latency_ms (0.6779), max_latency_ms (0.1497), packet_loss_rate (0.0785)

Input features:
```
mean_throughput_mbps, std_throughput_mbps, mean_latency_ms, std_latency_ms,
max_latency_ms, mean_packet_loss_pct, max_packet_loss_pct, mean_active_users,
mean_signal_rsrp_dbm
```

#### OSS Anomaly Model (IsolationForest)

- **Algorithm:** sklearn Pipeline(StandardScaler -> IsolationForest(n_estimators=150, contamination=0.05))
- **Input:** 5 per-record KPI features
- **Output:** Binary anomaly label + normalized anomaly score (0-1)
- **Precision:** 0.7813 | **Recall:** 1.0 | **F1:** 0.8772 | **ROC-AUC:** 1.0
- **Confusion Matrix:** TN=2808, FP=42, FN=0, TP=150

Input features:
```
throughput_mbps, latency_ms, packet_loss_pct, active_users, signal_rsrp_dbm
```

#### BSS Revenue Anomaly Model (IsolationForest)

- **Algorithm:** sklearn Pipeline(StandardScaler -> IsolationForest(n_estimators=150, contamination=0.05))
- **Input:** 5 per-record BSS features
- **Output:** Binary anomaly label + normalized anomaly score (0-1)
- **Precision:** 1.0 | **Recall:** 1.0 | **F1:** 1.0 | **ROC-AUC:** 1.0
- **Confusion Matrix:** TN=2850, FP=0, FN=0, TP=150

Input features:
```
revenue_tnd, data_used_gb, voice_min, sms_count, churn_risk
```

### Model Hot-Reload

The AI service implements a cache with 30-second TTL and mtime-based invalidation:
1. On each inference request, check if models need reloading
2. If 30+ seconds since last check, compare file mtimes to last load time
3. If any model file is newer, reload all models
4. Force-reload available via `POST /models/reload` (used by L4 Agent playbook)

This allows notebooks to retrain models while the AI service is running.

### Bootstrap Models

If no pre-trained models exist at startup (e.g., fresh deployment), `bootstrap_models.py` generates default models from synthetic data. These are replaced once notebooks produce real trained models.

---

## 6. Database Schema

PostgreSQL 16 with 9 tables. Schema auto-applied via `docker-entrypoint-initdb.d/schema.sql`.

### Entity Relationship

```
users (standalone)

pipeline_runs (parent)
  |-- dataset_registry    (FK: run_id)
  |-- anomalies           (FK: run_id)
  |-- revenue_anomalies   (FK: run_id)
  |-- sla_risk_scores     (FK: run_id)
  |-- correlation_insights (FK: run_id)

model_registry (standalone, unique on model_name+version)
agent_actions (standalone, unique on action_id)
```

### Table Details

| Table | Rows/Run | Purpose |
|-------|----------|---------|
| `users` | N/A | Auth: email, password_hash, provider, role |
| `pipeline_runs` | 1 | Run metadata: status, timing, error_message |
| `dataset_registry` | 5 | Tracks all data lake objects (raw/processed/curated) |
| `model_registry` | 3 | Model version tracking (idempotent upsert) |
| `anomalies` | ~10 | Flagged OSS anomalies with severity, value, baseline |
| `revenue_anomalies` | ~10 | Flagged BSS anomalies with operator, plan, subscriber |
| `sla_risk_scores` | 1 | Risk score + JSONB explanation (feature importances) |
| `correlation_insights` | 10 | 5 metric pairs x 2 methods (Pearson + Spearman) |
| `agent_actions` | varies | L4 Agent action audit trail with execution_log JSONB |

### Key Design Decisions

- **No ORM:** Raw psycopg2 with parameterized queries throughout. Chosen for simplicity and direct control over SQL.
- **JSONB for ML explanations:** `sla_risk_scores.explanation` stores feature importances, top drivers, and input features as JSONB. Queried with JSON path operators (`explanation->'input_features'->>'mean_latency_ms'`) for the capacity planning page.
- **`pipeline_runs` as FK parent:** All analytics tables reference `run_id` with `ON DELETE SET NULL`, allowing pipeline history cleanup without losing anomaly data.

---

## 7. API Reference

### API Gateway (:8000)

All endpoints except `/health` require `Authorization: Bearer <JWT>` header.

| Method | Path | Query Params | Description |
|--------|------|-------------|-------------|
| GET | `/health` | — | Liveness check |
| GET | `/sla-risk` | — | Latest SLA risk score with explanation JSONB |
| GET | `/sla-risk/history` | `limit` (1-200, default 20) | Historical SLA risk scores |
| GET | `/anomalies` | `limit` (1-500, default 50) | OSS anomalies (newest first) |
| GET | `/revenue-anomalies` | `limit` (1-500, default 50) | BSS revenue anomalies |
| GET | `/correlation` | `limit` (1-200, default 50) | OSS-BSS correlation insights |
| GET | `/pipeline-runs` | `limit` (1-100, default 10) | Pipeline execution history |
| GET | `/anomaly-stats` | `limit` (1-200, default 20) | Per-run anomaly counts (joins 3 tables) |
| GET | `/kpi-summary` | `limit` (1-200, default 20) | KPI aggregates from SLA explanation JSONB |
| GET | `/infra-stats` | — | DB size, row counts, table sizes, pipeline timing |
| GET | `/platform-stats` | — | Aggregated stats for capacity/topology pages |
| GET | `/actions` | `limit`, `status` | List L4 Agent actions (filterable) |
| POST | `/actions` | — | Create action (idempotent via ON CONFLICT) |
| PATCH | `/actions/{action_id}` | — | Update action status (approve/reject) |
| POST | `/actions/{action_id}/execute` | — | Execute playbook, store execution_log |

### Auth Service (:8002)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/signup` | Register with email/password (returns JWT) |
| POST | `/auth/login` | Login with email/password (returns JWT) |
| GET | `/auth/me` | Get current user profile (requires Bearer token) |
| GET | `/auth/google` | Redirect to Google OAuth |
| GET | `/auth/google/callback` | Google OAuth callback (redirects to frontend with token) |
| GET | `/auth/github` | Redirect to GitHub OAuth |
| GET | `/auth/github/callback` | GitHub OAuth callback |

### AI Service (:8001) — Internal

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health + model version |
| POST | `/infer/sla-risk` | SLA risk prediction from aggregated features |
| POST | `/infer/anomaly` | OSS anomaly detection (batch of records) |
| POST | `/infer/revenue-anomaly` | BSS revenue anomaly detection (batch) |
| POST | `/models/reload` | Force-reload all models from disk |

---

## 8. Dashboard (Frontend)

### Technology Stack

- **Framework:** Next.js 14.2.5 (App Router, React Server Components)
- **React:** 18.3.1
- **Charts:** Recharts 2.15.3 (pinned — v3.x causes React error #310)
- **Language:** TypeScript 5.4.5
- **Build output:** Standalone (for Docker `node server.js`)

### Page Inventory (15+ pages)

| Route | Type | Description |
|-------|------|-------------|
| `/overview` | SSR | Platform overview: SLA gauge, anomaly timeline, bar chart, SLA trend |
| `/anomalies` | SSR | OSS/BSS anomaly browser with timeline and heatmap |
| `/sla-risk` | SSR | SLA risk score, history chart, explanation details |
| `/correlations` | SSR | OSS-BSS correlation heatmap explorer |
| `/intelligence` | SSR | AI intelligence hub with root cause analysis |
| `/predictive` | SSR | Forecast analytics from anomaly-stats data |
| `/capacity` | SSR | Capacity planning from real KPI features (JSONB queries) |
| `/topology` | Static | Network topology (demo structure with real severity overlay) |
| `/data-warehouse` | SSR | Data lake explorer (dataset_registry) |
| `/pipeline-runs` | SSR | Pipeline execution history and status |
| `/ops-metrics` | SSR | Platform health: infra stats, DB size, table sizes |
| `/model-evaluation` | Static | Real ML model metrics + charts (from notebooks) |
| `/l4-agent` | CSR | ADN L4 Agent: chat, actions, live monitor (3 tabs) |
| `/login` | Static | Authentication page (login/signup forms) |
| `/signup` | Static | Registration page |
| `/auth/callback` | Static | OAuth callback handler (stores token in cookie) |

### Key Components

| Component | Purpose |
|-----------|---------|
| `TopNav.tsx` | Top navigation bar with all page links |
| `ThemeProvider.tsx` | Dark/light theme context with localStorage persistence |
| `ThemeToggle.tsx` | Theme switch button (sun/moon icons) |
| `CommandPalette.tsx` | Cmd+K command palette with fuzzy search |
| `AICopilotIcon.tsx` | Floating AI agent launcher (bottom-right FAB) |
| `LiveIndicator.tsx` | "LIVE" badge with pulse dot and seconds counter |
| `RiskGauge.tsx` | SLA risk gauge with gradient bar and severity label |
| `ScoreBar.tsx` | Horizontal bar with value display |
| `AnomalyTimeline.tsx` | Chronological event stream (OSS+BSS merged, filterable) |
| `AnomaliesBarChart.tsx` | Bar chart showing anomaly distribution |
| `SlaChart.tsx` | Area chart for SLA risk history |
| `AnomalyHeatmap.tsx` | Cell-based severity heatmap |
| `CorrelationHeatmap.tsx` | Correlation coefficient heatmap |
| `RootCauseAnalysis.tsx` | AI-driven root cause analysis display |

### Data Fetching Pattern

Two patterns are used depending on the page type:

**1. Server-side pages (SSR):** Use `dashboard/lib/api.ts` which calls `cookies()` from `next/headers` to read the `auth_token` httpOnly cookie, then fetches from the API gateway with `Authorization: Bearer` header.

**2. Client-side pages (L4 Agent):** Use `/api/platform-data` SSR proxy route. The client component calls this Next.js API route, which reads the cookie server-side and proxies to the API gateway.

### Auth Flow

1. User submits login form -> `/api/login` route proxies to auth-service
2. Auth-service returns JWT -> API route sets `auth_token` httpOnly cookie
3. `middleware.ts` checks for cookie on every request, redirects to `/login` if missing
4. SSR pages read cookie via `cookies()` and pass Bearer token to API gateway
5. Client pages use `/api/platform-data` proxy to avoid exposing the token

---

## 9. ADN L4 Autonomous Agent

### Design Philosophy

The L4 Agent implements Huawei's ADN Level 4 concept: **conditional automation** where safe actions are auto-approved and risky actions require human approval.

### Auto-Approve Logic

```
if type == 'remediation' AND (severity == 'critical' OR severity == 'warning'):
    -> REQUIRES HUMAN APPROVAL
else:
    -> AUTO-APPROVED (info actions, predictions)
```

### Playbooks (Real Backend Operations)

| Playbook ID | What It Does |
|-------------|-------------|
| `pb-model-retrain` | POSTs to `ai-service:8001/models/reload` to force-reload all 3 ML models from disk |
| `pb-anomaly-triage` | Queries last 30 min of anomalies, classifies by severity, identifies affected cells, cross-references correlations for root cause |
| `pb-revenue-protect` | Queries high-severity revenue anomalies, flags suspicious subscribers, computes total revenue at risk |
| `pb-sla-breach` | Reads current SLA score + explanation, identifies KPIs exceeding thresholds, recommends remediation focus |
| `pb-capacity-scale` | Computes capacity metrics from recent KPI history, calculates throughput and user headroom percentages |

### Action Lifecycle

1. `generateActions()` creates actions from live platform data
2. `POST /actions` persists each action (idempotent via `ON CONFLICT`)
3. On page load: `GET /actions` restores persisted actions
4. Approve: `PATCH /actions/{id}` (status='approved') -> `POST /actions/{id}/execute` (runs playbook)
5. Reject: `PATCH /actions/{id}` (status='rejected')
6. All execution results stored in `execution_log` JSONB column

### Three Tabs

1. **Agent Chat** — Conversation with Qwen2.5:7b via Ollama (local LLM)
2. **Actions** — Pending actions (approval buttons) + auto-approved list
3. **Live Monitor** — Real-time metrics: sparkline charts, donut chart, system stats

---

## 10. Authentication & Authorization

### Supported Methods

| Method | Flow |
|--------|------|
| **Local** | Email + password (bcrypt hashed, min 8 chars) -> JWT |
| **Google OAuth** | Redirect -> Google consent -> callback -> JWT |
| **GitHub OAuth** | Redirect -> GitHub authorize -> callback -> JWT |

### JWT Structure

```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "viewer",
  "exp": "...",
  "iat": "..."
}
```

- **Algorithm:** HS256
- **Default expiry:** 24 hours (configurable via `JWT_EXPIRE_MINUTES`)
- **Secret:** Shared between auth-service and api-gateway via `JWT_SECRET` env var

### OAuth Account Linking

When a user logs in via OAuth with an email that already exists (different provider), the system links the OAuth identity to the existing account by updating the `provider` and `provider_id` fields.

---

## 11. Infrastructure & Deployment

### Local Development

```bash
# Start all services
docker compose up --build -d

# Dashboard standalone development
cd dashboard && npm install && npm run dev

# Verify services
curl http://localhost:8000/health   # API Gateway
curl http://localhost:8001/health   # AI Service
curl http://localhost:8002/health   # Auth Service
```

### Docker Compose Services

| Service | Image/Build | Ports | Health Check |
|---------|-------------|-------|-------------|
| postgres | `postgres:16` | 5432 | `pg_isready` |
| minio | `minio/minio:latest` | 9000, 9001 | HTTP /minio/health/live |
| auth-service | `./services/auth-service` | 8002 | — |
| api-gateway | `./services/api-gateway` | 8000 | — |
| ai-service | `./services/ai-service` | 8001 | — |
| pipeline-worker | `./services/pipeline-worker` | — | — |
| dashboard | `./dashboard` | 3001 | — |
| notebooks | `Dockerfile.notebooks` | 8888 | — |
| prometheus | `prom/prometheus:v2.54.0` | 9090 | — |
| grafana | `grafana/grafana:11.2.0` | 3000 | — |

### HCS (Huawei Cloud Stack) Mapping

| Local Component | HCS Service |
|----------------|-------------|
| MinIO | OBS (Object Storage Service) |
| PostgreSQL | RDS (Relational Database Service) |
| Docker containers | ECS (Elastic Cloud Server) |
| Ollama | ModelArts / EI (Enterprise Intelligence) |
| Prometheus+Grafana | AOM (Application Operations Management) |

### Default Credentials (Development Only)

| Service | Credentials |
|---------|------------|
| PostgreSQL | `telecom` / `telecom_pw` / `telecom_intel` |
| MinIO | `minio` / `minio_pw` |
| JWT Secret | `telecom-dev-secret-change-in-prod` |
| Grafana | `admin` / `admin` |

---

## 12. Observability

### Prometheus Metrics

All FastAPI services are auto-instrumented via `prometheus-fastapi-instrumentator`:
- `http_requests_total` — request count by method, path, status
- `http_request_duration_seconds` — request latency histogram
- `http_request_size_bytes` — request body size
- `http_response_size_bytes` — response body size

Metrics endpoints: `GET /metrics` on each service.

### Grafana Dashboards

Pre-configured dashboard: `infra/monitoring/grafana/provisioning/dashboards/json/ai-ops-overview.json`

Datasource: Prometheus at `http://prometheus:9090`

### Pipeline Observability

- Each pipeline run recorded in `pipeline_runs` table with status, timing, and error messages
- Pipeline logs printed to stdout (captured by Docker)
- Per-run anomaly counts visible via `/anomaly-stats` endpoint

---

## 13. Development Guide

### Adding a New API Endpoint

1. Add route function in `services/api-gateway/main.py`
2. Decorate with `@app.get("/path")` or `@app.post("/path")`
3. Add `user=Depends(require_auth)` for protected endpoints
4. Use `with _db() as conn:` for database access
5. Endpoint automatically instrumented by Prometheus

### Adding a New Dashboard Page

1. Create `dashboard/app/{page-name}/page.tsx`
2. Import `api` from `../../lib/api` for SSR data fetching
3. Add `export const dynamic = "force-dynamic"` for real-time data
4. Add nav item to `dashboard/components/TopNav.tsx`
5. Run `npx next build` to verify

### Adding a New ML Model

1. Train in a Jupyter notebook under `notebooks/`
2. Save as `.joblib` to `notebooks/models/`
3. Add inference endpoint in `services/ai-service/main.py`
4. Add feature list constant and request/response schemas
5. Add pipeline step in `services/pipeline-worker/worker/__main__.py`
6. Register model in `model_registry` table

### Code Style

- **Python:** Ruff linter + formatter (enforced in CI)
- **TypeScript:** Next.js default ESLint
- **Python naming:** `snake_case` for vars/functions, `UPPER_SNAKE_CASE` for constants
- **JS/TS naming:** `camelCase` for vars/functions
- **Git commits:** `type(scope): description` (feat, fix, chore, docs, phase#)

### CI/CD Pipeline

File: `.github/workflows/ci-cd.yml`

6 stages:
1. **Lint** — Ruff check on Python code
2. **Test** — pytest (if tests exist)
3. **Build** — Docker image build for all services
4. **Integration** — docker compose up + health checks
5. **Security** — pip-audit + safety scan
6. **Deploy** — Push to GHCR (main branch only)

Registry: `ghcr.io/souhayl1g/telecom-cloud-intelligence/*`

---

## 14. Known Constraints & Decisions

### Recharts v2 Pinning

Recharts is pinned to `2.15.3`. Version 3.x is a complete TypeScript rewrite that causes React error #310 ("Objects are not valid as React child") due to internal `useMemo` usage in Tooltip/Cell/Legend components. Do not upgrade.

### No ORM

All database access uses raw psycopg2 with parameterized queries. This was a deliberate choice for:
- Direct SQL control (JSONB path queries, window functions, FILTER clauses)
- Minimal dependencies
- Transparency (every query is visible in the code)

### Synthetic Data

Data is currently synthetic (demo mode). The pipeline worker generates realistic Tunisian telecom data with:
- 3 operators (Ooredoo, Tunisie Telecom, Orange)
- 80/20 prepaid/postpaid split (matching INTT 2023 market stats)
- Verified 2025 forfait pricing tiers
- Fault injection for anomaly detection validation

Real Tunisie Telecom data integration is a planned future phase.

### Topology Page

The topology page uses demo network structure with real severity overlay from anomaly data. A real network topology will be integrated when available.

### Pipeline Runner Duplication

`pipeline_runner.py` at the repo root is a simplified alternative pipeline runner (3 steps vs. 22) used by `Dockerfile.notebooks` for the Jupyter container. The authoritative pipeline is `services/pipeline-worker/worker/__main__.py`.

### OAuth State Verification

The OAuth2 `state` parameter is generated for CSRF protection but not verified in callbacks. This is acceptable for a controlled-deployment platform but should be addressed for public-facing deployments.

### Single-Provider OAuth Linking

When a user logs in via OAuth with an email matching an existing account on a different provider, the system overwrites the previous provider. A proper multi-provider identity table (`user_identities`) would be needed for production use with multiple OAuth providers per account.

---

*Generated 2026-04-15 as part of full codebase audit. Covers all services, all pages, all models, and all infrastructure.*
