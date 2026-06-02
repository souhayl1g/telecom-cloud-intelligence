"""v3.0 AI service HTTP client with retry logic.

The routers resolve the actual feature contract at inference time from the
*_feature_names.joblib files saved by training. The client therefore passes
the full enriched record through — the router picks the columns it needs and
zero-defaults anything missing. This prevents 422s when retraining widens
the feature set.
"""

import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from worker.config import AI_SERVICE_URL, INTERNAL_API_KEY

_ai_retry = retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)

# Drop non-numeric / identifier columns the model can't consume. Everything
# else flows through so the router-side feature contract is the source of truth.
_DROP_KEYS = {
    "ts", "subscriber_id", "imsi_hash", "area", "generation", "highest_rat",
    "usertype", "month_year", "source",
}


def _to_record(r: dict) -> dict:
    out = {}
    for k, v in r.items():
        if k in _DROP_KEYS:
            continue
        if isinstance(v, bool):
            out[k] = 1.0 if v else 0.0
        elif isinstance(v, (int, float)):
            out[k] = float(v)
        # other types (str, None) silently dropped — router defaults to 0.0
    return out


@_ai_retry
def infer_cem(run_id: str, region: str, records: list[dict]) -> dict:
    payload = {
        "run_id": run_id,
        "region": region,
        "records": [_to_record(r) for r in records],
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/cem", json=payload, timeout=30, headers={"X-Internal-Key": INTERNAL_API_KEY})
    r.raise_for_status()
    return r.json()


@_ai_retry
def infer_vae_anomaly(run_id: str, region: str, records: list[dict]) -> dict:
    payload = {
        "run_id": run_id,
        "region": region,
        "records": [
            {
                "throughput_mbps": float(v) if (v := r.get("throughput_mbps")) is not None else 80.0,
                "latency_ms": float(v) if (v := r.get("latency_ms")) is not None else 25.0,
                "packet_loss_rate": float(v) if (v := r.get("packet_loss_rate") or r.get("packet_loss_pct")) is not None else 0.5,
                "jitter_ms": float(v) if (v := r.get("jitter_ms")) is not None else 5.0,
                "cell_load_pct": float(v) if (v := r.get("cell_load_pct")) is not None else 50.0,
                "rsrp_dbm": float(v) if (v := r.get("rsrp_dbm") or r.get("signal_rsrp_dbm")) is not None else -85.0,
                "active_users": int(v) if (v := r.get("active_users")) is not None else 200,
                "integrity": float(v) if (v := r.get("integrity")) is not None else 0.95,
                "call_drop_rate": float(v) if (v := r.get("call_drop_rate")) is not None else 0.01,
            }
            for r in records
        ],
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/vae-anomaly", json=payload, timeout=30, headers={"X-Internal-Key": INTERNAL_API_KEY})
    r.raise_for_status()
    return r.json()


@_ai_retry
def infer_rat_underservice(run_id: str, region: str, records: list[dict]) -> dict:
    payload = {
        "run_id": run_id,
        "region": region,
        "records": [_to_record(r) for r in records],
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/rat-underservice", json=payload, timeout=30, headers={"X-Internal-Key": INTERNAL_API_KEY})
    r.raise_for_status()
    return r.json()
