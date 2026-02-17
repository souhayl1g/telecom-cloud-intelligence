flowchart TB

    USER["User / REST Client"]

    subgraph Docker["Docker Compose Environment (Local PoC)"]

        APIGW["API Gateway
(FastAPI REST Service)"]

        PIPE["Pipeline Worker
(Data Ingestion & Orchestration)"]

        AI["AI Service
(Anomaly Detection & SLA Risk)"]

        DB["PostgreSQL
(Metadata & Serving Layer)"]

        OBJ["Object Storage
(MinIO / OBS on HCS)"]

    end

    USER -->|HTTPS Requests| APIGW
    APIGW -->|Read Queries| DB

    PIPE -->|Inference Request| AI
    AI -->|Anomalies & SLA Scores| DB

    PIPE -->|Write Data| OBJ
    AI -->|Store Models| OBJ
