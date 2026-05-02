# Architecture

**Analysis Date:** 2026-04-25

## Pattern Overview

**Overall:** Microservices with event-driven data pipeline and LLM-powered autonomous agent layer

**Key Characteristics:**
- Five Python FastAPI microservices behind a single API Gateway (all on internal Docker bridge network)
- Three-layer data lake (raw / processed / curated) stored in MinIO (S3-compatible)
- PostgreSQL as the system of record for all ML outputs and platform events
- Next.js App Router dashboard uses an SSR proxy route (`/api/platform-data`) to bridge client-side rendering with httpOnly JWT cookies
- ADN L4 autonomous agent tier (Qwen2.5:7b via Ollama) dispatches to three specialist sub-agents via an LLM-powered Orchestrator with rule-based fallback

## Layers

**Data Ingestion / Pipeline:**
- Purpose: Generate or ingest OSS + BSS data, run the 22-step ETL pipeline, call ML inference, persist results
- Location: `services/pipeline-worker/worker/__main__.py`
- Contains: Synthetic data generators, MinIO bucket management, ML inference calls, DB persistence
- Depends on: MinIO (S3), PostgreSQL, `ai-service:8001`
- Used by: Nothing (daemon — runs on 2-minute cycles)

**ML Inference:**
- Purpose: Serve trained scikit-learn model predictions over HTTP
- Location: `services/ai-service/main.py`
- Contains: `/infer/sla-risk`, `/infer/anomaly`, `/infer/revenue-anomaly`, `/models/reload` endpoints; model hot-reload with file mtime cache
- Depends on: Trained `.joblib` model files from `notebooks/models/`
- Used by: `pipeline-worker` (during pipeline runs), `api-gateway` (playbook execution)

**Authentication:**
- Purpose: Issue and validate JWT tokens; support local email/password, Google OAuth, GitHub OAuth
- Location: `services/auth-service/main.py`
- Contains: `/auth/signup`, `/auth/login`, `/auth/me`, `/auth/google`, `/auth/github`
- Depends on: PostgreSQL (`users` table), bcrypt password hashing (`passlib`), `python-jose` JWT
- Used by: Dashboard (`/api/login` Next.js route proxies here), all clients needing tokens

**API Gateway:**
- Purpose: Single authenticated REST facade over all PostgreSQL data and downstream services
- Location: `services/api-gateway/main.py`
- Contains: 20+ REST endpoints (SLA risk, anomalies, correlations, actions, agent proxy, subscribers, areas, infra-stats)
- Depends on: PostgreSQL (raw `psycopg2`, no ORM), `ai-service:8001`, `agent-service:8003`
- Used by: Dashboard (`/api/platform-data` SSR proxy), any authenticated API client

**Multi-Agent Service:**
- Purpose: LLM-powered intent routing to specialist agents (CEMAgent, NetworkAgent, ActionAgent)
- Location: `services/agent-service/main.py`, `services/agent-service/orchestrator.py`, `services/agent-service/agents/`
- Contains: Orchestrator (Qwen2.5:7b via Ollama with keyword fallback), three specialist agents
- Depends on: Ollama (`http://host.docker.internal:11434`), PostgreSQL (via api-gateway)
- Used by: `api-gateway` agent proxy endpoints (`/agent/*`)

**Data Ingest (Real BSS Data):**
- Purpose: One-shot scripts to load real Tunisie Telecom BSS data into PostgreSQL and compute derived features
- Location: `services/data-ingest/ingest_bss.py`, `services/data-ingest/compute_features.py`, `services/data-ingest/simulate_oss.py`
- Contains: BSS CSV ingest, CEM feature computation, OSS simulation
- Depends on: PostgreSQL, real TT data in `TT_data/BSS/` (gitignored)
- Used by: Run manually (not part of 2-minute cycle)

