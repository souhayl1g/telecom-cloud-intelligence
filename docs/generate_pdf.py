#!/usr/bin/env python3
"""Generate project explanation PDF - Telecom Cloud Intelligence PFE 2025-2026"""

from fpdf import FPDF
from fpdf.enums import XPos, YPos
import datetime

PRIMARY   = (0, 71, 171)
HEADER_BG = (0, 71, 171)
LIGHT_BG  = (240, 245, 255)
CODE_BG   = (245, 245, 245)
TEXT      = (30, 30, 30)
MUTED     = (100, 100, 100)
WHITE     = (255, 255, 255)
GREEN     = (34, 139, 34)
ORANGE    = (200, 100, 0)


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*HEADER_BG)
        self.rect(0, 0, 210, 12, "F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*WHITE)
        self.set_xy(10, 2)
        self.cell(0, 8, "Telecom Cloud Intelligence  -  Project Documentation",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*TEXT)
        self.ln(4)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-13)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")

    def section_title(self, num, title):
        self.ln(6)
        self.set_fill_color(*HEADER_BG)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 10, f"  {num}  {title}",
                  fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*TEXT)
        self.ln(3)

    def subsection(self, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*PRIMARY)
        self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*PRIMARY)
        self.set_line_width(0.3)
        x, y = self.get_x(), self.get_y()
        self.line(x, y, x + 170, y)
        self.set_text_color(*TEXT)
        self.ln(3)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*TEXT)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, items):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*TEXT)
        for item in items:
            self.set_x(25)
            self.cell(5, 5.5, chr(149), new_x=XPos.RIGHT, new_y=YPos.LAST)
            self.multi_cell(0, 5.5, item)
        self.ln(1)

    def kv_table(self, rows, col1=55):
        fill = False
        for k, v in rows:
            self.set_fill_color(*(LIGHT_BG if fill else WHITE))
            self.set_font("Helvetica", "B", 9.5)
            self.cell(col1, 6.5, "  " + k, fill=True, border=0,
                      new_x=XPos.RIGHT, new_y=YPos.LAST)
            self.set_font("Helvetica", "", 9.5)
            self.cell(0, 6.5, v, fill=True, border=0,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            fill = not fill
        self.ln(3)

    def code_block(self, code):
        self.set_fill_color(*CODE_BG)
        self.set_font("Courier", "", 8.5)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5, code, fill=True, border=1)
        self.set_text_color(*TEXT)
        self.set_font("Helvetica", "", 10)
        self.ln(2)

    def badge(self, label, color):
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*color)
        self.set_text_color(*WHITE)
        self.cell(0, 6, f"  {label}  ",
                  fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*TEXT)
        self.ln(1)

    def step_row(self, n, title, desc):
        self.set_fill_color(*LIGHT_BG)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*PRIMARY)
        self.cell(0, 7, f"  Step {n}: {title}",
                  fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*TEXT)
        self.set_font("Helvetica", "", 10)
        self.set_x(26)
        self.multi_cell(0, 5.5, desc)
        self.ln(2)


