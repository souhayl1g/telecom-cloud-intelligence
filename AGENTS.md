# AGENTS.md — Telecom NeXoligence Platform

> AI agent context for the **Telecom NeXoligence** project.  
> Last updated: 2026-04-28

---

## 1. Project Overview

**Telecom NeXoligence** is a cloud-native AI operations platform that bridges OSS (network KPIs) and BSS (subscriber experience data) for telecom operators. It is designed for deployment on **Huawei Cloud Stack (HCS)** and aligns with Huawei's **ADN (Autonomous Driving Network)** architecture.

**What it does:**
- Ingests real + simulated OSS network data (18.8M real cell KPIs + 200K simulated) and BSS subscriber data (968K real + 1.5M simulated) across 5-6 months.
- Injects realistic faults via bootstrap simulation with temporal drift and Gaussian noise.
- Stores data in a 3-layer MinIO data lake (`raw` → `processed` → `curated`).
- Runs 6 ML models: v2.0 legacy (SLA GBR, OSS IF, BSS IF) + v3.0 real-data (CEM LightGBM/DART, VAE PyTorch, RAT XGBoost GPU).
- Computes OSS–BSS correlations (Pearson + Spearman on 5 metric pairs).
- Persists all results to PostgreSQL (9 tables).
- Serves insights through a FastAPI REST gateway and a Next.js dashboard with an ADN L4 autonomous operations agent.

**Owner:** Souhayl Guenichi — ESPRIT engineering student, internship at Huawei Tunisia.  
**Language:** All code, comments, and documentation are in **English**.

---

## 2. Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Services | Python | 3.11 |
| API Framework | FastAPI | 0.115 |
| ML / AI | scikit-learn | 1.5 |
| Deep Learning (planned) | PyTorch | 2.x |
| Statistics | SciPy | 1.14 |
| Frontend | Next.js | 14.2.5 |
| Frontend | React | 18.3.1 |
| Frontend | TypeScript | 5.4.5 |
| Charts | Recharts | 2.15.3 (pinned) |
| Storage | PostgreSQL | 16 |
| Object Store | MinIO | latest (S3-compatible) |
| Observability | SigNoz + OpenTelemetry | 0.55.0 |
| LLM (local) | Ollama | Qwen2.5:7b |
| Containerization | Docker + Docker Compose | — |
| CI/CD | GitHub Actions | — |
| Linting | Ruff | — |

**Base Docker image:** `python:3.11-slim` for all Python services.

---

## 3. Architecture & Services

The platform is orchestrated via `docker-compose.yml` with 15+ containers.

### Core Services

| Service | Port | Role | Key Files |
|---|---|---|---|
| `postgres` | 5432 | Serving store + metadata | `docs/db/schema.sql` |
| `minio` | 9000 / 9001 | S3-compatible data lake | — |
| `api-gateway` | 8000 | Public REST API (FastAPI, JWT-protected) | `services/api-gateway/` |
| `ai-service` | 8001 | ML inference engine (6 models: 3 v2 + 3 v3) | `services/ai-service/` |
| `auth-service` | 8002 | Authentication (JWT + OAuth2) | `services/auth-service/` |
| `pipeline-worker` | — | 22-step ETL orchestrator (daemon, 2-min cycles) | `services/pipeline-worker/` |
| `agent-service` | 8003 | LLM-powered multi-agent orchestrator | `services/agent-service/` |
| `dashboard` | 3001 | Next.js frontend (15+ pages) | `dashboard/` |
| `notebooks` | 8888 | Jupyter for model training + evaluation | `notebooks/` |

### Observability Stack (SigNoz)

| Service | Port | Role |
|---|---|---|
| `signoz-frontend` | 3301 | Observability UI (traces, metrics, logs) |
| `otel-collector` | 4317/4318 | OpenTelemetry OTLP receiver (gRPC/HTTP) |
| `clickhouse` | — | SigNoz metrics/traces storage (internal) |
| `zookeeper-1` | — | ClickHouse coordination |
| `signoz-alertmanager` | — | Alerting |
| `signoz-query-service` | — | Query API |

