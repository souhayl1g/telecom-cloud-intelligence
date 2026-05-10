import os
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from routers import health, sla, anomalies, correlations, pipelines, actions, agents, subscribers, stats, granger


def _setup_tracing() -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "api-gateway"),
        "service.version": "2.0",
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


_setup_tracing()

app = FastAPI(title="Telecom NeXoligence — API Gateway", version="2.0")
FastAPIInstrumentor.instrument_app(app)

# Prometheus /metrics endpoint — scraped per prometheus.yml.
# Without this, Grafana panels show "No data".
from prometheus_fastapi_instrumentator import Instrumentator  # noqa: E402

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(health.router)
app.include_router(sla.router)
app.include_router(anomalies.router)
app.include_router(correlations.router)
app.include_router(pipelines.router)
app.include_router(actions.router)
app.include_router(agents.router)
app.include_router(subscribers.router)
app.include_router(stats.router)
app.include_router(granger.router)
