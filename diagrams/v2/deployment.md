# Physical Deployment — Cloud-Native (no HCS lock-in)

```mermaid
flowchart TB
    subgraph host[Single Docker host · ECS / CCE / Kubernetes / Nomad portable]
        direction TB
        subgraph net[Docker bridge network · telecom-net]
            direction LR

            subgraph data[Data tier]
                PG[(postgres:16<br/>vol pgdata)]
                MN[(minio<br/>vol minio_data)]
            end

            subgraph svc[Service tier]
                GW[api-gateway<br/>:8000]
                AI[ai-service<br/>:8001]
                AUTH[auth-service<br/>:8002]
                AGENT[agent-service<br/>:8003]
                WORK[pipeline-worker]
                NB[notebooks<br/>:8888]
            end

            subgraph edge[Edge tier]
                UI[dashboard<br/>:3001 · next start]
            end

            subgraph obs[Observability tier]
                PROM[prometheus :9090]
                GRAF[grafana :3000]
                JAEG[jaeger :16686]
                NET[netdata :19999]
                OTEL[otel-collector<br/>:4319 / :4320]
            end
        end

        OLLAMA[Ollama on host<br/>qwen2.5:7b · :11434]
    end

    BROWSER([Browser / NOC console])
    BROWSER -->|HTTPS| UI
    UI -->|JWT cookie| GW
    AGENT -->|HTTP loopback| OLLAMA
    GW <--> PG
    WORK <--> PG
    WORK <--> MN
    AI <--> WORK
    GRAF <--> PROM
    JAEG <--- OTEL
```

**Cloud-native properties claimed:**

| Property | Evidence |
|---|---|
| 12-factor (config in env) | `.env.example`, `docker-compose.yml` env stanzas |
| Stateless services | All FastAPI services rebuild from PG state on restart |
| Horizontal scalability | Each service is a stateless container with health endpoint |
| Observability | `/metrics` on every FastAPI + OTLP traces + Netdata + Jaeger |
| Reproducibility | `Dockerfile` + `requirements.txt` per service + GitHub Actions CI |
| Portability | Identical compose runs on Docker desktop, ECS, CCE, Kubernetes, Nomad |

**Out-of-scope:** Huawei Cloud Stack OBS/RDS/ECS mapping. Removed from defense narrative; appendix-only.
