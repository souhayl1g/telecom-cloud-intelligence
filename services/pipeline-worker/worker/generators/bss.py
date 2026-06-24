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
    """Synthetic BSS records with correlated degradation patterns (v3.0 schema).

    Generates subscribers with fields compatible with CEM LightGBM and
    RAT XGBoost v3.0 inference endpoints.
    """
    rng = np.random.default_rng(seed)
    if cells is None:
        cells = [f"CELL-{i:03d}" for i in range(1, 11)]

    fault_cells = set(fault_info["fault_cells"]) if fault_info else set()
    fault_start_idx = fault_info["fault_start_idx"] if fault_info else 0
    fault_end_idx = fault_info["fault_end_idx"] if fault_info else 0

    now = datetime.now(timezone.utc)
    rows = []
    for i in range(n):
        ts = now - timedelta(minutes=n - i)
        serving_cell = cells[i % len(cells)]

        # Device generation / RAT
        generation = rng.choice(["4G", "5G", "3G", "2G"])
        highest_rat = generation
        usertype = rng.choice(["Data User", "Voice User", "Mixed"])

        # Base subscriber metrics
        dou_total = int(rng.uniform(0.5, 45.0) * 1e9)  # bytes
        duration = float(rng.uniform(60, 18000))  # voice seconds
        s1_mme_sr = float(rng.uniform(0.85, 0.99))
        iu_attach_sr = float(rng.uniform(0.80, 0.98))
        gb_attach_sr = float(rng.uniform(0.75, 0.97))

        data_intensity = dou_total / max(duration, 1)
        network_experience_index = (
            s1_mme_sr * 0.5 + iu_attach_sr * 0.3 + gb_attach_sr * 0.2
        )
        usim_bottleneck = (
            1.0
            if ("4G" in generation or "5G" in generation)
            and highest_rat in ["2G", "3G"]
            else 0.0
        )

        # ── correlated BSS degradation ───────────────────────────────────────────
        cell_faulted = (
            serving_cell in fault_cells and fault_start_idx <= i <= fault_end_idx
        )
        if cell_faulted:
            dou_total = int(dou_total * rng.uniform(0.3, 0.6))
            duration *= float(rng.uniform(0.4, 0.7))
            s1_mme_sr = max(0.5, s1_mme_sr - float(rng.uniform(0.1, 0.3)))
            iu_attach_sr = max(0.5, iu_attach_sr - float(rng.uniform(0.1, 0.3)))
            gb_attach_sr = max(0.5, gb_attach_sr - float(rng.uniform(0.1, 0.3)))
            network_experience_index = (
                s1_mme_sr * 0.5 + iu_attach_sr * 0.3 + gb_attach_sr * 0.2
            )

        rows.append(
            {
                "ts": ts.isoformat(),
                "region": region,
                "subscriber_id": f"TN-{rng.integers(100000, 999999)}",
                "area": serving_cell,
                "generation": generation,
                "highest_rat": highest_rat,
                "dou_total": int(dou_total),
                "duration": float(round(duration, 2)),
                "s1_mme_sr": float(round(s1_mme_sr, 4)),
                "iu_attach_sr": float(round(iu_attach_sr, 4)),
                "gb_attach_sr": float(round(gb_attach_sr, 4)),
                "usertype": usertype,
                "usim_bottleneck": float(usim_bottleneck),
                "data_intensity": float(round(data_intensity, 4)),
                "network_experience_index": float(round(network_experience_index, 4)),
                "rat_gap_score": float(round(rng.uniform(0, 0.8), 4)),
            }
        )
    return rows
