a# CLAUDE.md — Telecom Cloud Intelligence Platform

> Last updated: 2026-04-06 | Phase 4 (auth + CI/CD) complete, on `dev` branch

---

## Project Identity

**Title:** Cloud-Native AI Operations Agent for CEM-CVM Intelligence (HCS-Ready)
**Owner:** Souhayl Guenichi — ESPRIT engineering student, 6-month internship at Huawei Tunisia (Cloud IT / Sales-Solution)
**Goal:** Graduate with excellence, deliver an industrial-grade AI Operations Agent trained on real Tunisie Telecom data, demonstrate Huawei Cloud Stack maturity within the ADN paradigm.

**What it does:** Bridges Huawei CEM (SmartCare) and CVM by ingesting OSS network KPIs + BSS subscriber/revenue data, running 3 ML models (SLA risk, OSS anomaly, BSS revenue anomaly), computing OSS-BSS correlations, and serving actionable intelligence via REST API + Next.js dashboard.

**Strategic position:** Intelligence layer in Huawei's ADN (Autonomous Driving Network) architecture for O+B (OSS+BSS) convergence.

---

## Quick Reference

| Service           | Port  | Tech                     |
|-------------------|-------|--------------------------|
| api-gateway       | 8000  | FastAPI 0.115, Python 3.11 |
| ai-service        | 8001  | FastAPI + scikit-learn 1.5 |
| auth-service      | 8002  | FastAPI + bcrypt + OAuth2  |
| pipeline-worker   | —     | Python daemon (2-min cycles) |
| dashboard         | 3001  | Next.js 14, React 18, TypeScript |
| postgres          | 5432  | PostgreSQL 16              |
| minio             | 9000  | S3-compatible object store |
| prometheus        | 9090  | Metrics scraper            |
| grafana           | 3000  | Observability dashboards   |

---

## How to Run

```bash
# Full stack
docker compose up --build -d

# Dashboard (separate)
cd dashboard && npm install && npm run dev

# Verify
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Default Credentials (dev only)

- **PostgreSQL:** telecom / telecom_pw / telecom_intel
- **MinIO:** minio / minio_pw
- **JWT Secret:** telecom-dev-secret-change-in-prod
- **Grafana:** admin / admin

---

## Architecture

```
[CEM / SmartCare] --> [AI Operations Agent] --> [CVM]
                            |
                   (this project - cloud native)
```

### Data Flow
1. **pipeline-worker** generates/ingests OSS+BSS data (200 records each per run)
2. Stores raw -> processed -> curated in **MinIO** (3-layer data lake)
3. Calls **ai-service** for ML inference (3 models)
4. Computes Pearson+Spearman correlations
5. Persists all results to **PostgreSQL** (7 tables)
6. **api-gateway** serves results via 7 REST endpoints (JWT-protected)
7. **dashboard** visualizes everything

### ML Models (v2.0)
| Model | Algorithm | Purpose |
|-------|-----------|---------|
| SLA Risk | GradientBoostingRegressor (200 est, depth=4) | Predict SLA breach probability (0-1) |
| OSS Anomaly | IsolationForest (150 est, contamination=0.05) | Detect network anomalies |
| BSS Revenue Anomaly | IsolationForest (150 est, contamination=0.05) | Detect revenue anomalies |

---

## Code Conventions

### Git Commits
```
type(scope): description

