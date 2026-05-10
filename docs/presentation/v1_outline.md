# NeXo — Defense Presentation Outline (v1)

> Versioned outline for the final-defense slide deck. Mid-June → mid-July 2026.
> Owner: Souhayl Guenichi · CRISP-DM + MLOps overlay methodology.

| Version | Date | Notes |
|---|---|---|
| v1 | 2026-05-10 | Initial post-expert-feedback skeleton. 13 slides + Q&A backup. |
| v2 | TBD | After mentor review pass. |
| ... | TBD | |

---

## Audience & Tone
- **Jury**: ESPRIT engineering panel + TT/Huawei industrial mentor.
- **Pain hook**: "Network anomalies are invisible to OSS until a customer complaint reaches Care."
- **Methodology**: Hybrid CRISP-DM + MLOps overlay — every section ties back to a phase.
- **Length target**: 25-30 minutes presentation + 15 minutes Q&A.

---

## Slide-to-Phase Map

| # | Slide | CRISP-DM Phase | Source artifact |
|---|---|---|---|
| 1 | Title + context | — | n/a |
| 2 | Pain hook + stakeholder | Phase 1 — Business Understanding | `docs/business/objectives.md` §1 |
| 3 | BO + DSO + KPI tree | Phase 1 + Phase 4 | `docs/business/objectives.md` §2-4 |
| 4 | Methodology — Hybrid CRISP-DM + MLOps | (cross-cutting) | `diagrams/v2/ml_lifecycle.md` |
| 5 | Phase 1 — Business Understanding | Phase 1 | `docs/business/objectives.md` |
| 6 | Phase 2 — Data Understanding (EDA, quality audit, generator validation) | Phase 2 | `notebooks/00_data_understanding_eda.py` outputs |
| 7 | Phase 3 — Data Preparation (Granger gate, augmentation) | Phase 3 | `notebooks/10_granger_feature_selection.py` + `services/data-ingest/` |
| 8 | Phase 4 — Modeling (3 v3 models + L4 ADN) | Phase 4 | `docs/v3_real_data_training_report.md` + `services/ai-service/` |
| 9 | Phase 5 — Evaluation (lead-time, R², ROC-AUC) | Phase 5 | `EVAL-REVIEW.md` if produced + `dashboard/app/model-evaluation/page.tsx` |
| 10 | Phase 6 — Deployment (cloud-native arch, observability, CI/CD) | Phase 6 | `diagrams/v2/c4_*.md`, `diagrams/v2/deployment.md` |
| 11 | Live demo storyboard | (cross-cutting) | dashboard pages |
| 12 | Limitations + future work | — | `docs/business/objectives.md` §6 |
| 13 | Q&A backup (terminology, generator, Granger gate) | — | this doc + `DEFENSE_BRIEF.md` |

---

## Slide-by-Slide Detail

### Slide 1 — Title
- Project: **NeXo — Cloud-Native AI Operations Agent for OSS+CEM Convergence**
- Tagline: "Granger-validated intelligence between Huawei ADN and Tunisie Telecom."
- Author / mentor / supervisor / institution / date.

### Slide 2 — Pain Hook
- Visual: timeline showing OSS alarm at T=0, Care complaint at T=+45 min, NeXo detection at T=−15 min.
- One sentence: "TT learns about CEM drops via customer calls; intervention happens after damage."
- Cite: `docs/business/objectives.md` §1.

### Slide 3 — BO + DSO + KPI Tree
- Three-column table: BO1/2/3 ⇆ DSO1-5 ⇆ Current state.
- Visual: KPI tree from `docs/business/objectives.md` §4.
- Punchline: "All targets are measurable; 4 of 5 already met by the v3 release."

### Slide 4 — Methodology
- Visual: `diagrams/v2/ml_lifecycle.md` (CRISP-DM × MLOps overlay).
- Caption: "CRISP-DM (Chapman 2000) for academic spine + MLOps for industrial-grade evidence."
- Cite: Google MLOps Maturity Lvl 1 + Microsoft TDSP.

### Slide 5 — Phase 1 — Business Understanding
- Stakeholder + pain + project objectives (BO1-3).
- Out-of-scope statements (HCS migration, LSTM churn).

### Slide 6 — Phase 2 — Data Understanding
- Snapshots from `notebooks/data/eda/*.png`:
  - 01_inventory.png — rows per month, real vs simulated.
  - 02_missingness.png — heatmap of NaN.
  - 04_outliers.png — IQR + IsolationForest.
  - 05a_oss_corr.png — Pearson + Spearman.
  - 09_generator_overlay.png — real vs simulated overlay.
- Numbers from `notebooks/data/eda/summary.json`.

### Slide 7 — Phase 3 — Data Preparation
- Two halves: **Augmentation Module** (bootstrap-simulated months) and **Granger Gate** (`granger_feature_gate.json` driving training feature selection).
- Visual: schematic from `docs/data-model/data-augmentation.md` (TBD WS5).

### Slide 8 — Phase 4 — Modeling
- Three model cards: CEM LightGBM DART, OSS VAE PyTorch, RAT XGBoost GPU.
- Mention L4 ADN agent + Spirits/Mates roster.
- One architecture frame: `diagrams/v2/c4_container.md`.

### Slide 9 — Phase 5 — Evaluation
- Headline number: detection lead time (live from `/api/granger-lead-time`).
- Metrics table (R², MAE, RMSE, Recall, Precision, F1, ROC-AUC) per model.
- Confusion matrix screenshots from `dashboard/app/model-evaluation`.

### Slide 10 — Phase 6 — Deployment
- Cloud-native deployment diagram: `diagrams/v2/deployment.md`.
- Observability stack (Prometheus, Grafana, Jaeger, Netdata, OTel-Collector).
- CI/CD pipeline screenshot or YAML excerpt from `.github/workflows/ci-cd.yml`.

### Slide 11 — Live Demo Storyboard
- Sequence: `/overview` → `/l4-agent` (autonomy meter, action approval) → `/granger-causality` (lead time + significance table) → `/model-evaluation` (real metrics).
- Backup screenshots in case live demo fails.

### Slide 12 — Limitations + Future Work
- LSTM churn (4th model deferred).
- Real NOC alarm baseline missing.
- Cycle-grain Granger refresh (currently monthly).

### Slide 13 — Q&A Backup
- "Why CEM, not BSS?" → SmartCare alignment, terminology rename done in WS1.
- "Generator engine — completes models or independent?" → Subordinate Data Augmentation Module, fills missing months.
- "Granger before training — why?" → Two-tier gate explained in `docs/business/objectives.md` DSO5.
- "Why no HCS mapping?" → Cloud-native by design; HCS deferred as appendix.
