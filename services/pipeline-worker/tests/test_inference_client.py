"""Tests for AI inference client — mock HTTP calls."""
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from worker.inference.client import infer_sla_risk, infer_anomaly


def test_infer_sla_risk_parses_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "score": 0.72,
        "explanation": {"method": "GBR"},
        "model_version": "v2.0",
    }
    mock_resp.raise_for_status = lambda: None

    with patch("worker.inference.client.requests.post", return_value=mock_resp):
        score, explanation, version = infer_sla_risk(
            "run-001", "test",
            datetime(2026, 3, 1, tzinfo=timezone.utc),
            datetime(2026, 3, 1, 0, 15, tzinfo=timezone.utc),
            {"mean_latency_ms": 25.0},
        )
    assert score == 0.72
    assert version == "v2.0"
    assert explanation["method"] == "GBR"


def test_infer_anomaly_returns_dict():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "anomalous_count": 2,
        "anomaly_rate": 0.1,
        "records": [],
        "model_version": "v2.0",
    }
    mock_resp.raise_for_status = lambda: None

    records = [
        {"throughput_mbps": 10.0, "latency_ms": 120.0,
         "packet_loss_pct": 5.0, "active_users": 100, "signal_rsrp_dbm": -110.0}
    ]
    with patch("worker.inference.client.requests.post", return_value=mock_resp):
        result = infer_anomaly("run-001", "test", records)
    assert result["anomalous_count"] == 2
