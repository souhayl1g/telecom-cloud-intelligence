# Bilan Périodique — Début de stage (6ème semaine)

**Nom et Prénom :** Souhayl Guenichi  
**Spécialité :** Ingénierie Informatique  
**Organisme d'accueil :** Huawei Tunisia — Cloud IT / Sales-Solution

---

## Qu'est-ce qui vous plaît et vous motive dans votre stage ?

Ce qui me plaît le plus dans ce stage, c'est la possibilité de travailler sur un projet concret avec un impact réel dans le secteur des télécommunications. Concevoir une plateforme AIOps qui relie les systèmes OSS et BSS pour un opérateur comme Tunisie Telecom me donne le sentiment de résoudre un vrai problème industriel. J'apprécie également l'autonomie qui m'est accordée pour les choix techniques (architecture microservices, choix des technologies, design des modèles ML) et l'environnement international de Huawei qui m'expose à des pratiques et standards de niveau mondial.

---

## Décrivez une situation de travail marquante que vous avez vécu pendant votre stage.

La mise en place du pipeline d'inférence ML complet a été une situation marquante. J'ai dû concevoir un orchestrateur en 22 étapes qui s'exécute toutes les 2 minutes : il génère les données réseau, les ingère dans le data lake MinIO, entraîne les modèles de machine learning (GradientBoostingRegressor pour le scoring SLA, IsolationForest pour la détection d'anomalies), exécute l'inférence, et persiste les résultats dans PostgreSQL. Voir le système fonctionner de bout en bout pour la première fois — des données brutes jusqu'aux scores de risque affichés sur le dashboard — a été un moment très satisfaisant et m'a donné confiance dans l'architecture que j'avais conçue.

---

## Avez-vous vécu pendant votre stage une situation difficile ou problématique ? Si oui, comment avez-vous réagi ?

Oui, l'intégration du système d'authentification OAuth2 (Google + GitHub) avec le frontend Next.js a été particulièrement problématique. Les callbacks OAuth ne fonctionnaient pas correctement à cause de la gestion des tokens entre le backend FastAPI et le frontend. Les cookies httpOnly n'étaient pas transmis correctement en cross-origin, et le middleware Next.js rejetait les requêtes authentifiées. J'ai réagi méthodiquement : j'ai d'abord isolé le problème en testant chaque composant individuellement (auth-service seul, puis avec le dashboard), j'ai consulté la documentation officielle de Next.js et FastAPI, et j'ai itéré jusqu'à trouver la bonne configuration CORS et cookie. Cette expérience m'a appris l'importance du débogage systématique et de la patience face à des problèmes d'intégration complexes.

---

## Que retirez-vous comme apprentissages depuis le début de votre stage ?

- **Culture d'entreprise :** Huawei fonctionne avec une rigueur technique très élevée et une culture de documentation exhaustive. Chaque décision technique doit être justifiée et documentée.
- **Secteur télécom :** J'ai découvert la complexité des réseaux 5G, les KPI réseau (RSRP, throughput, latency, packet loss), et la problématique de convergence OSS/BSS. Le marché tunisien des télécoms (80% prépayé) a ses spécificités qui influencent la modélisation des données.
- **Métier d'ingénieur cloud :** J'ai compris qu'un ingénieur cloud doit maîtriser à la fois l'infrastructure (Docker, orchestration), le développement (microservices, API), la data (ML, pipelines), et les opérations (CI/CD, monitoring). C'est un métier transversal qui demande de la polyvalence.

---

## Comment gérez-vous les délais dans votre travail ?

