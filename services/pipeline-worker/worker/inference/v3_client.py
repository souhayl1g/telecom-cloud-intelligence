"""v3.0 AI service HTTP client with retry logic."""
from datetime import datetime

import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from worker.config import AI_SERVICE_URL

_ai_retry = retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)


@_ai_retry
def infer_cem(run_id: str, region: str, records: list[dict]) -> dict:
    payload = {
        "run_id": run_id,
        "region": region,
        "records": [
            {
                "usim_bottleneck": float(r.get("usim_bottleneck") or 0),
                "data_intensity": float(r.get("data_intensity") or 0),
                "dou_total": float(r.get("dou_total") or 0),
                "duration": float(r.get("duration") or 0),
                "s1_mme_sr": float(r.get("s1_mme_sr") or 0.5),
                "iu_attach_sr": float(r.get("iu_attach_sr") or 0.5),
                "gb_attach_sr": float(r.get("gb_attach_sr") or 0.5),
                "avg_throughput": float(r.get("avg_throughput") or 80.0),
                "avg_latency": float(r.get("avg_latency") or 25.0),
                "avg_packet_loss": float(r.get("avg_packet_loss") or 0.5),
                "anomaly_rate": float(r.get("anomaly_rate") or 0.05),
                "generation_4g": float(r.get("generation_4g") or 0),
                "generation_5g": float(r.get("generation_5g") or 0),
            }
            for r in records
        ],
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/cem", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


@_ai_retry
def infer_vae_anomaly(run_id: str, region: str, records: list[dict]) -> dict:
    payload = {
        "run_id": run_id,
        "region": region,
        "records": [
            {
                "throughput_mbps": float(r.get("throughput_mbps") or 80.0),
                "latency_ms": float(r.get("latency_ms") or 25.0),
                "packet_loss_rate": float(r.get("packet_loss_rate") or 0.5),
                "jitter_ms": float(r.get("jitter_ms") or 5.0),
                "cell_load_pct": float(r.get("cell_load_pct") or 50.0),
                "rsrp_dbm": float(r.get("rsrp_dbm") or -85.0),
                "active_users": int(r.get("active_users") or 200),
                "integrity": float(r.get("integrity") or 0.95),
                "call_drop_rate": float(r.get("call_drop_rate") or 0.01),
            }
            for r in records
        ],
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/vae-anomaly", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


@_ai_retry
def infer_rat_underservice(run_id: str, region: str, records: list[dict]) -> dict:
    payload = {
        "run_id": run_id,
        "region": region,
        "records": [
            {
                "dou_total": float(r.get("dou_total") or 0),
                "duration": float(r.get("duration") or 0),
                "s1_mme_sr": float(r.get("s1_mme_sr") or 0.5),
                "iu_attach_sr": float(r.get("iu_attach_sr") or 0.5),
                "gb_attach_sr": float(r.get("gb_attach_sr") or 0.5),
                "network_experience_index": float(r.get("network_experience_index") or 0.5),
                "avg_throughput": float(r.get("avg_throughput") or 80.0),
                "avg_latency": float(r.get("avg_latency") or 25.0),
                "avg_packet_loss": float(r.get("avg_packet_loss") or 0.5),
                "anomaly_rate": float(r.get("anomaly_rate") or 0.05),
            }
            for r in records
        ],
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/rat-underservice", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()
