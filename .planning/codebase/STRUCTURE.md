# Codebase Structure

**Analysis Date:** 2026-04-25

## Directory Layout

```
telecom-cloud-intelligence/
├── services/                    # Backend microservices
│   ├── api-gateway/             # REST API gateway (port 8000)
│   │   ├── main.py              # All FastAPI routes + DB queries
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── ai-service/              # ML inference engine (port 8001)
│   │   ├── main.py              # Inference endpoints + model hot-reload
│   │   ├── bootstrap_models.py  # Model loading on startup
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── auth-service/            # JWT + OAuth2 service (port 8002)
│   │   ├── main.py              # Login, signup, OAuth routes
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── pipeline-worker/         # ETL orchestrator (background daemon)
│   │   └── worker/
│   │       ├── __main__.py      # 22-step pipeline + 2-min cycle loop
│   │       └── __init__.py
│   ├── agent-service/           # Multi-agent system (NeXo)
│   │   ├── main.py              # FastAPI entry for agent-service
│   │   ├── orchestrator.py      # LLM-powered intent routing
│   │   ├── requirements.txt
│   │   └── agents/
│   │       ├── base.py          # BaseAgent abstract class
│   │       ├── cem_agent.py     # CEM subscriber experience agent
│   │       ├── network_agent.py # OSS network monitoring agent
│   │       └── action_agent.py  # Remediation / playbook agent
│   └── data-ingest/             # Data ingestion helpers
├── dashboard/                   # Next.js 14 frontend (port 3001)
│   ├── app/                     # Next.js App Router pages
│   │   ├── layout.tsx           # Root layout (theme, fonts)
│   │   ├── globals.css          # All CSS (utility + component classes)
│   │   ├── ClientLayout.tsx     # Client-side layout (AICopilotIcon)
│   │   ├── overview/page.tsx
│   │   ├── anomalies/page.tsx
│   │   ├── sla-risk/page.tsx
│   │   ├── correlations/page.tsx
│   │   ├── intelligence/page.tsx
│   │   ├── predictive/page.tsx
│   │   ├── topology/page.tsx
│   │   ├── capacity/page.tsx
│   │   ├── data-warehouse/page.tsx
│   │   ├── pipeline-runs/page.tsx
│   │   ├── ops-metrics/page.tsx
│   │   ├── model-evaluation/page.tsx
│   │   ├── l4-agent/page.tsx    # ADN L4 autonomous agent
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   └── api/                 # Next.js API routes (SSR proxies)
│   │       ├── platform-data/route.ts  # Auth proxy → api-gateway:8000
│   │       ├── chat/route.ts           # Ollama / LLM chat proxy
│   │       ├── agent-query/route.ts    # Agent service proxy
│   │       ├── model-metrics/route.ts  # Static real ML metrics
│   │       ├── health-check/route.ts   # Service health aggregator
│   │       ├── login/route.ts          # Auth login proxy
│   │       └── logout/route.ts         # Cookie clear
│   ├── components/              # Shared React components
│   │   ├── TopNav.tsx           # Navigation bar with all page links
│   │   ├── TopHeader.tsx        # Page header bar
│   │   ├── AICopilotIcon.tsx    # Floating AI agent FAB (bottom-right)
│   │   ├── CommandPalette.tsx   # Cmd+K command palette
│   │   ├── AnomalyTimeline.tsx  # Anomaly chart component
│   │   ├── AnomaliesBarChart.tsx
│   │   ├── AnomalyHeatmap.tsx
│   │   ├── CorrelationHeatmap.tsx
│   │   ├── SlaChart.tsx
│   │   ├── RiskGauge.tsx
│   │   ├── ScoreBar.tsx
│   │   ├── PageHero.tsx
│   │   ├── PageHeroServer.tsx
│   │   ├── RefreshContext.tsx   # Global data refresh context
│   │   ├── ThemeProvider.tsx
│   │   ├── ThemeToggle.tsx
│   │   └── LiveIndicator.tsx
│   ├── lib/
│   │   └── api.ts               # Typed API client helpers
│   ├── public/images/           # Static assets (logos, icons)
│   ├── middleware.ts             # Auth guard (JWT cookie check)
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── package.json
│   └── Dockerfile
├── notebooks/                   # Jupyter model training + evaluation
│   ├── 01_data_preparation_eda.ipynb
│   ├── 02_sla_risk_model.ipynb
│   ├── 03_anomaly_detection_models.ipynb
│   ├── models/                  # Trained model artifacts (.joblib)
│   │   └── *.joblib
│   ├── data/                    # Processed training data (.npz)
│   │   └── *.npz
│   └── requirements.txt
├── docs/                        # Architecture and data-model docs
│   ├── db/schema.sql            # PostgreSQL schema (source of truth)
│   ├── architecture/            # C4 diagrams, ML model specs
│   ├── data-model/              # ER diagrams, data lake design
│   ├── deployment/              # Local Docker guide
│   ├── data-request/            # TT data schema requirements
│   └── overview/                # Project snapshot
├── infra/                       # Infrastructure configuration
│   ├── monitoring/              # SigNoz + OTel Collector configs
│   │   └── grafana/             # Legacy Grafana provisioning (kept for reference)
│   └── db/                      # DB init scripts
├── diagrams/                    # Architecture diagram exports
│   └── export/
├── final-defense-report/        # LaTeX defense report
│   └── chapters/                # Individual chapter .tex files
├── report/                      # Progress reports and Gantt charts
├── graphify-out/                # Knowledge graph output (auto-generated)
│   └── cache/
├── memory/                      # Agent memory files
├── .planning/                   # GSD planning artifacts
│   └── codebase/                # Codebase map documents (this directory)
├── .github/workflows/           # CI/CD pipeline YAML
│   └── ci-cd.yml
├── docker-compose.yml           # 10-service orchestration
├── Makefile                     # Dev convenience targets
├── entrypoint.sh                # Container entrypoint script
├── pipeline_runner.py           # Simplified pipeline (Dockerfile.notebooks only)
├── Dockerfile.notebooks         # Jupyter notebook container
└── CLAUDE.md                    # Project instructions for Claude
```

