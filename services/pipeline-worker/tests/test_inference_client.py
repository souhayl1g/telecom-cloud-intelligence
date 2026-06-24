"""Tests for v3.0 AI inference client — mock HTTP calls."""

from unittest.mock import patch, MagicMock
from worker.inference.v3_client import (
    infer_cem,
    infer_vae_anomaly,
    infer_rat_underservice,
)


def test_infer_cem_parses_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "run_id": "run-001",
        "region": "test",
        "total": 2,
        "predictions": [
            {"index": 0, "cem_score": 0.85},
            {"index": 1, "cem_score": 0.72},
        ],
        "model_version": "v3.0",
    }
    mock_resp.raise_for_status = lambda: None

    records = [
        {
            "usim_bottleneck": 0,
            "data_intensity": 1.2,
            "dou_total": 1e9,
            "duration": 100,
            "s1_mme_sr": 0.95,
            "iu_attach_sr": 0.90,
            "gb_attach_sr": 0.85,
            "avg_throughput": 80.0,
            "avg_latency": 25.0,
            "avg_packet_loss": 0.5,
            "anomaly_rate": 0.05,
            "generation_4g": 1.0,
            "generation_5g": 0.0,
        },
    ]
    with patch("worker.inference.v3_client.requests.post", return_value=mock_resp):
        result = infer_cem("run-001", "test", records)
    assert result["total"] == 2
    assert result["predictions"][0]["cem_score"] == 0.85
    assert result["model_version"] == "v3.0"


def test_infer_vae_anomaly_returns_dict():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "run_id": "run-001",
        "region": "test",
        "total": 10,
        "anomalous_count": 1,
        "anomaly_rate": 0.1,
        "threshold": 0.18,
        "records": [
            {
                "index": 0,
                "is_anomaly": True,
                "anomaly_score": 0.95,
                "reconstruction_error": 0.25,
            },
        ],
        "model_version": "v3.0",
    }
    mock_resp.raise_for_status = lambda: None

    records = [
        {
            "throughput_mbps": 10.0,
            "latency_ms": 120.0,
            "packet_loss_rate": 5.0,
            "jitter_ms": 10.0,
            "cell_load_pct": 80.0,
            "rsrp_dbm": -110.0,
            "active_users": 100,
            "integrity": 0.95,
            "call_drop_rate": 0.01,
        },
    ]
    with patch("worker.inference.v3_client.requests.post", return_value=mock_resp):
        result = infer_vae_anomaly("run-001", "test", records)
    assert result["anomalous_count"] == 1
    assert result["anomaly_rate"] == 0.1


def test_infer_rat_underservice_returns_dict():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "run_id": "run-001",
        "region": "test",
        "total": 5,
        "underserved_count": 2,
        "underserved_rate": 0.4,
        "predictions": [
            {"index": 0, "is_underserved": True, "underservice_prob": 0.82},
            {"index": 1, "is_underserved": False, "underservice_prob": 0.12},
        ],
        "model_version": "v3.0",
    }
    mock_resp.raise_for_status = lambda: None

    records = [
        {
            "dou_total": 1e9,
            "duration": 100,
            "s1_mme_sr": 0.95,
            "iu_attach_sr": 0.90,
            "gb_attach_sr": 0.85,
            "network_experience_index": 0.88,
            "avg_throughput": 80.0,
            "avg_latency": 25.0,
            "avg_packet_loss": 0.5,
            "anomaly_rate": 0.05,
        },
    ]
    with patch("worker.inference.v3_client.requests.post", return_value=mock_resp):
        result = infer_rat_underservice("run-001", "test", records)
    assert result["underserved_count"] == 2
    assert result["underserved_rate"] == 0.4