J'organise mon travail en phases clairement définies avec des livrables précis pour chacune. J'ai découpé le projet en 10 phases progressives, chaque phase construisant sur la précédente. J'utilise un diagramme de Gantt pour suivre l'avancement global et je fixe des objectifs hebdomadaires. Quand une tâche prend plus de temps que prévu (comme l'intégration OAuth2), je réévalue mes priorités et je communique avec mon encadrant pour ajuster le planning. Le fait d'avoir un pipeline CI/CD automatisé me permet aussi de détecter rapidement les régressions et de maintenir un rythme de développement soutenu.

---

## De quelle(s) manière(s) utilisez-vous vos capacités/talents dans votre stage ?

J'utilise mes compétences en développement full-stack pour concevoir et implémenter l'ensemble de la plateforme, du backend Python/FastAPI au frontend Next.js/React. Ma capacité d'apprentissage rapide m'a permis de monter en compétence sur des domaines que je ne maîtrisais pas initialement, comme le machine learning appliqué aux télécoms et l'architecture cloud Huawei (HCS). Mon sens de l'organisation me permet de gérer un projet complexe avec de nombreux composants (7 conteneurs Docker, 4 microservices, dashboard, CI/CD) tout en maintenant une cohérence architecturale. Enfin, ma curiosité technique me pousse à explorer les meilleures pratiques (observabilité avec Prometheus/Grafana, sécurité avec JWT/OAuth2) plutôt que de me contenter de solutions minimales.

---

## Auto-évaluation des compétences

### Travailler en équipe : 3/4

Je collabore efficacement avec mon encadrant chez Huawei et je communique régulièrement sur l'avancement du projet. J'ai participé à des réunions techniques où j'ai présenté mes choix architecturaux et intégré les retours de l'équipe. Je ne me mets pas un 4 car le projet est principalement individuel, ce qui limite les occasions de collaboration intensive au quotidien.

### Être autonome : 4/4

L'ensemble du projet a été conçu et développé de manière autonome. J'ai pris en charge la totalité du cycle de développement : de l'étude de l'existant à la conception de l'architecture, de l'implémentation du code au déploiement avec CI/CD. J'ai su rechercher l'information dont j'avais besoin (documentation Huawei, documentation technique des frameworks) sans attendre qu'on me la fournisse. Par exemple, j'ai mis en place le système d'authentification OAuth2 complet en autonomie.

### Être résilient : 3/4

J'ai fait face à plusieurs obstacles techniques importants (configuration Docker inter-conteneurs, intégration OAuth2, calibrage des modèles ML) sans me décourager. Chaque échec m'a poussé à approfondir ma compréhension et à trouver des solutions plus robustes. Le pipeline CI/CD a nécessité de nombreuses itérations avant de fonctionner correctement, mais j'ai persisté en corrigeant les erreurs une par une (lint ruff, tests, builds).

### Organiser votre travail dans les délais : 3/4

J'ai respecté les grandes étapes du planning en livrant 6 phases sur 10 dans les délais prévus. Le découpage en phases m'aide à maintenir un rythme régulier. Cependant, certaines phases ont pris plus de temps que prévu (notamment la Phase 4 avec l'authentification) ce qui m'a obligé à réajuster le planning pour les phases suivantes.

### Prendre des initiatives : 4/4

J'ai pris de nombreuses initiatives au-delà du périmètre initial du projet : mise en place du monitoring complet avec Prometheus et Grafana, implémentation d'un pipeline CI/CD en 6 étapes, ajout de l'authentification OAuth2 avec Google et GitHub, rebranding complet de la plateforme sous "NeXo", et implémentation de la Command Palette pour améliorer l'UX. Ces ajouts n'étaient pas explicitement demandés mais apportent une valeur significative au projet.

### Réaliser un travail de qualité : 4/4

Je maintiens un haut niveau de qualité dans mon travail : le code passe un linter (ruff) automatique, les tests sont exécutés à chaque commit via CI/CD, la documentation technique est exhaustive (diagrammes C4, ER, séquence, guides de déploiement), et l'architecture respecte les bonnes pratiques (microservices, séparation des responsabilités, sécurité). Le projet totalise plus de 2000 lignes de code backend structuré, un dashboard de 9+ pages, et une documentation complète.

---

## Souhaitez-vous me contacter pour échanger sur le déroulement de votre stage ?

Oui — par mail ou rendez-vous selon la disponibilité.
