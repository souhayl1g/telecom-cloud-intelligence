# Email — Data Request for AI Operations Agent Project

**Subject:** Demande de données OSS/BSS — Projet PFE Cloud-Native AI Operations Agent (ESPRIT / Huawei Tunisia)

---

Bonjour,

Je me permets de vous contacter dans le cadre de mon projet de fin d'études (PFE) réalisé chez **Huawei Tunisia**, en partenariat avec **ESPRIT**, sous la supervision de [Nom du superviseur].

## Objet

Je développe une plateforme **Cloud-Native AI Operations Agent** qui constitue la couche d'intelligence entre le **CEM (Huawei SmartCare)** et le **CVM (Customer Value Management)**. Cette plateforme :

- Ingère les KPIs réseau (OSS) et les données abonnés/revenus (BSS)
- Applique 3 modèles de Machine Learning : prédiction de risque SLA, détection d'anomalies réseau, détection d'anomalies de revenus
- Calcule les corrélations croisées OSS↔BSS
- Produit des scores de risque, alertes et insights actionnables pour le CVM

La plateforme est **actuellement opérationnelle** avec des données synthétiques (Docker, 5 services, pipeline de 22 étapes, 3 modèles ML, 7 endpoints REST). Pour passer à la validation industrielle, j'ai besoin de **données réelles anonymisées** de Tunisie Telecom.

## Données demandées

### 1. Données OSS (KPIs réseau)

| Champ | Type | Unité |
|-------|------|-------|
| cell_id / eNodeB_id | string | — |
| **throughput_dl_mbps** | float | Mbps |
| **latency_rtt_ms** | float | ms |
| **packet_loss_pct** | float | % |
| **active_ue_count** | integer | — |
| **rsrp_dbm** | float | dBm |
| region / site_name | string | — |
| timestamp | datetime | — |

**Volume souhaité :** 3+ mois de données, 50+ cellules, granularité 15 min ou horaire.

**Nice-to-have :** rsrq_db, sinr_db, cqi, prb_utilization_pct, handover_success_rate

### 2. Données BSS (SmartCare / Abonnés / Revenus)

| Champ | Type | Unité |
|-------|------|-------|
| subscriber_id / MSISDN | string | — |
| operator | string | — |
| line_type (prepaid/postpaid) | string | — |
| plan / forfait_code | string | — |
| **revenue_tnd** | float | TND |
| **data_used_gb** | float | GB |
| **voice_min** | float | minutes |
| **sms_count** | integer | — |
| **churn_risk** | float | 0–1 |
| appu_tnd | float | TND |
| dou_gb | float | GB |
| region / gouvernorat | string | — |
| serving_cell | string | — |
| timestamp / period | datetime | — |

**Volume souhaité :** 3+ mois de données, 5 000+ abonnés, mix ~80% prépayé / 20% postpayé.

### 3. Données SmartCare / CEM (optionnel mais à haute valeur)

- Scores KQI / CEI par service par cellule
- Résultats de démarcation (RAN / Transport / Core / Terminal)
- Alertes d'expérience SmartCare

## Format accepté

- **CSV** (préféré), Excel, JSON, ou Parquet
- Plusieurs fichiers par domaine acceptés (ex : un fichier par mois)

## Engagements de confidentialité

- Toutes les données personnelles seront **anonymisées** (hachage SHA-256)
- Aucun MSISDN, nom, adresse ou NIN ne sera stocké en clair
- Précision géographique limitée au gouvernorat
- Les données servent uniquement à l'entraînement et la validation des modèles AI dans le cadre du PFE

## Pièces jointes

1. **Présentation du projet** — vue d'ensemble architecture, modèles AI, positionnement CEM→Agent→CVM
2. **Document technique** — documentation complète du système (architecture, pipeline, schéma DB, modèles ML)
3. **Spécification des données** — document détaillé des champs requis, volumes et formats (data-requirements.md)

## Ce que les données produiront

Avec les données réelles de Tunisie Telecom, la plateforme délivrera :

- **Scores de risque SLA** par region (0.0–1.0) avec explication des KPIs contributeurs
- **Alertes d'anomalies réseau** par cellule avec scores de sévérité
- **Alertes d'anomalies de revenus** par abonné (fraude, SIM dormantes, pics de churn)
- **Corrélations OSS↔BSS** (latence↔revenu, packet_loss↔data_usage, etc.)
- **3 modèles AI validés** sur données réelles d'opérateur tunisien (v3.0)

Toute la plateforme est prête à ingérer les données dès réception. Le pipeline supporte un mode dual (données réelles + synthétiques comme fallback).

Je reste à votre entière disposition pour toute question ou précision complémentaire.

Cordialement,

**Souhayl Guenichi**  
Étudiant ingénieur — ESPRIT  
Stagiaire — Huawei Tunisia (Cloud IT / Sales-Solution)  
[Email]  
[Téléphone]

---

*Note: Cette demande a été validée par mon encadrant chez Huawei Tunisia.*
