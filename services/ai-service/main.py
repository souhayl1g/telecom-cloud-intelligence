"""
AI Service — Real inference with pre-trained scikit-learn models.

Models are loaded dynamically from /app/models/ on each inference request
to support continuous training in notebooks:
  sla_risk_model.joblib            — GradientBoostingRegressor
                                      Predicts SLA breach risk (0–1) from aggregated KPI features.
  anomaly_model.joblib             — IsolationForest
                                      Detects anomalous OSS KPI records from per-record features.
  revenue_anomaly_model.joblib     — IsolationForest
                                      Detects anomalous BSS revenue/usage records.

Training notebooks:
  notebooks/01_data_preparation_eda.ipynb   — Data generation & EDA
  notebooks/02_sla_risk_model.ipynb         — SLA risk model training & evaluation
  notebooks/03_anomaly_detection_models.ipynb — Anomaly models training & evaluation
"""

import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from config import MODEL_VERSION
from routers.health import router as health_router
from routers.v2.sla_risk import router as sla_risk_router
from routers.v2.anomaly import router as anomaly_router
from routers.v2.revenue import router as revenue_router
from model_cache import load_models


def _setup_tracing() -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "ai-service"),
        "service.version": "2.0",
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


_setup_tracing()

app = FastAPI(title="AI Service", version=MODEL_VERSION)
FastAPIInstrumentor.instrument_app(app)

# Initialize model cache at startup
print("[ai-service] initializing model cache...")
_sla_model, _anomaly_model, _revenue_anomaly_model = load_models(force=True)
print("[ai-service] models ready — 3 models loaded")

app.include_router(health_router)
app.include_router(sla_risk_router)
app.include_router(anomaly_router)
app.include_router(revenue_router)