### Data Flow

```
pipeline-worker (manual mode, 22 steps, controlled cycles)
  ├── Load real OSS (18.8M) + BSS (968K) + simulated OSS (200K) + BSS (1.5M)
  ├── generate 200 OSS records + 200 BSS records (from bootstrap reservoirs)
  ├── upload raw JSON → minio  s3://raw/oss/...  s3://raw/bss/...
  ├── process + enrich → minio  s3://processed/oss/...  s3://processed/bss/...
  ├── POST /infer/sla-risk → ai-service (GBR v2.0, 9 features)
  ├── POST /infer/anomaly → ai-service (IsolationForest v2.0, OSS)
  ├── POST /infer/revenue-anomaly → ai-service (IsolationForest v2.0, BSS)
  ├── POST /infer/cem → ai-service (LightGBM v3.0, 13 features)
  ├── POST /infer/vae-anomaly → ai-service (PyTorch VAE v3.0, 9 features)
  ├── POST /infer/rat-underservice → ai-service (XGBoost v3.0, 10 features)
  ├── compute Pearson + Spearman correlations (5 pairs × 2 methods)
  ├── build curated dataset → minio s3://curated/...
  └── INSERT → postgres (9 tables)

api-gateway (:8000)
  └── SELECT → postgres (serves to clients via REST)

dashboard (:3001)
  └── Consumes api-gateway via SSR proxy + direct internal calls
```

### HCS Deployment Mapping

| Local | Huawei Cloud Stack |
|---|---|
| Docker containers | ECS / CCE |
| MinIO volumes | OBS (Object Storage Service) |
| PostgreSQL container | RDS for PostgreSQL |
| Docker network | VPC |
| Env-var secrets | IAM / KMS |
| Ollama | ModelArts / EI |

---

## 4. Directory Structure

