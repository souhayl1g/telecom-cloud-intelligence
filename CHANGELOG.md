# Changelog

All notable changes to **Telecom NeXoligence** are tracked here.
Format inspired by [Keep a Changelog](https://keepachangelog.com).

---

## 2026-05-10 — Expert-Feedback Realignment + Full Cleanup

### Methodology

- Locked **Hybrid CRISP-DM + MLOps overlay** as the project methodology.
- Dropped HCS portability narrative; project framed as cloud-native by design.
- Defense pain hook locked: *"Network anomalies are invisible to OSS until a customer complaint reaches Care."*
- Two retained problem statements: Modeling/Data-Science + Automation/ADN L4. Cloud-Mapping/HCS dropped.

### Added

- `notebooks/00_data_understanding_eda.py` — 10-section CRISP-DM Phase 2 EDA.
- `notebooks/10_granger_feature_selection.py` — offline Granger feature-selection gate, writes `granger_feature_gate.json`.
- `services/api-gateway/routers/granger.py` — new `GET /granger-causality/lead-time?area=X` endpoint (`LAG_WINDOW_MINUTES` env).
- `dashboard/components/LeadTimeHistogram.tsx` + `dashboard/app/api/granger-lead-time/route.ts` — UI + Next.js proxy.
- `docs/business/objectives.md` — BO1-3 + DSO1-5 + KPI tree.
- `docs/presentation/v1_outline.md` — versioned 13-slide deck outline (CRISP-DM phase mapping).
- `diagrams/v2/c4_context.md`, `c4_container.md`, `deployment.md`, `ml_lifecycle.md` — Mermaid architecture diagrams.
- `docs/data-model/data-augmentation.md` — Data Augmentation Module rationale + validation.
- `docs/db/migrations/001_bss_to_cem_rename.sql` — idempotent BSS→CEM analytic-surface rename.
- `docs/db/migrations/002_drop_model_registry.sql` — drop unused table.
- `memory/REALIGNMENT_2026-05-10.md` — single canonical update reference for project memory layer.
- Auto-memory entries under `~/.claude/projects/.../memory/`.

### Changed

- DB: `revenue_anomalies` → `cem_anomalies`. `granger_causality_results.bss_variable` → `cem_variable`.
- API: `/revenue-anomalies` → `/cem-anomalies`. Field `bss_anomaly_count` → `cem_anomaly_count` in `/anomaly-stats`.
- Dashboard: `lib/api.ts` `revenueAnomalies()` → `cemAnomalies()`. Sidebar group "Subscriber (BSS)" → "Subscriber (CEM)", "OSS ∩ BSS Convergence" → "OSS ∩ CEM Convergence". All "OSS↔BSS" analytic-layer phrasing reframed to "OSS↔CEM".
- Pipeline: `worker/analytics/granger.py` field/variable rename to `cem_variable`/`cem_metric`.
- README, CLAUDE.md, AGENTS.md, DEFENSE_BRIEF.md updated to reflect new naming + realignment.

### Removed

- `pipeline_runner.py` (Jupyter-only alt runner — drift risk vs real pipeline).
- `Dockerfile.notebooks` (duplicated pipeline).
- `dashboard/app/topology/` (demo data, not real topology).
- Empty `dashboard/app/sla-risk/`, `dashboard/app/anomalies/`.
- Root orphans: `DELIVERABLES_REPORT.md`, `output.png`, `data/`, `node_modules/`, `package.json`, `package-lock.json`, `make` symlink.
- Stale docs: `docs/FULL_PROJECT_DOCUMENTATION.md`, `docs/Project's Overview.pptx`, supervisor briefings, three legacy PDFs, `docs/design/`.
- Stale notebooks: `notebooks/05_master_v3_combined_training.py`, `notebooks/06_oss_bss_granger_causality.py`.
- Stale memoir LaTeX trees: `report/`, `final-defense-report/` (memoir restarts from scratch with ESPRIT templates).
- DB table `model_registry` (Migration 002).
- All `__pycache__`, `.pytest_cache`, `.ruff_cache`, `dashboard/.next` build caches.

### Moved

- `test_v3_manual_pipeline.py` → `scripts/test_v3_manual_pipeline.py`.

### Out of Scope (locked)

- HCS migration / cloud portability mapping.
- LSTM Churn 4th model.
- Real NOC alarm baseline (TT did not share).
- Memoir chapter structure (deferred until ESPRIT examples uploaded).
