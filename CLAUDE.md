# CLAUDE.md — Telecom NeXoligence Platform

> Last updated: 2026-04-27 | Phase 1 Backend Restructuring complete (modular services, 26 tests, ruff clean) | Next: Phase 3.5 (BSS ETL + Rolling Window) blocked on OSS data arrival

---

## Project Identity

**Title:** Cloud-Native AI Operations Agent for CEM-CVM Intelligence (HCS-Ready)
**Owner:** Souhayl Guenichi — ESPRIT engineering student, 6-month internship at Huawei Tunisia (Cloud IT / Sales-Solution)
**Goal:** Graduate with excellence, deliver an industrial-grade AI Operations Agent trained on real Tunisie Telecom data, demonstrate Huawei Cloud Stack maturity within the ADN paradigm.

**What it does:** Bridges Huawei CEM (SmartCare) and CVM by ingesting OSS network KPIs + BSS subscriber experience data, running ML/DL models (CEM experience scoring, experience anomaly detection via Autoencoder, churn trajectory prediction via LSTM, RAT underservice classification), computing OSS↔BSS correlations with Granger causality, and serving actionable intelligence via REST API + Next.js dashboard with ADN L4 autonomous operations.

**Strategic position:** Intelligence layer in Huawei's ADN (Autonomous Driving Network) architecture for O+B (OSS+BSS) convergence. CEM-oriented subscriber profiling (not billing) — aligned with SmartCare architecture.

**Data orientation:** CEM (Customer Experience Management) subscriber profiling. Real TT BSS data provides usage/device/network-quality features. Revenue/billing analysis is out of scope — CEM aligns with SmartCare, provides richer ML surface, and matches available data.

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
| signoz-frontend   | 3301  | All-in-one observability UI (traces, metrics, logs) |
| otel-collector    | 4317/4318 | OpenTelemetry OTLP receiver (gRPC/HTTP) |
| clickhouse        | —     | ClickHouse 24.1 (SigNoz storage, internal only) |
| ollama            | 11434 | Local LLM (Qwen2.5:7b)    |

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

# Ollama (models stored on D:/ to save space)
OLLAMA_MODELS=/mnt/d/ollama-models ollama serve
ollama run qwen2.5:7b
```

### Default Credentials (dev only)

- **PostgreSQL:** telecom / telecom_pw / telecom_intel
- **MinIO:** minio / minio_pw
- **JWT Secret:** telecom-dev-secret-change-in-prod
- **SigNoz:** No login required (dev mode) — open http://localhost:3301
- **ClickHouse:** admin / 27ff0399-0d3a-4bd8-919d-17c2181e6fb9 (internal only)

---

## Architecture

```
[CEM / SmartCare] --> [AI Operations Agent] --> [CVM]
                            |
                   (this project - cloud native)
                            |
                    [ADN L4 Auto-Ops Agent]
                    (Qwen2.5:7b via Ollama)