def build():
    pdf = PDF()
    pdf.set_title("Telecom Cloud Intelligence - Project Documentation")
    pdf.set_author("Souhayl - Huawei Tunisia PFE 2025-2026")

    # ---------------------------------------------------------------- COVER
    pdf.add_page()
    pdf.set_fill_color(*HEADER_BG)
    pdf.rect(0, 0, 210, 90, "F")
    pdf.set_xy(10, 20)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(190, 14, "Telecom Cloud Intelligence", align="C")
    pdf.set_xy(10, 54)
    pdf.set_font("Helvetica", "", 13)
    pdf.multi_cell(190, 7, "PFE Project  |  Huawei Tunisia  |  2025-2026", align="C")
    pdf.set_xy(10, 67)
    pdf.set_font("Helvetica", "I", 11)
    pdf.multi_cell(
        190, 7,
        "Cloud-native AI platform for telecom network monitoring and anomaly detection",
        align="C")
    pdf.set_xy(30, 105)
    pdf.set_text_color(*TEXT)
    for label, val in [
        ("Student",    "Souhayl"),
        ("Supervisor", "Huawei Tunisia Engineering Team"),
        ("Date",       datetime.date.today().strftime("%B %d, %Y")),
        ("Version",    "v1.4  (dev branch)"),
        ("Stack",      "Python 3.11  |  FastAPI  |  PostgreSQL 16  |  MinIO  |  Docker"),
    ]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(44, 8, label + ":", new_x=XPos.RIGHT, new_y=YPos.LAST)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, val, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*PRIMARY)
    pdf.set_line_width(0.8)
    pdf.line(30, 162, 180, 162)
    pdf.set_xy(10, 166)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        190, 6,
        "This document explains the entire codebase: every service, every file, "
        "every table, in plain language so you understand what was built, "
        "why each piece exists, and how they all connect.",
        align="C")

    # ================================================ SECTION 1 - OVERVIEW
    pdf.add_page()
    pdf.section_title("1", "Project Overview")
    pdf.body(
        "Telecom Cloud Intelligence is a cloud-native AI platform that runs entirely "
        "on your laptop (or on Huawei Cloud later). Its job is to watch a telecom "
        "operator's network, detect when the network is misbehaving (anomaly detection), "
        "predict whether service quality (SLA) will degrade, and expose that intelligence "
        "through a REST API."
    )
    pdf.body(
        "This is your PFE (final year engineering project) at Huawei Tunisia. "
        "It simulates what a real telco Operations team would need: live data from "
        "the radio network (OSS - Operations Support Systems) combined with "
        "billing and revenue data (BSS - Business Support Systems), processed through "
        "machine-learning models, and served over HTTP for dashboards or automated alerts."
    )
    pdf.subsection("Why this project exists")
    pdf.bullet([
        "OSS data (radio cells, latency, signal strength) tells you when the network is sick.",
        "BSS data (revenue, subscribers, plans in TND) tells you when the business is losing money.",
        "Together they answer: Is network degradation causing revenue loss?",
        "The platform automates that analysis with real ML models instead of manual reports.",
    ])
    pdf.subsection("What has been completed (Phase 1 and 2)")
    pdf.bullet([
        "Synthetic data generator: 200 OSS + 200 BSS records per run, full Tunisian context.",
        "MinIO data lake (S3-compatible): stores records as JSON files organized by run ID.",
        "PostgreSQL database with 6 tables: pipeline runs, dataset metadata, SLA scores, anomalies.",
        "AI Service with two real scikit-learn models: GBR SLA risk scorer + IsolationForest anomaly detector.",
        "API Gateway with 5 REST endpoints to query all results.",
        "Wired together with Docker Compose: one command starts the full stack.",
        "Verified execution: run-a8f5b0809b6c, SLA score=0.724, 7/200 anomalies detected (3.5%).",
    ])

    # ============================================= SECTION 2 - ARCHITECTURE
    pdf.add_page()
    pdf.section_title("2", "Global Architecture - 5 Docker Containers")
    pdf.body(
        "The entire platform is defined in docker-compose.yml. "
        "It starts 5 containers that communicate over an internal Docker network."
    )
    pdf.kv_table([
        ("Container",         "Role"),
        ("postgres:16",       "Persistent SQL database - stores all results, metadata, run history"),
        ("minio",             "S3-compatible object storage - the data lake (raw JSON files)"),
        ("api-gateway :8000", "Public REST API - external users and dashboards talk to this"),
        ("ai-service :8001",  "ML inference engine - trains and serves two scikit-learn models"),
        ("pipeline-worker",   "One-shot orchestrator - runs once, generates data, calls AI, saves results"),
    ])
    pdf.subsection("How the containers connect")
    lines = [
        "[ pipeline-worker ] (run-once)",
        "   |",
        "   |-- generates 200 OSS records + 200 BSS records",
        "   |",
        "   |-- MinIO      : uploads s3://raw/{run_id}/oss.json",
        "   |                uploads s3://raw/{run_id}/bss.json",
        "   |",
        "   |-- ai-service : POST /infer/sla-risk  (9-feature vector) -> score 0-1",
        "   |-- ai-service : POST /infer/anomaly   (200 raw records)  -> per-record flags",
        "   |",
        "   |-- PostgreSQL : INSERT pipeline_runs, dataset_registry,",
        "                    sla_risk_scores, anomalies",
        "",
        "[ api-gateway :8000 ]  <-- external HTTP calls from you or a dashboard",
        "   |-- PostgreSQL : SELECT queries to fetch stored results",
        "",
        "[ ai-service :8001 ]   <-- internal HTTP from pipeline-worker only",
        "   |-- Docker volume : loads/saves trained models from /app/models/",
    ]
    pdf.code_block("\n".join(lines))
    pdf.subsection("Named Docker Volumes (data persists after restart)")
    pdf.kv_table([
        ("pgdata",    "PostgreSQL data files  - database survives container restarts"),
        ("miniodata", "MinIO object storage   - all uploaded JSON files"),
        ("aimodels",  "Trained .joblib models - no retraining needed on restart"),
    ])
    pdf.subsection("Ports exposed on localhost")
    pdf.kv_table([
        ("localhost:8000", "API Gateway  - main query entry point"),
        ("localhost:8001", "AI Service   - ML inference (normally called internally)"),
        ("localhost:5432", "PostgreSQL   - direct DB access via psql or pgAdmin"),
        ("localhost:9000", "MinIO S3 API"),
        ("localhost:9001", "MinIO browser console (web UI)"),
    ])

    # ============================================== SECTION 3 - DB SCHEMA
    pdf.add_page()
    pdf.section_title("3", "Database Schema - 6 Tables")
    pdf.body(
        "Database: telecom_intel  |  User: telecom  |  Password: telecom_pw\n"
        "All tables use BIGSERIAL (auto-increment integer) primary keys. "
        "Tables linked to a pipeline run use run_id TEXT as a foreign key."
    )
    schema_tables = [
        ("pipeline_runs",
         "One row per pipeline-worker execution. Tracks status and timing.",
         [("id",               "Auto-increment primary key"),
          ("run_id",           "Unique text ID, e.g. run-a8f5b0809b6c"),
          ("status",           "running  |  succeeded  |  failed"),
          ("started_at",       "Timestamp when worker started"),
          ("finished_at",      "Timestamp when worker finished (NULL while running)"),
          ("records_processed","Integer count of records (400 = 200 OSS + 200 BSS)"),
          ("error_message",    "NULL if success, error text if failed")]),
        ("dataset_registry",
         "Metadata about each file uploaded to MinIO. One row per uploaded file.",
         [("run_id",         "Which pipeline run created this file"),
          ("dataset_name",   "oss_raw  or  bss_raw"),
          ("s3_path",        "Full MinIO path e.g. s3://raw/run-xxx/oss.json"),
          ("record_count",   "How many records are in the file"),
          ("schema_version", "e.g. v1")]),
        ("sla_risk_scores",
         "One row per pipeline run. The SLA risk score and model explanation.",
         [("run_id",        "Which run produced this score"),
          ("score",         "Float 0.0 to 1.0  (0=healthy network, 1=critical SLA risk)"),
          ("model_version", "e.g. v1.0"),
          ("scored_at",     "Timestamp"),
          ("explanation",   "JSONB: feature_importances dict + top_driver field")]),
        ("anomalies",
         "One row per anomalous OSS record detected by IsolationForest. "
         "If 7 of 200 records are flagged, 7 rows are inserted.",
         [("run_id",         "Which run detected this anomaly"),
          ("cell_id",        "e.g. CELL-003"),
          ("kpi_name",       "Which KPI was anomalous, e.g. latency_ms"),
          ("severity",       "Float 0-1 normalized anomaly score (higher = more anomalous)"),
          ("value",          "The actual KPI value that was flagged"),
          ("baseline_value", "NULL for now, will hold expected normal value in Phase 3")]),
        ("correlation_insights",
         "EMPTY NOW - Phase 3 feature. Will store statistical correlations between "
         "OSS and BSS metrics (e.g. when CELL-003 degrades, Ooredoo revenue drops).",
         [("metric_x",   "OSS metric name"),
          ("metric_y",   "BSS metric name"),
          ("corr_value", "Pearson or Spearman correlation coefficient"),
          ("p_value",    "Statistical significance (p < 0.05 = significant)")]),
        ("model_registry",
         "EMPTY NOW - Phase 3 feature. Will track all trained model versions and their accuracy.",
         [("model_name", "e.g. sla_risk_gbr"),
          ("version",    "e.g. v1.0"),
          ("trained_at", "Timestamp"),
          ("metrics",    "JSONB: precision, recall, F1 score")]),
    ]
    for tname, desc, cols in schema_tables:
        pdf.subsection(f"Table: {tname}")
        pdf.body(desc)
        pdf.kv_table(cols, col1=65)

    # =========================================== SECTION 4 - PIPELINE WORKER
    pdf.add_page()
    pdf.section_title("4", "Service: Pipeline Worker")
    pdf.body(
        "File: services/pipeline-worker/worker/__main__.py  (335 lines)\n\n"
        "The pipeline-worker is the engine of the platform. Run it with:\n"
        "   docker compose run --rm pipeline-worker\n\n"
        "It performs 12 sequential steps then exits. Think of it as a "
        "scheduled data pipeline script that generates data, stores it, "
        "runs AI inference, and saves every result to the database."
    )
    pdf.subsection("12 Steps in order")
    pipeline_steps = [
        ("Create MinIO buckets",
         "Ensures the buckets raw, processed, and curated exist in MinIO. "
         "Creates any that are missing."),
        ("Generate OSS data",
         "Creates 200 synthetic radio network records for 10 cells (CELL-001 to CELL-010). "
         "Records cover the last 4 hours. Each record has: cell_id, region, throughput_mbps, "
         "latency_ms, packet_loss_pct, active_users, signal_rsrp_dbm."),
        ("Generate BSS data",
         "Creates 200 synthetic billing records for 3 Tunisian operators. "
         "Revenue in TND with plan-based bands. Subscriber IDs in TN-XXXXXX format."),
        ("Upload OSS to MinIO",
         "Serializes OSS records to JSON and uploads to s3://raw/{run_id}/oss.json"),
        ("Upload BSS to MinIO",
         "Serializes BSS records to JSON and uploads to s3://raw/{run_id}/bss.json"),
        ("Insert pipeline_runs row",
         "Saves run_id, status=running, started_at, records_processed=400 to the database."),
        ("Register OSS dataset",
         "Inserts a row in dataset_registry: name=oss_raw, s3_path, record_count=200."),
        ("Register BSS dataset",
         "Inserts a row in dataset_registry: name=bss_raw, s3_path, record_count=200."),
        ("Compute OSS features",
         "compute_oss_features() aggregates 200 OSS records into a 9-number vector. "
         "This vector is sent to the GBR model for inference."),
        ("SLA risk inference",
         "HTTP POST to ai-service:8001/infer/sla-risk with the 9-feature dict. "
         "Gets back: score (0-1), feature_importances, top_driver."),
        ("Anomaly inference",
         "HTTP POST to ai-service:8001/infer/anomaly with all 200 raw OSS records. "
         "Gets back per-record: is_anomaly flag and anomaly_score (0-1)."),
        ("Persist all results",
         "Inserts 1 row in sla_risk_scores (score + explanation JSONB). "
         "Inserts 1 row per anomalous record in anomalies table. "
         "Updates pipeline_runs status to succeeded."),
    ]
    for i, (t, d) in enumerate(pipeline_steps, 1):
        pdf.step_row(i, t, d)

    pdf.subsection("OSS Record Fields (generate_oss)")
    pdf.kv_table([
        ("ts",               "Timestamp - random within last 4 hours"),
        ("region",           "Tunis / Sfax / Sousse / Monastir / Bizerte"),
        ("cell_id",          "CELL-001 to CELL-010"),
        ("throughput_mbps",  "Float 10-200 Mbps  (higher is better)"),
        ("latency_ms",       "Float 5-150 ms     (lower is better)"),
        ("packet_loss_pct",  "Float 0-10 %       (lower is better)"),
        ("active_users",     "Integer 10-500"),
        ("signal_rsrp_dbm",  "Float -120 to -60 dBm  (closer to -60 is better)"),
    ])
    pdf.subsection("BSS Record Fields (generate_bss)")
    pdf.kv_table([
        ("ts",             "Timestamp"),
        ("operator",       "Ooredoo Tunisie  |  Tunisie Telecom  |  Orange Tunisie"),
        ("subscriber_id",  "TN-XXXXXX format, e.g. TN-482931"),
        ("plan",           "basic  |  standard  |  premium"),
        ("revenue_tnd",    "basic 15-35 TND  |  standard 35-75 TND  |  premium 75-150 TND"),
        ("data_used_gb",   "Float 0.5-50 GB"),
        ("calls_minutes",  "Float 0-600 minutes"),
    ])
    pdf.subsection("9 OSS Features sent to the ML model (compute_oss_features)")
    pdf.kv_table([
        ("latency_mean",      "Average latency across all 200 records"),
        ("latency_std",       "Standard deviation of latency - how variable it is"),
        ("latency_max",       "Worst (highest) latency seen in this window"),
        ("packet_loss_mean",  "Average packet loss %"),
        ("packet_loss_max",   "Worst packet loss %"),
        ("throughput_mean",   "Average throughput Mbps"),
        ("throughput_std",    "Standard deviation of throughput"),
        ("users_mean",        "Average active user count"),
        ("rsrp_mean",         "Average signal strength dBm"),
    ])

    # ============================================= SECTION 5 - AI SERVICE
    pdf.add_page()
    pdf.section_title("5", "Service: AI Service (ML Engine)")
    pdf.body(
        "File: services/ai-service/main.py  (311 lines)\n\n"
        "The AI service is a FastAPI web server on port 8001. "
        "It trains two machine-learning models at startup, then listens for "
        "inference requests from the pipeline-worker. "
        "Models are saved to disk so they survive container restarts without retraining."
    )
    pdf.subsection("Model 1 - SLA Risk Scorer: GradientBoostingRegressor")
    pdf.body(
        "Answers: 'How likely is the SLA to be breached this time window?'\n"
        "Output: a single float score from 0.0 (healthy) to 1.0 (critical risk)."
    )
    pdf.kv_table([
        ("Algorithm",       "GradientBoostingRegressor - scikit-learn"),
        ("Training data",   "3000 synthetic 9-feature samples generated at startup"),
        ("n_estimators",    "200 decision trees"),
        ("max_depth",       "4 levels per tree"),
        ("learning_rate",   "0.05  (slow learning = more stable generalization)"),
        ("subsample",       "0.8   (uses 80% of data per tree = prevents overfitting)"),
        ("Label formula",   "0.4*latency_norm + 0.35*loss_norm + 0.25*(1 - throughput_norm)"),
        ("Extra output",    "feature_importances dict + top_driver = most impactful feature name"),
        ("Model file",      "sla_risk_gbr_v1.0.joblib  saved in /app/models/"),
    ])
    pdf.subsection("What Gradient Boosting does (plain language)")
    pdf.body(
        "Gradient boosting builds hundreds of small decision trees one after another. "
        "Each new tree tries to correct the mistakes made by the previous trees. "
        "The final prediction is the weighted sum of all trees. "
        "It is one of the best algorithms for structured table data and typically "
        "outperforms neural networks on real-world telecom KPI datasets."
    )
    pdf.subsection("Model 2 - Anomaly Detector: IsolationForest")
    pdf.body(
        "Answers: 'Which of the 200 OSS records are behaving abnormally?'\n"
        "Output: for each record, is_anomaly (true/false) + anomaly_score (0.0-1.0)."
    )
    pdf.kv_table([
        ("Algorithm",      "IsolationForest - scikit-learn"),
        ("Training data",  "3000 samples: 2850 normal + 150 injected faults"),
        ("Injected faults","latency multiplied 3-5x, packet_loss multiplied 5-10x"),
        ("Input/record",   "throughput_mbps, latency_ms, packet_loss_pct, active_users, rsrp"),
        ("n_estimators",   "150 trees"),
        ("contamination",  "0.05 - expects about 5% of records to be anomalous"),
        ("Model file",     "anomaly_iforest_v1.0.joblib  saved in /app/models/"),
    ])
    pdf.subsection("What IsolationForest does (plain language)")
    pdf.body(
        "IsolationForest randomly splits data with random cuts. "
        "Normal data points are hard to isolate because they cluster together - "
        "it takes many random cuts to separate one normal point from the rest. "
        "Anomalies are easy to isolate because their values are far from the normal cluster - "
        "just a few cuts separate them. "
        "The fewer cuts it takes to isolate a record, the higher its anomaly score."
    )
    pdf.subsection("Model Persistence")
    pdf.body(
        "Both models are saved with joblib to /app/models/ which is mounted from "
        "the Docker named volume 'aimodels'. "
        "On restart the ai-service loads the saved files in under 1 second "
        "instead of retraining (which takes about 10 seconds)."
    )
    pdf.subsection("AI Service API Endpoints (port 8001)")
    pdf.kv_table([
        ("GET  /health",         "Returns: {status: ok, models_loaded: true}"),
        ("POST /infer/sla-risk", "Input: {features: {latency_mean: ..., ...}}  ->  score + explanation"),
        ("POST /infer/anomaly",  "Input: list of OSS records  ->  per-record is_anomaly + severity"),
    ], col1=60)

    # =========================================== SECTION 6 - API GATEWAY
    pdf.add_page()
    pdf.section_title("6", "Service: API Gateway (Public REST API)")
    pdf.body(
        "File: services/api-gateway/main.py  (94 lines)\n\n"
        "The API gateway is the public face of the platform running on port 8000. "
        "It reads directly from PostgreSQL and returns JSON. "
        "External users, dashboards, or Grafana only talk to this service - "
        "they never call ai-service directly. "
        "Each endpoint executes a simple SELECT query and returns the result as JSON."
    )
    pdf.subsection("5 Available Endpoints")
    pdf.kv_table([
        ("GET /health",                   "Health check  ->  {status: ok}"),
        ("GET /sla-risk",                 "Latest SLA score with feature importance explanation"),
        ("GET /sla-risk/history?limit=N", "Last N scores - good for trend analysis"),
        ("GET /anomalies?limit=N",        "Last N flagged records: cell_id, kpi_name, severity, value"),
        ("GET /pipeline-runs?limit=N",    "Last N executions: run_id, status, timestamps"),
    ], col1=72)
    pdf.subsection("Example response from GET /sla-risk")
    sla_example = [
        "{",
        '  "run_id": "run-a8f5b0809b6c",',
        '  "score": 0.724,',
        '  "model_version": "v1.0",',
        '  "scored_at": "2025-04-01T14:23:11",',
        '  "explanation": {',
        '    "top_driver": "latency_mean",',
        '    "feature_importances": {',
        '      "latency_mean": 0.38,',
        '      "packet_loss_mean": 0.27,',
        '      "throughput_mean": 0.18,',
        '      "latency_max": 0.09,',
        '      "packet_loss_max": 0.08',
        "    }",
        "  }",
        "}",
    ]
    pdf.code_block("\n".join(sla_example))
    pdf.subsection("Example response from GET /anomalies?limit=3")
    anom_example = [
        "[",
        '  {"cell_id":"CELL-007","kpi_name":"latency_ms",    "severity":0.82,"value":143.2},',
        '  {"cell_id":"CELL-003","kpi_name":"packet_loss_pct","severity":0.71,"value":8.9 },',
        '  {"cell_id":"CELL-001","kpi_name":"throughput_mbps","severity":0.58,"value":11.3}',
        "]",
    ]
    pdf.code_block("\n".join(anom_example))

    # ============================================== SECTION 7 - DATA FLOW
    pdf.add_page()
    pdf.section_title("7", "Full Data Flow - End to End")
    pdf.body(
        "Here is exactly what happens from the moment you run the pipeline "
        "to the moment you can query results from the API:"
    )
    flow = [
        ("Run the pipeline",
         "docker compose run --rm pipeline-worker\n"
         "This starts the pipeline-worker container which runs once then exits."),
        ("Bucket setup",
         "Worker checks that MinIO has the buckets raw, processed, and curated.\n"
         "Creates any that are missing."),
        ("Synthetic data generation",
         "200 OSS records: 10 cells, last 4 hours, 5 Tunisian regions.\n"
         "200 BSS records: 3 Tunisian operators, TND revenue bands by plan."),
        ("Upload to data lake (MinIO)",
         "Both datasets serialized to JSON and uploaded:\n"
         "  s3://raw/{run_id}/oss.json  (200 records)\n"
         "  s3://raw/{run_id}/bss.json  (200 records)"),
        ("Save run metadata to PostgreSQL",
         "INSERT pipeline_runs row:  status=running, records_processed=400.\n"
         "INSERT 2 dataset_registry rows: one per uploaded file."),
        ("Feature engineering",
         "compute_oss_features() aggregates 200 OSS records into 9 numbers.\n"
         "Example: latency_mean=67.3, packet_loss_mean=3.1, throughput_mean=112.5 ..."),
        ("SLA risk inference",
         "HTTP POST to ai-service:8001/infer/sla-risk with the 9-feature dict.\n"
         "GBR returns: score=0.724, top_driver=latency_mean, importances dict."),
        ("Anomaly inference",
         "HTTP POST to ai-service:8001/infer/anomaly with 200 raw OSS records.\n"
         "IsolationForest returns per record: {is_anomaly: true, anomaly_score: 0.82}."),
        ("Persist all results to PostgreSQL",
         "INSERT 1 row in sla_risk_scores (score + explanation JSONB).\n"
         "INSERT N rows in anomalies (one per flagged record, typically 3-10).\n"
         "UPDATE pipeline_runs: status=succeeded, finished_at=now()."),
        ("Query results via API",
         "GET localhost:8000/sla-risk      ->  {score: 0.724, top_driver: latency_mean}\n"
         "GET localhost:8000/anomalies     ->  list of flagged cells with severity scores\n"
         "GET localhost:8000/pipeline-runs ->  run history with status and timestamps"),
    ]
    for i, (t, d) in enumerate(flow, 1):
        pdf.step_row(i, t, d)

    # ============================================= SECTION 8 - STATUS
    pdf.add_page()
    pdf.section_title("8", "Current Status and Roadmap")

    pdf.badge("COMPLETE  -  Phase 1: Vertical Slice", GREEN)
    pdf.bullet([
        "Schema designed and applied to live PostgreSQL database.",
        "Pipeline runs end-to-end: data generation -> MinIO -> AI -> DB -> API.",
        "All 5 API endpoints return real data from real DB rows.",
        "Verified execution: run-a8f5b0809b6c, SLA score=0.724, 7/200 anomalies (3.5%).",
    ])
    pdf.ln(2)

    pdf.badge("COMPLETE  -  Phase 2: Real ML Models", GREEN)
    pdf.bullet([
        "GradientBoostingRegressor SLA risk model v1.0 - trained and serving.",
        "IsolationForest anomaly detector v1.0 - trained and serving.",
        "Models persist to Docker volume - no retraining after restart.",
        "Feature importances exposed in every /sla-risk API response.",
        "NumPy 2.0 compatibility fix applied (ptp() replaced with max()-min()).",
    ])
    pdf.ln(2)

    pdf.badge("COMPLETE  -  BSS Tunisian Operator Context", GREEN)
    pdf.bullet([
        "Revenue in Tunisian Dinar (TND) - not USD.",
        "Three real operators: Ooredoo Tunisie, Tunisie Telecom, Orange Tunisie.",
        "Plan-banded revenue ranges realistic for TN market.",
        "Subscriber IDs in TN-XXXXXX format.",
    ])
    pdf.ln(2)

    pdf.badge("PENDING  -  Phase 3: Fault Injection and OSS-BSS Correlation", ORANGE)
    pdf.bullet([
        "Inject realistic fault patterns: business-hour load curves, timed outages.",
        "Make BSS revenue dips correlate with OSS cell degradation events.",
        "Add revenue anomaly model (second IsolationForest on BSS data).",
        "Implement OSS-BSS correlation engine (Pearson and Spearman coefficients).",
        "Populate correlation_insights table. Add /correlation and /revenue-anomalies endpoints.",
    ])
    pdf.ln(2)

    pdf.badge("PENDING  -  Phase 4: Evaluation - Precision, Recall, F1", ORANGE)
    pdf.bullet([
        "Generate labeled dataset with known fault timestamps.",
        "Compute precision, recall, F1 score for both ML models.",
        "Add model evaluation section to the technical report.",
    ])
    pdf.ln(2)

    pdf.badge("PENDING  -  Phase 5: Observability with Prometheus and Grafana", ORANGE)
    pdf.bullet([
        "Expose Prometheus metrics endpoints from all 3 custom services.",
        "Build Grafana dashboard: SLA score trend, anomaly rate, run history.",
        "Add prometheus and grafana containers to docker-compose.yml.",
    ])
    pdf.ln(2)

    pdf.badge("PENDING  -  Phase 6: Huawei Cloud Deployment", ORANGE)
    pdf.bullet([
        "Replace MinIO with Huawei OBS (Object Bucket Storage).",
        "Replace PostgreSQL container with Huawei RDS for PostgreSQL.",
        "Deploy api-gateway and ai-service on Huawei ECS (Elastic Cloud Server).",
        "Screenshot evidence required for supervisor presentation.",
    ])

    # =========================================== SECTION 9 - COMMANDS
    pdf.add_page()
    pdf.section_title("9", "Key Commands Reference")

    pdf.subsection("Start the entire platform")
    pdf.code_block(
        "# First time - builds all Docker images (takes 2-4 minutes)\n"
        "docker compose up --build -d\n\n"
        "# After first build - much faster\n"
        "docker compose up -d\n\n"
        "# Check all 5 containers are healthy\n"
        "docker compose ps"
    )
    pdf.subsection("Run the pipeline (generates data, uploads, infers, saves)")
    pdf.code_block(
        "# Run one complete cycle\n"
        "docker compose run --rm pipeline-worker\n\n"
        "# Watch the pipeline logs live\n"
        "docker compose logs -f pipeline-worker"
    )
    pdf.subsection("Query the API")
    pdf.code_block(
        "# Latest SLA risk score with explanation\n"
        "curl http://localhost:8000/sla-risk\n\n"
        "# Last 5 scores - trend over time\n"
        "curl http://localhost:8000/sla-risk/history?limit=5\n\n"
        "# Last 20 anomalies sorted by recency\n"
        "curl http://localhost:8000/anomalies?limit=20\n\n"
        "# Last 10 pipeline runs\n"
        "curl http://localhost:8000/pipeline-runs?limit=10"
    )
    pdf.subsection("Inspect the database")
    pdf.code_block(
        "# Connect to PostgreSQL\n"
        "docker compose exec postgres psql -U telecom -d telecom_intel\n\n"
        "# Queries inside psql\n"
        "SELECT run_id, status, records_processed FROM pipeline_runs ORDER BY id DESC LIMIT 5;\n"
        "SELECT run_id, score, scored_at FROM sla_risk_scores ORDER BY id DESC LIMIT 5;\n"
        "SELECT cell_id, kpi_name, severity FROM anomalies ORDER BY severity DESC LIMIT 10;"
    )
    pdf.subsection("Browse the MinIO data lake")
    pdf.code_block(
        "# Open in your browser:\n"
        "http://localhost:9001\n"
        "Username: minio\n"
        "Password: minio_pw\n\n"
        "# Navigate: Buckets -> raw -> run-xxxxxxxx/\n"
        "# You will see oss.json and bss.json for each pipeline run"
    )
    pdf.subsection("Force ML models to retrain from scratch")
    pdf.code_block(
        "# Delete the saved model files from the volume\n"
        "docker volume rm telecom-cloud-intelligence_aimodels\n\n"
        "# Restart ai-service - it will retrain on startup (~10 seconds)\n"
        "docker compose restart ai-service\n\n"
        "# Watch retraining progress in the logs\n"
        "docker compose logs -f ai-service"
    )
    pdf.subsection("Stop everything")
    pdf.code_block(
        "# Stop all containers (data preserved in volumes)\n"
        "docker compose down\n\n"
        "# Full reset - stop and delete all data\n"
        "docker compose down -v"
    )

    out = "/home/souhayl/projects/telecom-cloud-intelligence/docs/telecom-cloud-intelligence-explained.pdf"
    pdf.output(out)
    print(f"PDF written to: {out}")
    return out


if __name__ == "__main__":
    build()
