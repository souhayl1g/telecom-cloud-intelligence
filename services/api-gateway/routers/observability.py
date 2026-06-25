"""Native observability surfaces — Prometheus metrics + Jaeger traces.

Replaces the external Grafana/Jaeger UIs with in-dashboard pages (the experts'
"everything inside the dashboard, no external links" mandate). This router is a
thin, read-only proxy over the Prometheus HTTP API and the Jaeger query API,
reachable on the docker network. Pure stdlib (urllib) — no new dependency.

Honesty: if the upstream is unreachable or a metric is absent, the field is null
(the UI renders '—'), never a fabricated value.
"""

import json
import os
import time
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, Query

from auth import require_role

router = APIRouter()

PROM_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
JAEGER_URL = os.getenv("JAEGER_URL", "http://jaeger:16686")

# Curated panels. Each PromQL degrades to null if the metric isn't present.
_PANELS = [
    {
        "key": "api_req_rate",
        "label": "Request rate",
        "unit": "req/s",
        "q": "sum(rate(http_requests_total[5m]))",
    },
    {
        "key": "api_p95",
        "label": "p95 latency",
        "unit": "s",
        "q": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))",
    },
    {
        "key": "cpu",
        "label": "CPU",
        "unit": "s/s",
        "q": "sum(rate(process_cpu_seconds_total[5m]))",
    },
    {
        "key": "rss",
        "label": "Memory RSS",
        "unit": "MB",
        "q": "sum(process_resident_memory_bytes)/1024/1024",
    },
]


def _get_json(url: str, timeout: float = 4.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def _prom_range(promql: str, minutes: int):
    end = int(time.time())
    start = end - minutes * 60
    step = max(15, (minutes * 60) // 120)  # ~120 points
    qs = urllib.parse.urlencode(
        {"query": promql, "start": start, "end": end, "step": step}
    )
    data = _get_json(f"{PROM_URL}/api/v1/query_range?{qs}")
    if not data or data.get("status") != "success":
        return None
    result = data.get("data", {}).get("result", [])
    if not result:
        return []
    # First series only (our panels aggregate to a single series).
    values = result[0].get("values", [])
    return [{"t": int(ts), "v": float(v)} for ts, v in values if v not in ("NaN",)]


@router.get("/observability/metrics")
def metrics(
    minutes: int = Query(30, ge=5, le=360), user=Depends(require_role("engineer"))
):
    """Curated Prometheus panels over the trailing window + scrape-target health."""
    panels = [
        {
            **{k: p[k] for k in ("key", "label", "unit")},
            "series": _prom_range(p["q"], minutes),
        }
        for p in _PANELS
    ]
    targets = _get_json(f"{PROM_URL}/api/v1/targets")
    up = total = None
    if targets and targets.get("status") == "success":
        active = targets.get("data", {}).get("activeTargets", [])
        total = len(active)
        up = sum(1 for t in active if t.get("health") == "up")
    return {
        "panels": panels,
        "targets": {"up": up, "total": total},
        "window_minutes": minutes,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@router.get("/observability/services")
def trace_services(user=Depends(require_role("engineer"))):
    """Services Jaeger has seen (for the trace-explorer dropdown)."""
    data = _get_json(f"{JAEGER_URL}/api/services")
    services = (data or {}).get("data") or []
    # Jaeger lists its own internal service; keep the app services first.
    return {"services": [s for s in services if s not in ("jaeger-all-in-one",)]}


@router.get("/observability/traces")
def traces(
    service: str = Query("api-gateway"),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(require_role("engineer")),
):
    """Recent traces for a service, flattened to a list the UI can render."""
    qs = urllib.parse.urlencode({"service": service, "limit": limit})
    data = _get_json(f"{JAEGER_URL}/api/traces?{qs}")
    out = []
    for tr in (data or {}).get("data", []) or []:
        spans = tr.get("spans", [])
        if not spans:
            continue
        procs = tr.get("processes", {})
        root = min(spans, key=lambda s: s.get("startTime", 0))
        root_proc = procs.get(root.get("processID", ""), {})
        durations = [s.get("duration", 0) for s in spans]
        out.append(
            {
                "trace_id": tr.get("traceID"),
                "service": root_proc.get("serviceName", service),
                "operation": root.get("operationName"),
                "span_count": len(spans),
                "duration_us": max(durations) if durations else 0,
                "start_us": root.get("startTime", 0),
            }
        )
    out.sort(key=lambda x: x["start_us"], reverse=True)
    return {"service": service, "traces": out, "count": len(out)}
