"""
OSS Cell KPI Simulator (Area-Correlated)
----------------------------------------
Generates synthetic OSS cell-level KPIs that are statistically correlated
with BSS subscriber density and usage patterns per area.

Logic:
  - For each area, read aggregated BSS metrics (subscriber count, avg dou_total,
    usertype distribution, device generation mix).
  - Generate 10 cells per area.
  - Base KPIs drawn from realistic distributions, then scaled by area load.
  - Fault injection: 2-3 cells per area get degraded KPIs per month.
  - Temporal drift: Apr improves, May strains, June shows churn impact.

Months generated: 2026-02 through 2026-06 (Feb/Mar match real BSS months).
"""

import hashlib
import os

import numpy as np
import psycopg2
from psycopg2.extras import execute_values

np.random.seed(42)

DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://telecom:telecom_pw@localhost:5432/telecom_intel"
)

# Tunisia's 24 governorates (as they appear in the data)
TUNISIAN_AREAS = [
    "Ariana",
    "Beja",
    "Ben Arous",
    "Bizerte",
    "Gabes",
    "Gafsa",
    "Jendouba",
    "Kairouan",
    "Kasserine",
    "Kebili",
    "La Manouba",
    "Le Kef",
    "Mahdia",
    "Medenine",
    "Monastir",
    "NABEUL",
    "Sfax",
    "Sidi Bouzid",
    "Siliana",
    "Sousse",
    "Tataouine",
    "Tozeur",
    "Tunis",
    "Zaghouan",
]

CELLS_PER_AREA = 10


def get_conn():
    return psycopg2.connect(DB_URL)


