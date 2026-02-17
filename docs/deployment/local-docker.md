```mermaid
flowchart LR
  subgraph Local["Local (Docker Compose)"]
    APIGW["api-gateway\n:8080"]
    PIPE["pipeline-worker"]
    AI["ai-service"]
    DB["postgres"]
    OBJ["minio"]
  end

  User["User / REST Client"] --> APIGW
  APIGW --> DB
  PIPE --> OBJ
  PIPE --> AI
  AI --> DB
  AI --> OBJ

  subgraph HCS["Huawei Cloud Stack"]
    ECS["ECS"]
    OBS["OBS"]
    RDS["RDS"]
    VPC["VPC"]
  end

  APIGW -.maps to .-> ECS
  PIPE  -.maps to .-> ECS
  AI    -.maps to .-> ECS
  OBJ   -.maps to .-> OBS
  DB    -.maps to .-> RDS
  Local -.runs inside .-> VPC
```