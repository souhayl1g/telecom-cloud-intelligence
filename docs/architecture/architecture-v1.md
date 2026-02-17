# Architecture v1 — Container Diagram (C4 Level 2)

This diagram presents the container-level architecture of the Cloud-Native Telecom Intelligence Platform.

It illustrates the main microservices, storage components, and their interactions within the Docker-based local deployment environment.

---

## Container Architecture (C4 Level 2)

```mermaid
flowchart LR

    subgraph Docker["Docker Compose Environment (Local PoC)"]

        APIGW["API Gateway\n(FastAPI REST Service)"]

        PIPE["Pipeline Worker\n(Data Ingestion & Orchestration)"]

        AI["AI Service\n(Anomaly Detection & SLA Risk Scoring)"]

        DB["PostgreSQL\n(Metadata & Serving Layer)"]

        OBJ["Object Storage\n(MinIO locally / OBS on HCS)"]

    end

    USER["User / REST Client"]

    USER -->|HTTPS Requests| APIGW

    APIGW -->|Read Queries| DB

    PIPE -->|Write Raw/Processed/Curated Data| OBJ
    PIPE -->|Metadata & Correlation Results| DB
    PIPE -->|Inference Requests| AI

    AI -->|Model Artifacts| OBJ
    AI -->|Anomalies & SLA Scores| DB
