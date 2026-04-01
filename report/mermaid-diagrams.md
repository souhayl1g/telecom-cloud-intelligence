# Mermaid Diagrams for Presentation Slides

All diagrams below are in Mermaid syntax. Paste directly into Dokie AI, Mermaid Live Editor, or any Mermaid-supporting tool.

---

## 1. Industrial Positioning: CEM - AI Agent - CVM

```mermaid
flowchart LR
    subgraph ADN["ADN L4 -- Highly Autonomous"]
        direction LR
        CEM["CEM
Huawei SmartCare
KPI / KQI / CEI
Demarcation"]
        AGENT["AI Operations Agent
Detect: Anomaly + SLA Risk
Decide: O+B Correlation
Act: Recommendations + Triggers
THIS IS OUR PROJECT"]
        CVM["CVM
Customer Value Mgmt
Churn / Upsell / Retain
Revenue Impact"]

        CEM -->|"OSS + Experience Data"| AGENT
        AGENT -->|"Actions + Intelligence"| CVM
    end
    AGENT <-->|"Cloud-Native
(Docker to HCS)"| CLOUD["Container Platform"]

    style AGENT fill:#8E44AD,color:#fff,stroke:#6C3483
    style CEM fill:#1ABC9C,color:#fff,stroke:#16A085
    style CVM fill:#E67E22,color:#fff,stroke:#CA6F1E
    style CLOUD fill:#3498DB,color:#fff,stroke:#2E86C1
```

---

## 2. Container Architecture (5 Services)

```mermaid
flowchart TB
    USER["User / CVM
REST Client"] -->|REST| APIGW
    TTDATA["TT Data
CSV / Excel"] -->|Ingest| WORKER

    subgraph DOCKER["Docker Compose"]
        APIGW["API Gateway
FastAPI :8000"]
        AI["AI Service
scikit-learn :8001"]
        WORKER["Pipeline Worker
5-phase orchestrator"]
        MINIO[("MinIO
Object Storage
:9000")]
        PG[("PostgreSQL 16
Serving Store
:5432")]

        APIGW -->|Read| PG
        WORKER -->|Inference| AI
        WORKER -->|Write| MINIO
        WORKER -->|Persist| PG
        AI -->|Artifacts| MINIO
    end

    style APIGW fill:#2E86AB,color:#fff
    style AI fill:#8E44AD,color:#fff
    style WORKER fill:#1ABC9C,color:#fff
    style MINIO fill:#3498DB,color:#fff
    style PG fill:#2ECC71,color:#fff
```

---

## 3. 5-Phase Pipeline

```mermaid
flowchart TB
    subgraph P1["Phase 1: Data Ingestion"]
        S1["Create MinIO buckets"]
        S2["Ingest OSS data from TT"]
        S3["Ingest BSS data from TT"]
        S4["Upload raw data to MinIO"]
        S5["Register datasets in PostgreSQL"]
        S1 --> S2 --> S3 --> S4 --> S5
    end
    subgraph P2["Phase 2: Feature Engineering"]
        S6["Process OSS: severity, QoS, load"]
        S7["Process BSS: ARPU, APPU, DOU"]
        S8["Aggregate 9+7 features"]
        S6 --> S7 --> S8
    end
    subgraph P3["Phase 3: AI Inference"]
        S9["SLA Risk Prediction via GBR"]
        S10["OSS Anomaly Detection via IF"]
        S11["BSS Anomaly Detection via IF"]
        S12["O+B Correlation: Pearson + Spearman"]
        S9 --> S10 --> S11 --> S12
    end
    subgraph P4["Phase 4: Decision and Action Engine"]
        S13["Evaluate ML outputs against rules"]
        S14["Generate action recommendations"]
        S15["Assign priority and confidence"]
        S13 --> S14 --> S15
    end
    subgraph P5["Phase 5: Curation and Persistence"]
        S16["Build curated dataset (OSS+BSS+AI+Actions)"]
        S17["Upload to MinIO curated layer"]
        S18["Persist all results to PostgreSQL"]
        S16 --> S17 --> S18
    end
    P1 --> P2 --> P3 --> P4 --> P5

    style P1 fill:#1ABC9C22,stroke:#1ABC9C
    style P2 fill:#2E86AB22,stroke:#2E86AB
    style P3 fill:#8E44AD22,stroke:#8E44AD
    style P4 fill:#E74C3C22,stroke:#E74C3C
    style P5 fill:#2ECC7122,stroke:#2ECC71
```