```
telecom-cloud-intelligence/
├── docker-compose.yml              # 15+ service orchestration
├── Makefile                        # Dev commands (start, stop, logs, health, db-*)
├── Dockerfile.notebooks            # Jupyter container build
├── entrypoint.sh                   # Notebook container entrypoint
├── .github/workflows/ci-cd.yml     # CI/CD pipeline
├── .env.pipeline.example           # Example env for notebooks
│
├── services/
│   ├── api-gateway/                # FastAPI REST gateway
│   │   ├── main.py                 # App factory + middleware
│   │   ├── auth.py                 # JWT validation dependency
│   │   ├── config.py               # Environment config
│   │   ├── db.py                   # PostgreSQL connection helper
│   │   ├── routers/                # Domain routers (9 files)
│   │   │   ├── health.py
│   │   │   ├── sla.py
│   │   │   ├── anomalies.py
│   │   │   ├── correlations.py
│   │   │   ├── pipelines.py
│   │   │   ├── stats.py
│   │   │   ├── actions.py          # L4 agent actions
│   │   │   ├── agents.py
│   │   │   └── subscribers.py
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── ai-service/                 # ML inference engine
│   │   ├── main.py                 # App factory (mounts v2 + v3 routers)
│   │   ├── config.py               # Model paths + env (v2 + v3)
│   │   ├── model_cache.py          # Lazy model loader (6 models)
│   │   ├── vae_arch.py             # PyTorch VAE architectures (Legacy + v3)
│   │   ├── bootstrap_models.py     # Initial training script
│   │   ├── routers/
│   │   │   ├── health.py
│   │   │   ├── v2/
│   │   │   │   ├── sla_risk.py
│   │   │   │   ├── anomaly.py
│   │   │   │   └── revenue.py
│   │   │   └── v3/
│   │   │       ├── cem.py
│   │   │       ├── rat.py
│   │   │       └── vae_anomaly.py
│   │   ├── models/                 # .joblib + .pt model files
│   │   ├── tests/
│   │   ├── requirements.txt        # includes torch, lightgbm, xgboost
│   │   └── Dockerfile
│   ├── auth-service/               # Authentication (JWT + OAuth)
│   │   ├── main.py                 # Single-file service
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── agent-service/              # LLM-powered multi-agent system
│   │   ├── main.py
│   │   ├── orchestrator.py         # Agent dispatch logic
│   │   ├── agents/                 # CEMAgent, NetworkAgent, ActionAgent
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── pipeline-worker/            # 22-step ETL daemon
│   │   ├── worker/
│   │   │   ├── __main__.py         # Entrypoint
│   │   │   ├── pipeline.py         # Orchestrator
│   │   │   ├── config.py           # Env + S3 config
│   │   │   ├── db.py               # DB helper
│   │   │   ├── storage.py          # MinIO S3 helper
│   │   │   ├── generators/         # OSS + BSS synthetic data
│   │   │   ├── processors/         # Enrichment logic
│   │   │   ├── inference/          # ai-service HTTP client
│   │   │   └── analytics/          # Correlations + features
│   │   ├── tests/                  # 5 test files
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── data-ingest/                # Real TT data loaders + BSS/OSS simulators
│       ├── ingest_bss.py           # Load real BSS CSVs into PostgreSQL
│       ├── ingest_oss_real.py      # Load real OSS KPI CSVs (2G/3G/4G) via chunked COPY
│       ├── simulate_oss_bootstrap.py  # Bootstrap-simulate OSS from real reservoir
│       ├── simulate_oss.py         # Generate synthetic OSS cell KPIs (legacy)
│       ├── compute_features.py     # Build subscriber_features + area_network_health
│       └── generate_bss_months.py  # Bootstrap-simulate BSS months from real data
│
### BSS Simulation Method
Simulated months (`smartcare_cem_jan.csv`, `smartcare_cem_avr.csv`, `smartcare_cem_mai.csv`) are generated by:
1. **Stratified bootstrap**: Sample 500K rows with replacement from 968K real rows (Feb+Mar). Preserves all categorical joint distributions and correlations.
2. **Log-normal perturbation**: Numerical columns multiplied by `exp(N(0, 0.06))` to prevent exact duplicates.
3. **Month drift**: DOU, traffic, highest_RAT (4G↔5G), and usertype shift per month (Jan lower DOU/5G, Apr/May higher with churn emergence).
4. **Identity replacement**: New IMSI (`60502`+10 digits) and TAC (15 digits) per record.
5. **DOU guard**: Traffic sum capped at 1.5× DOU.

Script: `services/data-ingest/generate_bss_months.py`

```

---

```
├── dashboard/                      # Next.js 14 frontend
│   ├── app/                        # App Router pages (15+ routes)
│   ├── components/                 # React components
│   ├── lib/                        # Utilities
│   ├── middleware.ts               # Auth middleware
│   ├── next.config.js
│   ├── package.json
│   └── Dockerfile
│
├── notebooks/                      # Jupyter + model training
│   ├── 01_data_preparation_eda.ipynb
│   ├── 02_sla_risk_model.ipynb
│   ├── 03_anomaly_detection_models.ipynb
│   ├── 04_phase2_data_foundation.ipynb
│   ├── 05_real_data_etl_engineering.ipynb  # ETL + feature engineering for real data
│   ├── 06_cem_v3_training.ipynb            # CEM LightGBM v3.0
│   ├── 07_oss_vae_anomaly.ipynb            # PyTorch VAE anomaly v3.0
│   ├── 08_rat_underservice.ipynb           # XGBoost RAT v3.0
│   ├── 09_master_v3_training.py            # Master combined training (1.5M+ data)
│   ├── models/                     # Trained .joblib + .pt files
│   └── data/                       # Training NPZ + evaluation PNGs
│
├── docs/
│   ├── db/schema.sql               # PostgreSQL schema (9 tables)
│   ├── architecture/               # C4 diagrams, ML model docs
│   ├── data-model/                 # ER diagrams, data lake docs
│   ├── deployment/                 # Local + HCS deployment guides
│   └── overview/                   # Project snapshot
│
├── TT_data/                        # CONFIDENTIAL — real + simulated Tunisie Telecom data
│   └── BSS/                        # 968K real + 1.5M simulated subscriber CEM profiles
│
├── infra/monitoring/               # SigNoz + OTel configs
├── diagrams/                       # Architecture PNG exports
├── memory/                         # Agent memory files
└── graphify-out/                   # Knowledge graph output
```

