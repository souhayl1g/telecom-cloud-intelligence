# Telecom NeXoligence Platform

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![LightGBM](https://img.shields.io/badge/LightGBM-DART-9ACD32)
![PyTorch](https://img.shields.io/badge/PyTorch-VAE-EE4C2C?logo=pytorch&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

> **Cloud-Native AI Operations Agent for CEM–CVM Intelligence.**
> An intelligence layer in Huawei's ADN (Autonomous Driving Network) architecture for O+B (OSS+BSS) convergence.
> Ingests real Tunisie Telecom network KPIs and subscriber-experience data, runs v3.0 ML/DL models, computes
> OSS↔CEM causality via Granger F-tests, and serves actionable intelligence through a REST API and an
> autonomous **L4 operations dashboard**.

---

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [AI Models (v3.0)](#ai-models-v30)
- [Dashboard](#dashboard)
- [L4 Autonomous Agent](#l4-autonomous-agent)
- [API Reference](#api-reference)
- [Data](#data)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)

---

## Overview

NeXoligence bridges Huawei **CEM** (SmartCare customer-experience management) and **CVM** (customer value management).
It is oriented to **CEM subscriber profiling** — not billing/revenue — aligned with the SmartCare architecture.

The platform:

1. **Ingests** real TT BSS subscriber profiles + OSS cell KPIs into PostgreSQL.
2. **Samples** stratified batches each pipeline cycle (by area × usertype × RAT).
3. **Runs three v3.0 models** — CEM experience scoring (LightGBM/DART), experience-anomaly detection (PyTorch VAE), RAT underservice classification (XGBoost).
4. **Converges OSS↔CEM** geographically (governorate-level join) and computes **Granger causality** (two-tier: offline gate + online lead-time).
5. **Persists** results to PostgreSQL and serves them via a JWT-protected REST API.
6. **Acts** — an ADN **L4 agent** auto-approves safe actions and fires real playbooks (tickets, SMS alerts, capacity PDFs, churn interventions, model retrain).

**Methodology:** CRISP-DM (single methodology; MLOps practices map to the Deployment phase, not a separate hybrid).

**The pain it solves:** *network anomalies are invisible to OSS until a customer complaint reaches Care.*
Granger F-tests on OSS→CEM pairs surface the convergence early, then the L4 agent turns it into action.

---

## Architecture

```
[CEM / SmartCare] ──▶ [NeXo AI Operations Agent] ──▶ [CVM]
                            │  (this project — cloud native)
                            ▼
                    [ADN L4 Auto-Ops Agent]
              OSS+CEM convergence · Granger causality
```

### Services

| Service | Port | Role |
|---|---|---|
| `api-gateway` | 8000 | Public REST API (FastAPI 0.115), JWT-protected |
| `ai-service` | 8001 | ML inference engine — 3× v3.0 models, hot-reloadable |
| `auth-service` | 8002 | JWT auth + OAuth2 + password reset (SMTP) |
| `agent-service` | — | LLM orchestrator (OpenRouter cloud, free models) |
| `pipeline-worker` | — | Daemon pipeline, real ~70–180s cycles |
| `dashboard` | 3001 | Next.js 14 operations UI (24 pages, liquid-glass design) |
| `postgres` | 5432 | Serving store + run metadata |
| `minio` | 9000 / 9001 | S3-compatible 3-layer data lake |

**Observability (opt-in `--profile monitoring`):** netdata `19999` · prometheus `9090` · grafana `3000` · jaeger `16686` · otel-collector.

### Convergence join key

OSS cell-site KPIs and BSS subscriber records have **no direct IMSI↔cell link** — the join key is **geographic area (governorate)**.
Cell-site names (≈4,300 distinct) and subscriber areas (24 governorates) are normalized to a canonical governorate before correlation.

---

## Quick Start

**Prerequisites:** Docker + Docker Compose. (Dev hardware reference: Ryzen 5 5600H, 24 GB RAM, RTX 3050, WSL2.)

```bash
git clone https://github.com/souhayl1g/telecom-cloud-intelligence.git
cd telecom-cloud-intelligence
cp .env.example .env          # set OPENROUTER_API_KEY for the L4 agent (optional)

# Demo stack — all UIs (dashboard, API docs, MinIO, Jupyter), staged startup + memory watchdog
make start-demo

# Defense stack — core services + full monitoring stack
make start-defense
```

Verify:

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

| UI | URL | Credentials |
|---|---|---|
| Dashboard | http://localhost:3001 | sign up on `/login` |
| API docs | http://localhost:8000/docs | JWT bearer |
| MinIO console | http://localhost:9001 | `minio` / `minio_pw` |
| Grafana | http://localhost:3000 | `admin` / `admin` |
| Jupyter | http://localhost:8888 | (demo stack) |

> Data persists in the `pgdata` volume across `make stop`/`restart`. A `data-init` sidecar auto-loads data on first boot if tables are empty. Wipe only with `make nuke` / `make db-reset`.

---

## AI Models (v3.0)

| Model | Algorithm | Training data | Key metric |
|---|---|---|---|
| **CEM Experience Score** | LightGBM (DART, 256 leaves, depth 12) | 2.47M subscribers (real+sim) | Test R² = 0.9784, MAE = 0.0304 |
| **Experience Anomaly** | PyTorch VAE (9→32→16→Latent 8) | 1M OSS records, normal-only | ROC-AUC = 0.9821, PR-AUC = 0.9974 |
| **RAT Underservice** | XGBoost (500 trees, depth 8, GPU) | 2.47M subscribers | ROC-AUC = 0.9203, F1 = 0.8927 |
| Churn Trajectory | LSTM/GRU | *planned (needs rolling-window history)* | — |
| O+B Correlation | Pearson + Spearman + **Granger** | temporal lag analysis | — |

Model metrics on the dashboard come from `notebooks/models/metrics.json` (generated from trainer notebooks) — **no hardcoded fallbacks**. Missing data renders as `—`, never a fake `0`.

The feature contract is the **joblib, not the code**: routers load `*_feature_names.joblib` at startup, so retraining with a wider feature set needs no router change.

---

## Dashboard

Next.js 14 + React 18 + TypeScript, **24 pages**, organized as a 6-group story arc (Start Here · Autonomy · Convergence · ML Models · Actuation · More). Highlights:

- **Liquid-glass design system** — token-driven frosted-glass material (backdrop-blur + saturate, specular edges) applied platform-wide; dark + light themes share one cyan/blue palette; `prefers-reduced-motion` aware.
- **Tunisia geographic intelligence** — governorate choropleth heatmaps (VAE anomalies, CEM scores, RAT underservice).
- **Granger explorer** with lead-time histogram, CEM/VAE/RAT browsers, capacity & forecast (Granger lagged OLS).
- **Cmd+K** command palette fires playbooks from anywhere; 30s-polling status strip.

All client pages requiring auth data go through the `/api/platform-data` SSR proxy (reads the httpOnly `auth_token` cookie, forwards a bearer token to the API gateway).

---

## L4 Autonomous Agent

ADN Level-4 operations: auto-approves safe actions, requires human approval for risky remediations. All actions persist to `agent_actions` (full audit trail).

**Actuation playbooks** (real backend operations):

| Playbook | Action |
|---|---|
| `pb-alert-subscriber` | SMS (Twilio, console fallback) to top-10 at-risk + audit row |
| `pb-create-ticket` | Internal NOC ticket (`TT-YYYY-NNNNN`), emails on-call if critical |
| `pb-retrain-model` | papermill notebook → hot-reload ai-service → audit row |
| `pb-capacity-report` | fpdf2 PDF → MinIO `reports/` bucket → presigned URL |
| `pb-churn-prevention` | `rat_gap>0.5 AND cem<0.3` → SMS → bulk ticket if ≥20 |

**Chat:** an LLM orchestrator over **OpenRouter** (free cloud models) with an automatic multi-model fallback chain (retries the next free model on 404/429). Local Ollama is an offline fallback.

---

## API Reference

Base URL `http://localhost:8000` — all routes except `/health` require a JWT bearer token.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness |
| `GET` | `/cem-scores` / `/vae-anomalies` / `/rat-underservice` | v3.0 model outputs |
| `GET` | `/correlation?limit=N` | OSS↔CEM Pearson + Spearman (governorate-level) |
| `GET` | `/granger-causality/lead-time?area=X` | Online Granger lead-time |
| `GET` | `/anomalies` · `/pipeline-runs` · `/kpi-summary` | Operations data |
| `GET/POST/PATCH` | `/actions[/{id}][/execute]` | L4 agent action lifecycle + playbook execution |

**ai-service (:8001, internal):** `POST /infer/cem` · `POST /infer/vae-anomaly` · `POST /infer/rat-underservice` · `POST /models/reload`.

**auth-service (:8002):** `/auth/signup` · `/auth/login` · `/auth/me` · `/auth/forgot-password` · `/auth/reset-password` · OAuth (`/auth/google`, `/auth/github`).

---

## Data

| Source | Status |
|---|---|
| **BSS** | 968,077 real subscribers (Feb+Mar) + 1.5M simulated (Jan/Apr/May) — 26 features each |
| **OSS** | 18.8M real cell KPIs (2G/3G/4G) + 200K bootstrap-simulated reservoir |

Real TT data lives in `TT_data/` and is **strictly confidential** — gitignored, never committed, processed locally only.
Simulated months are generated by stratified bootstrap with log-normal perturbation + temporal drift to fill missing months; the generator is **subordinate to real data**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI 0.115, Uvicorn, psycopg2 (no ORM) |
| ML / DL | LightGBM (DART), XGBoost (GPU), PyTorch (VAE), scikit-learn 1.5, SHAP |
| Statistics | SciPy (Pearson/Spearman), statsmodels (Granger, ADF/KPSS) |
| Frontend | Next.js 14, React 18, TypeScript, framer-motion, d3-geo, lucide-react |
| LLM | OpenRouter (free cloud models) + Ollama (offline fallback) |
| Storage | PostgreSQL 16, MinIO (S3-compatible) |
| Observability | Prometheus, Grafana, Netdata, Jaeger, OpenTelemetry |
| Containers | Docker, Docker Compose |

---

## Project Structure

```
telecom-cloud-intelligence/
├── docker-compose.yml            # multi-service stack (+ monitoring/retrain profiles)
├── Makefile                      # start-demo · start-defense · watchdog · data ops
├── services/
│   ├── api-gateway/              # REST API (:8000), domain routers
│   ├── ai-service/               # v3.0 inference (:8001), model_cache hot-reload
│   ├── auth-service/             # JWT + OAuth + password reset (:8002)
│   ├── agent-service/            # LLM orchestrator (OpenRouter)
│   └── pipeline-worker/          # daemon pipeline, sampler, analytics, inference client
├── dashboard/                    # Next.js 14 UI (24 pages, liquid-glass design system)
├── notebooks/                    # 00 EDA · 01 ETL · 02 CEM · 03 VAE · 04 RAT · 10 Granger
├── docs/                         # architecture, data model, deployment, defense prep
└── TT_data/                      # CONFIDENTIAL real TT data (gitignored)
```

---

> Owner: **Souhayl Guenichi** — ESPRIT engineering student, Huawei Tunisia internship (Cloud IT / Sales-Solution).
> Client: **Tunisie Telecom**. Focus: CEM subscriber profiling + OSS+CEM convergence.
