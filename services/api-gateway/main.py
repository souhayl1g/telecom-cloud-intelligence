import os
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from routers import (
    health,
    correlations,
    pipelines,
    actions,
    agents,
    subscribers,
    stats,
    granger,
    notifications,
    tickets,
    reports,
    interventions,
    autonomy,
    data_lake,
    drift,
    observability,
    storage_browser,
    notebooks,
    explorer,
    browse,
    admin,
    mlflow_proxy,
)


def _setup_tracing() -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", "api-gateway"),
            "service.version": "2.0",
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)


_setup_tracing()

app = FastAPI(title="Telecom NeXoligence — API Gateway", version="2.0")
FastAPIInstrumentor.instrument_app(app)

# Prometheus /metrics endpoint — scraped per prometheus.yml.
# Without this, Grafana panels show "No data".
from prometheus_fastapi_instrumentator import Instrumentator  # noqa: E402

Instrumentator().instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)

app.include_router(health.router)
app.include_router(correlations.router)
app.include_router(pipelines.router)
app.include_router(actions.router)
app.include_router(agents.router)
app.include_router(subscribers.router)
app.include_router(stats.router)
app.include_router(granger.router)
app.include_router(notifications.router)
app.include_router(tickets.router)
app.include_router(reports.router)
app.include_router(interventions.router)
app.include_router(autonomy.router)
app.include_router(data_lake.router)
app.include_router(drift.router)
app.include_router(observability.router)
app.include_router(storage_browser.router)
app.include_router(notebooks.router)
app.include_router(explorer.router)
app.include_router(browse.router)
app.include_router(admin.router)
app.include_router(mlflow_proxy.router)