```

### Data Flow (current — synthetic, will be replaced by rolling window engine)
1. **pipeline-worker** generates/ingests OSS+BSS data (200 records each per run)
2. Stores raw -> processed -> curated in **MinIO** (3-layer data lake)
3. Calls **ai-service** for ML inference (3 models)
4. Computes Pearson+Spearman correlations
5. Persists all results to **PostgreSQL** (7 tables)
6. **api-gateway** serves results via 7 REST endpoints (JWT-protected)
7. **dashboard** visualizes everything + L4 Agent auto-approves safe actions

### Data Flow (planned — real TT data + rolling window engine)
1. **Bootstrap:** Load 500K BSS CSV + OSS data into PostgreSQL staging
2. **Rolling window engine** samples batches per 2-min cycle (stratified by area/usertype/rat)
3. **Feature computer** builds derived features + window features across last W cycles
4. Calls **ai-service** v3.0 for ML/DL inference (5 models: CEM Score, AE anomaly, LSTM churn, RAT underservice, O+B correlation)
5. O+B convergence engine joins BSS subscriber data with OSS cell KPIs by geography
6. Persists results + updates window buffer
7. **dashboard** visualizes CEM scores, experience anomalies, churn trajectories, underservice map

### ML Models — Current (v2.0, synthetic data) + Planned (v3.0, real TT data)

**Current models (v2.0 — synthetic, still running):**
| Model | Algorithm | Purpose | Key Metric |
|-------|-----------|---------|-----------|
| SLA Risk | GradientBoostingRegressor (200 est, depth=4) | Predict SLA breach probability (0-1) | Test R²=0.9791 |
| OSS Anomaly | IsolationForest (150 est, contamination=0.05) | Detect network anomalies | F1=0.8772, ROC-AUC=1.0 |
| BSS Revenue Anomaly | IsolationForest (150 est, contamination=0.05) | Detect revenue anomalies | F1=1.0, ROC-AUC=1.0 |

**Planned models (v3.0 — real TT data, blocked on OSS arrival):**
| Model | Algorithm | Purpose | Replaces |
|-------|-----------|---------|----------|
| CEM Experience Score | GradientBoosting (interpretable) | Subscriber experience quality (0-1) + feature explanation | SLA Risk |
| Experience Anomaly | Autoencoder (PyTorch) | Multivariate anomaly detection on 26+ CEM features | OSS Anomaly IF + BSS Revenue IF |
| Churn Trajectory | LSTM/GRU (PyTorch) | Temporal churn prediction from rolling window sequences | New |
| RAT Underservice | XGBoost / small NN | Detect subscribers underserved vs device capability | New |
| O+B Correlation | Pearson + Spearman + Granger Causality | Causal link: network degradation → subscriber impact | Enhanced correlation |

### Real Model Evaluation Metrics (from `notebooks/` — v2.0)
**SLA Risk (GradientBoostingRegressor):**
- Test R²: 0.979108, Test MAE: 0.018495, Test RMSE: 0.027222, Test MSE: 0.000741
- CV R²: 0.977127 ± 0.002773
- Top features: mean_latency_ms=0.6779, max_latency_ms=0.1497, packet_loss_rate=0.0785, jitter_ms=0.0483, throughput_mbps=0.0269, call_drop_rate=0.0182

**OSS Anomaly (IsolationForest):**
- Confusion Matrix: TN=2808, FP=42, FN=0, TP=150
- Precision=0.7813, Recall=1.0, F1=0.8772, ROC-AUC=1.0

**BSS Revenue Anomaly (IsolationForest):**
- Confusion Matrix: TN=2850, FP=0, FN=0, TP=150
- Precision=1.0, Recall=1.0, F1=1.0, ROC-AUC=1.0

---

## Dashboard Pages (15+)

| Route | Page | Status |
|-------|------|--------|
| `/overview` | Platform overview with live metrics | ✅ |
| `/anomalies` | OSS/BSS anomaly browser | ✅ |
| `/sla-risk` | SLA risk scores + history | ✅ |
| `/correlations` | OSS-BSS correlation explorer | ✅ |
| `/intelligence` | AI intelligence hub | ✅ |
| `/predictive` | Predictive analytics / Forecast (real anomaly-stats data) | ✅ REAL DATA |
| `/topology` | Network topology view (demo structure, real severity overlay) | ✅ DEMO |
| `/capacity` | Capacity planning (real KPI from ML model features) | ✅ REAL DATA |
| `/data-warehouse` | DWH explorer | ✅ |
| `/pipeline-runs` | Pipeline run history | ✅ |
| `/ops-metrics` | Operational health | ✅ |
| `/model-evaluation` | Real ML model metrics + charts | ✅ NEW |
| `/l4-agent` | ADN L4 Autonomous Ops Agent (real playbooks, persisted actions) | ✅ REAL PLAYBOOKS |
| `/login` | Auth page (JWT + OAuth) | ✅ |

---

## ADN L4 Agent (`dashboard/app/l4-agent/page.tsx`)

**Purpose:** Autonomous Driving Network Level 4 operations — auto-approves safe actions, requires human approval for risky ones. All actions are persisted to PostgreSQL (`agent_actions` table) and playbooks execute real backend operations.

### Auto-Approve Logic (`classifyAction`)
```typescript
function classifyAction(severity: string, type: string, confidence: number): boolean {
    // Returns true = needs human approval
    // Returns false = auto-approved
    if (type === 'remediation' && (severity === 'critical' || severity === 'warning'))
        return true;  // Human must approve
    return false;     // Auto-approve info/predictions
}
```
- **Auto-approved:** info actions, predictions (any confidence level)
- **Requires human approval:** critical/warning remediations

### Real Playbook Execution (via POST /actions/{id}/execute)
| Playbook ID | What It Really Does |
|-------------|-------------------|
| `pb-model-retrain` | POSTs to ai-service:8001/models/reload — force-reloads all 3 ML models from disk |
| `pb-anomaly-triage` | Queries recent anomalies, classifies by severity bands, cross-references correlations for root cause analysis |
| `pb-revenue-protect` | Queries high-severity revenue anomalies, extracts subscriber IDs/operators, computes total revenue at risk |
| `pb-sla-breach` | Reads current SLA score + explanation features, identifies which KPIs exceed thresholds |
| `pb-capacity-scale` | Computes real capacity metrics from KPI history, calculates headroom percentages |

All execution results stored in `execution_log` JSONB column of `agent_actions` table.

### Action Lifecycle
1. `generateActions()` creates actions from live platform data → POST /actions (persisted)
2. On page load: GET /actions restores persisted actions (survive refresh)
3. Approve: PATCH /actions/{id} → POST /actions/{id}/execute (real backend work)
4. Reject: PATCH /actions/{id} status='rejected'

### Three Tabs
1. **Agent Chat** — Conversation with Qwen2.5:7b via Ollama
2. **Actions** — Pending (human approval buttons) + auto-approved list
3. **Live Monitor** — MiniSparkline charts + DonutChart + system metrics

### Notification Toasts
- Clickable toast notifications — clicking warning/danger toast switches to Actions tab
- X button to dismiss individual toasts
- Status: `'pending' | 'approved' | 'executed' | 'rejected' | 'auto_approved'`

### Auth Pattern (CRITICAL)
The L4 agent is a client component and cannot read httpOnly cookies directly.
**Solution:** All platform data fetched through `/api/platform-data` SSR proxy route.
```typescript
// Client calls: /api/platform-data (GET, POST, PATCH)
// API route (server): reads auth_token cookie → forwards to :8000 with Authorization: Bearer
// POST supports _action: "create" | "execute" for action management
// PATCH supports action status updates
```

---

## Next.js API Routes (`dashboard/app/api/`)

| Route | Purpose |
|-------|---------|
| `/api/login` | Auth proxy (login/signup/oauth callback) |
| `/api/logout` | Clear auth cookie |
| `/api/platform-data` | SSR proxy — reads auth_token cookie, fetches all :8000 endpoints |
| `/api/model-metrics` | Static real ML metrics from notebook evaluation |

### `/api/platform-data` Pattern
```typescript
import { cookies } from "next/headers";
// GET: Fetches 9 endpoints in parallel:
//   /sla-risk, /sla-risk/history, /anomalies, /revenue-anomalies, /correlation,
//   /pipeline-runs, /anomaly-stats, /kpi-summary, /actions
// POST: _action="create" → POST /actions, _action="execute" → POST /actions/{id}/execute
// PATCH: Updates action status via PATCH /actions/{action_id}
// All with Authorization: Bearer <token> header from httpOnly cookie
```

---

## Model Evaluation Page (`dashboard/app/model-evaluation/page.tsx`)

Fetches real metrics from `/api/model-metrics`. Shows:
- Info banner: "All metrics are real values computed from trained models in notebooks/"
- **Regression models:** R², MAE, RMSE, MSE bars + FeatureImportanceChart
- **Anomaly models:** Precision, Recall, F1, ROC-AUC + ConfusionMatrix visualization
- RadarChart for overall model comparison
- All charts: custom SVG-based (no extra chart library dependencies)

Custom chart components (all SVG, no dependencies):
- `Sparkline` — mini line trend
- `MetricBar` — horizontal progress bar
- `ConfusionMatrix` — 2×2 heatmap grid
- `RadarChart` — pentagon radar for model comparison
- `FeatureImportanceChart` — horizontal bar chart

---

## Components

### `dashboard/components/AICopilotIcon.tsx`
Floating Action Button (bottom-right corner) — NeXo Agent launcher.
- Opens menu with links to: L4 Agent Chat, Model Evaluation, Intelligence Hub
- **Key architecture:** menu and button are siblings (not nested) to avoid click propagation issues
- `useRef + mousedown` listener for outside-click close
- Rendered in `dashboard/app/ClientLayout.tsx`

### `dashboard/components/TopNav.tsx`
Top navigation bar with all page links + L4 Agent CTA button.
- Nav items include: Overview, Anomalies, SLA Risk, Correlations, Intelligence, Forecast, Topology, Capacity, DWH, Pipelines, Health, **Models** (new)
- L4 Agent as special animated CTA button (separate from main nav items)

---

## CSS Architecture (`dashboard/app/globals.css`)

### L4 Agent Tab Layout
```css
/* Tabs always visible (not mobile-only) */
.l4-tabs { display: flex; flex-shrink: 0; }
/* Panels hidden by default, shown with active class */
.l4-chat-panel { display: none; }
.l4-actions-panel { display: none; width: 100%; }
.l4-panel-active { display: flex !important; }
```
**Do NOT** add `display: none` to `.l4-tabs` — it was previously hidden (mobile-only) which broke desktop navigation.

### AI Copilot FAB Classes
- `.ai-copilot-fab` — circular gradient button
- `.ai-copilot-menu` — popup menu container
- `.ai-copilot-pulse` — animated ring effect
- `.ai-copilot-menu-header`, `.ai-copilot-menu-item`, `.ai-copilot-menu-footer`

### Toast Notification Classes
- `.l4-toast-container` — fixed position container
- `.l4-toast` — base toast
- `.l4-toast-warning`, `.l4-toast-danger`, `.l4-toast-info`

### Model Evaluation Classes
- `.me-model-card`, `.me-health-item`, `.me-metric-label`, `.me-metric-value`

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

8 tables: `users`, `pipeline_runs`, `dataset_registry`, `model_registry`, `sla_risk_scores`, `anomalies`, `revenue_anomalies`, `correlation_insights`, `agent_actions`

- `pipeline_runs` is the parent table (FK from 5 others via `run_id`)
- `users` table supports local + Google + GitHub OAuth
- JSONB used for ML explanation fields
- `agent_actions` stores L4 Agent actions with full audit trail (status, execution_log JSONB, resolved_at/by)

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
| GET | /anomaly-stats?limit=N | Per-run anomaly counts + avg severity (joins pipeline_runs, anomalies, revenue_anomalies) |
| GET | /kpi-summary?limit=N | Real KPI aggregates from sla_risk_scores.explanation JSONB |
| GET | /actions?limit=N&status=X | List L4 Agent actions (filterable by status) |
| POST | /actions | Create action (from L4 agent, idempotent via ON CONFLICT) |
| PATCH | /actions/{action_id} | Update action status (approve/reject), sets resolved_at/by |
| POST | /actions/{action_id}/execute | Execute playbook — real backend operations (see L4 Agent section) |

### auth-service (:8002)
| Method | Path | Purpose |
|--------|------|---------|
| POST | /auth/signup | Register (email/password) |
| POST | /auth/login | Login (returns JWT) |
| GET | /auth/me | Current user profile (JWT) |
| GET | /auth/google | Google OAuth redirect |
| GET | /auth/github | GitHub OAuth redirect |

### ai-service (:8001) — internal, called by pipeline-worker and api-gateway
| Method | Path | Purpose |
|--------|------|---------|
| POST | /infer/sla-risk | SLA risk prediction |
| POST | /infer/anomaly | OSS anomaly detection |
| POST | /infer/revenue-anomaly | BSS revenue anomaly detection |
| POST | /models/reload | Force model hot-reload from disk (used by pb-model-retrain playbook) |

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
  app/
    l4-agent/page.tsx   # ADN L4 autonomous agent (REWRITTEN)
    model-evaluation/page.tsx  # Real ML metrics page (NEW)
    api/platform-data/route.ts # SSR auth proxy (NEW)
    api/model-metrics/route.ts # Real metrics API (NEW)
  components/
    AICopilotIcon.tsx   # Floating AI agent launcher (REWRITTEN)
    TopNav.tsx          # Navigation bar
notebooks/              # Jupyter notebooks for model training + evaluation
  models/*.joblib       # Trained model files
  data/*.npz            # Training/test data
docs/                   # Architecture, data model, deployment guides
TT_data/                # CONFIDENTIAL — real Tunisie Telecom data (gitignored)
  BSS/                  #   500K subscriber CEM profiles (26 features, March 2026)
infra/monitoring/       # SigNoz + OTel Collector configs (replaces Prometheus + Grafana)
diagrams/               # Architecture diagram exports
docker-compose.yml      # 10-service orchestration
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
- `docs/data-model/bss-real-data-analysis.md` — BSS real data analysis, CEM architecture, DL model plan, rolling window engine design

---

## Current Status & Roadmap

### Completed Phases
- [x] **Phase 1:** Core infrastructure (PostgreSQL, MinIO, FastAPI services, Docker Compose)
- [x] **Phase 2:** Real ML models (GBR + IsolationForest), 22-step pipeline, 7 API endpoints
- [x] **Phase 3:** Full alignment with reference spec, professional docs, dashboard
- [x] **Phase 4:** Auth service (JWT + OAuth), dashboard auth integration, CI/CD pipeline
- [x] **Phase 5:** ADN L4 Agent (auto-approve logic, 3 tabs, toasts), Model Evaluation page (real metrics), AI Copilot FAB, SSR auth proxy, Ollama Qwen2.5:7b integration
- [x] **Phase 5.5:** Dashboard containerized, all data made real (Forecast uses anomaly-stats, Capacity uses KPI summary from JSONB), L4 Agent playbooks execute real backend operations (model reload, anomaly triage, revenue protection, SLA breach analysis, capacity scaling), `agent_actions` table for persistence, 6 new API endpoints, ai-service /models/reload
- [x] **Phase 1 Backend Restructuring (2026-04-25):** All services modularized — pipeline-worker (config/db/storage/generators/processors/analytics/inference/pipeline modules, 23 tests), api-gateway (9 routers + auth/config/db, 1 test), ai-service (model_cache + 4 routers, 2 tests). `ruff check services/` = 0 errors. Docker builds pass.

### Remaining Work
- [ ] **Phase 3.5:** Real TT data ingestion + Rolling Window Engine (BSS 500K loaded, waiting for OSS) — CEM-oriented subscriber profiling
- [ ] **Phase 4.5:** Model v3.0 — CEM Experience Score (GBR), Experience Anomaly (Autoencoder), RAT Underservice (XGBoost), retrained on real data
- [ ] **Phase DL:** Temporal models — LSTM Churn Trajectory, Granger Causality in O+B correlation (requires accumulated window history)
- [ ] **Phase 6:** HCS deployment evidence (OBS/RDS/ECS mapping, screenshots)
- [ ] **Final:** Report writing, presentation preparation

### Real TT Data Status
- **BSS:** ✅ Received — `TT_data/BSS/request_data_1month_500K.csv` (500K subscribers, 26 features, March 2026)
- **OSS:** ⏳ Waiting — blocked. O+B convergence and model retraining depend on this.
- **Data orientation:** CEM subscriber profiling (NOT billing/revenue)
- **Confidentiality:** TT_data/ is in .gitignore — NEVER commit real data
- **Architecture doc:** `docs/data-model/bss-real-data-analysis.md` — full feature analysis + DL plan

### Cloud Portability (HCS Mapping)
| Local | Huawei Cloud Stack |
|-------|-------------------|
| MinIO | OBS (Object Storage) |
| PostgreSQL | RDS |
| Docker containers | ECS |
| Ollama | ModelArts / EI |

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
3. API calls go through `dashboard/lib/` utilities or `/api/*` routes
4. Auth middleware in `dashboard/middleware.ts`
5. Client pages needing auth data → use `/api/platform-data` SSR proxy (NOT direct :8000 calls)

### Build issues
- If you get "Cannot find module './948.js'" or similar: `rm -rf dashboard/.next && npx next build`
- This happens when `.next` cache is partially stale
- **Recharts MUST stay at v2.x** (pinned `2.15.3`). Recharts v3.x is a full TypeScript rewrite that causes React error #310 ("Objects are not valid as React child") because its internal Tooltip/Cell/Legend components use `useMemo` in ways that produce non-serializable objects through React's reconciliation pipeline. Do NOT upgrade to recharts 3.x.

---

## Audit Log (2026-04-15)

Full codebase audit performed. Key fixes:

| Area | Issue | Fix |
|------|-------|-----|
| Dashboard | React error #310 at runtime (Recharts v3 incompatibility) | Downgraded recharts 3.8.1 -> 2.15.3 (pinned) |
| Dashboard | `AnomalyTimeline` passed Date objects through useMemo/JSX | Changed `timestamp` field from `Date` to ISO string |
| Dashboard | Dead `Nav.tsx` sidebar component (replaced by `TopNav.tsx`) | Deleted component + 96 lines of dead `.nav` CSS |
| ai-service | Misplaced docstring on `infer_revenue_anomaly` (string after code) | Moved docstring to first statement position |
| pipeline-worker | Failed pipeline runs stuck in `status='started'` forever | Added try/except in `run_once()` that marks failed runs with `status='failed'` and `error_message` |

All 25 dashboard routes compile. Zero TypeScript errors. Zero Python syntax errors.

---

## Important Notes

- Pipeline worker runs on 2-minute cycles in daemon mode
- All services use the same Docker network (internal bridge)
- OAuth credentials are optional (empty by default for local dev)
- Data is synthetic (demo mode) until real TT data is integrated, but all dashboard pages now consume real pipeline output (no hardcoded/fake values)
- **Real BSS data received** (500K subscribers, 26 features) — stored in `TT_data/BSS/` (gitignored, CONFIDENTIAL)
- **Waiting for OSS data** before starting Phase 3.5 implementation — O+B convergence is the backbone
- **DL stack planned:** PyTorch 2.x for Autoencoder (experience anomaly) + LSTM (churn trajectory). GBR stays for interpretable CEM scoring.
- **Rolling window engine** will replace synthetic `generate_bss()` — simulates real-time from static 500K snapshot
- Topology page uses demo structure (real severity overlay) — user will integrate real network topology later
- Ruff must pass before commits (enforced in CI)
- **Ollama models stored on D:/ drive** (C: drive is full): `OLLAMA_MODELS=/mnt/d/ollama-models`
- **Model: Qwen2.5:7b** (Q4_K_M, ~4.7GB) — default for L4 Agent chat
- **No extra chart dependencies** — all charts are custom SVG components (Sparkline, DonutChart, RadarChart, FeatureImportanceChart, ConfusionMatrix)
- **`pipeline_runner.py`** at repo root is an alternative pipeline runner used only by `Dockerfile.notebooks` (Jupyter container). It runs a simplified 3-step pipeline, NOT the full 22-step one. The real pipeline is `services/pipeline-worker/worker/__main__.py`

## DATA CONFIDENTIALITY — CRITICAL

**TT_data/ contains real Tunisie Telecom subscriber and network data. This is STRICTLY CONFIDENTIAL.**

- NEVER commit any data from TT_data/ to git
- NEVER export, share, or upload the data anywhere
- All processing must stay local in your system
- The data is used only for model training and inference within this project
- TT_data/ is already in .gitignore — DO NOT remove it

---

## NeXo — Project Update (April 2026)

### Real Data Received:
| Month | BSS (Subscriber) | OSS (Cell) |
|-------|-----------------|-----------|
| **February 2026** | 468,077 ✅ real | coming soon ✅ real |
| **March 2026** | 500,000 ✅ real | coming soon ✅ real |
| **April 2026** | simulated | simulated |
| **May 2026** | simulated | simulated |
| **June 2026** | simulated (training) | simulated (training) |

### Data Files:
```
TT_data/BSS/
  smartcare_cem_feb.csv     (February 2026 — 468K subscribers, REAL)
  smartcare_cem_mars.csv    (March 2026 — 500K subscribers, REAL)
  smartcare_cem_jan.csv     (January 2026 — 500K subscribers, BOOTSTRAP SIMULATED)
  smartcare_cem_avr.csv     (April 2026 — 500K subscribers, BOOTSTRAP SIMULATED)
  smartcare_cem_mai.csv     (May 2026 — 500K subscribers, BOOTSTRAP SIMULATED)

TT_data/OSS/
  (coming soon — real OSS cell KPIs for Feb + March)
```

### Bootstrap Simulation Method (BSS Simulated Months)
All simulated BSS files generated via **stratified bootstrap with log-normal perturbation** from real Feb+Mar data:
1. **Base sampling**: Sample 500K rows with replacement from 968K real rows. Preserves all categorical joint distributions and variable correlations exactly.
2. **Numerical perturbation**: Multiply numerical columns by `exp(N(0, 0.06))` — prevents exact duplicates while keeping distributions realistic.
3. **Month drift applied**:
   - **Jan**: DOU ×0.88, 5G traffic ×0.65, 8% 5G→4G demotion, silent users -3%
   - **Apr**: DOU ×1.18, 5G traffic ×1.35, 12% 4G→5G promotion per unit of 5G factor, silent users +4%
   - **May**: DOU ×1.35, 5G traffic ×1.65, 12% 4G→5G promotion per unit of 5G factor, silent users +8%
4. **Identity replacement**: New IMSI (`60502` + 10 random digits) and TAC (15 random digits) for every record. Original identities never appear.
5. **DOU guard**: If traffic sum exceeds 1.5× DOU, DOU is raised to match.

Script: `services/data-ingest/generate_bss_months.py`

### Data Strategy:
- **BSS**: 2 real months (Feb + Mar) + 3 simulated (Jan + Apr + May)
- **OSS**: 2 real months (Feb + Mar) + simulated (pending real data arrival)
- Simulation maintains same area distribution + realistic temporal drift
- Churn emergence patterns in simulated months

### NeXo Architecture — Multi-Agent System:
Based on Huawei ADN Level 4 + Cloud-Network Convergence:

```
┌─────────────────────────────────────────────────────┐
│      NeXo — TT Intelligence Agent       │
│   (Huawei ADN + Cloud-Network Style)  │
├─────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────┐ │
│  │   Orchestrator (LLM-powered)       │ │
│  │   Intent → Agent Dispatch        │ │
│  └───────┬──────────────┬─────────────┘ │
│          │              │             │
│  ┌──────┴─────┐ ┌───┴────┐ ┌────┴────┐  │
│  │  CEM Agent │ │Network │ │ Action  │  │
│  │ (Mate)    │ │ Agent  │ │ Agent   │  │
│  │            │ │(Spirit)│ │(Spirit)│  │
│  └──────┬─────┘ └───┬────┘ └───┬────┘  │
│         │           │          │        │
│  ┌─────┴───────────┴──────────┴────────┐│
│  │   OSS+BSS CONVERGENCE ENGINE       ││
│  │   (Area-level join)              ││
│  └─────────────────────────────────┘│
└──────────────────────────────────────┘
```

### Agent Roles:
| Agent | Role | Purpose |
|-------|------|---------|
| **CEMAgent** | Experience Analysis | Subscriber CEM scoring (0-1), NPS prediction |
| **NetworkAgent** | Network Monitoring | Cell KPI monitoring, capacity analysis |
| **ActionAgent** | Remediation | Auto-execution, playbook triggers |
| **Orchestrator** | Intent Routing | LLM-powered task understanding |

### OSS+BSS Convergence:
The backbone of this project — correlates subscriber experience with network performance:

```
BSS (subscriber level)          OSS (cell level)
   imsi ─────────────────► No direct link
   area │                  area │
        │                       │
        ▼                       ▼
   ┌──────────────────────────────────┐
   │   CONVERGENCE at AREA level        │
   │   - Map subscriber to cells     │
   │   - Network quality → CEM      │
   │   - RAT underservice detection  │
   │   - Anomaly correlation        │
   └──────────────────────────────────┘
```

### Implementation Timeline:
| Phase | Content | Duration |
|-------|---------|----------|
| Phase 1 | Data loading + BSS features + CEM scoring | Weeks 1-3 |
| Phase 2 | OSS simulation + convergence engine | Weeks 4-6 |
| Phase 3 | Multi-agent system + Ollama integration | Weeks 7-9 |
| Phase 4 | Real-time + dashboard + polish | Weeks 10-12 |

### Hardware Available:
- CPU: Ryzen 5 5600H (6 cores, 3.3GHz)
- RAM: 24GB (19.9GB usable)
- GPU: RTX 3050 4GB VRAM (for PyTorch training)
- Disk: ~1000GB available on D:/

### LLM: Qwen2.5:7b via Ollama
Model size: 7B parameters (~4.7GB)
Used for: Intent classification, agent reasoning, natural language queries

### Key Decisions (Confirmed):
- Q1: Model — Qwen2.5:7b ✅
- Q2: OSS — Full simulation (cell-focused) ✅
- Q3: Agents — 3 agents (CEM + Network + Action) ✅
- Q4: Real-time — 30-second windows ✅
- Q5: Deadline — July 1st, 2026 ✅

### Client:
TT — Tunisie Telecom (Tunisia)
Focus: CEM subscriber profiling + OSS+BSS convergence

---

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

---

## NeXo — Complete Outputs & Deliverables (2026-04-27)

### 1. Data Layer
| Deliverable | Description | Status |
|---|---|---|
| BSS Subscribers | 970K real subscribers (Feb 468K + Mar 500K) | ✅ Ready |
| OSS Cell KPIs | Cell-focused network data | 🔜 Coming |
| Simulated Months | Apr/May/Jun with realistic drift + churn emergence | 📋 Planned |
| Rolling Window Engine | Stratified batch sampler per 2-min cycle | 📋 Planned |

### 2. Target Database Schema (v3.0)
| Table | Purpose | Key Columns |
|---|---|---|
| `bss_subscribers` | Raw subscriber CEM data | 26 features + month_year |
| `oss_cells` | Network KPIs per cell | ~10 cols (tbd on OSS arrival) |
| `cem_scores` | Computed CEM scores | imsi, score, features, timestamp |
| `experience_anomalies` | AE-detected anomalies | imsi, anomaly_score, timestamp |
| `churn_trajectory` | LSTM predictions | imsi, churn_prob, trajectory |
| `rat_underservice` | XGBoost predictions | imsi, underservice_risk, gap |
| `ob_convergence` | OSS+BSS correlations | area, correlation, p_value |
| `agent_actions` | L4 action audit trail | status, execution_log JSONB |

### 3. ML Models v3.0 (target)
| Model | Algorithm | Key Features | Output |
|---|---|---|---|
| CEM Score | GBR + SHAP | attach_rates, usage, RAT_gap, area_oss | 0-1 score + explainability |
| RAT Underservice | XGBoost | generation vs highest_rat, device tier | underservice_risk |
| Experience Anomaly | PyTorch Autoencoder | 26 CEM features + OSS | anomaly_score |
| Churn Trajectory | LSTM (PyTorch) | Rolling window sequences | churn_prob + trajectory |

**Target metrics:** CEM Score R² > 0.90 | RAT F1 > 0.85 | Anomaly ROC-AUC > 0.90 | Churn AUC > 0.85

### 4. Planned API Endpoints (Phase 3.5+)
| Service | Endpoint | Purpose |
|---|---|---|
| api-gateway | GET /cem-score/{imsi} | Single subscriber CEM |
| api-gateway | POST /cem-score/batch | Bulk scoring |
| api-gateway | GET /rat-underservice | Device vs actual RAT gap |
| api-gateway | GET /convergence/area | Area-level OSS+BSS correlations |
| api-gateway | GET /convergence/degradation | OSS degradation → CEM impact |
| ai-service | POST /infer/autoencoder | Experience anomaly detection |
| ai-service | POST /infer/lstm-churn | Temporal churn prediction |

### 5. Planned Dashboard Pages (Phase 3.5+)
| Page | Data Source |
|---|---|
| `/cem-scores` | Real CEM distribution heatmap |
| `/convergence` | OSS degradation + CEM impact |
| `/churn-trajectory` | LSTM predictions over time |
| `/rat-underservice` | Subscribers underserved by RAT |
| `/anomalies` | AE-detected experience anomalies (replaces IF-based) |

### 6. Key Metrics Expected
| Model | Metric | Target |
|---|---|---|
| CEM Score (GBR) | R² | > 0.90 |
| RAT Underservice (XGBoost) | F1 | > 0.85 |
| Experience Anomaly (AE) | ROC-AUC | > 0.90 |
| Churn Trajectory (LSTM) | AUC | > 0.85 |
| O+B Convergence (Granger) | p-value | < 0.05 |