**Dashboard (Frontend):**
- Purpose: Visualize all platform intelligence; provide L4 Agent chat and action management UI
- Location: `dashboard/app/` (Next.js App Router), `dashboard/components/`
- Contains: 15+ pages, SSR proxy API routes, custom SVG chart components
- Depends on: `/api/platform-data` SSR route (all data), `/api/chat` (Ollama LLM chat), `/api/agent-query` (NeXo multi-agent)
- Used by: End users (browser)

## Data Flow

**Standard Pipeline Cycle (every 2 minutes):**

1. `pipeline-worker` starts run — inserts `pipeline_runs` record with `status='started'`
2. Generates synthetic OSS (200 records) and BSS (200 records) datasets
3. Uploads raw JSON to MinIO `raw` bucket; registers in `dataset_registry`
4. Processes data → uploads to MinIO `processed` bucket
5. Computes aggregate KPI features from OSS + BSS
6. Calls `ai-service:8001/infer/sla-risk` → GradientBoostingRegressor prediction
7. Calls `ai-service:8001/infer/anomaly` → IsolationForest OSS anomaly detection
8. Calls `ai-service:8001/infer/revenue-anomaly` → IsolationForest BSS anomaly detection
9. Computes Pearson + Spearman correlations between OSS and BSS metrics
10. Builds curated dataset (joined OSS + BSS + AI results) → uploads to MinIO `curated` bucket
11. Persists to PostgreSQL: `sla_risk_scores`, `anomalies`, `revenue_anomalies`, `correlation_insights`
12. Marks `pipeline_runs.status = 'succeeded'` (or `'failed'` with `error_message` on exception)

**Dashboard Data Request Flow:**

1. Browser page renders → calls `/api/platform-data` (Next.js SSR route, runs server-side)
2. SSR route reads `auth_token` httpOnly cookie via `cookies()` from `next/headers`
3. SSR route fires 11 parallel `fetch()` calls to `api-gateway:8000` with `Authorization: Bearer <token>`
4. api-gateway queries PostgreSQL for each endpoint
5. Aggregated response returned as single JSON to the browser client

**L4 Agent Action Lifecycle:**

1. Dashboard `generateActions()` creates actions from live platform data
2. Each action POSTed to `/api/platform-data` (`_action: "create"`) → `api-gateway POST /actions` → `agent_actions` table (idempotent via `ON CONFLICT`)
3. On page load: GET `/actions` restores persisted actions (survive browser refresh)
4. Human approves → PATCH `/actions/{id}` (`status='approved'`) → POST `/actions/{id}/execute`
5. Execute: api-gateway runs the playbook inline (queries DB, optionally calls ai-service), stores result in `execution_log` JSONB, marks `status='executed'`

**LLM Agent Query Flow:**

1. Dashboard chat or `/api/agent-query` route POSTs to `api-gateway POST /agent/query`
2. api-gateway proxies to `agent-service:8003 POST /agent/query`
3. `Orchestrator` sends query to `Qwen2.5:7b` via Ollama for intent classification + entity extraction
4. Orchestrator dispatches to `CEMAgent`, `NetworkAgent`, or `ActionAgent`
5. Specialist agent queries PostgreSQL (via its own DB connection) and returns structured `AgentResult`
6. Orchestrator synthesizes natural language response

## Key Abstractions

**`pipeline_runs` (Parent Record):**
- Purpose: Each 2-minute pipeline cycle produces one `pipeline_runs` row; all ML outputs FK to it via `run_id TEXT`
- Examples: `docs/db/schema.sql` lines 29-36
- Pattern: UUID `run_id` (text, not serial) used as FK across `anomalies`, `sla_risk_scores`, `revenue_anomalies`, `correlation_insights`, `dataset_registry`

**`agent_actions` (L4 Action Store):**
- Purpose: Full audit trail for L4 Agent decisions — status lifecycle, execution log, resolver identity
- Examples: `docs/db/schema.sql` lines 122-138
- Pattern: `action_id` TEXT UNIQUE (client-generated UUID); `execution_log` JSONB stores step-by-step playbook results; `status` enum: `pending → approved/auto_approved → executed | rejected`

