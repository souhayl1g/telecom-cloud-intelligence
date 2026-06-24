"""Synthetic OSS KPI record generator with fault injection."""

from datetime import datetime, timezone, timedelta
import numpy as np


def generate_oss(
    n: int = 200, region: str = "demo", seed: int = 42
) -> tuple[list[dict], dict]:
    """Synthetic OSS KPI records with realistic fault injection.

    Patterns:
      - Business-hour load curves (Gaussian peak at 13:00 local)
      - Fault injection: 2–3 random cells experience degradation for ~20 % of window
      - Degradation: throughput collapse, latency spike, packet loss surge, signal drop

    Returns (records, fault_info) describing injected faults.
    """
    rng = np.random.default_rng(seed)
    cells = [f"CELL-{i:03d}" for i in range(1, 11)]
    now = datetime.now(timezone.utc)

    # ── fault injection plan ───────────────────────────────────────────────
    n_fault_cells = int(rng.integers(2, 4))
    fault_cells = set(rng.choice(cells, size=n_fault_cells, replace=False))
    fault_start = int(n * rng.uniform(0.25, 0.45))
    fault_duration = int(n * rng.uniform(0.15, 0.25))
    fault_end = min(n - 1, fault_start + fault_duration)

    rows = []
    for i in range(n):
        ts = now - timedelta(minutes=n - i)
        cell = cells[i % len(cells)]

        # ── business-hour traffic modifier ─────────────────────────────────
        hour = ts.hour + ts.minute / 60.0
        biz_factor = 1.0 + 0.4 * np.exp(-0.5 * ((hour - 13.0) / 3.0) ** 2)

        # ── base KPIs (normal conditions) ──────────────────────────────────
        tput = float(rng.normal(80, 12)) * (0.7 + 0.3 / biz_factor)
        lat = float(rng.normal(22, 6)) * biz_factor
        loss = float(rng.uniform(0, 1.5)) * biz_factor
        usr = int(rng.integers(50, 300) * biz_factor)
        rsrp = float(rng.normal(-82, 8))

        # ── fault injection ───────────────────────────────────────────────
        is_fault = (cell in fault_cells) and (fault_start <= i <= fault_end)
        if is_fault:
            tput *= float(rng.uniform(0.10, 0.35))  # throughput collapse
            lat *= float(rng.uniform(2.5, 5.0))  # latency spike
            loss += float(rng.uniform(3.0, 8.0))  # packet loss surge
            rsrp -= float(rng.uniform(15, 30))  # signal degradation

        rows.append(
            {
                "ts": ts.isoformat(),
                "region": region,
                "cell_id": cell,
                "throughput_mbps": float(round(max(0.1, tput), 2)),
                "latency_ms": float(round(max(1.0, lat), 2)),
                "packet_loss_pct": float(round(min(15.0, max(0.0, loss)), 4)),
                "active_users": max(10, usr),
                "signal_rsrp_dbm": float(round(max(-140.0, min(-40.0, rsrp)), 2)),
                "is_fault": is_fault,
            }
        )

    fault_info = {
        "fault_cells": sorted(fault_cells),
        "fault_start_idx": fault_start,
        "fault_end_idx": fault_end,
        "fault_records": sum(1 for r in rows if r["is_fault"]),
    }
    return rows, fault_info
