"""
Correlated OSS Simulation — Jan / Feb / May / Jun
-------------------------------------------------
Generates simulated OSS KPIs for months where real data is missing.
KPIs are correlated with BSS subscriber experience per area:
  - Poor NE (low attach SR) → worse OSS (high latency, low throughput, more anomalies)
  - Good NE → better OSS

Target: ~8K-9K rows/month (300 cells × 30 daily snapshots).
Much smaller than real data (~18M) but sufficient for pipeline sampling.
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.getenv("DATABASE_URL", "postgresql://telecom:telecom_pw@localhost:5432/telecom_intel")

MONTHS = ["2026-01", "2026-02", "2026-05", "2026-06"]
CELLS_PER_AREA = 12
DAYS_IN_MONTH = {"2026-01": 31, "2026-02": 28, "2026-05": 31, "2026-06": 30}

RAT_WEIGHTS = {
    "2G": {"throughput": (0.1, 1.0), "latency": (80, 300), "rsrp": (-105, -85), "users": (5, 30)},
    "3G": {"throughput": (1.0, 8.0), "latency": (40, 120), "rsrp": (-100, -80), "users": (10, 80)},
    "4G": {"throughput": (5.0, 80.0), "latency": (15, 60), "rsrp": (-95, -70), "users": (20, 300)},
}


def get_conn():
    return psycopg2.connect(DB_URL)


def fetch_area_ne(month_year: str) -> dict[str, float]:
    """Fetch average network_experience_index per area via bss_subscribers join."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT b.area, AVG(s.network_experience_index) AS ne
                FROM bss_subscribers b
                JOIN subscriber_features s ON b.imsi_hash = s.imsi_hash AND b.month_year = s.month_year
                WHERE b.month_year = %s AND b.area IS NOT NULL
                GROUP BY b.area
            """, (month_year,))
            return {row[0]: float(row[1]) if row[1] else 0.5 for row in cur.fetchall()}


def fetch_area_rat_dist(month_year: str) -> dict[str, dict[str, float]]:
    """Fetch RAT distribution per area from BSS."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT area, highest_rat, COUNT(*)::float
                FROM bss_subscribers
                WHERE month_year = %s AND area IS NOT NULL AND highest_rat IS NOT NULL
                GROUP BY area, highest_rat
            """, (month_year,))
            dist: dict[str, dict[str, float]] = {}
            for area, rat, cnt in cur.fetchall():
                dist.setdefault(area, {})[rat] = cnt
            # Normalize to probabilities
            for area in dist:
                total = sum(dist[area].values())
                dist[area] = {k: v / total for k, v in dist[area].items()}
            return dist


def pick_rat(area: str, rat_dist: dict) -> str:
    dist = rat_dist.get(area, {"4G": 0.5, "3G": 0.3, "2G": 0.2})
    rats = list(dist.keys())
    probs = list(dist.values())
    # Simplify to 2G/3G/4G buckets
    simplified = {"2G": 0.0, "3G": 0.0, "4G": 0.0}
    for r, p in zip(rats, probs):
        ru = (r or "").upper()
        if "2G" in ru:
            simplified["2G"] += p
        elif "3G" in ru:
            simplified["3G"] += p
        elif "4G" in ru or "LTE" in ru:
            simplified["4G"] += p
        elif "5G" in ru:
            simplified["4G"] += p  # treat 5G as 4G-capable for OSS
    total = sum(simplified.values())
    if total == 0:
        simplified = {"4G": 0.5, "3G": 0.3, "2G": 0.2}
    else:
        simplified = {k: v / total for k, v in simplified.items()}
    return np.random.choice(list(simplified.keys()), p=list(simplified.values()))


def generate_kpis(rat: str, ne_index: float) -> dict:
    """Generate OSS KPIs correlated with NE index (0=bad, 1=good)."""
    w = RAT_WEIGHTS[rat]
    rng = np.random.default_rng()

    # NE-driven scaling: bad NE → worse KPIs
    ne_factor = max(0.1, min(1.0, ne_index))
    noise = rng.normal(0, 0.15)

    throughput = w["throughput"][0] + (w["throughput"][1] - w["throughput"][0]) * (ne_factor + noise)
    throughput = max(0.05, throughput)

    latency = w["latency"][1] - (w["latency"][1] - w["latency"][0]) * (ne_factor + noise)
    latency = max(5.0, latency)

    rsrp = w["rsrp"][1] - (w["rsrp"][1] - w["rsrp"][0]) * (1 - ne_factor - noise)
    rsrp = min(-60, max(-120, rsrp))

    users = int(w["users"][0] + (w["users"][1] - w["users"][0]) * rng.uniform(0.3, 1.0))

    packet_loss = max(0.0, (1.0 - ne_factor) * 2.0 + rng.normal(0, 0.3))
    jitter = max(0.0, latency * 0.05 + rng.normal(0, 1.5))
    cell_load = min(100.0, max(5.0, (1.0 - ne_factor) * 60 + rng.normal(20, 10)))

    # Probabilistic anomaly flagging (~3-12% depending on NE)
    base_anom_prob = max(0.0, (1.0 - ne_factor) * 0.10 + rng.normal(0, 0.02))
    is_anom = rng.random() < base_anom_prob

    if is_anom:
        integrity = min(100.0, max(50.0, ne_factor * 100 + rng.normal(0, 5)))
        call_drop = max(2.0, (1.0 - ne_factor) * 5.0 + rng.normal(0, 1.0))
    else:
        integrity = 100.0
        call_drop = max(0.0, (1.0 - ne_factor) * 0.5 + rng.normal(0, 0.2))

    return {
        "throughput_mbps": round(throughput, 2),
        "latency_ms": round(latency, 2),
        "packet_loss_rate": round(packet_loss, 4),
        "jitter_ms": round(jitter, 2),
        "active_users": users,
        "rsrp_dbm": round(rsrp, 1),
        "cell_load_pct": round(cell_load, 2),
        "anomaly_flag": is_anom,
        "integrity": round(integrity, 2),
        "call_drop_rate": round(call_drop, 4),
    }


def simulate_month(month_year: str) -> list[tuple]:
    print(f"[oss-sim] Generating for {month_year} ...")
    area_ne = fetch_area_ne(month_year)
    rat_dist = fetch_area_rat_dist(month_year)

    if not area_ne:
        print(f"  [warn] No BSS data for {month_year}, skipping")
        return []

    rows = []
    days = DAYS_IN_MONTH.get(month_year, 30)
    base_date = datetime.strptime(month_year, "%Y-%m")
    rng = np.random.default_rng(seed=int(month_year.replace("-", "")))

    area_list = sorted(area_ne.keys())

    for day in range(1, days + 1):
        ts = base_date + timedelta(days=day - 1)
        for area in area_list:
            ne = area_ne.get(area, 0.5)
            for cell_idx in range(CELLS_PER_AREA):
                rat = pick_rat(area, rat_dist)
                kpis = generate_kpis(rat, ne)
                cell_id = f"{area[:3].upper()}{rat}{cell_idx:03d}"
                site_name = f"SITE-{area[:3].upper()}-{cell_idx:02d}"

                rows.append((
                    cell_id,
                    area,
                    month_year,
                    kpis["throughput_mbps"],
                    kpis["latency_ms"],
                    kpis["packet_loss_rate"],
                    kpis["jitter_ms"],
                    kpis["active_users"],
                    kpis["rsrp_dbm"],
                    kpis["cell_load_pct"],
                    kpis["anomaly_flag"],
                    rat,
                    kpis["integrity"],
                    kpis["call_drop_rate"],
                    ts.isoformat(),
                    site_name,
                    "simulated",
                ))

    print(f"  ... {len(rows):,} rows generated")
    return rows


def insert_rows(rows: list[tuple]):
    sql = """
        INSERT INTO oss_cell_kpis (
            cell_id, area, month_year, throughput_mbps, latency_ms,
            packet_loss_rate, jitter_ms, active_users, rsrp_dbm,
            cell_load_pct, anomaly_flag, rat_type, integrity,
            call_drop_rate, timestamp, site_name, source
        ) VALUES %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
        conn.commit()


def main():
    for month in MONTHS:
        rows = simulate_month(month)
        if rows:
            insert_rows(rows)
    print("\n[done] Correlated OSS simulation complete")


if __name__ == "__main__":
    main()