**SSR Auth Proxy (`/api/platform-data`):**
- Purpose: Client components cannot read httpOnly cookies; this Next.js route handler runs server-side, reads the cookie, and injects the Bearer token into all api-gateway calls
- Examples: `dashboard/app/api/platform-data/route.ts`
- Pattern: GET aggregates 11 endpoints in parallel; POST dispatches to create/execute actions; PATCH updates action status

**`_db()` Context Manager:**
- Purpose: Per-request psycopg2 connection with commit-on-success / rollback-on-error / always-close semantics
- Examples: `services/api-gateway/main.py` lines 77-88
- Pattern: Used in every api-gateway endpoint; no connection pooling (one connection per request)

**Orchestrator with LLM + Keyword Fallback:**
- Purpose: Route natural language queries to specialist agents without hard-coded rules
- Examples: `services/agent-service/orchestrator.py`
- Pattern: Qwen2.5:7b classifies intent; if Ollama unavailable, `KEYWORD_MAP` provides deterministic fallback routing

## Entry Points

**Pipeline Daemon:**
- Location: `services/pipeline-worker/worker/__main__.py`
- Triggers: Docker container start; loops indefinitely with 120-second sleep between runs
- Responsibilities: Full 22-step ETL → ML inference → persistence cycle

**api-gateway:**
- Location: `services/api-gateway/main.py` (FastAPI app object at module root)
- Triggers: HTTP requests on port 8000
- Responsibilities: JWT validation, DB queries, playbook execution, agent proxying

**auth-service:**
- Location: `services/auth-service/main.py`
- Triggers: HTTP requests on port 8002
- Responsibilities: User signup/login, OAuth flows, JWT issuance

**ai-service:**
- Location: `services/ai-service/main.py`
- Triggers: HTTP requests on port 8001 from pipeline-worker and api-gateway
- Responsibilities: Serve ML model predictions; hot-reload models from disk on demand

**agent-service:**
- Location: `services/agent-service/main.py`
- Triggers: HTTP requests on port 8003 from api-gateway
- Responsibilities: LLM-powered intent routing, specialist agent dispatch

**Dashboard:**
- Location: `dashboard/app/layout.tsx` (root layout), `dashboard/app/page.tsx` (root redirect)
- Triggers: Browser navigation; Next.js dev server on port 3001
- Responsibilities: Render all 15+ pages, manage auth state, proxy API calls

## Error Handling

**Strategy:** Catch-and-raise at each layer boundary; pipeline worker catches all exceptions and marks run as `'failed'`

**Patterns:**
- All api-gateway endpoints: `try/except Exception as e → HTTPException(500, str(e))`
- HTTP 401 raised by `require_auth` dependency if JWT missing or invalid
- `HTTPException` re-raised explicitly to avoid being swallowed by generic `except Exception`
- Pipeline worker: outer `try/except` in `run_once()` → `UPDATE pipeline_runs SET status='failed', error_message=...`
- ai-service: model hot-reload uses file `mtime` cache to avoid reloading unchanged models
- SSR proxy (`/api/platform-data`): `safeFetch` returns `null` on any error; page renders with graceful empty states
- Orchestrator: Ollama call wrapped in try/except → falls back to `KEYWORD_MAP` rule-based routing

## Cross-Cutting Concerns

**Distributed Tracing:** OpenTelemetry SDK configured in all four Python services (`_setup_tracing()` called at module load); traces exported to `otel-collector:4317` (OTLP gRPC); SigNoz frontend at port 3301 for visualization

**Validation:** Pydantic models used in auth-service for request bodies (`BaseModel`); api-gateway uses inline field presence checks for action creation; no shared validation library

**Authentication:** JWT HS256 tokens issued by auth-service; validated inline in api-gateway via `python-jose`; shared `JWT_SECRET` env var across both services; dashboard stores token in httpOnly cookie `auth_token` set at login

**Database Access:** Raw `psycopg2` with `RealDictCursor` in api-gateway and auth-service; no ORM; per-request connections via `_db()` context manager; JSONB used for `explanation` (SLA scores) and `execution_log` (agent actions)

---

*Architecture analysis: 2026-04-25*
