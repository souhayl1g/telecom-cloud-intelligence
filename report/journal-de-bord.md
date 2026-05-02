# Journal de Bord — Stage PFE

**Nom et Prénom :** Souhayl Guenichi  
**Spécialité :** Ingénierie Informatique  
**Organisme d'accueil :** Huawei Tunisia — Cloud IT / Sales-Solution  
**Projet :** Telecom NeXoligence Platform (NeXo)

---

## Semaine 1–2 : Découverte et cadrage du projet

**Qu'ai-je appris ?**  
J'ai découvert l'écosystème télécom de Huawei, notamment les systèmes OSS (Operational Support System) et BSS (Business Support System). J'ai compris le concept d'ADN (Autonomous Driving Network) et la problématique de convergence O+B entre Huawei SmartCare (CEM) et le CVM (Customer Value Management). J'ai appris que les opérateurs comme Tunisie Telecom exploitent des systèmes cloisonnés, sans couche d'intelligence les reliant.

**Quelles missions ai-je accomplies ?**  
- Étude de l'existant et benchmarking des solutions CEM/CVM
- Rédaction du cahier des charges et définition du périmètre fonctionnel
- Conception de l'architecture C4 (diagrammes de contexte, conteneurs, composants)
- Création des diagrammes de cas d'utilisation, séquence, ER et déploiement

**Compétences mobilisées :**  
Analyse des besoins, modélisation UML/C4, rédaction technique, communication avec l'équipe Huawei.

**Difficultés rencontrées :**  
Comprendre la terminologie télécom spécifique (KPI réseau : RSRP, throughput, packet loss, latency) et les flux de données entre CEM et CVM. J'ai dû consulter la documentation interne Huawei et poser beaucoup de questions à mon encadrant pour clarifier ces concepts.

---

## Semaine 3–4 : Phase 1 — Fondation et infrastructure

**Qu'ai-je appris ?**  
J'ai approfondi Docker et Docker Compose pour orchestrer un stack multi-conteneurs. J'ai appris à concevoir une architecture data lake à 3 couches (raw → processed → curated) avec MinIO comme stockage objet S3-compatible. J'ai également appris à concevoir un schéma PostgreSQL adapté aux besoins d'une plateforme AIOps.

**Quelles missions ai-je accomplies ?**  
- Mise en place du stack Docker Compose avec 7 conteneurs (PostgreSQL, MinIO, API Gateway, AI Service, Pipeline Worker, Prometheus, Grafana)
- Conception et implémentation du schéma PostgreSQL (7 tables : pipeline_runs, dataset_registry, model_registry, sla_risk_scores, anomalies, revenue_anomalies, correlation_insights)
- Implémentation du data lake MinIO à 3 couches
- Création du vertical slice : génération de données → ingestion MinIO → PostgreSQL → API REST

**Compétences mobilisées :**  
Docker, Docker Compose, PostgreSQL, MinIO/S3, architecture microservices, Python/FastAPI.

**Difficultés rencontrées :**  
La configuration réseau entre conteneurs Docker m'a posé des problèmes au début, notamment les health checks et l'ordre de démarrage des services. J'ai résolu cela en utilisant les depends_on avec conditions de santé.

---

## Semaine 5–6 : Phase 2 — ML et inférence réelle

**Qu'ai-je appris ?**  
J'ai appris à entraîner et déployer des modèles de machine learning dans un contexte de production. J'ai découvert le GradientBoostingRegressor pour le scoring de risque SLA et l'IsolationForest pour la détection d'anomalies. J'ai compris l'importance de la sélection des features et de la persistance des modèles avec joblib.