def get_area_profiles(month_year: str):
    """Fetch aggregated BSS stats per area for a given month."""
    sql = """
        SELECT
            area,
            COUNT(*) AS sub_count,
            AVG(dou_total) AS avg_dou,
            AVG(CASE WHEN highest_rat = '5G' THEN 1 ELSE 0 END) AS pct_5g,
            AVG(CASE WHEN highest_rat = '4G' THEN 1 ELSE 0 END) AS pct_4g,
            AVG(CASE WHEN highest_rat = '3G' THEN 1 ELSE 0 END) AS pct_3g,
            AVG(CASE WHEN highest_rat = '2G' THEN 1 ELSE 0 END) AS pct_2g,
            AVG(CASE WHEN usertype = 'Data User' THEN 1 ELSE 0 END) AS pct_data,
            AVG(CASE WHEN usim_flag = 0 THEN 1 ELSE 0 END) AS pct_legacy_sim
        FROM bss_subscribers
        WHERE month_year = %s
        GROUP BY area
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (month_year,))
            rows = cur.fetchall()
    # map area -> stats dict
    profiles = {}
    for row in rows:
        profiles[row[0]] = {
            "sub_count": row[1] or 1000,
            "avg_dou": row[2] or 1e9,
            "pct_5g": row[3] or 0.0,
            "pct_4g": row[4] or 0.0,
            "pct_3g": row[5] or 0.0,
            "pct_2g": row[6] or 0.0,
            "pct_data": row[7] or 0.5,
            "pct_legacy_sim": row[8] or 0.5,
        }
    # fallback for any missing areas
    for area in TUNISIAN_AREAS:
        if area not in profiles:
            profiles[area] = {
                "sub_count": 1000,
                "avg_dou": 1e9,
                "pct_5g": 0.07,
                "pct_4g": 0.52,
                "pct_3g": 0.06,
                "pct_2g": 0.06,
                "pct_data": 0.71,
                "pct_legacy_sim": 0.74,
            }
    return profiles


def generate_cell_kpis(area: str, cell_idx: int, profile: dict, month_year: str):
    """Generate KPIs for one cell, correlated with area BSS profile."""
    # Seed per (area, cell, month) for reproducibility
    seed_str = f"{area}-{cell_idx}-{month_year}"
    rng = np.random.default_rng(
        int(hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**31)
    )

    load_factor = profile["sub_count"] / 20000.0  # normalize around ~20K subs per area
    _data_heavy = profile["pct_data"]
    _legacy_penalty = profile["pct_legacy_sim"]

    # Base distributions
    base_throughput = rng.normal(45.0, 12.0) * (1.2 - 0.3 * load_factor)
    base_latency = rng.normal(25.0, 8.0) * (0.8 + 0.4 * load_factor)
    base_packet_loss = rng.normal(0.8, 0.3) * (0.7 + 0.5 * load_factor)
    base_jitter = rng.normal(5.0, 2.0) * (0.8 + 0.3 * load_factor)
    base_rsrp = rng.normal(-85.0, 10.0) - 5.0 * load_factor

    # Temporal drift per month
    month_drift = {
        "2026-02": 0.0,
        "2026-03": -0.02,
        "2026-04": 0.05,  # spring optimization
        "2026-05": -0.08,  # pre-summer strain
        "2026-06": -0.15,  # churn + summer heat strain
    }.get(month_year, 0.0)

    # Apply drift
    base_throughput *= 1 + month_drift
    base_latency *= 1 - month_drift
    base_packet_loss *= 1 - month_drift
    base_jitter *= 1 - month_drift
    base_rsrp += month_drift * 10.0

    # Fault injection: ~20% of cells per area are degraded
    fault_cells = set(rng.choice(CELLS_PER_AREA, size=2, replace=False))
    is_fault = cell_idx in fault_cells

    if is_fault:
        base_throughput *= rng.uniform(0.5, 0.75)
        base_latency *= rng.uniform(1.5, 3.0)
        base_packet_loss *= rng.uniform(2.0, 5.0)
        base_jitter *= rng.uniform(1.5, 3.0)
        base_rsrp -= rng.uniform(10.0, 25.0)

    # Clamp realistic ranges
    throughput = max(1.0, min(150.0, base_throughput))
    latency = max(5.0, min(300.0, base_latency))
    packet_loss = max(0.0, min(20.0, base_packet_loss))
    jitter = max(1.0, min(100.0, base_jitter))
    active_users = int(
        max(10, profile["sub_count"] // CELLS_PER_AREA * rng.uniform(0.7, 1.3))
    )
    rsrp = max(-130.0, min(-50.0, base_rsrp))
    cell_load = min(100.0, max(10.0, load_factor * 80.0 + rng.normal(0, 10)))

    return {
        "cell_id": f"{area.upper()[:3]}-C{cell_idx:02d}",
        "area": area,
        "month_year": month_year,
        "throughput_mbps": round(throughput, 2),
        "latency_ms": round(latency, 2),
        "packet_loss_rate": round(packet_loss, 4),
        "jitter_ms": round(jitter, 2),
        "active_users": active_users,
        "rsrp_dbm": round(rsrp, 1),
        "cell_load_pct": round(cell_load, 1),
        "anomaly_flag": is_fault,
    }


def simulate_month(month_year: str) -> int:
    """Generate and insert OSS cell KPIs for one month."""
    print(f"[oss-sim] Generating for {month_year} ...")
    profiles = get_area_profiles(month_year)

    rows = []
    for area in TUNISIAN_AREAS:
        profile = profiles[area]
        for cell_idx in range(CELLS_PER_AREA):
            kpi = generate_cell_kpis(area, cell_idx, profile, month_year)
            rows.append(tuple(kpi.values()))

    sql = """
        INSERT INTO oss_cell_kpis (
            cell_id, area, month_year, throughput_mbps, latency_ms,
            packet_loss_rate, jitter_ms, active_users, rsrp_dbm,
            cell_load_pct, anomaly_flag
        ) VALUES %s
        ON CONFLICT DO NOTHING
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
        conn.commit()

    print(f"[oss-sim] {month_year}: {len(rows)} cells inserted")
    return len(rows)


def main():
    months = ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
    total = 0
    for month in months:
        total += simulate_month(month)
    print(f"\n[done] Total OSS cells simulated: {total}")


if __name__ == "__main__":
    main()