---

## 4. Three-Layer Data Lake

```mermaid
flowchart TB
    RAW["Raw Layer
Real TT data (anonymised)
MinIO bucket: raw"]
    PROC["Processed Layer
Feature-engineered
(severity, QoS, ARPU, APPU, DOU)
MinIO bucket: processed"]
    CUR["Curated Layer
Joined OSS+BSS+AI outputs + Actions
MinIO bucket: curated"]
    AI["AI Service
ML Inference"]

    RAW -->|"Clean + Feature Engineer"| PROC
    PROC -->|"Features"| AI
    PROC -->|"Join + Enrich + Act"| CUR
    AI -->|"Scores + Actions"| CUR

    style RAW fill:#1ABC9C,color:#fff
    style PROC fill:#2E86AB,color:#fff
    style CUR fill:#8E44AD,color:#fff
    style AI fill:#8E44AD,color:#fff
```

---

## 5. ML Model Pipeline with Action Engine

```mermaid
flowchart LR
    OSS["OSS Data
Real TT KPIs"]
    BSS["BSS Data
Real TT Subscribers"]
    FEAT["Feature
Engineering"]
    GBR["GBR
SLA Risk
score in 0 to 1"]
    IFOSS["IsolationForest
OSS Anomalies"]
    IFBSS["IsolationForest
BSS Anomalies"]
    CORR["Correlation
Pearson + Spearman"]
    ENGINE["Decision and
Action Engine
Rules + ML"]
    OUT["CVM Actions

Alerts
Churn Prevention
Upsell Triggers
Escalations"]

    OSS --> FEAT
    BSS --> FEAT
    FEAT --> GBR --> ENGINE
    FEAT --> IFOSS --> ENGINE
    FEAT --> IFBSS --> ENGINE
    FEAT --> CORR --> ENGINE
    ENGINE --> OUT

    style GBR fill:#8E44AD,color:#fff
    style IFOSS fill:#8E44AD,color:#fff
    style IFBSS fill:#8E44AD,color:#fff
    style CORR fill:#E67E22,color:#fff
    style ENGINE fill:#E74C3C,color:#fff
    style OUT fill:#2ECC71,color:#fff
    style FEAT fill:#2E86AB,color:#fff
    style OSS fill:#1ABC9C,color:#fff
    style BSS fill:#2ECC71,color:#fff
```

---

## 6. Data Ingestion Flow

```mermaid
flowchart LR
    CSV["CSV / Excel
from TT"]
    JSON["JSON / API
from Huawei"]
    INGEST["Data Ingest
Column mapping
Anonymisation
Validation"]
    SCHEMA["Schema
Validation"]
    RAW[("Raw Layer
MinIO / OBS")]
    SYNTH["Synthetic
Generator
(fallback)"]

    CSV --> INGEST
    JSON --> INGEST
    INGEST -->|Mapped| SCHEMA
    SCHEMA -->|Valid| RAW
    SYNTH -.->|fallback| SCHEMA

    style INGEST fill:#1ABC9C,color:#fff
    style SCHEMA fill:#2E86AB,color:#fff
    style RAW fill:#3498DB,color:#fff
```

---

## 7. ER Diagram (8 Tables)

