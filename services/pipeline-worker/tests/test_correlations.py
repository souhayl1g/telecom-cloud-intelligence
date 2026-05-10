"""Tests for correlation analytics."""
from worker.analytics.correlations import compute_correlations


def _make_correlated_records(n=10):
    """OSS records with high latency in CELL-001, low in CELL-002/003."""
    oss = []
    bss = []
    for i in range(n):
        # CELL-001: high latency → low NEI
        oss.append({
            "cell_id": "CELL-001",
            "area": "CELL-001",
            "latency_ms": 80.0 + i,
            "throughput_mbps": 20.0,
            "packet_loss_pct": 3.0,
        })
        bss.append({
            "area": "CELL-001",
            "dou_total": 1e9,
            "network_experience_index": 0.3,
            "s1_mme_sr": 0.60,
        })
        # CELL-002: low latency → high NEI
        oss.append({
            "cell_id": "CELL-002",
            "area": "CELL-002",
            "latency_ms": 20.0 + i * 0.1,
            "throughput_mbps": 80.0,
            "packet_loss_pct": 0.2,
        })
        bss.append({
            "area": "CELL-002",
            "dou_total": 5e9,
            "network_experience_index": 0.9,
            "s1_mme_sr": 0.98,
        })
        # CELL-003: medium latency → medium NEI (ensures 3+ cells)
        oss.append({
            "cell_id": "CELL-003",
            "area": "CELL-003",
            "latency_ms": 50.0 + i * 0.2,
            "throughput_mbps": 50.0,
            "packet_loss_pct": 1.5,
        })
        bss.append({
            "area": "CELL-003",
            "dou_total": 3e9,
            "network_experience_index": 0.6,
            "s1_mme_sr": 0.80,
        })
    return oss, bss


def test_compute_correlations_returns_list():
    oss, bss = _make_correlated_records()
    result = compute_correlations(oss, bss)
    assert isinstance(result, list)


def test_compute_correlations_methods_present():
    oss, bss = _make_correlated_records()
    result = compute_correlations(oss, bss)
    methods = {r["method"] for r in result}
    assert "pearson" in methods
    assert "spearman" in methods


def test_compute_correlations_requires_min_3_cells():
    # Only 1 common cell — should return empty
    oss = [{"cell_id": "A", "area": "A", "latency_ms": 20, "throughput_mbps": 80, "packet_loss_pct": 0.1}]
    bss = [{"area": "A", "dou_total": 1e9, "network_experience_index": 0.8, "s1_mme_sr": 0.95}]
    result = compute_correlations(oss, bss)
    assert result == []


def test_compute_correlations_corr_value_range():
    oss, bss = _make_correlated_records(n=20)
    result = compute_correlations(oss, bss)
    for r in result:
        if r["corr_value"] is not None:
            assert -1.0 <= r["corr_value"] <= 1.0
