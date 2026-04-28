"""
Real OSS Cell KPI Ingestion
---------------------------
STUB — to be completed when TT OSS data file arrives.

Expected OSS file schema (infer from actual file on arrival):
  cell_id, area, timestamp, throughput_mbps, latency_ms, packet_loss_rate,
  jitter_ms, active_users, rsrp_dbm, cell_load_pct

Run: python services/data-ingest/ingest_oss_real.py <filepath>
"""
import csv
import sys
from pathlib import Path

import psycopg2

DB_URL = ""


def get_conn():
    db_url = DB_URL or ""
    if not db_url:
        import os

        db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(db_url)


def main():
    OSS_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else None

    if OSS_FILE is None or not OSS_FILE.exists():
        print("[ingest-oss] No OSS file provided or file not found.")
        print("[ingest-oss] Usage: python ingest_oss_real.py <path-to-oss.csv>")
        print("[ingest-oss] When real OSS arrives: inspect columns, map to oss_cell_kpis schema, implement loader.")
        return

    # TODO: implement when OSS file arrives
    # 1. Read OSS file (CSV or pipe-delimited)
    # 2. Map columns to oss_cell_kpis schema
    # 3. Use psycopg2 execute_values for batch insert
    # 4. ON CONFLICT DO NOTHING (idempotent)
    print(f"[ingest-oss] File found: {OSS_FILE}")
    print("[ingest-oss] Inspecting first 5 rows...")
    with open(OSS_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        print(f"  Header: {header}")
        for i, row in enumerate(reader):
            print(f"  Row {i + 1}: {row}")
            if i >= 4:
                break
    print("[ingest-oss] Update this script with correct column mapping before ingesting.")
    print("[ingest-oss] Expected mapping:")
    print("  cell_id, area, month_year, throughput_mbps, latency_ms,")
    print("  packet_loss_rate, jitter_ms, active_users, rsrp_dbm, cell_load_pct")


if __name__ == "__main__":
    main()
