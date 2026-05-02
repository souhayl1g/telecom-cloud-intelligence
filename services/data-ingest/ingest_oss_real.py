"""
Real OSS Cell KPI Ingestion — 2G / 3G / 4G  (COPY-based)
--------------------------------------------------------
Ingests Huawei U2000 KPI export CSVs into PostgreSQL `oss_cell_kpis`.
Uses COPY FROM STDIN for maximum speed and reliability.
Resumable: skips RAT types already present, can delete partial loads.

Usage:
    export DATABASE_URL=postgresql://telecom:telecom_pw@localhost:5432/telecom_intel
    python services/data-ingest/ingest_oss_real.py          # all RATs
    python services/data-ingest/ingest_oss_real.py 3G 4G    # only 3G+4G
    python services/data-ingest/ingest_oss_real.py --force 3G  # delete+reload 3G

Files expected in TT_data/OSS/:
    - KPI Analysis Result_Query_Result_20260427105204494(KPI Analysis Result).csv   [2G]
    - KPI Analysis Result_Query_Result_2026042710520899(KPI Analysis Result).csv    [3G]
    - KPI Analysis Result_Query_Result_20260427105212826(KPI Analysis Result).csv   [4G]
"""

import argparse
import csv
import io
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg2

DB_URL = os.getenv("DATABASE_URL", "")
OSS_DIR = Path(__file__).parent.parent.parent / "TT_data" / "OSS"

FILES = [
    (
        "KPI Analysis Result_Query_Result_20260427105204494(KPI Analysis Result).csv",
        "2G",
    ),
    (
        "KPI Analysis Result_Query_Result_2026042710520899(KPI Analysis Result).csv",
        "3G",
    ),
    (
        "KPI Analysis Result_Query_Result_20260427105212826(KPI Analysis Result).csv",
        "4G",
    ),
]

COPY_SQL = """
COPY oss_cell_kpis (
    cell_id, area, month_year, throughput_mbps, latency_ms,
    packet_loss_rate, jitter_ms, active_users, rsrp_dbm,
    cell_load_pct, anomaly_flag, rat_type, integrity,
    call_drop_rate, timestamp, site_name, source
)
FROM STDIN WITH (FORMAT csv)
"""


def get_conn():
    if not DB_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DB_URL)


def parse_pct(val: str) -> str:
    if not val or val.strip() == "":
        return ""
    try:
        return str(float(val.replace("%", "").strip()))
    except ValueError:
        return ""


def parse_float(val: str) -> str:
    if not val or val.strip() == "":
        return ""
    try:
        return str(float(val.strip()))
    except ValueError:
        return ""


def parse_int(val: str) -> str:
    if not val or val.strip() == "":
        return ""
    try:
        return str(int(float(val.strip())))
    except ValueError:
        return ""


def parse_timestamp(val: str) -> str:
    try:
        ts = datetime.strptime(val.strip(), "%Y-%m-%d %H:%M")
        return ts.isoformat()
    except ValueError:
        return ""


def month_year_from_ts(val: str) -> str:
    try:
        ts = datetime.strptime(val.strip(), "%Y-%m-%d %H:%M")
        return ts.strftime("%Y-%m")
    except ValueError:
        return ""


def is_anomaly(integrity: str, cdr: str) -> str:
    try:
        i = float(integrity) if integrity else 100.0
        c = float(cdr) if cdr else 0.0
        return "t" if (i < 100.0 or c > 2.0) else "f"
    except ValueError:
        return "f"


CHUNK_SIZE = 500_000


def _write_row(writer, row, rat_type: str) -> bool:
    try:
        ts_raw = row[0]
        my = month_year_from_ts(ts_raw)
        ts = parse_timestamp(ts_raw)

        if rat_type == "2G":
            cell_id = row[3].strip()
            area = row[2].strip() if row[2] else row[1].strip()
            site_name = row[1].strip()
            integrity = parse_pct(row[6])
            cdr = parse_float(row[7])
            tput = ""
            users = ""
            rsrp = ""

        elif rat_type == "3G":
            cell_id = row[3].strip()
            area = row[2].strip() if row[2] else row[1].strip()
            site_name = row[1].strip()
            integrity = parse_pct(row[5])
            ps_cdr = parse_float(row[7])
            cs_cdr = parse_float(row[8])
            cdr = ps_cdr if ps_cdr else cs_cdr
            raw_thp = parse_float(row[6])
            tput = str(float(raw_thp) / 1000.0) if raw_thp else ""
            users = ""
            rsrp = ""

        elif rat_type == "4G":
            cell_id = row[3].strip()
            area = row[1].strip() if row[1] else row[2].strip()
            site_name = row[2].strip() if row[2] else row[1].strip()
            integrity = parse_pct(row[6])
            cdr = parse_float(row[7])
            tput = parse_float(row[8])
            rsrp = parse_float(row[9])
            users = parse_int(row[10])
        else:
            return False

        if not cell_id or not area:
            return False

        writer.writerow([
            cell_id,
            area,
            my,
            tput,
            "",  # latency_ms
            "",  # packet_loss_rate
            "",  # jitter_ms
            users,
            rsrp,
            "",  # cell_load_pct
            is_anomaly(integrity, cdr),
            rat_type,
            integrity,
            cdr,
            ts,
            site_name,
            "real",
        ])
        return True

    except Exception:
        return False


