# ML Lifecycle — CRISP-DM × MLOps Overlay

```mermaid
flowchart LR
    classDef phase fill:#1e293b,stroke:#94a3b8,color:#e2e8f0
    classDef artifact fill:#312e81,stroke:#a5b4fc,color:#e0e7ff
    classDef ops fill:#064e3b,stroke:#6ee7b7,color:#d1fae5

    P1[Phase 1<br/>Business Understanding]:::phase
    P2[Phase 2<br/>Data Understanding]:::phase
    P3[Phase 3<br/>Data Preparation]:::phase
    P4[Phase 4<br/>Modeling]:::phase
    P5[Phase 5<br/>Evaluation]:::phase
    P6[Phase 6<br/>Deployment]:::phase

    P1 --> P2 --> P3 --> P4 --> P5 --> P6
    P6 -. retrain trigger .-> P3

    A1[docs/business/objectives.md<br/>BO + DSO + KPI tree]:::artifact
    A2[notebooks/00_data_understanding_eda.py<br/>EDA + quality audit]:::artifact
    A3a[services/data-ingest/<br/>Data Augmentation Module]:::artifact
    A3b[notebooks/10_granger_feature_selection.py<br/>Granger gate JSON]:::artifact
    A4[notebooks/06_07_08_09<br/>+ services/ai-service/]:::artifact
    A5[dashboard/app/model-evaluation<br/>+ /granger-causality lead-time]:::artifact
    A6[docker-compose.yml<br/>+ .github/workflows/ci-cd.yml]:::artifact

    P1 --> A1
    P2 --> A2
    P3 --> A3a
    P3 --> A3b
    P4 --> A4
    P5 --> A5
    P6 --> A6

    O_CICD[CI/CD<br/>GitHub Actions · ruff · pytest · build · push GHCR]:::ops
    O_OBS[Observability<br/>Prometheus · Grafana · Jaeger · Netdata · OTel]:::ops
    O_REG[Model registry<br/>model_registry table + ai-service /models/reload]:::ops
    O_MON[Monitoring<br/>agent_actions audit · pipeline_runs status · drift signals]:::ops

    O_CICD -.-> P6
    O_OBS  -.-> P6
    O_REG  -.-> P4
    O_REG  -.-> P6
    O_MON  -.-> P5
    O_MON  -.-> P6
```

**Reading:**

* The horizontal arrow chain is **CRISP-DM** (academic spine).
* The four green ops boxes are **MLOps overlay** (industrial evidence).
* Each phase maps to a real artifact path in the repo.
* The dashed back-arrow from Phase 6 → Phase 3 is the retrain loop: monitoring detects drift → Granger gate is rerun → models retrained on the updated feature set.
