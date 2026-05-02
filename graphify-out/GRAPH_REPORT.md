# Graph Report - telecom-cloud-intelligence  (2026-04-23)

## Corpus Check
- 64 files · ~2,258,139 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 320 nodes · 451 edges · 15 communities detected
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 28 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 35|Community 35]]

## God Nodes (most connected - your core abstractions)
1. `GET()` - 25 edges
2. `_db()` - 23 edges
3. `_run_pipeline_steps()` - 18 edges
4. `PDF` - 15 edges
5. `KB` - 15 edges
6. `PDF` - 14 edges
7. `POST()` - 13 edges
8. `build()` - 11 edges
9. `build()` - 10 edges
10. `build()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `check_ai_service()` --calls--> `GET()`  [INFERRED]
  pipeline_runner.py → dashboard/app/api/health-check/route.ts
- `ensure_buckets()` --calls--> `GET()`  [INFERRED]
  pipeline_runner.py → dashboard/app/api/health-check/route.ts
- `run_inference()` --calls--> `POST()`  [INFERRED]
  pipeline_runner.py → dashboard/app/api/chat/route.ts
- `run_inference()` --calls--> `GET()`  [INFERRED]
  pipeline_runner.py → dashboard/app/api/health-check/route.ts
- `load_models()` --calls--> `load()`  [INFERRED]
  services/ai-service/main.py → dashboard/app/ops-metrics/page.tsx

## Communities

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (39): safe(), build_curated_dataset(), build_processed_bss(), build_processed_oss(), compute_bss_features(), compute_correlations(), compute_oss_features(), ensure_buckets() (+31 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (46): anomalies_latest(), anomaly_stats(), correlation_latest(), create_action(), _create_token(), _db(), _ensure_tables(), execute_action() (+38 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (28): check_ai_service(), check_database(), check_minio(), ensure_buckets(), from_env(), _generate_bss(), generate_data(), _generate_oss() (+20 more)

### Community 3 - "Community 3"
Cohesion: 0.21
Nodes (3): build(), PDF, Small italic source citation line.

### Community 4 - "Community 4"
Cohesion: 0.16
Nodes (15): BaseModel, AnomalyRequest, BssRecord, _get_model_file_mtime(), LoginRequest, OssRecord, platform_stats(), Telecom NeXoligence — Auth Service Handles user signup/login with email+p (+7 more)

### Community 5 - "Community 5"
Cohesion: 0.23
Nodes (3): FPDF, build(), PDF

### Community 6 - "Community 6"
Cohesion: 0.21
Nodes (2): build(), KB

### Community 7 - "Community 7"
Cohesion: 0.28
Nodes (4): classifyAction(), generateActions(), groupActions(), hourBucket()

### Community 8 - "Community 8"
Cohesion: 0.31
Nodes (5): add_bullet_slide_content(), add_paragraph(), add_textbox(), Generate a supervisor meeting PPTX presentation. Cloud-Native AI Operations Agen, slide_title()

### Community 12 - "Community 12"
Cohesion: 0.5
Nodes (2): isSelected(), statusColor()

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (2): buildRCA(), formatKPI()

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (2): getBucket(), getBucketData()

### Community 21 - "Community 21"
Cohesion: 0.67
Nodes (1): submit()

### Community 23 - "Community 23"
Cohesion: 0.67
Nodes (1): Bootstrap default ML models if none exist in /app/models/. This ensures ai-servi

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Gantt chart aligned with ESPRIT PFE milestones — English.

## Knowledge Gaps
- **45 isolated node(s):** `PipelineConfig`, `StepResult`, `Check PostgreSQL connectivity.`, `Check MinIO/S3 connectivity.`, `Check AI service availability.` (+40 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 6`** (15 nodes): `generate_knowledge_base.py`, `build()`, `KB`, `.body()`, `.bullet()`, `.code()`, `.divider()`, `.footer()`, `.header()`, `.__init__()`, `.kv()`, `.numbered()`, `.ref_card()`, `.section()`, `.sub()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (5 nodes): `page.tsx`, `generateTopology()`, `isSelected()`, `statusColor()`, `typeIcon()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (3 nodes): `RootCauseAnalysis.tsx`, `buildRCA()`, `formatKPI()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (3 nodes): `getBucket()`, `getBucketData()`, `AnomalyHeatmap.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (3 nodes): `page.tsx`, `page.tsx`, `submit()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (3 nodes): `bootstrap()`, `Bootstrap default ML models if none exist in /app/models/. This ensures ai-servi`, `bootstrap_models.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (2 nodes): `Gantt chart aligned with ESPRIT PFE milestones — English.`, `gantt.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GET()` connect `Community 0` to `Community 1`, `Community 2`, `Community 19`, `Community 7`?**
  _High betweenness centrality (0.160) - this node is a cross-community bridge._
- **Why does `_db()` connect `Community 1` to `Community 0`, `Community 4`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `GET()` (e.g. with `check_ai_service()` and `ensure_buckets()`) actually correct?**
  _`GET()` has 19 INFERRED edges - model-reasoned connections that need verification._
- **What connects `PipelineConfig`, `StepResult`, `Check PostgreSQL connectivity.` to the rest of the system?**
  _45 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.09 - nodes in this community are weakly interconnected._