# Supervisor Presentation: Cloud-Native Telecom Intelligence Platform (HCS-Ready)

Author: Project Team  
Date: 2026-02-20

---

## Slide 1 — Title
**Cloud-Native Telecom Intelligence Platform with AI Operations Agent**  
**Purpose:** connect telecom network performance (OSS) to business impact (BSS), with AI-driven risk and anomaly insights.

**One-line pitch:**
A containerized, HCS-portable intelligence platform that turns telecom KPIs into operational and revenue decisions.

---

## Slide 2 — Why This Project Matters
- Telecom degradations create direct revenue and customer-experience impact.
- OSS metrics are often monitored separately from BSS outcomes.
- Teams need faster root-cause and business-impact visibility.

**Problem statement:**
Current operations can detect technical issues, but struggle to quantify business impact quickly and consistently.

---

## Slide 3 — What We Are Building
- Ingest synthetic OSS KPI + synthetic BSS usage/revenue data.
- Organize data in a **3-layer lake**: Raw → Processed → Curated.
- Apply AI for:
  - anomaly detection
  - SLA risk scoring
- Compute OSS–BSS correlations (performance ↔ revenue).
- Expose insights via REST APIs.
- Design for local Docker PoC and Huawei Cloud Stack portability.

---

## Slide 4 — Users and Use Cases
**Primary users**
- Telecom Operations Engineer
- Business Analyst

**Core use cases**
- View OSS KPIs
- Detect network anomalies
- View SLA risk
- View BSS usage/revenue patterns
- Analyze OSS–BSS correlation
- Export insights via REST API

---

## Slide 5 — High-Level Architecture
**Components (Container/C4 level-2 intent)**
- API Gateway (FastAPI): query and integration entry point
- Pipeline Worker: ingestion, processing, correlation orchestration
- AI Service: anomaly + SLA risk inference
- PostgreSQL: serving + metadata store
- Object Storage (MinIO/OBS): datasets + model artifacts

**Data/Control flow (simplified)**
1. Worker writes datasets to object storage.
2. Worker writes metadata/results to PostgreSQL.
3. Worker triggers AI inference.
4. AI writes anomalies/risk results to PostgreSQL and artifacts to object storage.
5. API Gateway serves analytics results to clients.

---

## Slide 6 — End-to-End Example (SLA Risk Query)
1. User calls `GET /sla-risk?region=...&time_window=...`.
2. API Gateway checks PostgreSQL for latest score.
3. If score missing/stale, inference job is triggered.
4. Pipeline loads processed features from object storage.
5. AI service computes risk and stores results.
6. API returns JSON risk score.

**Outcome:** cached/serving-first behavior with on-demand refresh.

---

## Slide 7 — Data Architecture
**3-layer data lake design**
- **Raw:** synthetic OSS/BSS input datasets
- **Processed:** cleaned, aligned, feature-engineered windows
- **Curated:** joined OSS+BSS plus AI outputs and correlation insights

**Why this matters**
- Clear lineage and reproducibility
- Easier model training/inference handoff
- Better governance when moving to enterprise/hybrid cloud

---

## Slide 8 — Analytical Data Model (PostgreSQL)
**Key entities**
- `dataset_registry`
- `pipeline_runs`
- `anomalies`
- `sla_risk_scores`
- `correlation_insights`
- `model_registry`

**Value of this schema**
- Traceable runs and artifacts
- Time-windowed operational and business insights
- Foundation for dashboards and API consumption

---

## Slide 9 — Deployment Strategy: Local to HCS
**Local PoC:** Docker Compose-based services (`api-gateway`, `pipeline-worker`, `ai-service`, `postgres`, `minio`)  
**Target mapping:**
- Services → ECS
- Object Storage → OBS
- PostgreSQL → RDS
- Networking boundary → VPC

**Strategic point:**
The same architecture pattern is intentionally cloud-portable with minimal conceptual drift.

---

## Slide 10 — Current Project State (As of Today)
**Completed (documentation and design assets)**
- Architecture diagrams (system context, container flow, sequence)
- Data-lake and ER model definitions
- Use-case and deployment mapping diagrams
- Project vision and scope description

**Not yet implemented (code/runtime maturity)**
- Service implementations in `services/` are currently placeholders
- `docker-compose.yml` currently empty
- Security and business-value docs not yet populated

**Supervisor takeaway:**
Project has a strong design baseline; next phase is execution and measurable PoC delivery.

---

## Slide 11 — Risks, Gaps, and Mitigations
- **Gap:** No runnable services yet  
  **Mitigation:** implement thin vertical slice first (`/health`, `/sla-risk`, batch pipeline skeleton).
- **Gap:** Empty deployment composition  
  **Mitigation:** baseline Compose with app + postgres + minio and sample seed workflow.
- **Gap:** Security model not documented  
  **Mitigation:** define v1 controls (auth, secrets handling, network policy, data retention).
- **Gap:** Business KPI definition not finalized  
  **Mitigation:** lock 3–5 supervisor-approved success metrics.

---

## Slide 12 — Proposed 4-Week Execution Plan
**Week 1: Platform bootstrap**
- Implement service scaffolds and repo conventions
- Add Docker Compose baseline
- Define synthetic data contracts

**Week 2: Data pipeline + storage**
- Raw→Processed→Curated pipeline MVP
- Register datasets and pipeline runs in PostgreSQL

**Week 3: AI + API integration**
- Add anomaly and SLA-risk baseline models
- Implement `/sla-risk`, `/anomalies`, `/correlation` endpoints

**Week 4: Validation + supervisor demo**
- End-to-end runbook and smoke tests
- Demo with scenario: network degradation → SLA risk → revenue correlation
- Produce KPI evidence and next-phase plan

---

## Slide 13 — Success Metrics for Supervisor Review
- End-to-end pipeline completion time (target threshold to be agreed)
- API response latency for key endpoints
- Freshness of SLA risk scores
- Correlation insight consistency across test windows
- Reproducibility: rerun yields same lineage and traceable outputs

---

## Slide 14 — What We Need from Supervisor
- Confirm MVP scope for first milestone (must-have vs nice-to-have).
- Approve evaluation KPIs and acceptance criteria.
- Align on preferred demo scenario(s) and stakeholder audience.
- Confirm whether HCS deployment validation is in-scope for phase 1 or phase 2.

---

## Slide 15 — Closing
**Project status:** architecture-ready, implementation-start phase.  
**Immediate objective:** deliver a runnable vertical slice and measurable value evidence.  
**Decision request:** approve the 4-week MVP execution plan.

---

## Appendix — Existing Diagram Assets in Repo
Use these visuals directly in the deck:
- `diagrams/export/System Context Diagram (C4 Level 1).png`
- `diagrams/export/Container flowchart Digram (C4 level 2).png`
- `diagrams/export/Sequence Diagram.png`
- `diagrams/export/Data Lake Diagram (Raw  Processed  Curated).png`
- `diagrams/export/ER Diagram.png`
- `diagrams/export/Local Deployment Diagram.png`
- `diagrams/export/Use Case Diagram.png`

## Optional Presenter Notes (2-minute opening)
"This project addresses a practical telecom challenge: technical degradations are visible, but business impact is often delayed. We are building a cloud-native, HCS-portable platform that links OSS and BSS signals, applies AI for anomaly and SLA risk insights, and serves outputs through APIs. The architecture and data model are complete; our next step is implementation of an end-to-end MVP vertical slice with clear success KPIs in 4 weeks."