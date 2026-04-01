# Data Requirements Specification

**Project:** Cloud-Native AI Operations Agent for CEM–CVM Intelligence (HCS-Ready)  
**Author:** Souhayl Guenichi — ESPRIT / Huawei Tunisia  
**Date:** March 12, 2026  
**Version:** 1.0

---

## 1. Project Summary

This platform is the **AI intelligence layer** between Huawei SmartCare (CEM) and Customer Value Management (CVM). It ingests OSS network KPIs and BSS subscriber/revenue data, applies 3 ML models (SLA risk prediction, OSS anomaly detection, BSS revenue anomaly detection) and statistical correlation analysis, then outputs actionable intelligence: SLA breach risk scores, anomaly alerts, and cross-domain OSS↔BSS correlation insights.

```
[CEM / SmartCare] ──→ [AI Operations Agent] ──→ [CVM]
     OSS + BSS data                  Business decisions
```

The platform is currently operational with synthetic data. To move to production-grade validation and model retraining, **real anonymised data from Tunisie Telecom** is required.

---

## 2. Data Needed — Overview

| Domain | Source System | Purpose |
|--------|-------------|---------|
| **OSS KPIs** | RAN / NOM / Huawei SmartCare | SLA risk prediction, network anomaly detection |
| **BSS Subscriber & Revenue** | SmartCare BSS / CRM / Billing | Revenue anomaly detection, churn correlation |
| **OSS↔BSS Correlation** | Both sources joined | Cross-domain impact analysis |

---

## 3. OSS Data Requirements (Network KPIs)

### 3.1 Required Fields

| # | Field Name | Type | Unit | Description | Priority |
|---|-----------|------|------|-------------|----------|
| 1 | `cell_id` / `eNodeB_id` | string | — | Cell or eNodeB identifier | **Required** |
| 2 | `throughput_dl_mbps` | float | Mbps | Downlink throughput per cell | **Required** |
| 3 | `latency_rtt_ms` | float | ms | Round-trip time latency | **Required** |
| 4 | `packet_loss_pct` | float | % | Packet loss rate | **Required** |
| 5 | `active_ue_count` | integer | — | Number of active UEs (connected users) | **Required** |
| 6 | `rsrp_dbm` | float | dBm | Reference Signal Received Power | **Required** |
| 7 | `region` / `site_name` | string | — | Geographic region or site identifier | **Required** |
| 8 | `timestamp` | datetime | — | Measurement timestamp (minute-level preferred) | **Required** |

### 3.2 Nice-to-Have OSS Fields

| # | Field Name | Type | Unit | Description |
|---|-----------|------|------|-------------|
| 9 | `rsrq_db` | float | dB | Reference Signal Received Quality |
| 10 | `sinr_db` | float | dB | Signal-to-Interference-plus-Noise Ratio |
| 11 | `cqi` | integer | — | Channel Quality Indicator (0–15) |
| 12 | `prb_utilization_pct` | float | % | Physical Resource Block utilization |
| 13 | `handover_success_rate` | float | % | Inter-cell handover success rate |
| 14 | `rab_drop_rate` | float | % | RAB (Radio Access Bearer) drop rate |
| 15 | `cell_availability_pct` | float | % | Cell uptime percentage |
| 16 | `throughput_ul_mbps` | float | Mbps | Uplink throughput |

### 3.3 OSS Data — Volume & Granularity

| Parameter | Requirement |
|-----------|------------|
| **Temporal granularity** | 15-minute or hourly aggregation (minute-level if available) |
| **Time span** | Minimum 3 months (6+ months preferred for seasonal patterns) |
| **Geographic scope** | Multiple gouvernorats / regions (diversity needed for model robustness) |
| **Number of cells** | 50+ cells minimum (200+ preferred) |
| **Estimated rows** | ~100,000–500,000 records |

### 3.4 How OSS Data Is Used

| AI Model | Features Used | Output |
|----------|--------------|--------|
| **SLA Risk Scorer** (GradientBoostingRegressor) | mean/std/max latency, mean/max packet_loss, mean/std throughput, mean active_users, mean RSRP | Risk score 0.0–1.0 with feature importances |
| **OSS Anomaly Detector** (IsolationForest) | All 5 KPI metrics per record | Anomaly flag + severity score per record |
| **OSS↔BSS Correlation** | throughput, latency, packet_loss, active_users, RSRP | Pearson + Spearman correlation with BSS metrics |

---

## 4. BSS Data Requirements (Subscriber & Revenue)

### 4.1 Required Fields

| # | Field Name | Type | Unit | Description | Priority |
|---|-----------|------|------|-------------|----------|
| 1 | `subscriber_id` / `MSISDN` | string | — | Subscriber identifier (will be anonymised) | **Required** |
| 2 | `operator` | string | — | Operator name (TT, Orange, Ooredoo) | **Required** |
| 3 | `line_type` | string | — | "prepaid" or "postpaid" | **Required** |
| 4 | `plan` / `forfait_code` | string | — | Subscribed plan/forfait | **Required** |
| 5 | `revenue_tnd` | float | TND | Revenue generated (recharge or billing amount) | **Required** |
| 6 | `data_used_gb` | float | GB | Data consumption | **Required** |
| 7 | `voice_min` | float | minutes | Voice call duration | **Required** |
| 8 | `sms_count` | integer | — | SMS sent count | **Required** |
| 9 | `churn_risk` | float | 0–1 | Churn probability indicator | **Required** |
| 10 | `region` / `gouvernorat` | string | — | Subscriber's serving region | **Required** |
| 11 | `serving_cell` | string | — | Serving cell ID (for OSS↔BSS join) | **Required** |
| 12 | `timestamp` / `period` | datetime | — | Period of the record | **Required** |