```mermaid
erDiagram
    pipeline_runs {
        bigserial id PK
        text run_id UK
        text status
        timestamptz started_at
        timestamptz finished_at
    }
    dataset_registry {
        bigserial id PK
        text run_id FK
        text dataset_type
        text layer
        text object_key
        bigint row_count
    }
    model_registry {
        bigserial id PK
        text model_name
        text version
        text artifact_key
    }
    anomalies {
        bigserial id PK
        text run_id FK
        text cell_id
        text region
        float severity
        float value
    }
    sla_risk_scores {
        bigserial id PK
        text run_id FK
        text region
        float score
        jsonb explanation
    }
    correlation_insights {
        bigserial id PK
        text run_id FK
        text metric_x
        text metric_y
        text method
        float corr_value
        float p_value
    }
    revenue_anomalies {
        bigserial id PK
        text run_id FK
        text subscriber_id
        float severity
        float value
    }
    action_recommendations {
        bigserial id PK
        text run_id FK
        text action_type
        text target_entity
        float confidence
        text priority
        text explanation
        text status
        timestamptz created_at
    }

    pipeline_runs ||--o{ dataset_registry : "has"
    pipeline_runs ||--o{ anomalies : "produces"
    pipeline_runs ||--o{ sla_risk_scores : "produces"
    pipeline_runs ||--o{ correlation_insights : "produces"
    pipeline_runs ||--o{ revenue_anomalies : "produces"
    pipeline_runs ||--o{ action_recommendations : "generates"
    model_registry ||--o{ anomalies : "used_by"
    sla_risk_scores ||--o{ action_recommendations : "triggers"
```

---

## 8. HCS Mapping (Docker to Cloud)

```mermaid
flowchart LR
    subgraph LOCAL["Local (Docker Compose)"]
        LA["api-gateway
Docker"]
        LI["ai-service
Docker"]
        LW["pipeline-worker
Docker"]
        LM[("MinIO
Object Storage")]
        LP[("PostgreSQL 16")]
    end

    subgraph HCS["Huawei Cloud Stack"]
        HA["ECS/CCE
api-gateway"]
        HI["ECS/CCE
ai-service"]
        HW["ECS/CCE
worker"]
        HO[("OBS
Object Storage")]
        HR[("RDS
PostgreSQL")]
    end

    LA -.->|"same image"| HA
    LI -.->|"same image"| HI
    LW -.->|"same image"| HW
    LM -->|"S3 compatible"| HO
    LP -->|"same protocol"| HR

    style LA fill:#2E86AB,color:#fff
    style LI fill:#8E44AD,color:#fff
    style LW fill:#1ABC9C,color:#fff
    style HA fill:#2E86AB,color:#fff
    style HI fill:#8E44AD,color:#fff
    style HW fill:#1ABC9C,color:#fff
    style HCS fill:#CF0A2C11,stroke:#CF0A2C
```

---

## 9. HCS Target Architecture

```mermaid
flowchart TB
    EXT["CVM / Analyst
HTTPS"] --> ELB

    subgraph VPC["Huawei Cloud Stack -- VPC"]
        ELB["ELB
HTTPS Termination"]
        API["ECS
api-gateway"]
        AI["ECS
ai-service"]
        WK["ECS
pipeline-worker"]
        OBS[("OBS
raw / proc / curated")]
        RDS[("RDS
PostgreSQL managed")]

        ELB --> API
        WK --> AI
        WK --> OBS
        WK --> RDS
        API --> RDS
    end

    style ELB fill:#E67E22,color:#fff
    style API fill:#2E86AB,color:#fff
    style AI fill:#8E44AD,color:#fff
    style WK fill:#1ABC9C,color:#fff
    style VPC fill:#CF0A2C11,stroke:#CF0A2C
```

---

## 10. Gap Analysis

```mermaid
flowchart TB
    OSS["OSS Analytics
Network anomaly detection
KPI monitoring"]
    BSS["BSS Analytics
Revenue analytics
Churn prediction"]
    GAP["GAP
No correlation
No autonomous action"]
    OURS["Our AI Operations Agent
O+B Convergence | Real Data | Cloud-Native | Autonomous Actions | CEM to CVM"]

    OSS --- GAP --- BSS
    GAP -->|"We fill this"| OURS

    style OSS fill:#2E86AB,color:#fff
    style BSS fill:#2ECC71,color:#fff
    style GAP fill:#CF0A2C,color:#fff,stroke-dasharray: 5 5
    style OURS fill:#8E44AD,color:#fff
```