---

## 5. Build & Run Commands

### Prerequisites
- Docker + Docker Compose
- (Optional) Ollama for local LLM (`qwen2.5:7b`)
- (Optional) Node.js 20+ for standalone dashboard dev

### Full Stack

```bash
# Start everything (includes auto-pipeline + dashboard)
make start-NeXo

# Start in dev mode (no auto-pipeline)
make start-dev

# Stop all services
make stop

# Restart
make restart

# View logs (all or specific service)
make logs [service]
make logs-notebooks
make logs-api
make logs-ai

# Check health of all services
make svc-health

# Show service URLs and credentials
make show-info
```

### Database

```bash
# Open PostgreSQL shell
make db-shell

# Reset database (WARNING: deletes all data)
make db-reset

# Backup database
make db-backup

# List tables
make db-tables
```

### Pipeline

```bash
# View pipeline execution logs
make pipeline-logs

# Manually run pipeline in notebooks container
make test-pipeline

# Force run pipeline in background
make pipeline-force
```

### Dashboard (standalone)

```bash
cd dashboard
npm install
npm run dev        # port 3001
npm run build      # production build
npm run lint       # ESLint
```

### Jupyter

```bash
# Get access token
make jupyter-token

# URL: http://localhost:8888
```

---

## 6. Testing Strategy

### Python Services

Tests are located in `services/<service>/tests/` and run with **pytest**.

| Service | Test Files | Coverage Focus |
|---|---|---|
| `pipeline-worker` | 5 files (`test_generators.py`, `test_processors.py`, `test_correlations.py`, `test_inference_client.py`, `test_config.py`) | Data generation, enrichment, correlations, HTTP client, config |
| `ai-service` | 1 file (`test_model_cache.py`) | Model lazy-loading cache (v2 + v3) |
| `api-gateway` | 1 file (`test_health.py`) | Health endpoint |
| `auth-service` | — | (tests should be added) |

**Run tests locally:**
```bash
cd services/<service>
pip install -r requirements.txt
pip install pytest pytest-cov httpx
pytest tests/ -v --tb=short --cov=.
```

**CI behavior:**
- Tests run in GitHub Actions against a PostgreSQL 16 service container.
- Test database: `telecom_intel_test`.
- `auth-service` skips test stage if no `tests/` directory exists.

### Frontend

The dashboard uses Next.js default ESLint (`npm run lint`). There are no Jest/Vitest test suites currently.

### Integration Tests

The CI pipeline starts the full Docker Compose stack and verifies:
- Health endpoints (`/health`) on api-gateway, ai-service, auth-service.
- Signup + login flow on auth-service.
- JWT-protected endpoint access on api-gateway.
- Correct 401 rejection for unauthenticated requests.

---

## 7. Code Style Guidelines

### Python

- **Linter/Formatter:** Ruff (enforced in CI).
- **Naming:** `snake_case` for variables/functions, `UPPER_SNAKE_CASE` for constants, `PascalCase` for classes.
- **Docstrings:** Place docstrings as the **first statement** in a function/method. Misplaced docstrings (after code) will fail review.
- **Imports:** Group as stdlib → third-party → local.
- **DB access:** Use raw `psycopg2` queries. No ORM (SQLAlchemy, etc.) is used.
- **No type hints required** but appreciated for public function signatures.

**Check before committing:**
```bash
ruff check services/<service>/
ruff format --check services/<service>/
```

### TypeScript / React

