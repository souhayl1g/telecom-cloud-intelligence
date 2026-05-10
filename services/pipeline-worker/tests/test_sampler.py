"""Tests for rolling window sampler — mock DB queries."""
from unittest.mock import patch, MagicMock
from worker.sampler import sample_bss_records, sample_oss_records


def _mock_conn_bss():
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("hash001", "Tunis", "4G", "4G", 1500000000, 120.0, 0.95, 0.90, 0.85, "Data User", "2026-03",
         True, 12500000.0, 0.88, 0.1),
        ("hash002", "Sfax", "5G", "4G", 3000000000, 200.0, 0.88, 0.92, 0.80, "Data User", "2026-03",
         False, 15000000.0, 0.85, 0.3),
    ]
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn


def _mock_conn_oss():
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("TUN-C00", "Tunis", 45.0, 25.0, 0.8, 5.0, 150, -85.0, 60.0, False),
        ("SFX-C01", "Sfax", 30.0, 40.0, 1.2, 8.0, 200, -95.0, 75.0, True),
    ]
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn


def test_sample_bss_returns_list():
    with patch("worker.sampler.get_conn", return_value=_mock_conn_bss()):
        rows = sample_bss_records(n=2)
    assert len(rows) == 2


def test_sample_bss_required_fields():
    with patch("worker.sampler.get_conn", return_value=_mock_conn_bss()):
        rows = sample_bss_records(n=2)
    required = {"ts", "subscriber_id", "area", "generation", "highest_rat", "source",
                "dou_total", "duration", "s1_mme_sr", "usim_bottleneck",
                "data_intensity", "network_experience_index", "rat_gap_score"}
    for row in rows:
        assert required.issubset(row.keys())
        assert row["source"] == "real"


def test_sample_oss_returns_list():
    with patch("worker.sampler.get_conn", return_value=_mock_conn_oss()):
        rows = sample_oss_records(n=2)
    assert len(rows) == 2


def test_sample_oss_required_fields():
    with patch("worker.sampler.get_conn", return_value=_mock_conn_oss()):
        rows = sample_oss_records(n=2)
    required = {"ts", "region", "cell_id", "throughput_mbps", "latency_ms", "source",
                "jitter_ms", "cell_load_pct", "signal_rsrp_dbm"}
    for row in rows:
        assert required.issubset(row.keys())
        assert row["source"] == "real"


def test_sample_oss_fault_detection():
    with patch("worker.sampler.get_conn", return_value=_mock_conn_oss()):
        rows = sample_oss_records(n=2)
    assert rows[0]["is_fault"] is False
    assert rows[1]["is_fault"] is True