---

## 11. ADN Autonomy Levels

```mermaid
flowchart TB
    L5["L5 -- Fully Autonomous
Self-driving network"]
    L4["L4 -- Highly Autonomous
AI decides and acts -- OUR PROJECT"]
    L3["L3 -- Conditional Autonomy
AI recommends, human decides"]
    L2["L2 -- Partial
Some automated workflows"]
    L1["L1 -- Assisted
Manual operations"]

    L1 --> L2 --> L3 --> L4 --> L5

    style L4 fill:#8E44AD,color:#fff,stroke:#6C3483,stroke-width:3px
    style L1 fill:#BDC3C7,color:#2C3E50
    style L2 fill:#BDC3C7,color:#2C3E50
    style L3 fill:#BDC3C7,color:#2C3E50
    style L5 fill:#BDC3C7,color:#2C3E50
```

---

## 12. O+B Correlation Pairs

```mermaid
flowchart LR
    subgraph OSS["OSS Metrics"]
        T["throughput_mbps"]
        L["latency_ms"]
        P["packet_loss_pct"]
        S["signal_rsrp_dbm"]
    end

    subgraph BSS["BSS Metrics"]
        R["revenue_tnd"]
        C["churn_risk"]
        D["data_used_gb"]
    end

    T -->|"+ positive"| R
    L -->|"- negative"| R
    P -->|"+ positive"| C
    L -->|"- negative"| D
    S -->|"+ positive"| R

    style OSS fill:#2E86AB22,stroke:#2E86AB
    style BSS fill:#2ECC7122,stroke:#2ECC71
```

---

## 13. Decision and Action Engine Rules

```mermaid
flowchart TD
    ML["ML Outputs
SLA Risk, Anomalies, Correlations"]

    ML --> R1{"SLA Risk > 0.7?"}
    ML --> R2{"SLA Risk 0.4 to 0.7?"}
    ML --> R3{"OSS Anomaly +
Revenue Drop?"}
    ML --> R4{"BSS Anomaly +
Healthy Network?"}
    ML --> R5{"Significant O+B
Correlation?"}
    ML --> R6{"Multiple Anomalies
Same Region?"}

    R1 -->|Yes| A1["Proactive Alert
Priority: Critical"]
    R2 -->|Yes| A2["Watch Alert
Priority: Medium"]
    R3 -->|Yes| A3["Churn Prevention Campaign
Priority: High"]
    R4 -->|Yes| A4["Upsell Trigger
Priority: Medium"]
    R5 -->|Yes| A5["Insight Report
Priority: Low"]
    R6 -->|Yes| A6["Escalation Ticket
Priority: Critical"]

    style ML fill:#8E44AD,color:#fff
    style A1 fill:#E74C3C,color:#fff
    style A2 fill:#E67E22,color:#fff
    style A3 fill:#CF0A2C,color:#fff
    style A4 fill:#2ECC71,color:#fff
    style A5 fill:#3498DB,color:#fff
    style A6 fill:#E74C3C,color:#fff
```

---

## 14. Use Case Diagram

```mermaid
flowchart TB
    subgraph Actors
        OP["Network Operator
(NOC)"]
        CVM_A["CVM Analyst"]
        ADMIN["System Admin"]
    end

    subgraph System["AI Operations Agent"]
        UC1["View SLA Risk Scores"]
        UC2["View Network Anomalies"]
        UC3["View Revenue Anomalies"]
        UC4["View O+B Correlations"]
        UC5["View Action Recommendations"]
        UC6["Approve or Dismiss Action"]
        UC7["Trigger Pipeline Execution"]
        UC8["Monitor Pipeline Status"]
        UC9["Train / Retrain ML Models"]
    end

    OP --> UC1
    OP --> UC2
    OP --> UC5
    OP --> UC6
    CVM_A --> UC3
    CVM_A --> UC4
    CVM_A --> UC5
    CVM_A --> UC6
    ADMIN --> UC7
    ADMIN --> UC8
    ADMIN --> UC9

    style OP fill:#2E86AB,color:#fff
    style CVM_A fill:#E67E22,color:#fff
    style ADMIN fill:#1ABC9C,color:#fff
    style System fill:#8E44AD11,stroke:#8E44AD
```

