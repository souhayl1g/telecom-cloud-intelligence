"""
AI Service — Real inference with pre-trained ML models.

v2.0 models (legacy):
  sla_risk_model.joblib            — GradientBoostingRegressor
  anomaly_model.joblib             — IsolationForest
  revenue_anomaly_model.joblib     — IsolationForest

v3.0 models (real-data, GPU-trained on 1.5M+ records):
  cem_v3_lightgbm_gpu.joblib       — LightGBM (DART) for CEM experience scoring
  rat_v3_xgb_gpu.joblib            — XGBoost for RAT underservice detection
  oss_vae_v3_gpu.pt                — PyTorch VAE for OSS anomaly detection
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
from routers.v3.cem import router as cem_router
from routers.v3.rat import router as rat_router
from routers.v3.vae_anomaly import router as vae_router
from model_cache import load_models


def _setup_tracing() -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "ai-service"),
        "service.version": "3.0",
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


_setup_tracing()

app = FastAPI(title="AI Service", version=MODEL_VERSION)
FastAPIInstrumentor.instrument_app(app)

# Initialize model cache at startup
print("[ai-service] initializing model cache...")
_models = load_models(force=True)
loaded_count = sum(1 for k in ["sla", "anomaly", "revenue", "cem", "rat", "vae"] if _models.get(k) is not None)
print(f"[ai-service] models ready — {loaded_count}/6 models loaded")

app.include_router(health_router)
app.include_router(sla_risk_router)
app.include_router(anomaly_router)
app.include_router(revenue_router)
app.include_router(cem_router)
app.include_router(rat_router)
app.include_router(vae_router)
