# External Integrations

**Analysis Date:** 2026-04-25

## APIs & External Services

**LLM / AI:**
- Ollama (local) — Natural language processing for L4 Agent chat and multi-agent orchestration
  - Client: `requests` (sync HTTP in `services/agent-service/orchestrator.py`)
  - Connection: `OLLAMA_URL` env var (default: `http://host.docker.internal:11434`)
  - Model: `OLLAMA_MODEL` env var (default: `qwen2.5:7b`; dashboard compose uses `kimi-k2.5:cloud`)
  - Endpoints used: `POST /api/generate` (streaming completions)
  - Fallback: Rule-based keyword routing in `orchestrator.py` if Ollama is unavailable

**Google OAuth2:**
- Purpose: Social login for dashboard users
- Implementation: `services/auth-service/main.py` (`/auth/google`, `/auth/google/callback`)
- Auth: OAuth 2.0 authorization code flow
- External calls:
  - `https://accounts.google.com/o/oauth2/v2/auth` — Authorization redirect
  - `https://oauth2.googleapis.com/token` — Code exchange
  - `https://www.googleapis.com/oauth2/v2/userinfo` — User profile fetch
- Env vars: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- Status: Optional — disabled gracefully if env vars are empty (returns HTTP 501)

**GitHub OAuth2:**
- Purpose: Social login for dashboard users
- Implementation: `services/auth-service/main.py` (`/auth/github`, `/auth/github/callback`)
- Auth: OAuth 2.0 authorization code flow
- External calls:
  - `https://github.com/login/oauth/authorize` — Authorization redirect
  - `https://github.com/login/oauth/access_token` — Code exchange
  - `https://api.github.com/user` — User profile fetch
  - `https://api.github.com/user/emails` — Verified email fetch (if profile email is null)
- Env vars: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI`
- Status: Optional — disabled gracefully if env vars are empty (returns HTTP 501)

## Data Storage

**Databases:**
- PostgreSQL 16
  - Image: `postgres:16` (docker-compose.yml)
  - Port: 5432
  - Connection env var: `DATABASE_URL` (format: `postgresql://telecom:telecom_pw@postgres:5432/telecom_intel`)
  - Client: `psycopg2-binary` 2.9.9 — raw SQL, no ORM, `RealDictCursor` for dict-style results
  - Schema auto-initialized: `docs/db/schema.sql` mounted to `/docker-entrypoint-initdb.d/schema.sql`
  - 8 tables: `users`, `pipeline_runs`, `dataset_registry`, `model_registry`, `sla_risk_scores`, `anomalies`, `revenue_anomalies`, `correlation_insights`, `agent_actions`
  - JSONB used for: `explanation` (ML feature attribution), `execution_log` (L4 agent playbook results)
  - Services that connect: api-gateway, auth-service, pipeline-worker, agent-service, notebooks

**Object Storage (Data Lake):**
- MinIO (S3-compatible)
  - Image: `minio/minio:latest`
  - Ports: 9000 (API), 9001 (console)
  - Client: `boto3` 1.35.0 (pipeline-worker and notebooks)
  - Connection env vars: `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`
  - 3-layer data lake buckets: `raw`, `processed`, `curated`
  - Usage: Pipeline-worker uploads OSS+BSS datasets at each stage; curated joined dataset uploaded after ML inference
  - HCS equivalent: OBS (Object Storage Service)

**Caching:**
- None — no Redis or in-memory cache layer. Model files cached by mtime check in `services/ai-service/main.py` (file hash/mtime-based lazy reload, not a cache service)

## Authentication & Identity

**Auth Strategy:**
- JWT (HS256) — stateless bearer tokens, 24-hour expiry by default
  - Library: `python-jose[cryptography]` 3.3.0
  - Secret: `JWT_SECRET` env var
  - Algorithm: `HS256`, expiry: `JWT_EXPIRE_MINUTES` (default: 1440 = 24h)
  - Issued by: `services/auth-service/main.py`
  - Verified by: `services/api-gateway/main.py` (local decode, no auth-service call per request)

**Auth Flow:**
1. Client authenticates via `POST /auth/login` or OAuth callback → receives JWT
2. Dashboard stores JWT in httpOnly cookie (`auth_token`)
3. Client-side pages call `/api/platform-data` SSR proxy route
4. SSR route (`dashboard/app/api/platform-data/route.ts`) reads cookie and forwards `Authorization: Bearer <token>` to api-gateway:8000
5. API gateway decodes JWT locally; no round-trip to auth-service

**Password Hashing:**
- `passlib[bcrypt]` 1.7.4 + `bcrypt` 4.1.3
- Implementation: `CryptContext(schemes=["bcrypt"])` in auth-service

**Supported Providers:**
- `local` — email + password
- `google` — Google OAuth2
- `github` — GitHub OAuth2
- Provider stored in `users.provider` column; `users.provider_id` links to OAuth identity

## Monitoring & Observability

**Distributed Tracing + Metrics + Logs:**
- SigNoz (self-hosted, all-in-one observability platform) — replaces Prometheus + Grafana
  - Frontend UI: `signoz/frontend:0.55.0` at port 3301 (no login required in dev mode)
  - Query service: `signoz/query-service:0.55.0`
  - Alert manager: `signoz/alertmanager:0.23.4`
  - Storage backend: ClickHouse 24.1.2 (`clickhouse/clickhouse-server:24.1.2-alpine`)
  - Coordination: Zookeeper 3.7.1 (for ClickHouse cluster)
  - Config files: `infra/monitoring/` (clickhouse-config.xml, clickhouse-users.xml, signoz-nginx.conf, signoz-alertmanager.yml, signoz-prometheus.yml, otel-collector-config.yaml)

