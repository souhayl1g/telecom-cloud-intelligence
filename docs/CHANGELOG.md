# CHANGELOG — Telecom NeXoligence

Historical detail trimmed out of CLAUDE.md to keep that file fast for Claude Code.
See CLAUDE.md for current architecture, run instructions, and model status.

---

## 2026-05-12 — Data Persistence + Notebook Docs

| Area | Change | File |
|------|--------|------|
| **Data persistence** | New `data-init` sidecar service in compose runs `init-db-data.sh` after Postgres healthy; idempotent (skip if rows exist) | `docker-compose.yml`, `scripts/init-db-data.sh` |
| **Sampler default month** | `SAMPLE_MONTH: "2026-03"` → `""` so sampler auto-detects MAX(month_year) | `docker-compose.yml:124` |
| **init-db script** | Venv source guarded by `SKIP_VENV` env so container path uses system python | `scripts/init-db-data.sh` |
| **Notebooks doc** | README expanded with 2-tier Granger explanation + per-model training table | `notebooks/README.md` |
| **CLAUDE.md** | Trimmed ~13k chars (session logs + legacy detail + April update) → moved here | `CLAUDE.md` |

---

## 2026-05-04 — Mat Views + L4 ADN Reframe

| Area | Change | File / Location |
|------|--------|-----------------|
| **Performance** | 12 materialized views; dashboard 60s → <100ms (1500-3750× speedup) | `docs/db/dashboard_summary.sql` |
| **API routes** | cem-scores / vae-anomalies / rat-underservice / platform-data patched to read mat views | `dashboard/app/api/` |
| **SSR lib** | `vaeAnomalies()`, `cemScores()`, `ratUnderservice()`, `anomalyStats()` now use mat views | `dashboard/lib/api.ts` |
| **Production build** | Dashboard switched from `npm run dev` to `next build` + `next start` | `dashboard/Dockerfile` |
| **Pipeline integration** | Mat views auto-refresh after each succeeded run via `refresh_dashboard_views()` | `services/pipeline-worker/worker/pipeline.py` |
| **Pipeline mode** | `RUN_MODE: manual` → `daemon` with `CYCLE_SECONDS: 120` | `docker-compose.yml` |
| **otel-collector** | `logging` → `debug` exporter (deprecated in v0.119) | `infra/monitoring/otel-collector-config.yaml` |
| **Grafana** | Datasource explicit `uid: prometheus`; admin password reset via `grafana-cli admin reset-admin-password` | `infra/monitoring/grafana/...` |
| **Prometheus metrics** | All 4 FastAPI services expose `/metrics` via `prometheus-fastapi-instrumentator==7.0.0` | services/*/main.py |
| **api-gateway** | `/infra-stats` uses `pg_class.reltuples` (5s → ms); `/platform-stats` reads `mv_dashboard_summary` | `services/api-gateway/routers/stats.py` |
| **L4 page** | Reframed Huawei ADN-style: 3-layer architecture, 4-step closed loop, 5 Spirits + 3 Mates, autonomy meter L1-L4 | `dashboard/app/l4-agent/page.tsx` |
| **L4 architecture component** | New `<L4ADNArchitecture />` with collapsible content + autonomy score | `dashboard/components/L4ADNArchitecture.tsx` |
| **L4 explainer card** | Defense-mode `<details data-defense-explainer>` panel — removable via grep | `dashboard/app/l4-agent/page.tsx` |
| **L4 fetchData** | Action POST loop made fire-and-forget via `Promise.allSettled` | l4-agent page.tsx |
| **Sidebar** | Reorganized OSS↔CEM narrative: ADN Autonomy → OSS∩CEM Convergence → Network → Subscriber → Models | `dashboard/components/Sidebar.tsx` |
| **Granger frontend** | Two explainer panels — methodology + OSS∩CEM convergence justification | `dashboard/app/granger-causality/page.tsx` |
| **Granger backend** | New `GET /granger-causality/explain` metadata endpoint | `services/api-gateway/routers/granger.py` |

### Junk Audit Candidates (require approval before deletion)
1. `/topology` page — uses demo network structure, not real topology data
2. `dashboard/app/sla-risk/` — appears deleted in working tree; route audit needed
3. `pipeline_runner.py` at repo root — alternate runner, only used by Jupyter container
4. Legacy `model_registry` table — populated, not queried; either revive or drop
5. `lib/api.ts` legacy method names `anomalies` / `revenueAnomalies` — kept for back-compat

### Super-Mode Upgrade Proposals
1. LSTM Churn — complete 4th model from roadmap
2. Postgres LISTEN/NOTIFY pipeline — event-driven, replace 120s timer
3. TimescaleDB hypertable on `oss_cell_kpis` — 5-10× faster time-range queries
4. Multi-agent collaboration — agent-to-agent message passing
5. Streamlit explainer mode for AI Hub — interactive SHAP, what-if
6. Chaos playbook `pb-induce-fault` — deliberate anomaly injection for demo
7. Aggregate `/api/healthz` — single JSON status of all containers
8. Grafana p95/p99 latency panels — wire request_duration histogram
9. Redis pub/sub for pipeline state — cut 20-30% pipeline latency
10. Make targets for `pipeline-once` / `pipeline-daemon` — bulletproof demo commands

---

## Pre-v3.0 Model History (Legacy v2.0)

Legacy v2.0 models trained on synthetic data, kept for backward compatibility in `/infer/sla-risk`, `/infer/anomaly`, `/infer/revenue-anomaly` endpoints.

| Model | Algorithm | Purpose | Key Metric |
|-------|-----------|---------|-----------|
| SLA Risk | GradientBoostingRegressor (200 est, depth=4) | SLA breach probability (0-1) | Test R²=0.9791 |
| OSS Anomaly | IsolationForest (150 est, contamination=0.05) | Network anomalies | F1=0.8772, ROC-AUC=1.0 |
| BSS Revenue Anomaly | IsolationForest (150 est, contamination=0.05) | Revenue anomalies | F1=1.0, ROC-AUC=1.0 |

v3.0 models (CEM LightGBM, VAE Anomaly, RAT XGBoost) supersede these for real-data inference. See `CLAUDE.md` "Quick Reference" for current model status.

### v3.0 Real Evaluation Metrics (from `notebooks/02_cem_score_training.ipynb` etc.)

**CEM Experience Score (LightGBM DART):** Test R²=0.9784, MAE=0.0304, RMSE=0.0322. 13 features. Top SHAP: `s1_mme_sr` (0.1316), `dou_total` (0.0570), `iu_attach_sr` (0.0467). Target is formula-derived (attach SRs + DOU).

**Experience Anomaly (PyTorch VAE):** Architecture 9→32→16→Latent(8)→16→32→9 (2,057 params). Trained on normal-only data (424K). Threshold PR-curve optimized. Test: ROC-AUC=0.9821, PR-AUC=0.9974. Low precision by design — missing network anomalies is worse than false alarms.

**RAT Underservice (XGBoost GPU):** Test ROC-AUC=0.9203, F1=0.8927. `scale_pos_weight=9.87` (9.2% class imbalance). Top features: `dou_total` (0.5186), `network_experience_index` (0.3476).

---

## 2026-04 — Real Data Layer State

### Real Data Received
| Month | BSS (Subscriber) | OSS (Cell) |
|-------|-----------------|-----------|
| **January 2026** | 500K bootstrap simulated | 50K bootstrap simulated |
| **February 2026** | 468,077 ✅ real | 50K bootstrap simulated |
| **March 2026** | 500,000 ✅ real | 2.49M ✅ real |
| **April 2026** | 500K bootstrap simulated | 16.32M ✅ real |
| **May 2026** | 500K bootstrap simulated | 50K bootstrap simulated |
| **June 2026** | — | 50K bootstrap simulated |

### Data Files
```
TT_data/BSS/
  smartcare_cem_feb.csv     (468K subscribers, REAL)
  smartcare_cem_mars.csv    (500K subscribers, REAL)
  smartcare_cem_jan.csv     (500K subscribers, SIMULATED)
  smartcare_cem_avr.csv     (500K subscribers, SIMULATED)
  smartcare_cem_mai.csv     (500K subscribers, SIMULATED)

TT_data/OSS/
  KPI_2G.csv    (3.4M rows, REAL)
  KPI_3G.csv    (6.9M rows, REAL)
  KPI_4G.csv    (8.5M rows, REAL)
```

### Bootstrap Simulation Method (BSS Simulated Months)
Stratified bootstrap with log-normal perturbation from real Feb+Mar data:
1. **Base sampling**: Sample 500K rows with replacement from 968K real rows. Preserves categorical joint distributions and variable correlations.
2. **Numerical perturbation**: Multiply numerical cols by `exp(N(0, 0.06))` — no exact duplicates.
3. **Month drift**:
   - **Jan**: DOU ×0.88, 5G traffic ×0.65, 8% 5G→4G demotion, silent users -3%
   - **Apr**: DOU ×1.18, 5G traffic ×1.35, 12% 4G→5G promotion per unit 5G factor, silent users +4%
   - **May**: DOU ×1.35, 5G traffic ×1.65, 12% 4G→5G promotion per unit 5G factor, silent users +8%
4. **Identity replacement**: New IMSI (`60502` + 10 random digits), new TAC (15 random digits).
5. **DOU guard**: If traffic sum > 1.5× DOU, DOU is raised to match.

Script: `services/data-ingest/generate_bss_months.py`.

### NeXo Multi-Agent Architecture (April 2026 draft)
```
┌─────────────────────────────────────────────────────┐
│      NeXo — TT Intelligence Agent                   │
│   (Huawei ADN + Cloud-Network Style)                │
├─────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────┐               │
│  │   Orchestrator (LLM-powered)     │               │
│  │   Intent → Agent Dispatch        │               │
│  └───────┬──────────────┬───────────┘               │
│          │              │                           │
│  ┌──────┴─────┐ ┌───┴────┐ ┌────┴────┐              │
│  │  CEM Agent │ │Network │ │ Action  │              │
│  │ (Mate)     │ │ Agent  │ │ Agent   │              │
│  │            │ │(Spirit)│ │(Spirit) │              │
│  └──────┬─────┘ └───┬────┘ └───┬────┘               │
│         │           │          │                    │
│  ┌─────┴───────────┴──────────┴────────┐            │
│  │   OSS+CEM CONVERGENCE ENGINE        │            │
│  │   (Area-level join)                 │            │
│  └─────────────────────────────────────┘            │
└─────────────────────────────────────────────────────┘
```

Agent roles: CEMAgent (experience analysis, NPS), NetworkAgent (cell KPI, capacity), ActionAgent (remediation), Orchestrator (LLM intent routing — Qwen2.5:7b via Ollama).

Convergence join key: **area** (no direct IMSI-to-cell link). Subscriber experience tied to network performance through geographic area aggregates.

### Hardware Baseline
- CPU: Ryzen 5 5600H (6 cores, 3.3GHz)
- RAM: 24GB (19.9GB usable)
- GPU: RTX 3050 4GB VRAM (PyTorch training)
- Disk: ~1000GB on D:/

---

## 2026-04-25 — Backend Modularization (Phase 1 Restructuring)

All services modularized:
- **pipeline-worker**: split into config/db/storage/generators/processors/analytics/inference/pipeline modules. 23 tests.
- **api-gateway**: 9 routers + auth/config/db modules. 1 test.
- **ai-service**: model_cache + 4 routers. 2 tests.

`ruff check services/` = 0 errors. Docker builds pass.

---

## 2026-04-15 — Codebase Audit Fixes

| Area | Issue | Fix |
|------|-------|-----|
| Dashboard | React error #310 at runtime (Recharts v3 incompatibility) | Downgraded recharts 3.8.1 → 2.15.3 (pinned — do not upgrade) |
| Dashboard | `AnomalyTimeline` passed Date objects through useMemo/JSX | Changed `timestamp` field from `Date` to ISO string |
| Dashboard | Dead `Nav.tsx` sidebar component (replaced by `TopNav.tsx`) | Deleted component + 96 lines of dead `.nav` CSS |
| ai-service | Misplaced docstring on `infer_revenue_anomaly` (string after code) | Moved docstring to first statement position |
| pipeline-worker | Failed pipeline runs stuck in `status='started'` forever | Added try/except in `run_once()` marks failed runs with `status='failed'` + `error_message` |

All 25 dashboard routes compile. Zero TypeScript errors. Zero Python syntax errors.
