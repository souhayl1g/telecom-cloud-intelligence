# Defense & Academic Memory

> ⚠️ Read [REALIGNMENT_2026-05-10.md](REALIGNMENT_2026-05-10.md) first for the post-expert-feedback realignment + cleanup. The content below is pre-realignment context.


> Last updated: 2026-04-29

## Project Context

- **Owner:** Souhayl Guenichi — ESPRIT engineering student
- **Internship:** Huawei Tunisia
- **Platform:** Telecom NeXoligence
- **Deployment Target:** Huawei Cloud Stack (HCS)
- **Architecture Alignment:** Huawei ADN (Autonomous Driving Network) L4

## Key Contributions

### 1. OSS↔CEM Convergence
- Built cell-to-governorate mapping for 3,487 cell towers → 24 governorates (~80% coverage)
- Computed area-level aggregates with proper OSS↔CEM alignment
- Found 13 significant Granger causal relationships across 9 months

### 2. ML Model Suite
- **CEM Score:** LightGBM DART, R²=0.9933 on 2.47M subscribers
- **OSS Anomaly:** PyTorch VAE, ROC-AUC=0.9307
- **RAT Underservice:** XGBoost GPU, ROC-AUC=0.9605
- **SLA Risk:** GradientBoostingRegressor (v2.0 baseline)

### 3. Data Engineering
- Identity-preserving bootstrap simulation for 7 months (3.17M total BSS rows)
- Bootstrap OSS simulation for 7 months (550K simulated OSS rows)
- Real data: 968K BSS (Feb+Mar), 18.8M OSS (Mar+Apr)

### 4. L4 Autonomous Agent
- Multi-agent orchestrator with Qwen2.5:7b LLM
- 5 playbook executions with real backend effects
- Natural language intent classification + response synthesis

### 5. Dashboard
- Next.js 14 dashboard with 18+ pages
- Custom SVG charts (no external chart library dependencies)
- Real-time data via SSR + client-side polling

## Data Confidentiality (CRITICAL)

- `TT_data/` contains real Tunisie Telecom subscriber and network data
- **NEVER** commit to git, **NEVER** export, **NEVER** share
- Already in `.gitignore` — do not remove

## Defense Presentation Materials

- `final-defense-report/` — LaTeX thesis document
- `docs/architecture/` — C4 architecture diagrams
- `docs/data-model/` — ER diagrams, data lake docs
- `diagrams/` — Architecture PNG exports
