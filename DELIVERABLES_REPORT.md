# Telecom NeXoligence Platform — Full Deliverables Report

> **Project:** Cloud-Native AI Operations Agent for CEM-CVM Intelligence (HCS-Ready)  
> **Author:** Souhayl Guenichi — ESPRIT / Huawei Tunisia  
> **Date:** 2026-04-27 | Phase 5.5 Complete + Phase 1 Backend Restructuring  
> **Client:** Tunisie Telecom (TT)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Software & System Deliverables](#2-software--system-deliverables)
3. [Machine Learning & AI Deliverables](#3-machine-learning--ai-deliverables)
4. [Data & Pipeline Deliverables](#4-data--pipeline-deliverables)
5. [Frontend & Dashboard Deliverables](#5-frontend--dashboard-deliverables)
6. [Documentation Deliverables](#6-documentation-deliverables)
7. [Academic & Defense Deliverables](#7-academic--defense-deliverables)
8. [Infrastructure & DevOps Deliverables](#8-infrastructure--devops-deliverables)
9. [Observability Deliverables](#9-observability-deliverables)
10. [Planned Future Deliverables](#10-planned-future-deliverables)
11. [Deliverables Matrix](#11-deliverables-matrix)

---

## 1. Executive Summary

This report inventories every output, artifact, and deliverable produced by the **Telecom NeXoligence Platform** — a cloud-native AI Operations Agent that bridges OSS network KPIs and BSS subscriber data for Huawei's CEM-CVM convergence strategy. The platform is designed as a **Huawei Cloud Stack (HCS)-ready** solution with ADN Level 4 autonomous operations.

**Total Deliverable Categories:** 11  
**Total Artifacts:** 80+ files, 15+ services, 3 ML models, 15+ dashboard pages

---

## 2. Software & System Deliverables

### 2.1 Backend Microservices (6 Services)

| Service | Port | Purpose | Key Files | Status |
|---------|------|---------|-----------|--------|
| **API Gateway** | `8000` | Central REST API — 15+ endpoints, JWT-protected, direct SQL queries | `services/api-gateway/main.py`, `routers/`, `auth.py`, `db.py` | ✅ Complete |
| **AI Service** | `8001` | ML inference engine — 3 models with hot-reload (30s TTL cache) | `services/ai-service/main.py`, `model_cache.py`, `bootstrap_models.py`, `routers/` | ✅ Complete |
| **Auth Service** | `8002` | Authentication — local (bcrypt) + Google OAuth + GitHub OAuth | `services/auth-service/main.py` | ✅ Complete |
| **Pipeline Worker** | — | 22-step ETL/ML pipeline daemon (2-min cycles) | `services/pipeline-worker/worker/__main__.py`, 23 tests | ✅ Complete |
| **Agent Service** | `8003` | Multi-agent orchestrator (CEM + Network + Action agents) | `services/agent-service/main.py`, `orchestrator.py`, `agents/` | ✅ Complete |
| **Data Ingest** | — | Real TT data ingestion + OSS simulation + feature computation | `services/data-ingest/ingest_bss.py`, `simulate_oss.py`, `compute_features.py` | 🔄 Partial |

### 2.2 REST API Endpoints (15+ Endpoints)

**API Gateway (:8000)** — All protected by JWT Bearer except `/health`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service liveness check |
| GET | `/sla-risk` | Latest SLA risk score + feature explanation |
| GET | `/sla-risk/history` | Historical SLA scores (limit 1-200) |
| GET | `/anomalies` | OSS anomaly records with severity |
| GET | `/revenue-anomalies` | BSS revenue anomaly records |
| GET | `/correlation` | OSS-BSS Pearson + Spearman correlations |
| GET | `/pipeline-runs` | Pipeline execution history |
| GET | `/anomaly-stats` | Per-run anomaly counts + avg severity |
| GET | `/kpi-summary` | KPI aggregates from SLA explanation JSONB |
| GET | `/infra-stats` | DB size, row counts, table sizes |
| GET | `/platform-stats` | Aggregated stats for capacity/topology |
| GET | `/actions` | L4 Agent actions (filterable by status) |
| POST | `/actions` | Create action (idempotent) |
| PATCH | `/actions/{id}` | Update action status (approve/reject) |
| POST | `/actions/{id}/execute` | Execute playbook — real backend operations |

**Auth Service (:8002)**:
- `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`
- `GET /auth/google`, `GET /auth/google/callback`
- `GET /auth/github`, `GET /auth/github/callback`

**AI Service (:8001)** — Internal:
- `POST /infer/sla-risk`, `POST /infer/anomaly`, `POST /infer/revenue-anomaly`
- `POST /models/reload` — Force model hot-reload

### 2.3 Next.js API Routes (Dashboard Backend)

| Route | Purpose |
|-------|---------|
| `/api/login` | Auth proxy (login/signup/OAuth callback) |
| `/api/logout` | Clear auth cookie |
| `/api/platform-data` | SSR proxy — reads auth_token, fetches all :8000 endpoints |
| `/api/model-metrics` | Static real ML metrics from notebook evaluation |

---

## 3. Machine Learning & AI Deliverables

### 3.1 Trained Models (v2.0 — Synthetic Data)

| Model | Algorithm | File | Metrics | Status |
|-------|-----------|------|---------|--------|
| **SLA Risk Scorer** | GradientBoostingRegressor | `notebooks/models/sla_risk_model.joblib` | R²=0.9791, MAE=0.0185, RMSE=0.0272 | ✅ Trained |
| **OSS Anomaly Detector** | IsolationForest | `notebooks/models/anomaly_model.joblib` | Precision=0.78, Recall=1.0, F1=0.88, ROC-AUC=1.0 | ✅ Trained |
| **BSS Revenue Anomaly** | IsolationForest | `notebooks/models/revenue_anomaly_model.joblib` | Precision=1.0, Recall=1.0, F1=1.0, ROC-AUC=1.0 | ✅ Trained |

### 3.2 Jupyter Notebooks

| Notebook | Purpose | Output |
|----------|---------|--------|
| `01_data_preparation_eda.ipynb` | Data generation, EDA, feature engineering | Sample CSVs, distribution PNGs, correlation matrix |
| `02_sla_risk_model.ipynb` | SLA Risk model training (GradientBoosting) | `sla_risk_model.joblib`, evaluation metrics, feature importance chart |
| `03_anomaly_detection_models.ipynb` | OSS/BSS anomaly detection training | `anomaly_model.joblib`, `revenue_anomaly_model.joblib`, confusion matrices, PR curves |

### 3.3 Training Data Artifacts

| File | Description |
|------|-------------|
| `notebooks/data/sla_risk_training.npz` | Training arrays for SLA risk model |
| `notebooks/data/oss_anomaly_training.npz` | Training arrays for OSS anomaly model |
| `notebooks/data/bss_revenue_anomaly_training.npz` | Training arrays for BSS anomaly model |
| `notebooks/data/oss_sample.csv` | Sample OSS dataset |
| `notebooks/data/bss_sample.csv` | Sample BSS dataset |

### 3.4 Visualization Outputs (from Notebooks)

- `bss_anomaly_boxplots.png` — BSS anomaly feature boxplots
- `bss_anomaly_distributions.png` — BSS anomaly distributions
- `bss_anomaly_evaluation.png` — BSS anomaly evaluation chart
- `bss_anomaly_feature_space.png` — BSS feature space visualization
- `bss_anomaly_pr_curve.png` — BSS precision-recall curve
- `bss_distributions.png` — BSS data distributions
- `oss_anomaly_boxplots.png` — OSS anomaly boxplots
- `oss_anomaly_evaluation.png` — OSS evaluation chart
- `oss_anomaly_feature_space.png` — OSS feature space
- `oss_anomaly_pairplot.png` — OSS pairwise feature plots
- `oss_anomaly_pr_curve.png` — OSS precision-recall curve
- `oss_distributions.png` — OSS data distributions
- `oss_bss_correlation_matrix.png` — OSS-BSS correlation heatmap
- `oss_timeseries_faults.png` — OSS time series with fault injection
- `sla_risk_distribution.png` — SLA risk score distribution

---

## 4. Data & Pipeline Deliverables

### 4.1 Data Pipeline (22 Steps)

The pipeline worker executes every 2 minutes:

1. Insert `pipeline_runs` record
2. Ensure MinIO buckets exist (raw, processed, curated)
3. Generate 200 synthetic OSS records with fault injection
4. Generate 200 synthetic BSS records with correlated dips
5. Upload OSS raw → `s3://raw/oss/{date}/{run_id}.json`
6. Upload BSS raw → `s3://raw/bss/{date}/{run_id}.json`
7. Register raw datasets in `dataset_registry`
8. Process OSS (severity, QoS score, load factor)
9. Process BSS (ARPU category, data intensity, churn bucket)
10. Register processed datasets
11. Compute 9 aggregate KPI features
12. Call `/infer/sla-risk` → SLA score
13. Call `/infer/anomaly` → OSS anomaly labels
14. Call `/infer/revenue-anomaly` → BSS anomaly labels
15. Compute Pearson + Spearman correlations (5 pairs × 2 methods = 10 values)
16. Build curated dataset → `s3://curated/joined/{date}/{run_id}_curated.json`
17. Register curated dataset
18. Persist SLA risk score → `sla_risk_scores`
19. Persist OSS anomalies → `anomalies`
20. Persist BSS anomalies → `revenue_anomalies`
21. Register models in `model_registry`
22. Persist correlations + mark pipeline succeeded

### 4.2 Database Schema (PostgreSQL 16 — 9 Tables)

| Table | Purpose | Rows/Run |
|-------|---------|----------|
| `users` | Auth accounts (local + OAuth) | N/A |
| `pipeline_runs` | Run lifecycle metadata | 1 |
| `dataset_registry` | MinIO object tracking | 5 |
| `model_registry` | Model version tracking | 3 |
| `sla_risk_scores` | GBR risk score + explanation JSONB | 1 |
| `anomalies` | Flagged OSS anomalies | ~10 |
| `revenue_anomalies` | Flagged BSS anomalies | ~10 |
| `correlation_insights` | Pearson/Spearman correlations | 10 |
| `agent_actions` | L4 Agent action audit trail | varies |

**Schema file:** `docs/db/schema.sql`

### 4.3 Data Lake (MinIO — 3-Layer)

| Layer | Bucket | Content |
|-------|--------|---------|
| Raw | `raw` | Unprocessed OSS/BSS JSON records |
| Processed | `processed` | Enriched records (severity, QoS, ARPU) |
| Curated | `curated` | Joined OSS+BSS+AI output per run |

### 4.4 Real Data Assets (Confidential — TT Data)

| File | Description | Status |
|------|-------------|--------|
| `TT_data/BSS/smartcare_Acem_feb.csv` | February 2026 — 468,077 real subscribers, 26 features | ✅ Received |
| `TT_data/BSS/request_data_1month_500K.csv` | March 2026 — 500,000 real subscribers, 26 features | ✅ Received |
| `TT_data/OSS/` | Real OSS cell KPIs (Feb + Mar) | ⏳ Waiting |

---

## 5. Frontend & Dashboard Deliverables

### 5.1 Dashboard Application (Next.js 14)

**Technology:** Next.js 14.2.5, React 18.3.1, TypeScript 5.4.5, Recharts 2.15.3  
**Port:** 3001  
**Output Mode:** Standalone (Docker `node server.js`)

### 5.2 Dashboard Pages (17 Routes)

| Route | Type | Description | Status |
|-------|------|-------------|--------|
| `/` (home) | Static | Landing/redirect | ✅ |
| `/overview` | SSR | Platform overview — SLA gauge, anomaly timeline, bar chart, SLA trend | ✅ |
| `/anomalies` | SSR | OSS/BSS anomaly browser with timeline and heatmap | ✅ |
| `/sla-risk` | SSR | SLA risk score, history chart, explanation details | ✅ |
| `/correlations` | SSR | OSS-BSS correlation heatmap explorer | ✅ |
| `/intelligence` | SSR | AI intelligence hub with root cause analysis | ✅ |
| `/predictive` | SSR | Forecast analytics from real anomaly-stats data | ✅ Real Data |
| `/capacity` | SSR | Capacity planning from real KPI features (JSONB queries) | ✅ Real Data |
| `/topology` | Static | Network topology (demo structure + real severity overlay) | ✅ Demo |
| `/data-warehouse` | SSR | Data lake explorer (dataset_registry) | ✅ |
| `/pipeline-runs` | SSR | Pipeline execution history and status | ✅ |
| `/ops-metrics` | SSR | Platform health — infra stats, DB size, table sizes | ✅ |
| `/model-evaluation` | Static | Real ML model metrics + custom SVG charts | ✅ |
| `/l4-agent` | CSR | ADN L4 Agent — chat, actions, live monitor (3 tabs) | ✅ Real Playbooks |
| `/login` | Static | Authentication (login/signup forms) | ✅ |
| `/signup` | Static | Registration page | ✅ |
| `/auth/callback` | Static | OAuth callback handler | ✅ |

### 5.3 Custom Chart Components (SVG — No External Dependencies)

| Component | Purpose |
|-----------|---------|
| `Sparkline` | Mini line trend charts |
| `MetricBar` | Horizontal progress bar |
| `ConfusionMatrix` | 2×2 heatmap grid |
| `RadarChart` | Pentagon radar for model comparison |
| `FeatureImportanceChart` | Horizontal bar chart |
| `RiskGauge` | SLA risk gauge with gradient bar |
| `AnomalyTimeline` | Chronological event stream |
| `AnomalyHeatmap` | Cell-based severity heatmap |
| `CorrelationHeatmap` | Correlation coefficient heatmap |
| `SlaChart` | Area chart for SLA risk history |

### 5.4 UI Components

| Component | Purpose |
|-----------|---------|
| `TopNav.tsx` | Top navigation with all page links |
| `ThemeProvider.tsx` / `ThemeToggle.tsx` | Dark/light mode with persistence |
| `CommandPalette.tsx` | Cmd+K fuzzy search |
| `AICopilotIcon.tsx` | Floating AI agent launcher (FAB) |
| `LiveIndicator.tsx` | "LIVE" badge with pulse dot |
| `AnimatedCard.tsx` / `AnimatedCounter.tsx` | Motion UI elements |
| `PageHero.tsx` / `PageHeroServer.tsx` | Page header components |
| `Sidebar.tsx` | Sidebar navigation |
| `TopHeader.tsx` | Header bar |
| `RefreshContext.tsx` | Real-time data refresh |

### 5.5 ADN L4 Autonomous Agent Features

| Feature | Description |
|---------|-------------|
| **Auto-Approve Logic** | Info/predictions auto-approved; critical/warning remediations need human approval |
| **5 Real Playbooks** | Model retrain, anomaly triage, revenue protect, SLA breach, capacity scale |
| **Agent Chat** | Conversation with Qwen2.5:7b via Ollama |
| **Actions Tab** | Pending + auto-approved action lists with approve/reject buttons |
| **Live Monitor** | Mini sparklines, donut chart, system metrics |
| **Notification Toasts** | Clickable toasts — click switches to Actions tab |
| **Action Persistence** | All actions stored in PostgreSQL `agent_actions` table with audit trail |

---

## 6. Documentation Deliverables

### 6.1 Technical Documentation

| Document | File | Description |
|----------|------|-------------|
| **Full Technical Documentation** | `docs/FULL_PROJECT_DOCUMENTATION.md` | 671-line master doc covering all services, APIs, models, schema |
| **Project Snapshot** | `docs/overview/project-snapshot.md` | Master state document |
| **Architecture v1** | `docs/architecture/architecture-v1.md` | C4 architecture diagrams |
| **ML Models Spec** | `docs/architecture/ml-models.md` | Complete ML model documentation (586 lines) |
| **Data Lake Architecture** | `docs/data-model/data-lake.md` | 3-layer data lake design |
| **PostgreSQL Schema** | `docs/data-model/postgres-schema.md` | ER diagram (Mermaid) |
| **BSS Real Data Analysis** | `docs/data-model/bss-real-data-analysis.md` | CEM architecture, DL model plan, rolling window engine |
| **Data Requirements** | `docs/data-request/data-requirements.md` | Expected TT data schema |
| **Local Deployment** | `docs/deployment/local-docker.md` | Local deployment guide |
| **Technical Foundations** | `docs/technical-foundations.md` | Core technical concepts |
| **Advanced AI Architecture** | `docs/advanced-ai-architecture.md` | Deep learning architecture plans |

### 6.2 Generated PDFs

| Document | File | Description |
|----------|------|-------------|
| **Complete Technical Reference** | `docs/complete-technical-reference.pdf` | Full technical reference |
| **Knowledge Base** | `docs/knowledge-base.pdf` | Academic reference (24 IEEE citations) |
| **Cloud Native Telecom Intelligence** | `docs/overview/cloud_Native_Telecom_Intelligence_Platform_with_AI_Operations_Agent.pdf` | Overview paper |
| **Telecom Cloud Infrastructure Report** | `docs/overview/telecom_cloud_infrastructure_report.pdf` | Infrastructure report |
| **Telecom Cloud Intelligence Explained** | `docs/telecom-cloud-intelligence-explained.pdf` | Explainer document |

### 6.3 Project Reports

| Document | File | Description |
|----------|------|-------------|
| **Dashboard Report** | `report/dashboard-report.md` | Dashboard development report |
| **Phase 4 Auth + CI/CD Report** | `report/phase4-auth-cicd-report.md` | Authentication and CI/CD implementation |
| **Supervisor Briefing** | `docs/supervisor-briefing-2026-04-15.md` | Status briefing for supervisor |
| **Supervisor Feedback Response** | `docs/supervisor-feedback-response.md` | Response to feedback |
| **Backend Transformation Plan** | `docs/superpowers/plans/2026-04-25-nexo-backend-transformation.md` | Backend restructuring plan |
| **Gantt Chart** | `report/gantt.html`, `report/gantt.md`, `report/gantt.py` | Project timeline |
| **Gantt PDF** | `report/gantt_pfe.pdf`, `report/gantt_pfe.png` | Gantt chart exports |
| **Journal de Bord** | `report/journal-de-bord.md` | Development log |
| **6th Week Progress Report** | `report/bilan-periodique-6eme-semaine.md` | Periodic progress |
| **Dokie Prompt** | `report/dokie-prompt.md` | AI assistant prompt |

---

## 7. Academic & Defense Deliverables

### 7.1 Final Defense Report (LaTeX — PFE/Final Project)

**Main file:** `final-defense-report/main.tex`

| Chapter | File | Content |
|---------|------|---------|
| Title Page | `chapters/00_titlepage.tex` | Project title, author, institution |
| Dedication | `chapters/00_dedication.tex` | Personal dedication |
| Acknowledgments | `chapters/00_acknowledgments.tex` | Thanks and credits |
| Abstract | `chapters/00_abstract.tex` | Executive summary |
| 1. Introduction | `chapters/01_introduction.tex` | Project context and objectives |
| 2. State of the Art | `chapters/02_state_of_art.tex` | Literature review, ADN, CEM-CVM |
| 3. Requirements Analysis | `chapters/03_requirements_analysis.tex` | Functional & non-functional requirements |
| 4. Architecture Design | `chapters/04_architecture_design.tex` | System architecture, C4 diagrams |
| 5. Implementation | `chapters/05_implementation.tex` | Development details |
| 6. ML Models | `chapters/06_ml_models.tex` | Model design, training, evaluation |
| 7. L4 Agent | `chapters/07_l4_agent.tex` | ADN Level 4 autonomous agent |
| 8. Deployment | `chapters/08_deployment.tex` | Cloud deployment, HCS mapping |
| 9. Results | `chapters/09_results.tex` | Evaluation results, metrics |
| 10. Conclusion | `chapters/10_conclusion.tex` | Summary, future work |
| Appendix A — API | `chapters/appendix_a_api.tex` | Full API reference |
| Appendix B — Schemas | `chapters/appendix_b_schemas.tex` | Database schema details |
| References | `references.bib` | Bibliography |

### 7.2 Periodic Report (LaTeX)

**Main file:** `report/main.tex`

| Chapter | File | Content |
|---------|------|---------|
| Front Matter | `chapters/00-frontmatter.tex` | Title, abstract |
| 1. Introduction | `chapters/01-introduction.tex` | Project intro |
| 2. Context | `chapters/02-context.tex` | Organizational context |
| 3. State of Art | `chapters/03-state-of-art.tex` | Literature review |
| 4. Architecture | `chapters/04-architecture.tex` | Technical architecture |
| 5. Data Strategy | `chapters/05-data-strategy.tex` | Data pipeline and lake |
| 6. AI Models | `chapters/06-ai-models.tex` | ML model details |
| 7. Implementation | `chapters/07-implementation.tex` | Code implementation |
| 8. Evaluation | `chapters/08-evaluation.tex` | Testing and validation |
| 9. Cloud Deployment | `chapters/09-cloud-deployment.tex` | HCS deployment |
| 10. Conclusion | `chapters/10-conclusion.tex` | Final thoughts |
| Appendix A — API | `chapters/appendix-a-api.tex` | API documentation |
| Appendix B — Schema | `chapters/appendix-b-schema.tex` | Database schema |
| References | `report/references.bib` | Bibliography |

### 7.3 Presentations

| Presentation | File | Description |
|--------------|------|-------------|
| **Project Overview** | `docs/Project's Overview.pptx` | Main project presentation |
| **Supervisor Meeting** | `report/supervisor-meeting.pptx` | Supervisor review presentation |
| **Supervisor Presentation** | `docs/overview/supervisor-presentation.md` | Presentation notes |
| **Speech Script** | `report/speech-script.tex` / `.pdf` | Defense speech |
| **First Document** | `report/first-doc.tex` / `.pdf` | Initial project document |

---

## 8. Infrastructure & DevOps Deliverables

### 8.1 Container Orchestration

| File | Description |
|------|-------------|
| `docker-compose.yml` | 10+ service orchestration (postgres, minio, auth, api, ai, pipeline, dashboard, notebooks, SigNoz stack) |
| `Dockerfile.notebooks` | Jupyter container with pipeline runner |
| `entrypoint.sh` | Container entrypoint script |

### 8.2 Service Dockerfiles

| Service | Dockerfile |
|---------|------------|
| API Gateway | `services/api-gateway/Dockerfile` |
| AI Service | `services/ai-service/Dockerfile` |
| Auth Service | `services/auth-service/Dockerfile` |
| Pipeline Worker | `services/pipeline-worker/Dockerfile` |
| Agent Service | `services/agent-service/Dockerfile` |
| Dashboard | `dashboard/Dockerfile` |

### 8.3 CI/CD Pipeline

| File | Description |
|------|-------------|
| `.github/workflows/ci-cd.yml` | 6-stage pipeline: lint → test → build → integration → security → deploy |
| Registry | `ghcr.io/souhayl1g/telecom-cloud-intelligence/*` |

### 8.4 Makefile Commands

| Command | Purpose |
|---------|---------|
| `make start-NeXo` | Start full stack with auto-pipeline + dashboard |
| `make start-dev` | Start stack without auto-pipeline |
| `make stop` / `make restart` | Service control |
| `make logs [service]` | View logs |
| `make svc-health` | Health checks |
| `make db-shell` / `make db-reset` / `make db-backup` | Database ops |
| `make build` / `make clean` | Maintenance |
| `make test-pipeline` / `make pipeline-force` | Pipeline testing |
| `make jupyter-token` | Get Jupyter access |
| `make open` / `make api-docs` | Quick access |

### 8.5 Configuration Files

| File | Purpose |
|------|---------|
| `.env.pipeline.example` | Pipeline environment template |
| `dashboard/.env.local` | Dashboard env vars |
| `dashboard/.env.example` | Dashboard env template |
| `dashboard/next.config.js` | Next.js build config |
| `dashboard/middleware.ts` | Auth middleware (redirect to login) |
| `dashboard/tsconfig.json` | TypeScript config |

---

## 9. Observability Deliverables

### 9.1 SigNoz Observability Stack

| Component | Config File | Purpose |
|-----------|-------------|---------|
| **OpenTelemetry Collector** | `infra/monitoring/otel-collector-config.yaml` | Receives traces/metrics/logs from services |
| **ClickHouse** | `infra/monitoring/clickhouse-config.xml`, `clickhouse-users.xml` | Metrics/traces storage |
| **SigNoz Query Service** | `infra/monitoring/signoz-prometheus.yml` | Query engine |
| **SigNoz Alertmanager** | `infra/monitoring/signoz-alertmanager.yml` | Alerting |
| **SigNoz Frontend** | `infra/monitoring/signoz-nginx.conf` | Web UI (:3301) |
| **SigNoz Init** | `infra/monitoring/signoz-init.sql` | Database init |

### 9.2 Legacy Prometheus + Grafana

| Component | Config File | Purpose |
|-----------|-------------|---------|
| **Prometheus** | `infra/monitoring/prometheus.yml` | Metrics scraping |
| **Grafana Datasource** | `infra/monitoring/grafana/provisioning/datasources/datasource.yml` | Prometheus connection |
| **Grafana Dashboard** | `infra/monitoring/grafana/provisioning/dashboards/json/ai-ops-overview.json` | Pre-configured dashboard |
| **Dashboards YAML** | `infra/monitoring/grafana/provisioning/dashboards/dashboards.yaml` | Dashboard provisioning |

### 9.3 Auto-Instrumented Metrics

All FastAPI services expose:
- `http_requests_total` — request count by method/path/status
- `http_request_duration_seconds` — latency histogram
- `http_request_size_bytes` — request body size
- `http_response_size_bytes` — response body size

---

## 10. Planned Future Deliverables

### 10.1 Phase 3.5 — Real TT Data Integration

| Deliverable | Description | Blocker |
|-------------|-------------|---------|
| Rolling Window Engine | Samples batches from 500K BSS snapshot per 2-min cycle | OSS data arrival |
| Feature Computer | Derived features + window features across last W cycles | OSS data arrival |
| O+B Convergence Engine | Joins BSS subscriber data with OSS cell KPIs by geography | OSS data arrival |

### 10.2 Phase 4.5 — Model v3.0 (Real Data)

| Model | Algorithm | Replaces |
|-------|-----------|----------|
| **CEM Experience Score** | GradientBoostingRegressor (interpretable) | SLA Risk v2.0 |
| **Experience Anomaly** | Autoencoder (PyTorch) | OSS + BSS IsolationForest |
| **Churn Trajectory** | LSTM/GRU (PyTorch) | New |
| **RAT Underservice** | XGBoost / small NN | New |
| **O+B Correlation** | Pearson + Spearman + Granger Causality | Enhanced correlation |

### 10.3 Phase 6 — HCS Deployment Evidence

| Deliverable | Description |
|-------------|-------------|
| OBS Bucket Mapping | S3 → OBS migration proof |
| RDS Instance | PostgreSQL → RDS migration |
| ECS Deployment | Container deployment on Huawei Cloud |
| VPC Configuration | Network architecture on HCS |
| Screenshots | Console screenshots of deployed services |

### 10.4 Final Academic Deliverables

| Deliverable | Description | Deadline |
|-------------|-------------|----------|
| **Final Defense Report** | Complete LaTeX thesis | July 2026 |
| **Defense Presentation** | PowerPoint + speech | July 2026 |
| **Demo Video** | Platform walkthrough | July 2026 |
| **Source Code Archive** | GitHub repository + documentation | July 2026 |

---

## 11. Deliverables Matrix

### By Phase

| Phase | Deliverables | Status |
|-------|--------------|--------|
| **Phase 1** | Core infrastructure (PostgreSQL, MinIO, FastAPI, Docker Compose) | ✅ Complete |
| **Phase 2** | Real ML models (GBR + IsolationForest), 22-step pipeline, 7 API endpoints | ✅ Complete |
| **Phase 3** | Full alignment, professional docs, dashboard | ✅ Complete |
| **Phase 4** | Auth service (JWT + OAuth), dashboard auth, CI/CD | ✅ Complete |
| **Phase 5** | ADN L4 Agent, Model Evaluation page, AI Copilot, Ollama integration | ✅ Complete |
| **Phase 5.5** | Dashboard containerized, real data pages, real playbooks, agent_actions persistence | ✅ Complete |
| **Phase 1 Backend Restructure** | Modularized services, tests, ruff compliance | ✅ Complete (2026-04-25) |
| **Phase 3.5** | Real TT data ingestion + Rolling Window Engine | 🔄 Blocked (waiting OSS) |
| **Phase 4.5** | Model v3.0 — CEM Score, Autoencoder, LSTM, XGBoost | 🔄 Planned |
| **Phase DL** | Temporal models — LSTM Churn, Granger Causality | 🔄 Planned |
| **Phase 6** | HCS deployment evidence (OBS/RDS/ECS) | 🔄 Planned |
| **Final** | Report writing, presentation preparation | 🔄 In Progress |

### By Category

| Category | Count | Status |
|----------|-------|--------|
| Backend Microservices | 6 | 6 ✅ |
| REST API Endpoints | 15+ | 15+ ✅ |
| Dashboard Pages | 17 | 17 ✅ |
| ML Models | 3 | 3 ✅ |
| Jupyter Notebooks | 3 | 3 ✅ |
| Database Tables | 9 | 9 ✅ |
| Data Lake Layers | 3 | 3 ✅ |
| Documentation Files | 15+ | 15+ ✅ |
| Architecture Diagrams | 8 PNGs | 8 ✅ |
| LaTeX Chapters (Defense) | 14 | 14 ✅ |
| LaTeX Chapters (Periodic) | 13 | 13 ✅ |
| CI/CD Stages | 6 | 6 ✅ |
| Custom Chart Components | 10 | 10 ✅ |
| L4 Agent Playbooks | 5 | 5 ✅ |
| Multi-Agent System | 3 agents | 3 ✅ |
| Observability Components | 6 | 6 ✅ |
| Real Data Months | 2 BSS | 2 ✅ / OSS pending |

---

## File Manifest Summary

```
telecom-cloud-intelligence/
├── services/                    # 6 microservices (Python/FastAPI)
│   ├── api-gateway/             # REST API (15+ endpoints)
│   ├── ai-service/              # ML inference (3 models)
│   ├── auth-service/            # JWT + OAuth2
│   ├── pipeline-worker/         # 22-step ETL daemon
│   ├── agent-service/           # Multi-agent orchestrator
│   └── data-ingest/             # Real data ingestion
├── dashboard/                   # Next.js 14 frontend (17 pages)
│   ├── app/                     # Pages + API routes
│   ├── components/              # 25+ React components
│   └── lib/                     # API clients
├── notebooks/                   # Jupyter notebooks + models
│   ├── *.ipynb                  # 3 training notebooks
│   ├── models/*.joblib          # 3 trained models
│   └── data/                    # Training arrays + viz PNGs
├── docs/                        # Technical documentation
│   ├── *.md                     # 10+ markdown docs
│   ├── *.pdf                    # 5 generated PDFs
│   ├── architecture/            # C4 diagrams
│   ├── data-model/              # Schema + lake docs
│   ├── db/schema.sql            # PostgreSQL schema
│   └── deployment/              # Deployment guides
├── report/                      # Periodic report (LaTeX)
│   ├── chapters/*.tex           # 13 chapters
│   ├── main.tex / main.pdf      # Compiled report
│   └── *.md / *.pptx            # Supporting docs
├── final-defense-report/        # Final PFE thesis (LaTeX)
│   ├── chapters/*.tex           # 14 chapters
│   ├── main.tex                 # Main thesis file
│   └── references.bib           # Bibliography
├── diagrams/export/             # 8 architecture PNGs
├── infra/monitoring/            # SigNoz + Prometheus configs
├── TT_data/                     # CONFIDENTIAL — real TT data
├── docker-compose.yml           # 10+ service orchestration
├── Makefile                     # 20+ commands
└── .github/workflows/           # CI/CD pipeline
```

---

*Report generated: 2026-04-27*  
*Total artifacts tracked: 80+ files across 11 categories*  
*Completion status: Phase 5.5 (100%) | Overall Project: ~75%*
