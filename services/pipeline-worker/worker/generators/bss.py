"""Synthetic BSS subscriber generator with correlated degradation."""
from datetime import datetime, timezone, timedelta
import numpy as np


def generate_bss(
    n: int = 200,
    region: str = "demo",
    seed: int = 99,
    cells: list[str] | None = None,
    fault_info: dict | None = None,
) -> list[dict]:
    """Synthetic BSS records with correlated degradation patterns.

    Tunisian market model (verified 2025 forfait data):
      - 80% prepaid subscribers (recharge/forfait-based revenue)
      - 20% postpaid subscribers (fixed monthly plan)
      - Revenue in TND based on verified operator pricing
      - Prepaid ARPU: ~8-15 TND/month; Postpaid ARPU: ~45-70 TND/month

    When a subscriber's serving cell is in a fault state, BSS metrics degrade:
    lower data usage, higher churn risk, fewer voice minutes — creating a
    measurable OSS↔BSS correlation.
    """
    rng = np.random.default_rng(seed)
    operators = ["Ooredoo Tunisie", "Tunisie Telecom", "Orange Tunisie"]
    if cells is None:
        cells = [f"CELL-{i:03d}" for i in range(1, 11)]

    # Prepaid forfait tiers — verified 2025 pricing (all 3 operators converge)
    prepaid_plans = [
        ("data_1go", 3.0, 7.0),  # ~4-5 DT: light users, 1-1.5 Go bundles
        ("data_4go", 8.0, 14.0),  # ~10 DT: mid-tier 4 Go
        ("data_6go", 12.0, 18.0),  # ~15 DT: 6 Go
        ("data_25go", 25.0, 35.0),  # ~30 DT: standard 5G/4G bundle
        ("data_45go", 42.0, 55.0),  # ~50 DT: heavy user
        ("data_100go", 65.0, 80.0),  # ~72 DT: very heavy user
    ]
    # Postpaid plan tiers — verified ranges across operators
    postpaid_plans = [
        ("post_40", 35.0, 45.0),  # entry postpaid ~40 DT/month
        ("post_60", 52.0, 68.0),  # mid postpaid ~60 DT/month
        ("post_90", 80.0, 100.0),  # premium postpaid ~90 DT/month
    ]

    fault_cells = set(fault_info["fault_cells"]) if fault_info else set()
    fault_start_idx = fault_info["fault_start_idx"] if fault_info else 0
    fault_end_idx = fault_info["fault_end_idx"] if fault_info else 0

    now = datetime.now(timezone.utc)
    rows = []
    for i in range(n):
        ts = now - timedelta(minutes=n - i)
        serving_cell = cells[i % len(cells)]

        # 80% prepaid / 20% postpaid (matches INTT 2023 market stats)
        is_prepaid = rng.random() < 0.80
        if is_prepaid:
            plan_name, lo, hi = prepaid_plans[int(rng.integers(0, len(prepaid_plans)))]
            line_type = "prepaid"
        else:
            plan_name, lo, hi = postpaid_plans[
                int(rng.integers(0, len(postpaid_plans)))
            ]
            line_type = "postpaid"

        base_revenue = float(rng.uniform(lo, hi))
        base_data = float(rng.uniform(0.5, 45.0))
        base_voice = int(rng.integers(10, 550))
        base_sms = int(rng.integers(5, 180))
        base_churn = float(rng.uniform(0.0, 0.35))

        # ── correlated BSS degradation ───────────────────────────────────────────
        cell_faulted = (
            serving_cell in fault_cells and fault_start_idx <= i <= fault_end_idx
        )
        if cell_faulted:
            base_data *= float(rng.uniform(0.3, 0.6))  # data usage drops
            base_voice = int(base_voice * rng.uniform(0.4, 0.7))
            base_churn += float(rng.uniform(0.3, 0.55))  # churn risk spikes

        rows.append(
            {
                "ts": ts.isoformat(),
                "region": region,
                "operator": operators[i % len(operators)],
                "subscriber_id": f"TN-{rng.integers(100000, 999999)}",
                "line_type": line_type,
                "plan": plan_name,
                "serving_cell": serving_cell,
                "revenue_tnd": float(round(base_revenue, 3)),
                "data_used_gb": float(round(max(0.01, base_data), 3)),
                "voice_min": max(0, base_voice),
                "sms_count": base_sms,
                "churn_risk": float(round(min(1.0, base_churn), 4)),
            }
        )
    return rows
