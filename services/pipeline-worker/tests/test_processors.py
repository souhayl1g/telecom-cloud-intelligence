"""Tests for OSS/BSS processors."""

from worker.processors.oss import build_processed_oss
from worker.processors.bss import build_processed_bss, build_curated_dataset


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


def test_build_processed_bss_generation_flags():
    rec = {"generation": "4G", "rat_gap_score": 0.1}
    result = build_processed_bss([rec])
    assert result[0]["generation_4g"] == 1.0
    assert result[0]["generation_5g"] == 0.0
    assert result[0]["rat_bucket"] == "matched"


def test_build_processed_bss_rat_bucket_underserved():
    rec = {"generation": "5G", "rat_gap_score": 0.6}
    result = build_processed_bss([rec])
    assert result[0]["generation_5g"] == 1.0
    assert result[0]["rat_bucket"] == "underserved"


def test_build_curated_dataset_v3():
    oss = [_make_oss_record()]
    bss = [
        {
            "area": "test",
            "dou_total": 1e9,
            "duration": 100,
            "network_experience_index": 0.8,
        }
    ]
    vae = {"anomalous_count": 1, "anomaly_rate": 0.5}
    cem = {"predictions": [{"index": 0, "cem_score": 0.9}]}
    rat = {"underserved_count": 0, "underserved_rate": 0.0}
    corr = []
    result = build_curated_dataset(oss, bss, vae, cem, rat, corr)
    assert result["vae_anomaly_count"] == 1
    assert result["cem_predictions"] == 1
    assert result["rat_underserved_count"] == 0
    assert len(result["areas_summary"]) == 1