### 4.2 Nice-to-Have BSS Fields

| # | Field Name | Type | Unit | Description |
|---|-----------|------|------|-------------|
| 13 | `appu_tnd` | float | TND | Average Purchase Per User (per recharge event) |
| 14 | `dou_gb` | float | GB | Data of Use (monthly data consumption profile) |
| 15 | `tenure_months` | integer | months | How long the subscriber has been active |
| 16 | `complaint_count` | integer | — | Number of complaints filed |
| 17 | `recharge_frequency` | integer | — | Number of recharges per period (prepaid) |
| 18 | `service_type` | string | — | Primary service usage (data/voice/mixed) |
| 19 | `device_category` | string | — | Smartphone / feature phone / MBB |
| 20 | `arpu_category` | string | — | Low (<10 TND) / Mid (<40 TND) / High (≥40 TND) |

### 4.3 BSS Data — Volume & Granularity

| Parameter | Requirement |
|-----------|------------|
| **Temporal granularity** | Daily or weekly aggregation (monthly minimum) |
| **Time span** | Minimum 3 months (6+ months preferred) |
| **Subscriber mix** | ~80% prepaid / 20% postpaid (reflects Tunisian market) |
| **Number of subscribers** | 5,000+ unique subscribers (10,000+ preferred) |
| **Estimated rows** | ~50,000–200,000 records |

### 4.4 How BSS Data Is Used

| AI Model | Features Used | Output |
|----------|--------------|--------|
| **Revenue Anomaly Detector** (IsolationForest) | revenue_tnd, data_used_gb, voice_min, sms_count, churn_risk, appu_tnd, dou_gb | Anomaly flag + severity (fraud, dormant SIM, churn spike) |
| **OSS↔BSS Correlation** | revenue_tnd, data_used_gb, voice_min, sms_count, churn_risk | Cross-domain correlation with OSS KPIs |

---

## 5. SmartCare / CEM Data (Optional but High-Value)

If available from Huawei SmartCare exports at Tunisie Telecom:

| # | Field Name | Type | Description |
|---|-----------|------|-------------|
| 1 | `kqi_score` | float | Key Quality Indicator per service per cell |
| 2 | `cei_score` | float | Customer Experience Index per subscriber |
| 3 | `demarcation_result` | string | Root cause layer (RAN / Transport / Core / Terminal) |
| 4 | `experience_alert_type` | string | Alert category from SmartCare |
| 5 | `service_type` | string | Service monitored (VoLTE, HTTP, Video, Gaming) |
| 6 | `affected_subscribers` | integer | Number of impacted subscribers per event |

---

## 6. Data Format & Delivery

### Accepted Formats

| Format | Support |
|--------|---------|
| **CSV** | Preferred — easiest to ingest |
| **Excel (.xlsx)** | Supported |
| **JSON** | Supported |
| **Parquet** | Supported |

### Delivery Method

- Files can be delivered via secure file transfer or shared drive
- Multiple files per domain are acceptable (e.g., one file per month)
- Column headers should match or be mappable to the field names above

---

## 7. Anonymisation & Privacy

All personal data will be anonymised before processing:

| Element | Method |
|---------|--------|
| MSISDN / subscriber_id | SHA-256 hash with salt → pseudonymised ID |
| Name / address / NIN | Stripped entirely — not needed |
| Geographic precision | Gouvernorat-level only — no GPS coordinates |
| Cell IDs | Can be mapped to opaque IDs if required |
| Temporal precision | Minute-level granularity preserved (needed for correlation) |

**Commitment:** No personal subscriber data is stored in clear text at any stage. Only anonymised, aggregated data is used for AI model training.

---

## 8. What the Data Will Produce

With real data from Tunisie Telecom, the platform will deliver:

| Output | Description |
|--------|-------------|
| **SLA Risk Scores** | Per-region risk prediction (0.0–1.0) with top contributing KPIs |
| **Network Anomaly Alerts** | Per-cell anomaly detection with severity scores |
| **Revenue Anomaly Alerts** | Per-subscriber fraud/dormancy/churn-spike detection |
| **OSS↔BSS Correlations** | 10 cross-domain correlations per run (e.g., latency↔revenue, packet_loss↔data_usage) |
| **Validated AI Models** | 3 models retrained on real Tunisian operator data (v3.0) |
| **Industrial Proof** | "Trained on anonymised production data from TT via Huawei" — PFE defense differentiator |

---

## 9. Summary Table — All Required Data

| # | Field | Domain | Required |
|---|-------|--------|----------|
| 1 | cell_id / eNodeB_id | OSS | Yes |
| 2 | throughput_dl_mbps | OSS | Yes |
| 3 | latency_rtt_ms | OSS | Yes |
| 4 | packet_loss_pct | OSS | Yes |
| 5 | active_ue_count | OSS | Yes |
| 6 | rsrp_dbm | OSS | Yes |
| 7 | region / site_name | OSS | Yes |
| 8 | timestamp | OSS | Yes |
| 9 | subscriber_id / MSISDN | BSS | Yes |
| 10 | operator | BSS | Yes |
| 11 | line_type | BSS | Yes |
| 12 | plan / forfait_code | BSS | Yes |
| 13 | revenue_tnd | BSS | Yes |
| 14 | data_used_gb | BSS | Yes |
| 15 | voice_min | BSS | Yes |
| 16 | sms_count | BSS | Yes |
| 17 | churn_risk | BSS | Yes |
| 18 | region / gouvernorat | BSS | Yes |
| 19 | serving_cell | BSS | Yes |
| 20 | timestamp / period | BSS | Yes |