---

## 15. Sequence Diagram: Pipeline Execution with Action Generation

```mermaid
sequenceDiagram
    participant TT as TT Data Source
    participant PW as Pipeline Worker
    participant ML as MinIO (Data Lake)
    participant AI as AI Service
    participant AE as Action Engine
    participant PG as PostgreSQL
    participant API as API Gateway

    Note over PW: Phase 1 - Data Ingestion
    TT->>PW: CSV / Excel files
    PW->>ML: Upload raw OSS + BSS data
    PW->>PG: Register datasets (metadata)

    Note over PW: Phase 2 - Feature Engineering
    PW->>PW: Process OSS (9 features)
    PW->>PW: Process BSS (7 features)
    PW->>ML: Upload processed features

    Note over PW: Phase 3 - AI Inference
    PW->>AI: POST /infer/sla-risk
    AI-->>PW: Risk score + importances
    PW->>AI: POST /infer/anomaly (OSS)
    AI-->>PW: Anomaly flags + severity
    PW->>AI: POST /infer/revenue-anomaly (BSS)
    AI-->>PW: Revenue anomaly flags
    PW->>PW: Compute O+B correlations

    Note over PW: Phase 4 - Decision and Action
    PW->>AE: Evaluate ML outputs
    AE->>AE: Apply business rules
    AE-->>PW: Action recommendations

    Note over PW: Phase 5 - Curation and Persistence
    PW->>ML: Upload curated dataset
    PW->>PG: Persist anomalies, risk, correlations
    PW->>PG: Persist action recommendations

    Note over API: CVM Consumption
    API->>PG: GET /actions (pending)
    PG-->>API: Action list with priority
    API->>PG: PATCH /actions/{id} (approve)
```

---

## 16. Sequence Diagram: Action Lifecycle

```mermaid
sequenceDiagram
    participant PW as Pipeline Worker
    participant AE as Action Engine
    participant PG as PostgreSQL
    participant API as API Gateway
    participant OP as NOC Operator
    participant CVM as CVM System

    PW->>AE: ML outputs (risk=0.83, anomaly=true)
    AE->>AE: Rule: SLA risk > 0.7
    AE->>PG: INSERT action (type=proactive_alert, priority=critical)

    PW->>AE: ML outputs (oss_anomaly + revenue_drop)
    AE->>AE: Rule: anomaly + correlated drop
    AE->>PG: INSERT action (type=churn_prevention, priority=high)

    OP->>API: GET /actions?status=pending
    API->>PG: Query pending actions
    PG-->>API: 2 actions returned
    API-->>OP: Action list

    OP->>API: PATCH /actions/1 (approve)
    API->>PG: UPDATE status=approved
    Note over CVM: Proactive alert dispatched

    CVM->>API: GET /actions?type=churn_prevention
    API-->>CVM: Churn prevention recommendations
    CVM->>CVM: Launch retention campaign
```

---

## 17. Competitive Comparison Matrix

```mermaid
flowchart TB
    subgraph Comparison["Competitive Positioning"]
        direction TB
        SELF["SELFNET
Self-healing 5G
No real data | No O+B | No actions"]
        ETSI["ETSI ZSM
Zero-touch management
Spec only | Partial O+B | Spec"]
        NOKIA["Nokia AVA
Telecom analytics
Real data | No O+B | No actions"]
        SMART["SmartCare
CEM + demarcation
Real data | Partial O+B | No actions"]
        OURS["OUR PROJECT
CEM-CVM Agent
Real data | Full O+B | Autonomous actions"]
    end

    style SELF fill:#BDC3C7,color:#2C3E50
    style ETSI fill:#BDC3C7,color:#2C3E50
    style NOKIA fill:#BDC3C7,color:#2C3E50
    style SMART fill:#BDC3C7,color:#2C3E50
    style OURS fill:#8E44AD,color:#fff,stroke:#6C3483,stroke-width:3px
```