def ingest_file(conn, filepath: Path, rat_type: str):
    print(f"\n[ingest-oss] Starting {rat_type}: {filepath.name}")
    print(f"  File size: {filepath.stat().st_size / 1_048_576:.1f} MB")

    cursor = conn.cursor()
    total = 0
    skipped = 0
    chunk_rows = 0

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        # Skip Huawei metadata header lines (7 lines)
        for _ in range(7):
            try:
                next(reader)
            except StopIteration:
                break

        for row in reader:
            if len(row) < 8:
                skipped += 1
                continue

            ok = _write_row(writer, row, rat_type)
            if ok:
                total += 1
                chunk_rows += 1
            else:
                skipped += 1

            if chunk_rows >= CHUNK_SIZE:
                buffer.seek(0)
                cursor.copy_expert(COPY_SQL, buffer)
                conn.commit()
                print(f"  ... {total:,} rows copied")
                buffer = io.StringIO()
                writer = csv.writer(buffer, lineterminator="\n")
                chunk_rows = 0

    # Final chunk
    if chunk_rows > 0:
        buffer.seek(0)
        cursor.copy_expert(COPY_SQL, buffer)
        conn.commit()

    cursor.close()
    print(f"  Done: {total:,} rows inserted, {skipped:,} skipped")
    return total


def get_existing_counts(conn) -> dict[str, int]:
    cursor = conn.cursor()
    counts = {}
    for _, rat_type in FILES:
        cursor.execute(
            "SELECT COUNT(*) FROM oss_cell_kpis WHERE rat_type = %s",
            (rat_type,),
        )
        counts[rat_type] = cursor.fetchone()[0]
    cursor.close()
    return counts


def delete_rat(conn, rat_type: str) -> int:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM oss_cell_kpis WHERE rat_type = %s", (rat_type,))
    deleted = cursor.rowcount
    conn.commit()
    cursor.close()
    return deleted


def main():
    parser = argparse.ArgumentParser(description="Ingest real OSS KPI CSVs into PostgreSQL")
    parser.add_argument("rats", nargs="*", help="RAT types to ingest (2G, 3G, 4G). Default: all")
    parser.add_argument("--force", action="store_true", help="Delete existing data for selected RATs before ingest")
    args = parser.parse_args()

    target_rats = set(args.rats) if args.rats else {"2G", "3G", "4G"}

    if not DB_URL:
        print("[ERROR] DATABASE_URL is not set.")
        sys.exit(1)

    conn = get_conn()
    existing = get_existing_counts(conn)

    print("[ingest-oss] Existing row counts:")
    for rat, cnt in existing.items():
        print(f"  {rat}: {cnt:,} rows")

    grand_total = 0

    for filename, rat_type in FILES:
        if rat_type not in target_rats:
            continue

        filepath = OSS_DIR / filename
        if not filepath.exists():
            print(f"[WARN] File not found: {filepath}")
            continue

        if existing.get(rat_type, 0) > 0:
            if args.force:
                print(f"[ingest-oss] Deleting existing {rat_type} data ({existing[rat_type]:,} rows) ...")
                deleted = delete_rat(conn, rat_type)
                print(f"  Deleted {deleted:,} rows")
            else:
                print(f"[ingest-oss] Skipping {rat_type}: already has {existing[rat_type]:,} rows (use --force to overwrite)")
                continue

        grand_total += ingest_file(conn, filepath, rat_type)

    print(f"\n[ingest-oss] Grand total this run: {grand_total:,} rows inserted")
    conn.close()


if __name__ == "__main__":
    main()