**OpenTelemetry Collector:**
- Image: `signoz/signoz-otel-collector:0.102.11`
- Ports: 4317 (OTLP gRPC, used by all services), 4318 (OTLP HTTP)
- All FastAPI services export traces to `http://otel-collector:4317`
- Auto-instrumentation: `FastAPIInstrumentor.instrument_app(app)` in every service's `main.py`
- Env vars per service: `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`

**Error Tracking:**
- No dedicated external error tracking (e.g., Sentry) — errors surface via SigNoz traces and Docker logs

**Logging:**
- Python stdlib `logging` via `opentelemetry-instrumentation-logging` for trace-correlated logs
- No structured JSON logging library (e.g., structlog) — plain logging statements

## CI/CD & Deployment

**Version Control:**
- GitHub — repository at `souhayl1g/telecom-cloud-intelligence`
- Branches: `main` (production-ready), `dev` (active development)

**Container Registry:**
- GitHub Container Registry (GHCR): `ghcr.io/souhayl1g/telecom-cloud-intelligence/*`
- Images built and pushed on every push to `main` or `dev`
- Tags: branch name, commit SHA, `latest` (main only)

**CI Pipeline:**
- GitHub Actions: `.github/workflows/ci-cd.yml`
- 6 sequential stages:
  1. Lint — `ruff check` + `ruff format --check` (matrix: 4 services, parallel)
  2. Test — `pytest` if `tests/` directory exists (currently skips all services)
  3. Build — Docker Buildx with GHCR push, GHA layer cache
  4. Integration — Full `docker compose up`, health checks + auth flow smoke tests
  5. Security — `pip-audit` dependency scan + hardcoded secrets grep
  6. Deploy — Notification only (no actual deployment automation yet); triggers on `main` push only
- Tools used in CI: `ruff`, `pytest`, `pytest-cov`, `httpx`, `pip-audit`, `safety`, `docker/setup-buildx-action@v3`, `docker/metadata-action@v5`, `docker/build-push-action@v5`

**Target Hosting (planned):**
- Huawei Cloud Stack (HCS):
  - ECS — container hosting (replaces local Docker)
  - RDS — managed PostgreSQL (replaces local postgres container)
  - OBS — object storage (replaces MinIO)
  - ModelArts / EI — LLM serving (replaces local Ollama)
  - SWR — Software Repository (replaces GHCR for HCS deployments)
  - CCE — Cloud Container Engine (Kubernetes-based orchestration)

## Internal Service Communication

**Service-to-Service (HTTP):**
- api-gateway → agent-service: `AGENT_SERVICE_URL` env var (default: `http://agent-service:8003`)
- api-gateway → auth-service: `AUTH_SERVICE_URL` env var (default: `http://auth-service:8002`) — for proxying login
- pipeline-worker → ai-service: `AI_SERVICE_URL` env var (default: `http://ai-service:8001`)
- agent-service → api-gateway: `API_GATEWAY_URL` env var (default: `http://api-gateway:8000`)
- dashboard (SSR) → api-gateway: `NEXT_PUBLIC_API_BASE_URL` env var (internal: `http://api-gateway:8000`)
- dashboard (SSR) → auth-service: `AUTH_SERVICE_URL` env var

**Model Sharing:**
- Trained model files (`.joblib`) shared via Docker named volume `notebooks_models`
- notebooks service writes to `/app/models/`, ai-service mounts same volume read-only at `/app/models/`
- Hot reload: ai-service checks file mtime on each request to detect updated models without restart

## Webhooks & Callbacks

**Incoming:**
- OAuth callbacks (handled internally by auth-service):
  - `GET /auth/google/callback` — Google redirects here after user consent
  - `GET /auth/github/callback` — GitHub redirects here after user consent
- No external webhook receivers for third-party events

**Outgoing:**
- None — no outgoing webhooks to external services

## Environment Configuration Reference

**Required for full stack:**
| Variable | Service | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | api-gateway, auth-service, pipeline-worker, agent-service | PostgreSQL connection string |
| `JWT_SECRET` | api-gateway, auth-service | JWT signing key |
| `S3_ENDPOINT` | pipeline-worker | MinIO API endpoint |
| `S3_ACCESS_KEY` | pipeline-worker | MinIO access key |
| `S3_SECRET_KEY` | pipeline-worker | MinIO secret key |
| `AI_SERVICE_URL` | pipeline-worker | ai-service HTTP endpoint |
| `OLLAMA_URL` | agent-service, dashboard | Ollama API base URL |
| `OLLAMA_MODEL` | agent-service, dashboard | LLM model name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | all FastAPI services | OTel collector gRPC endpoint |

**Optional (OAuth disabled if absent):**
| Variable | Service | Purpose |
|----------|---------|---------|
| `GOOGLE_CLIENT_ID` | auth-service | Google OAuth app ID |
| `GOOGLE_CLIENT_SECRET` | auth-service | Google OAuth app secret |
| `GITHUB_CLIENT_ID` | auth-service | GitHub OAuth app ID |
| `GITHUB_CLIENT_SECRET` | auth-service | GitHub OAuth app secret |
| `FRONTEND_URL` | auth-service | OAuth redirect target after login |

**Secrets location:**
- Dev: baked into `docker-compose.yml` with safe defaults (e.g., `JWT_SECRET: ${JWT_SECRET:-telecom-dev-secret-change-in-prod}`)
- Prod: GitHub Actions repository secrets (referenced as `${{ secrets.GITHUB_TOKEN }}` etc.)
- Dashboard example: `dashboard/.env.example`

---

*Integration audit: 2026-04-25*