- **Naming:** `camelCase` for variables/functions, `PascalCase` for components/types.
- **Framework:** Next.js 14 App Router.
- **Styling:** CSS modules in `globals.css` + Tailwind-style utility classes.
- **Charts:** Custom SVG components only (Sparkline, DonutChart, RadarChart, ConfusionMatrix, FeatureImportanceChart). No extra chart library dependencies.

### Git Commits

```
type(scope): description

Types: feat, fix, chore, docs, phase#
Example: feat(phase-2): real ML inference - GradientBoosting + IsolationForest
```

---

## 8. Database Schema (PostgreSQL)

Database: `telecom_intel`  
Schema file: `docs/db/schema.sql` (applied automatically on first postgres startup via Docker volume mount).

### Tables

| Table | Purpose | Key Notes |
|---|---|---|
| `users` | Authentication & OAuth | Supports local / Google / GitHub OAuth. `provider` + `provider_id` unique. |
| `pipeline_runs` | Run lifecycle | Parent table. FK from 5 others via `run_id`. |
| `dataset_registry` | MinIO object metadata | 2 raw + 2 processed + 1 curated per run. |
| `model_registry` | Model artifact registry | `sla-risk`, `anomaly`, `revenue-anomaly` (v2.0); `cem`, `vae-anomaly`, `rat-underservice` (v3.0). |
| `sla_risk_scores` | GBR predictions | `score` CHECK (0–1). `explanation` is JSONB. |
| `anomalies` | OSS per-record anomalies | `severity`, `kpi_name`, `cell_id`, `model_version`. |
| `revenue_anomalies` | BSS per-subscriber anomalies | `operator`, `line_type`, `plan`, `severity`. |
| `correlation_insights` | OSS–BSS correlations | 5 pairs × 2 methods = 10 results per run. |
| `agent_actions` | L4 Agent audit trail | `status`, `execution_log` JSONB, `resolved_at`, `resolved_by`. |

### Default Credentials (dev only)

- **PostgreSQL:** `telecom` / `telecom_pw` / `telecom_intel`
- **MinIO:** `minio` / `minio_pw`
- **JWT Secret:** `telecom-dev-secret-change-in-prod`
- **SigNoz:** No login required (dev mode)
- **ClickHouse:** `admin` / `27ff0399-0d3a-4bd8-919d-17c2181e6fb9` (internal only)

---

## 9. API Structure

### api-gateway (`:8000`)

All endpoints except `/health` require `Authorization: Bearer <JWT>`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/sla-risk` | Latest SLA risk score + feature importances |
| GET | `/sla-risk/history?limit=N` | Historical scores (default 20, max 200) |
| GET | `/anomalies?limit=N` | OSS anomalies (default 50, max 500) |
| GET | `/revenue-anomalies?limit=N` | BSS anomalies (default 50, max 500) |
| GET | `/correlation?limit=N` | OSS–BSS correlations (default 50, max 200) |
| GET | `/pipeline-runs?limit=N` | Pipeline history (default 10, max 100) |
| GET | `/anomaly-stats?limit=N` | Per-run anomaly counts + avg severity |
| GET | `/kpi-summary?limit=N` | Real KPI aggregates from JSONB |
| GET | `/actions?limit=N&status=X` | L4 Agent actions (filterable) |
| POST | `/actions` | Create action (idempotent via ON CONFLICT) |
| PATCH | `/actions/{action_id}` | Update status (approve/reject) |
| POST | `/actions/{action_id}/execute` | Execute playbook (real backend ops) |

### ai-service (`:8001`) — internal

| Method | Path | Model | Version |
|---|---|---|---|
| GET | `/health` | Returns model version + load status | — |
| POST | `/infer/sla-risk` | GradientBoostingRegressor | v2.0 (legacy) |
| POST | `/infer/anomaly` | IsolationForest | v2.0 (legacy, OSS) |
| POST | `/infer/revenue-anomaly` | IsolationForest | v2.0 (legacy, BSS) |
| POST | `/infer/cem` | LightGBM (DART) | v3.0 |
| POST | `/infer/vae-anomaly` | PyTorch VAE | v3.0 |
| POST | `/infer/rat-underservice` | XGBoost (GPU) | v3.0 |
| POST | `/models/reload` | Hot-reload all 6 models from disk | — |

### auth-service (`:8002`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/signup` | Register (email/password) |
| POST | `/auth/login` | Login (returns JWT) |
| GET | `/auth/me` | Current user profile |
| GET | `/auth/google` | Google OAuth redirect |
| GET | `/auth/github` | GitHub OAuth redirect |