## Directory Purposes

**`services/api-gateway/`:**
- Purpose: Single REST API surface exposed to the dashboard and external clients
- Contains: All endpoint handlers, raw psycopg2 DB queries, JWT auth middleware, Prometheus instrumentation
- Key file: `services/api-gateway/main.py` — all routes defined here (no routing split)
- No ORM — raw SQL via psycopg2

**`services/ai-service/`:**
- Purpose: Loads trained .joblib models at startup; serves inference via POST endpoints
- Contains: Model loading (`bootstrap_models.py`), three inference routes, `/models/reload` hot-reload endpoint
- Key file: `services/ai-service/main.py`
- Trained models read from `notebooks/models/*.joblib` (volume-mounted in Docker)

**`services/auth-service/`:**
- Purpose: Standalone JWT issuance and OAuth2 callbacks (Google, GitHub)
- Contains: Signup, login, `/auth/me`, OAuth redirect handlers; bcrypt password hashing
- Key file: `services/auth-service/main.py`

**`services/pipeline-worker/worker/`:**
- Purpose: 22-step ETL daemon running on 2-minute cycles
- Contains: Data generation/ingestion, MinIO lake writes, ai-service calls, PostgreSQL persistence
- Key file: `services/pipeline-worker/worker/__main__.py` — the real pipeline (not `pipeline_runner.py` at repo root)

**`services/agent-service/`:**
- Purpose: Multi-agent NeXo system (ADN-style orchestrator + 3 specialist agents)
- Contains: `orchestrator.py` (LLM-powered routing), `agents/cem_agent.py`, `agents/network_agent.py`, `agents/action_agent.py`
- All agents extend `agents/base.py`

**`dashboard/app/`:**
- Purpose: Next.js App Router pages — one subdirectory per route
- Contains: `page.tsx` per route, `layout.tsx` at root, `globals.css` for all styles
- Auth pattern: client pages use `/api/platform-data` SSR proxy; never call `:8000` directly
- All custom charts are inline SVG components — no third-party chart library except recharts v2.x (pinned `2.15.3`)