Types: feat, fix, chore, docs, phase#
Example: feat(phase-2): real ML inference - GradientBoosting + IsolationForest
```

### Style
- **Python:** Ruff linter + formatter (enforced in CI)
- **TypeScript:** Next.js default ESLint
- **Python naming:** snake_case for vars/functions, UPPER_SNAKE_CASE for constants
- **JS/TS naming:** camelCase for vars/functions

### File Organization
- Each service: `main.py`, `requirements.txt`, `Dockerfile`
- Base image: `python:3.11-slim` for all services
- API routes organized by domain
- DB schema: `docs/db/schema.sql`

---

## Database Schema (PostgreSQL)

7 tables: `users`, `pipeline_runs`, `dataset_registry`, `model_registry`, `sla_risk_scores`, `anomalies`, `revenue_anomalies`, `correlation_insights`

- `pipeline_runs` is the parent table (FK from 5 others via `run_id`)
- `users` table supports local + Google + GitHub OAuth
- JSONB used for ML explanation fields

Schema file: `docs/db/schema.sql`

---

## API Endpoints

### api-gateway (:8000) — all except /health require JWT Bearer token
| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | Liveness |
| GET | /sla-risk | Latest SLA risk score |
| GET | /sla-risk/history?limit=N | Historical SLA scores |
| GET | /anomalies?limit=N | OSS anomalies |
| GET | /revenue-anomalies?limit=N | BSS anomalies |
| GET | /correlation?limit=N | OSS-BSS correlations |
| GET | /pipeline-runs?limit=N | Pipeline execution history |

### auth-service (:8002)
| Method | Path | Purpose |
|--------|------|---------|
| POST | /auth/signup | Register (email/password) |
| POST | /auth/login | Login (returns JWT) |
| GET | /auth/me | Current user profile (JWT) |
| GET | /auth/google | Google OAuth redirect |
| GET | /auth/github | GitHub OAuth redirect |

### ai-service (:8001) — internal, called by pipeline-worker
| Method | Path | Purpose |
|--------|------|---------|
| POST | /infer/sla-risk | SLA risk prediction |
| POST | /infer/anomaly | OSS anomaly detection |
| POST | /infer/revenue-anomaly | BSS revenue anomaly detection |

---

## CI/CD Pipeline

**File:** `.github/workflows/ci-cd.yml`
**Triggers:** push to main/dev, PRs to main
**Registry:** ghcr.io/souhayl1g/telecom-cloud-intelligence/*

6 stages: lint (ruff) -> test (pytest) -> build (docker) -> integration -> security (pip-audit, safety) -> deploy (main only)

---

## Project Structure

```
services/
  api-gateway/          # REST API gateway
  ai-service/           # ML inference engine
  auth-service/         # Authentication (JWT + OAuth)
  pipeline-worker/      # ETL orchestrator (22 steps)
dashboard/              # Next.js frontend (15+ pages)
docs/                   # Architecture, data model, deployment guides
infra/monitoring/       # Prometheus + Grafana configs
diagrams/               # Architecture diagram exports
docker-compose.yml      # 7-service orchestration
.github/workflows/      # CI/CD pipeline
```

---

## Key Documentation

- `docs/overview/project-snapshot.md` — Master project state document
- `docs/architecture/architecture-v1.md` — C4 diagrams
- `docs/architecture/ml-models.md` — Full ML model specs (586 lines)
- `docs/data-model/postgres-schema.md` — ER diagram (Mermaid)
- `docs/data-model/data-lake.md` — 3-layer data lake architecture
- `docs/deployment/local-docker.md` — Local deployment guide
- `docs/data-request/data-requirements.md` — Expected TT data schema

---

## Current Status & Roadmap

### Completed Phases
- [x] **Phase 1:** Core infrastructure (PostgreSQL, MinIO, FastAPI services, Docker Compose)
- [x] **Phase 2:** Real ML models (GBR + IsolationForest), 22-step pipeline, 7 API endpoints
- [x] **Phase 3:** Full alignment with reference spec, professional docs, dashboard
- [x] **Phase 4:** Auth service (JWT + OAuth), dashboard auth integration, CI/CD pipeline

### Remaining Work
- [ ] **Phase 3.5:** Real Tunisie Telecom data ingestion (APPU/DOU schema, anonymization)
- [ ] **Phase 4.5:** Model v3.0 retraining on real data + evaluation metrics
- [ ] **Phase 5:** Dashboard enhancements (real-time updates, advanced visualizations)
- [ ] **Phase 6:** HCS deployment evidence (OBS/RDS/ECS mapping, screenshots)
- [ ] **Final:** Report writing, presentation preparation

### Cloud Portability (HCS Mapping)
| Local | Huawei Cloud Stack |
|-------|-------------------|
| MinIO | OBS (Object Storage) |
| PostgreSQL | RDS |
| Docker containers | ECS |

---

## Working With This Codebase

### Adding a new API endpoint
1. Add route in `services/api-gateway/main.py`
2. Add DB query if needed (raw psycopg2, no ORM)
3. Endpoint auto-instrumented by prometheus-fastapi-instrumentator

### Adding a new ML model
1. Train in `services/ai-service/train_models.py`
2. Add inference endpoint in `services/ai-service/main.py`
3. Add pipeline step in `services/pipeline-worker/main.py`
4. Register model in `model_registry` table

### Frontend development
1. Pages in `dashboard/app/` (Next.js App Router)
2. Components in `dashboard/components/`
3. API calls go through `dashboard/lib/` utilities
4. Auth middleware in `dashboard/middleware.ts`

---

## Important Notes

- Pipeline worker runs on 2-minute cycles in daemon mode
- All services use the same Docker network (internal bridge)
- OAuth credentials are optional (empty by default for local dev)
- Data is synthetic (demo mode) until real TT data is integrated
- Ruff must pass before commits (enforced in CI)