---

## 10. Security Considerations

### Authentication
- JWT Bearer tokens required for all protected api-gateway endpoints.
- Auth service supports local (bcrypt-hashed passwords), Google OAuth, and GitHub OAuth.
- JWT secret is configurable via `JWT_SECRET` env var. Default dev secret **must** be changed in production.
- OAuth credentials (`GOOGLE_CLIENT_ID`, `GITHUB_CLIENT_ID`, etc.) are optional for local dev (empty by default).

### Authorization
- `users.role` column supports `viewer | analyst | admin`. Currently used for future RBAC expansion.
- Dashboard auth middleware in `dashboard/middleware.ts`.

### Secrets Handling
- No hardcoded passwords in source code (enforced by CI secret-scanning step).
- All secrets are env-var injected.
- `.env.local` and `.env.example` are present for reference.

### CI Security Scan
- Stage 5 of CI/CD runs `pip-audit` and `safety` on all service `requirements.txt` files.
- A grep-based secret scan checks for hardcoded password assignments.

### Data Confidentiality (CRITICAL)

**`TT_data/` contains real Tunisie Telecom subscriber and network data. This is STRICTLY CONFIDENTIAL.**

- **NEVER** commit any data from `TT_data/` to git.
- **NEVER** export, share, or upload the data anywhere.
- All processing must stay local.
- `TT_data/` is already in `.gitignore` — **DO NOT** remove it.

---

## 11. Deployment & CI/CD

**File:** `.github/workflows/ci-cd.yml`

**Triggers:** Push to `main` or `dev`; PRs to `main`.

**Registry:** `ghcr.io/souhayl1g/telecom-cloud-intelligence/*`

### Stages

1. **Lint** — `ruff check` + `ruff format --check` per service.
2. **Test** — `pytest` per service (with PostgreSQL service container).
3. **Build** — Docker image build + push to GHCR.
4. **Integration** — Full Docker Compose stack startup + health + auth flow tests.
5. **Security** — `pip-audit` + hardcoded secret scan.
6. **Deploy** — Notification only (main branch push). Actual HCS deployment is manual.

### Deploy Targets

- **Local:** `make start-NeXo`
- **Production (Docker):** `docker compose -f docker-compose.prod.yml up -d` (file to be created)
- **Huawei Cloud Stack:** Push images to SWR → deploy on CCE → verify health endpoints.

---

## 12. Development Conventions

### Adding a New API Endpoint
1. Add route in `services/api-gateway/routers/<domain>.py`.
2. Add DB query if needed (raw `psycopg2`, no ORM).
3. Endpoints are auto-instrumented by OpenTelemetry FastAPI instrumentation.

### Adding a New ML Model
1. Train in `notebooks/` (save artifacts to `notebooks/models/`).
2. Copy artifacts to `services/ai-service/models/` (`.joblib` for sklearn, `.pt` for PyTorch).
3. Add inference router in `services/ai-service/routers/v3/` (follow existing patterns).
4. Add model path to `services/ai-service/config.py`.
5. Add loader to `services/ai-service/model_cache.py`.
6. Add pipeline step in `services/pipeline-worker/worker/pipeline.py`.
7. Register model in `model_registry` table.

### Frontend Development
1. Pages in `dashboard/app/` (Next.js App Router).
2. Components in `dashboard/components/`.
3. API calls go through `dashboard/lib/` utilities or `/api/*` Next.js routes.
4. Auth middleware in `dashboard/middleware.ts`.
5. **CRITICAL:** Client pages needing auth data must use `/api/platform-data` SSR proxy (NOT direct `:8000` calls). The proxy reads the `auth_token` httpOnly cookie and forwards with `Authorization: Bearer` header.