**`dashboard/app/api/`:**
- Purpose: Server-side API routes that proxy to backend services with auth cookie forwarding
- Key route: `platform-data/route.ts` — aggregates 9 endpoints from api-gateway:8000 in parallel

**`dashboard/components/`:**
- Purpose: Shared React components used across multiple pages
- Contains: Navigation, charts, layout helpers, context providers
- No barrel index file — import directly by filename

**`dashboard/lib/`:**
- Purpose: Typed API client utilities
- Key file: `dashboard/lib/api.ts` — fetch helpers with TypeScript types

**`notebooks/`:**
- Purpose: Model training, evaluation, and EDA — not part of production runtime
- `notebooks/models/*.joblib` — artifact files consumed by ai-service at container startup
- `notebooks/data/*.npz` — processed train/test splits

**`docs/db/schema.sql`:**
- Source of truth for PostgreSQL schema (8 tables)
- Changes here must be reflected in api-gateway queries

**`infra/monitoring/`:**
- Netdata + Prometheus + Grafana + Jaeger + OpenTelemetry Collector configuration
- SigNoz replaces the legacy Grafana/Prometheus stack (Grafana configs kept for reference only)

## Key File Locations

**Entry Points:**
- `services/api-gateway/main.py` — FastAPI app, all REST routes
- `services/ai-service/main.py` — ML inference FastAPI app
- `services/auth-service/main.py` — Auth FastAPI app
- `services/pipeline-worker/worker/__main__.py` — ETL daemon loop
- `services/agent-service/main.py` — Agent service FastAPI app
- `dashboard/app/layout.tsx` — Next.js root layout
- `dashboard/middleware.ts` — Route auth guard

**Configuration:**
- `docker-compose.yml` — All service wiring, ports, volumes, env vars
- `dashboard/next.config.js` — Next.js build config
- `dashboard/tsconfig.json` — TypeScript paths and settings
- `.github/workflows/ci-cd.yml` — CI/CD stages (lint → test → build → deploy)
- `docs/db/schema.sql` — Database schema (authoritative)

**Core Logic:**
- `services/api-gateway/main.py` — All DB queries and business logic for API
- `services/pipeline-worker/worker/__main__.py` — 22-step ETL pipeline
- `services/agent-service/orchestrator.py` — LLM intent routing
- `dashboard/app/l4-agent/page.tsx` — L4 autonomous ops agent UI + action lifecycle
- `dashboard/app/api/platform-data/route.ts` — SSR auth proxy (critical pattern)

**CSS:**
- `dashboard/app/globals.css` — Single CSS file for all component and utility styles
  - L4 agent layout classes: `.l4-tabs`, `.l4-chat-panel`, `.l4-actions-panel`, `.l4-panel-active`
  - Toast classes: `.l4-toast-container`, `.l4-toast`, `.l4-toast-warning/danger/info`
  - FAB classes: `.ai-copilot-fab`, `.ai-copilot-menu`, `.ai-copilot-pulse`
  - Model evaluation: `.me-model-card`, `.me-health-item`, `.me-metric-label`, `.me-metric-value`

## Naming Conventions

**Python files:**
- Services: `main.py` at each service root (single module, no sub-routing)
- Agents: `<role>_agent.py` (e.g., `cem_agent.py`, `network_agent.py`)
- Scripts: `snake_case.py`

**TypeScript/TSX files:**
- Pages: `page.tsx` inside route directory (Next.js App Router convention)
- API routes: `route.ts` inside `app/api/<name>/` directory
- Components: `PascalCase.tsx` (e.g., `TopNav.tsx`, `AICopilotIcon.tsx`)
- Utilities: `camelCase.ts` (e.g., `api.ts`)

**Directories:**
- Next.js pages: `kebab-case/` (e.g., `l4-agent/`, `model-evaluation/`, `sla-risk/`)
- Python services: `kebab-case/` (e.g., `api-gateway/`, `ai-service/`)
- Agent modules: `snake_case/` matching Python convention

**Variables and functions:**
- Python: `snake_case` for all vars/functions, `UPPER_SNAKE_CASE` for constants
- TypeScript/JS: `camelCase` for vars/functions, `PascalCase` for components and types

## Where to Add New Code

