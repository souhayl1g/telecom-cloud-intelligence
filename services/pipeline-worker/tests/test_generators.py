"""Tests for synthetic data generators."""

from worker.generators.oss import generate_oss
from worker.generators.bss import generate_bss


def test_generate_oss_record_count():
    records, fault_info = generate_oss(n=10, region="test", seed=42)
    assert len(records) == 10


def test_generate_oss_required_fields():
    records, _ = generate_oss(n=5, seed=1)
    required = {
        "ts",
        "cell_id",
        "throughput_mbps",
        "latency_ms",
        "packet_loss_pct",
        "active_users",
        "signal_rsrp_dbm",
        "is_fault",
    }
    for rec in records:
        assert required.issubset(rec.keys())


def test_generate_oss_value_ranges():
    records, _ = generate_oss(n=100, seed=7)
    for rec in records:
        assert rec["throughput_mbps"] > 0
        assert rec["latency_ms"] > 0
        assert 0 <= rec["packet_loss_pct"] <= 15
        assert -140 <= rec["signal_rsrp_dbm"] <= -40


def test_generate_oss_fault_injection():
    records, fault_info = generate_oss(n=200, seed=42)
    assert fault_info["fault_records"] > 0
    assert len(fault_info["fault_cells"]) >= 2


def test_generate_bss_record_count():
    rows = generate_bss(n=20, seed=5)
    assert len(rows) == 20


def test_generate_bss_required_fields():
    rows = generate_bss(n=5, seed=1)
    required = {
        "ts",
        "subscriber_id",
        "area",
        "generation",
        "highest_rat",
        "dou_total",
        "duration",
        "s1_mme_sr",
        "iu_attach_sr",
        "gb_attach_sr",
        "usertype",
        "usim_bottleneck",
        "data_intensity",
        "network_experience_index",
        "rat_gap_score",
    }
    for row in rows:
        assert required.issubset(row.keys())


def test_generate_bss_dou_positive():
    rows = generate_bss(n=200, seed=99)
    for row in rows:
        assert row["dou_total"] >= 0
        assert row["duration"] >= 0


def test_generate_bss_sr_range():
    rows = generate_bss(n=100, seed=42)
    for row in rows:
        assert 0 <= row["s1_mme_sr"] <= 1
        assert 0 <= row["iu_attach_sr"] <= 1
        assert 0 <= row["gb_attach_sr"] <= 1