### L4 Agent Playbooks

Real playbook execution happens via `POST /actions/{id}/execute`:

| Playbook ID | Backend Effect |
|---|---|
| `pb-model-retrain` | POST to `ai-service:8001/models/reload` |
| `pb-anomaly-triage` | Queries anomalies + cross-references correlations |
| `pb-revenue-protect` | Queries high-severity revenue anomalies + computes at-risk revenue |
| `pb-sla-breach` | Reads SLA score + identifies threshold-exceeding KPIs |
| `pb-capacity-scale` | Computes capacity headroom from KPI history |

---

## 13. Known Issues & Constraints

### Build Issues
- **Stale Next.js cache:** If you get "Cannot find module './948.js'" or similar:
  ```bash
  rm -rf dashboard/.next && npx next build
  ```
- **Recharts MUST stay at v2.x** (`2.15.3`). Recharts v3.x is a full TypeScript rewrite that causes React error #310 ("Objects are not valid as React child"). **Do NOT upgrade to recharts 3.x.**

### Runtime Notes
- Pipeline worker switched to **manual mode** (`RUN_MODE=manual`) for controlled v3.0 pipeline cycles.
- All services share the same Docker bridge network.
- OAuth credentials are optional (empty by default for local dev).
- **Real data integrated:** BSS 968K real + 1.5M simulated, OSS 18.8M real + 200K simulated.
- All v3.0 models trained on combined real+simulated data (1.5M+ records).
- Dashboard model-evaluation page shows real v3.0 metrics (not mocked).
- **LightGBM GPU:** Not available in pip build (OpenCL/CUDA not compiled). Uses CPU with DART + deep trees + regularization.
- **XGBoost GPU:** Uses `tree_method="hist"` + `device="cuda"` (XGBoost 3.x API).
- **VAE GPU:** Full CUDA acceleration via PyTorch.

### Hardware Context
- CPU: Ryzen 5 5600H (6 cores, 3.3GHz)
- RAM: 24GB (19.9GB usable)
- GPU: RTX 3050 4GB VRAM (for PyTorch training)
- Disk: ~1000GB available on D:/
- Ollama models stored on D:/ drive (`OLLAMA_MODELS=/mnt/d/ollama-models`) because C:/ is full.

---

## 14. Key Documentation References

- `CLAUDE.md` — Comprehensive project knowledge (architecture, data flow, dashboard pages, model specs, ADN L4 Agent, API routes, DB schema, audit log).
- `README.md` — Public-facing project overview (badges, quick start, API reference).
- `docs/overview/project-snapshot.md` — Master project state document.
- `docs/architecture/architecture-v1.md` — C4 architecture diagrams.
- `docs/architecture/ml-models.md` — Full ML model specs (586 lines).
- `docs/data-model/postgres-schema.md` — ER diagram (Mermaid).
- `docs/data-model/data-lake.md` — 3-layer data lake architecture.
- `docs/data-model/bss-real-data-analysis.md` — BSS real data analysis + DL plan + rolling window engine design.
- `docs/deployment/local-docker.md` — Local deployment guide.

---

## 15. Quick Command Reference

```bash
# Start everything
make start-NeXo

# Dev mode (no auto-pipeline)
make start-dev

# Health check
make svc-health

# Logs
make logs api-gateway
make logs ai-service
make logs notebooks

# Database
make db-shell
make db-reset
make db-backup

# Lint (before commit)
ruff check services/api-gateway/ services/ai-service/ services/pipeline-worker/ services/auth-service/
ruff format services/api-gateway/ services/ai-service/ services/pipeline-worker/ services/auth-service/

# Test
pytest services/pipeline-worker/tests/ -v
pytest services/ai-service/tests/ -v
pytest services/api-gateway/tests/ -v

# Clean everything
make clean
```
