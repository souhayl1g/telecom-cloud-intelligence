# Realignment — 2026-05-10

> Single canonical update block referenced by every other file in `memory/`.
> Triggered by post-expert-meeting realignment + project cleanup.

## What changed

| Workstream | Outcome |
|---|---|
| **WS1** BSS → CEM rename | DB table `revenue_anomalies` → `cem_anomalies`. Column `granger_causality_results.bss_variable` → `cem_variable`. API route `/revenue-anomalies` → `/cem-anomalies`. Sidebar groups + dashboard pages relabeled. Raw `bss_subscribers` load table preserved (data-source layer). Migration: `docs/db/migrations/001_bss_to_cem_rename.sql`. |
| **WS2** Granger 2-tier + lead-time | Offline gate `notebooks/10_granger_feature_selection.py` produces `granger_feature_gate.json` (canonical) + ai-service copy. Online refresh persists into `granger_causality_results`. New endpoint `GET /granger-causality/lead-time?area=X` (env `LAG_WINDOW_MINUTES`, default 43200). Dashboard panel via `LeadTimeHistogram.tsx` + `/api/granger-lead-time`. |
| **WS3** EDA / data-quality | `notebooks/00_data_understanding_eda.py` — 10 sections (inventory · missingness · distributions · outliers · correlations · corruption · imbalance · drift · generator validation · conclusions). Outputs PNG/JSON/markdown to `notebooks/data/eda/`. |
| **WS4** BO/DSO + presentation + diagrams | `docs/business/objectives.md` (BO1-3 + DSO1-5 + KPI tree). `docs/presentation/v1_outline.md` (13-slide CRISP-DM map, versioned). `diagrams/v2/c4_context.md`, `c4_container.md`, `deployment.md`, `ml_lifecycle.md` (all Mermaid). |
| **WS5** Augmentation reframing | `docs/data-model/data-augmentation.md` — generator reframed as subordinate Data Augmentation Module that fills missing months only. |
| **Cleanup** | Deleted: `pipeline_runner.py`, `Dockerfile.notebooks`, `dashboard/app/topology/`, `DELIVERABLES_REPORT.md`, root `node_modules`, `package*.json`, `data/`, `imported/`, `preview/`, `img/`, `report/`, `final-defense-report/`, 4 stale docs PDFs/PPTX, `docs/FULL_PROJECT_DOCUMENTATION.md`, supervisor briefings, `notebooks/05_master_v3_combined_training.py`, `notebooks/06_oss_bss_granger_causality.py`, `model_registry` table (Migration 002). |
| **Methodology** | Locked **Hybrid CRISP-DM + MLOps overlay**. HCS portability removed; project framed as **cloud-native** (microservices + containers + observability). |
| **Defense pain hook** | "Network anomalies are invisible to OSS until a customer complaint reaches Care." |

## Locked decisions

- Primary stakeholder: TT CTO / Strategic office.
- Problem statements: **Modeling/Data-Science + Automation/ADN L4** (Cloud-Mapping/HCS dropped).
- Generator framing: subordinate Data Augmentation Module.
- Granger placement: two-tier (offline gate + online refresh).
- Defense window: mid-June → mid-July 2026. Implementation freeze: first week of June. Memoir drafting: August 2026.
- Memoir starts from scratch when ESPRIT examples uploaded.

## Where to look

| Need | File |
|---|---|
| BO + DSO + KPI tree | `docs/business/objectives.md` |
| Presentation skeleton | `docs/presentation/v1_outline.md` |
| Architecture diagrams | `diagrams/v2/*.md` |
| EDA evidence | `notebooks/00_data_understanding_eda.py` (PNGs in `notebooks/data/eda/`) |
| Granger gate | `notebooks/10_granger_feature_selection.py` → `granger_feature_gate.json` |
| Augmentation rationale | `docs/data-model/data-augmentation.md` |
| DB migrations | `docs/db/migrations/001_bss_to_cem_rename.sql`, `002_drop_model_registry.sql` |

## Out-of-scope (locked)

- HCS migration (cloud-native instead).
- LSTM Churn 4th model (deferred).
- Real NOC alarm baseline (TT did not share).

---
