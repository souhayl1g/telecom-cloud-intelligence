"""Tests for OSS/BSS processors."""
from worker.processors.oss import build_processed_oss
from worker.processors.bss import build_processed_bss


def _make_oss_record(lat=25.0, tput=80.0, loss=0.5, users=150, rsrp=-82.0, fault=False):
    return {
        "ts": "2026-03-01T10:00:00+00:00",
        "region": "test",
        "cell_id": "CELL-001",
        "throughput_mbps": tput,
        "latency_ms": lat,
        "packet_loss_pct": loss,
        "active_users": users,
        "signal_rsrp_dbm": rsrp,
        "is_fault": fault,
    }


def test_build_processed_oss_removes_is_fault():
    rec = _make_oss_record()
    result = build_processed_oss([rec])
    assert "is_fault" not in result[0]


def test_build_processed_oss_latency_severity_normal():
    rec = _make_oss_record(lat=20.0)
    result = build_processed_oss([rec])
    assert result[0]["latency_severity"] == "normal"


def test_build_processed_oss_latency_severity_critical():
    rec = _make_oss_record(lat=90.0)
    result = build_processed_oss([rec])
    assert result[0]["latency_severity"] == "critical"


def test_build_processed_oss_throughput_category_degraded():
    rec = _make_oss_record(tput=10.0)
    result = build_processed_oss([rec])
    assert result[0]["throughput_category"] == "degraded"


def test_build_processed_bss_arpu_low():
    rec = {"revenue_tnd": 5.0, "data_used_gb": 2.0, "churn_risk": 0.1}
    result = build_processed_bss([rec])
    assert result[0]["arpu_category"] == "low"


def test_build_processed_bss_churn_bucket_risk():
    rec = {"revenue_tnd": 30.0, "data_used_gb": 5.0, "churn_risk": 0.75}
    result = build_processed_bss([rec])
    assert result[0]["churn_bucket"] == "risk"


def test_build_processed_bss_data_intensity():
    rec = {"revenue_tnd": 10.0, "data_used_gb": 5.0, "churn_risk": 0.2}
    result = build_processed_bss([rec])
    assert result[0]["data_intensity"] == round(5.0 / 10.0, 4)
