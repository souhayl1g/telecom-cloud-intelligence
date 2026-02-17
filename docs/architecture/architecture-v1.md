flowchart TB
  User["User / REST Client"]

  subgraph Docker["Docker Compose (Local PoC)"]
    APIGW["API Gateway\n(FastAPI)"]
    PIPE["Pipeline Worker\n(Ingestion/Processing/Correlation)"]
    AI["AI Service\n(Anomaly + SLA Risk)"]
    DB["PostgreSQL\n(Serving + Metadata)"]
    OBJ["Object Storage\n(MinIO / OBS)"]
  end

  User -->|HTTPS| APIGW
  APIGW -->|Read analytics| DB

  PIPE -->|Write datasets| OBJ
  PIPE -->|Write metadata/results| DB
  PIPE -->|Inference request| AI

  AI -->|Write anomalies/risk| DB
  AI -->|Store model artifacts| OBJ


sequenceDiagram
  autonumber
  participant U as User/Client
  participant G as API Gateway
  participant P as PostgreSQL
  participant W as Pipeline Worker
  participant A as AI Service
  participant O as Object Storage

  U->>G: GET /sla-risk?region=R&from=T1&to=T2
  G->>P: Query SLA risk scores
  alt Missing/Stale results
    G->>W: POST /jobs/run-inference (R,T1..T2)
    W->>O: Read processed features
    W->>A: POST /infer/sla-risk (features)
    A->>P: Write SLA risk results
  end
  P-->>G: SLA risk scores
  G-->>U: JSON response
