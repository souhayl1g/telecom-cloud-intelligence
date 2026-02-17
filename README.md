# Cloud-Native Telecom Intelligence Platform with AI Operations Agent (HCS-Ready)

In an era where every millisecond of network degradation can translate into revenue loss and customer dissatisfaction, telecom operators require intelligence that connects operational performance to business impact.

## What this project delivers
A cloud-native, containerized telecom intelligence platform that:
- ingests **synthetic OSS KPI** data and **synthetic BSS usage/revenue** data
- structures data into a **3-layer data lake** (raw / processed / curated)
- applies AI for **anomaly detection** and **SLA risk scoring**
- computes **OSS–BSS correlation** (performance ↔ revenue impact)
- exposes insights through **REST APIs**
- runs locally via **Docker Compose** and is designed for **Huawei Cloud Stack portability**

## System Context (C4 Level 1)

```mermaid
flowchart TB
    subgraph System["Cloud-Native Telecom Intelligence Platform (HCS-Ready)"]
        Platform["AI-Powered Telecom Intelligence Platform"]
    end

    Ops["Telecom Operations Engineer"]
    Biz["Business Analyst"]
    Client["REST Client / Dashboard"]
    HCS["Huawei Cloud Stack (ECS, OBS, RDS, VPC)"]

    Ops -->|Queries KPIs, anomalies, SLA risk| Platform
    Biz -->|Queries revenue impact and correlation| Platform
    Client -->|HTTPS REST API| Platform
    Platform -->|Designed for deployment on| HCS
