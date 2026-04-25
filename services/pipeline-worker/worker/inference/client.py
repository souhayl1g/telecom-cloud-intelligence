"""AI service HTTP client with retry logic."""
from datetime import datetime

import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from worker.config import AI_SERVICE_URL

_ai_retry = retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)


@_ai_retry
def infer_sla_risk(
    run_id: str,
    region: str,
    window_start: datetime,
    window_end: datetime,
    features: dict,
) -> tuple[float, dict, str]:
    payload = {
        "run_id": run_id,
        "region": region,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "features": features,
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/sla-risk", json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()
    return float(data["score"]), data.get("explanation", {}), data.get("model_version", "v2.0")


@_ai_retry
def infer_anomaly(run_id: str, region: str, records: list[dict]) -> dict:
    payload = {
        "run_id": run_id,
        "region": region,
        "records": [
            {
                "throughput_mbps": r["throughput_mbps"],
                "latency_ms": r["latency_ms"],
                "packet_loss_pct": r["packet_loss_pct"],
                "active_users": r["active_users"],
                "signal_rsrp_dbm": r["signal_rsrp_dbm"],
            }
            for r in records
        ],
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/anomaly", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


@_ai_retry
def infer_revenue_anomaly(run_id: str, region: str, records: list[dict]) -> dict:
    payload = {
        "run_id": run_id,
        "region": region,
        "records": [
            {
                "revenue_tnd": r["revenue_tnd"],
                "data_used_gb": r["data_used_gb"],
                "voice_min": float(r["voice_min"]),
                "sms_count": float(r["sms_count"]),
                "churn_risk": r["churn_risk"],
            }
            for r in records
        ],
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/revenue-anomaly", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()
