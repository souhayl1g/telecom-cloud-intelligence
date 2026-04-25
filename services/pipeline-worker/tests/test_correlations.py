"""Tests for correlation analytics."""
from worker.analytics.correlations import compute_correlations


def _make_correlated_records(n=10):
    """OSS records with high latency in CELL-001, low in CELL-002/003."""
    oss = []
    bss = []
    for i in range(n):
        # CELL-001: high latency → low revenue
        oss.append({
            "cell_id": "CELL-001",
            "latency_ms": 80.0 + i,
            "throughput_mbps": 20.0,
            "packet_loss_pct": 3.0,
        })
        bss.append({
            "serving_cell": "CELL-001",
            "revenue_tnd": 5.0 - i * 0.1,
            "data_used_gb": 1.0,
            "churn_risk": 0.8,
        })
        # CELL-002: low latency → high revenue
        oss.append({
            "cell_id": "CELL-002",
            "latency_ms": 20.0 + i * 0.1,
            "throughput_mbps": 80.0,
            "packet_loss_pct": 0.2,
        })
        bss.append({
            "serving_cell": "CELL-002",
            "revenue_tnd": 30.0 + i * 0.5,
            "data_used_gb": 10.0,
            "churn_risk": 0.1,
        })
        # CELL-003: medium latency → medium revenue (ensures 3+ cells)
        oss.append({
            "cell_id": "CELL-003",
            "latency_ms": 50.0 + i * 0.2,
            "throughput_mbps": 50.0,
            "packet_loss_pct": 1.5,
        })
        bss.append({
            "serving_cell": "CELL-003",
            "revenue_tnd": 17.5 + i * 0.2,
            "data_used_gb": 5.5,
            "churn_risk": 0.45,
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
    # Only 2 common cells — should return empty
    oss = [{"cell_id": "A", "latency_ms": 20, "throughput_mbps": 80, "packet_loss_pct": 0.1}]
    bss = [{"serving_cell": "A", "revenue_tnd": 10, "data_used_gb": 5, "churn_risk": 0.2}]
    result = compute_correlations(oss, bss)
    assert result == []


def test_compute_correlations_corr_value_range():
    oss, bss = _make_correlated_records(n=20)
    result = compute_correlations(oss, bss)
    for r in result:
        if r["corr_value"] is not None:
            assert -1.0 <= r["corr_value"] <= 1.0
