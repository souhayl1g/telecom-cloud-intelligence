# Technology Stack

**Analysis Date:** 2026-04-25

## Languages

**Primary:**
- Python 3.11 — All backend microservices (`services/api-gateway/`, `services/ai-service/`, `services/auth-service/`, `services/pipeline-worker/`, `services/agent-service/`)
- TypeScript 5.4.5 — Next.js dashboard (`dashboard/`)

**Secondary:**
- SQL — PostgreSQL schema and raw psycopg2 queries (`docs/db/schema.sql`, all service `main.py` files)
- Jupyter Notebooks — ML model training and evaluation (`notebooks/`)

## Runtime

**Environment:**
- Python: 3.11 (pinned in CI via `PYTHON_VERSION: "3.11"` in `.github/workflows/ci-cd.yml`)
- Node.js: 20-alpine (dashboard Dockerfile base image)

**Package Manager:**
- Python: pip (per-service `requirements.txt` files, no lockfile)
- Node.js: npm (lockfile: `dashboard/package-lock.json` present)

## Frameworks

**Backend:**
- FastAPI 0.115.0 — All Python microservices (api-gateway, ai-service, auth-service, agent-service)
- Uvicorn 0.30.6 (standard extras) — ASGI server for all FastAPI services
- Pydantic 2.8.2 — Request/response validation across all services

**Frontend:**
- Next.js 14.2.5 — Dashboard app router (`dashboard/`)
- React 18.3.1 — UI framework
- Framer Motion 12.38.0 — Animations
- Recharts 2.15.3 — Chart library (PINNED — do NOT upgrade to v3.x; causes React error #310)

**ML/Data Science:**
- scikit-learn 1.5.2 — Current ML models (GradientBoostingRegressor, IsolationForest) in `services/ai-service/`
- joblib 1.4.2 — Model serialization/deserialization (`.joblib` files in `notebooks/models/`)
- numpy 2.0.1 — Numerical computation across ai-service and pipeline-worker
- scipy 1.14.0 — Statistical functions (Pearson/Spearman correlations) in pipeline-worker
- pandas 2.2.2, matplotlib 3.9.2, seaborn 0.13.2 — Used in Jupyter notebooks only

**Planned (not yet implemented):**
- PyTorch 2.x — Planned for Autoencoder (experience anomaly) and LSTM (churn trajectory) in Phase 4.5/DL

## Key Dependencies

**Critical:**
- `python-jose[cryptography]` 3.3.0 — JWT encoding/decoding (api-gateway, auth-service); algorithm: HS256
- `passlib[bcrypt]` 1.7.4 + `bcrypt` 4.1.3 — Password hashing in auth-service
- `psycopg2-binary` 2.9.9 — PostgreSQL driver; raw SQL, no ORM (all services that touch DB)
- `boto3` 1.35.0 — S3-compatible MinIO client in pipeline-worker and notebooks
- `httpx` 0.27.0 — Async HTTP client for OAuth token exchange in auth-service
- `requests` 2.32.3 — Sync HTTP client for internal service calls (api-gateway → agent-service, pipeline-worker → ai-service)
- `tenacity` 9.0.0 — Retry logic in pipeline-worker for resilient service calls

**Observability:**
- `opentelemetry-api` 1.25.0 + `opentelemetry-sdk` 1.25.0 — Tracing instrumentation (all FastAPI services)
- `opentelemetry-exporter-otlp-proto-grpc` 1.25.0 — OTLP gRPC exporter to otel-collector:4317
- `opentelemetry-instrumentation-fastapi` 0.46b0 — Auto-instrumentation via `FastAPIInstrumentor.instrument_app(app)`
- `opentelemetry-instrumentation-logging` 0.46b0 — Log correlation with traces

## Configuration

**Environment:**
- All services configured via environment variables injected by `docker-compose.yml`
- No `.env` file at root (dev defaults baked into docker-compose); `dashboard/.env.example` and `dashboard/.env.local` exist
- Key env vars per service:
  - All DB-connected services: `DATABASE_URL`
  - Auth-bearing services: `JWT_SECRET`
  - All services: `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`
  - Pipeline-worker: `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `AI_SERVICE_URL`
  - Agent-service: `OLLAMA_URL`, `OLLAMA_MODEL`, `API_GATEWAY_URL`
  - Dashboard: `NEXT_PUBLIC_API_BASE_URL`, `AUTH_SERVICE_URL`, `OLLAMA_URL`, `OLLAMA_MODEL`
  - Auth-service: `GOOGLE_CLIENT_ID/SECRET`, `GITHUB_CLIENT_ID/SECRET`, `FRONTEND_URL`

**Build:**
- Python services: `Dockerfile` using `python:3.11-slim` base image (all 5 Python services)
- Dashboard: `Dockerfile` using `node:20-alpine` base image
- Notebooks: `Dockerfile.notebooks` at repo root (separate, for Jupyter container)
- Orchestration: `docker-compose.yml` (10 services + named volumes)

## Linting / Formatting

**Python:**
- Ruff — linter and formatter (enforced in CI Stage 1 across all 4 core services)
- CI command: `ruff check services/$svc/` and `ruff format --check services/$svc/`

**TypeScript:**
- Next.js built-in ESLint config (run via `npm run lint`)

## Testing

**Python:**
- pytest + pytest-cov + httpx — declared in CI; no `tests/` directories currently exist in services
- CI skips gracefully: `if [ -d "tests" ]; then pytest...; else echo "No tests — skipping"`

**Integration:**
- Full docker-compose stack spun up in CI Stage 4; health endpoints and auth flow exercised via curl

## Platform Requirements

**Development:**
- Docker + Docker Compose (all services containerized)
- Node.js 20+ and npm for dashboard standalone dev (`cd dashboard && npm install && npm run dev`)
- Ollama running separately (models stored on D:/ drive): `OLLAMA_MODELS=/mnt/d/ollama-models ollama serve`
- Default model: `qwen2.5:7b` (Q4_K_M, ~4.7GB)

**Production (target):**
- Container images published to GitHub Container Registry (`ghcr.io/souhayl1g/telecom-cloud-intelligence/*`)
- Huawei Cloud Stack (HCS) target: ECS (containers), RDS (PostgreSQL), OBS (MinIO/S3), ModelArts/EI (Ollama)
- CI triggers deploy stage only on `main` branch push

---

*Stack analysis: 2026-04-25*