**Quelles missions ai-je accomplies ?**  
- Entraînement du modèle GradientBoostingRegressor v2.0 pour le scoring de risque SLA (3000 échantillons, 9 features KPI agrégés)
- Entraînement de 2 modèles IsolationForest v2.0 (détection d'anomalies OSS réseau + BSS revenus)
- Implémentation de l'orchestrateur pipeline 22 étapes (exécution toutes les 2 minutes)
- Persistance des artefacts de modèles dans les volumes Docker
- Exposition des endpoints d'inférence via FastAPI

**Compétences mobilisées :**  
scikit-learn, machine learning (régression, détection d'anomalies), feature engineering, FastAPI, architecture de pipeline de données.

**Difficultés rencontrées :**  
Le calibrage des modèles IsolationForest pour éviter les faux positifs a été un défi. J'ai dû expérimenter avec le paramètre contamination et valider les résultats manuellement. De plus, la gestion de la mémoire lors de l'entraînement sur le pipeline worker m'a obligé à optimiser le chargement des données.

---

## Semaine 7–8 : Phase 3 — Intégration des données et analytics

**Qu'ai-je appris ?**  
J'ai appris à modéliser un marché télécom réaliste (marché tunisien : 80% prépayé / 20% postpayé) et à injecter des fautes pour simuler des dégradations réseau. J'ai découvert les corrélations statistiques (Pearson + Spearman) pour quantifier les liens entre métriques OSS et BSS.

**Quelles missions ai-je accomplies ?**  
- Injection de fautes : simulation de dégradation de 2–3 cellules (effondrement throughput, pic de latence)
- Corrélation BSS associée (baisse de revenus, pics de churn)
- Analyse de corrélation Pearson + Spearman sur 5 paires de métriques OSS↔BSS (latency↔revenue, throughput↔data_usage, packet_loss↔churn, RSRP↔APPU, active_users↔DOU)
- Développement de l'API Gateway avec 7 endpoints
- Construction du dashboard Next.js avec 9+ pages (overview, SLA risk, anomalies, corrélations, pipeline runs, L4 agent workspace)

**Compétences mobilisées :**  
Next.js 14, React 18, TypeScript, Recharts, statistiques (corrélation), modélisation de données télécom, conception d'API REST.

**Difficultés rencontrées :**  
La visualisation des données de corrélation de manière intuitive sur le dashboard a nécessité plusieurs itérations de design. J'ai également dû gérer les appels API asynchrones côté frontend et la mise à jour en temps réel des graphiques.

---

## Semaine 9–10 : Phase 4 — Authentification, sécurité et CI/CD

**Qu'ai-je appris ?**  
J'ai appris à implémenter un système d'authentification complet avec JWT, OAuth2 (Google et GitHub), et le hachage de mots de passe avec bcrypt. J'ai découvert les bonnes pratiques de sécurité API (middleware d'authentification, RBAC). J'ai également appris à mettre en place un pipeline CI/CD avec GitHub Actions.

**Quelles missions ai-je accomplies ?**  
- Développement du service d'authentification complet (FastAPI, port 8002)
  - Inscription/connexion email + mot de passe avec bcrypt
  - Intégration OAuth2 Google et GitHub
  - Tokens JWT (expiration 24h)
  - Fusion de comptes (même email, différents providers)
  - Contrôle d'accès basé sur les rôles (viewer, analyst, admin)
- Intégration auth dans le dashboard (pages signup/login, callback OAuth, cookies httpOnly, middleware Next.js)
- Pipeline CI/CD GitHub Actions en 6 étapes (lint ruff, tests pytest, build Docker, tests d'intégration, scan sécurité pip-audit, déploiement)

**Compétences mobilisées :**  
Sécurité applicative, JWT, OAuth2, bcrypt, GitHub Actions, CI/CD, tests automatisés, conteneurisation.

**Difficultés rencontrées :**  
L'intégration OAuth2 avec les callbacks et la gestion des tokens entre le frontend Next.js et le backend FastAPI m'a demandé beaucoup de débogage. Le pipeline CI/CD a aussi nécessité plusieurs itérations pour résoudre les erreurs de lint ruff et configurer correctement les services PostgreSQL dans les runners GitHub.

---

## Semaine 11–12 : Phase 5–6 — UX avancée et branding

**Qu'ai-je appris ?**  
J'ai appris l'importance du branding et de l'expérience utilisateur dans un produit professionnel. J'ai découvert comment implémenter une Command Palette (Ctrl+K) pour la navigation rapide, un pattern UX moderne utilisé dans les outils développeur.

**Quelles missions ai-je accomplies ?**  
- Rebranding complet de la plateforme sous le nom "NeXo"
- Implémentation de la Command Palette (Ctrl+K) pour navigation rapide
- Mise en valeur du L4 Agent CTA (Call-To-Action)
- Création de la page Data Warehouse
- Amélioration globale du styling et de l'UX du dashboard
- Documentation technique complète (spécifications, diagrammes, guides de déploiement)

**Compétences mobilisées :**  
UX/UI design, React avancé, branding produit, rédaction de documentation technique.

**Difficultés rencontrées :**  
Trouver le bon équilibre entre une interface riche en fonctionnalités et une expérience utilisateur fluide et intuitive. La Command Palette a nécessité une gestion fine des raccourcis clavier et des conflits avec les raccourcis navigateur.

---

## Bilan général à mi-parcours

Ce stage m'a permis de développer une plateforme cloud-native complète, de bout en bout. J'ai acquis des compétences techniques solides en architecture microservices, machine learning appliqué aux télécommunications, et DevOps. Le travail au sein de l'équipe Huawei Tunisia m'a donné une vision concrète du métier d'ingénieur cloud dans le secteur télécom. La prochaine étape est le déploiement sur Huawei Cloud Stack (HCS) et l'intégration des données réelles de Tunisie Telecom.
