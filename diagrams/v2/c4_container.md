# C4 Level 2 — Containers

```mermaid
flowchart TB
    subgraph Dashboard
        UI[dashboard<br/>Next.js 14 · TS · :3001]
    end

    subgraph API
        GW[api-gateway<br/>FastAPI · :8000]
        AUTH[auth-service<br/>FastAPI · :8002]
        AGENT[agent-service<br/>LLM orchestrator · :8003]
    end

    subgraph ML
        AI[ai-service<br/>LightGBM · VAE · XGBoost · :8001]
        MODELS[(models<br/>.joblib + .pt)]
    end

    subgraph Pipeline
        WORK[pipeline-worker<br/>22-step ETL daemon]
        NB[notebooks<br/>Jupyter · training + EDA]
    end

    subgraph Storage
        PG[(postgres :5432<br/>9 tables + mat views)]
        MN[(minio :9000<br/>raw / processed / curated)]
    end

    subgraph Observability
        PROM[prometheus :9090]
        GRAF[grafana :3000]
        JAEG[jaeger :16686]
        NET[netdata :19999]
        OTEL[otel-collector :4319/4320]
    end

    UI -->|JWT cookie · /api/platform-data| GW
    UI -->|login / signup| AUTH
    UI -->|LLM chat| AGENT
    GW --> PG
    AGENT --> AI
    AGENT --> GW
    AI --> MODELS
    WORK --> PG
    WORK --> MN
    WORK --> AI
    NB --> PG
    NB --> MN
    GW -. /metrics .-> PROM
    AI -. /metrics .-> PROM
    AUTH -. /metrics .-> PROM
    AGENT -. /metrics .-> PROM
    PROM --> GRAF
    GW -. OTLP traces .-> OTEL
    OTEL --> JAEG
    NET -. host metrics .-> GRAF
```

**Spirits & Mates** (logical, run inside ai-service + agent-service):

| Type | Name | Container |
|---|---|---|
| Spirit | ExperienceSpirit (CEM LightGBM) | ai-service |
| Spirit | NetworkSpirit (VAE) | ai-service |
| Spirit | UnderserviceSpirit (XGBoost) | ai-service |
| Spirit | ConvergenceSpirit (Granger) | pipeline-worker + api-gateway |
| Spirit | ActionSpirit (playbooks) | api-gateway + agent-service |
| Mate | NOCMate (LLM chat) | agent-service + dashboard l4-agent |
| Mate | AnalystMate (RCA narratives) | dashboard /intelligence |
| Mate | FieldMate (playbook explainability) | dashboard l4-agent execution tab |