**New API endpoint (api-gateway):**
1. Add route handler in `services/api-gateway/main.py` — all routes live in this one file
2. Write raw SQL query using psycopg2 (no ORM)
3. Protect with `Depends(verify_token)` JWT dependency
4. Endpoint auto-instrumented by prometheus-fastapi-instrumentator
5. Update `dashboard/app/api/platform-data/route.ts` if the new endpoint should be fetched by the dashboard

**New ML model:**
1. Train and evaluate in a new notebook under `notebooks/` (follow existing naming: `04_*.ipynb`)
2. Save `.joblib` artifact to `notebooks/models/`
3. Add inference endpoint to `services/ai-service/main.py`
4. Load model in `services/ai-service/bootstrap_models.py`
5. Add pipeline step calling the new inference endpoint in `services/pipeline-worker/worker/__main__.py`
6. Add a new table or column in `docs/db/schema.sql`, then apply migration
7. Register model entry in `model_registry` DB table

**New dashboard page:**
1. Create directory `dashboard/app/<route-name>/`
2. Add `page.tsx` inside it (Next.js App Router auto-registers the route)
3. If the page is client-side and needs auth data, fetch through `/api/platform-data` — never call `:8000` directly
4. Add the route to `dashboard/components/TopNav.tsx` nav items list
5. Add custom CSS to `dashboard/app/globals.css` using project CSS class naming

**New dashboard API route:**
1. Create `dashboard/app/api/<name>/route.ts`
2. Read `auth_token` cookie from `next/headers`
3. Forward request to backend service with `Authorization: Bearer <token>` header

**New shared component:**
1. Add `PascalCase.tsx` to `dashboard/components/`
2. Import directly — no barrel file (`import X from "@/components/X"`)
3. Charts must be custom SVG — do not add new chart library dependencies
4. Exception: recharts is already installed at v2.15.3 (pinned — do NOT upgrade to v3.x)

**New agent:**
1. Create `services/agent-service/agents/<role>_agent.py`
2. Extend `BaseAgent` from `services/agent-service/agents/base.py`
3. Register in `services/agent-service/orchestrator.py` dispatch table

**New database table:**
1. Add `CREATE TABLE` statement to `docs/db/schema.sql` (source of truth)
2. Apply migration to running PostgreSQL (manual via psql or `infra/db/` scripts)
3. Add corresponding queries in `services/api-gateway/main.py`

## Special Directories

**`TT_data/`:**
- Purpose: Real Tunisie Telecom subscriber and network data (CONFIDENTIAL)
- Generated: No — received from TT
- Committed: NO — in `.gitignore`. NEVER commit contents.
- Contains: `BSS/smartcare_Acem_feb.csv` (468K subscribers, Feb 2026), `BSS/request_data_1month_500K.csv` (500K, March 2026)

**`notebooks/models/`:**
- Purpose: Trained `.joblib` model artifacts consumed by ai-service at startup
- Generated: Yes — output of notebook training cells
- Committed: Yes — model files are tracked in git

**`notebooks/data/`:**
- Purpose: Processed `.npz` train/test splits used during training
- Generated: Yes — output of notebook data preparation
- Committed: Selectively (small files only)

**`graphify-out/`:**
- Purpose: Auto-generated knowledge graph from codebase AST analysis
- Generated: Yes — by `graphify update .`
- Committed: Yes — wiki and graph report are useful reference
- Key file: `graphify-out/GRAPH_REPORT.md`

**`.planning/codebase/`:**
- Purpose: GSD codebase map documents consumed by planner/executor agents
- Generated: Yes — by `/gsd-map-codebase`
- Committed: Yes

**`pipeline_runner.py` (root):**
- Purpose: Simplified 3-step pipeline used only by `Dockerfile.notebooks` (Jupyter container)
- This is NOT the production pipeline — production pipeline is `services/pipeline-worker/worker/__main__.py`
- Do not modify expecting it to affect the deployed worker

**`infra/monitoring/grafana/`:**
- Purpose: Legacy Grafana provisioning configs (kept for reference)
- Active monitoring stack is SigNoz + OTel Collector (`infra/monitoring/` YAML configs)
- Grafana is no longer in `docker-compose.yml`

---

*Structure analysis: 2026-04-25*
