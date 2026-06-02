"""
One-shot UPDATE: populate active_users_max for already-ingested 4G rows.

Why this exists
---------------
The original ingest dropped Huawei's L.Traffic.User.Max column (real data,
column index 11 in the 4G CSV). The 004 migration adds the column; this
script re-reads the 4G CSV and UPDATES matching (cell_id, timestamp) rows.

No new data is created. Only a column that was already in the source CSV
is now landed in the table.
"""
from __future__ import annotations

import csv
import os
import time
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.getenv("DATABASE_URL", "postgresql://telecom:telecom_pw@postgres:5432/telecom_intel")
CSV_PATH = Path(os.getenv(
    "OSS_4G_CSV",
    "/app/TT_data/OSS/KPI Analysis Result_Query_Result_20260427105212826(KPI Analysis Result).csv",
))
BATCH = int(os.getenv("REFRESH_BATCH", "10000"))


def parse_int(val: str) -> int | None:
    try:
        v = (val or "").strip()
        if not v:
            return None
        return int(float(v))
    except ValueError:
        return None


def parse_ts(val: str) -> str | None:
    try:
        return datetime.strptime(val.strip(), "%Y-%m-%d %H:%M").isoformat()
    except Exception:
        return None


def main() -> None:
    if not CSV_PATH.exists():
        raise SystemExit(f"4G CSV not found: {CSV_PATH}")

    print(f"[refresh-4g-users-max] reading {CSV_PATH.name} ...")
    rows: list[tuple[int, int, str]] = []  # (users_max, cell_id_int, ts)

    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        # Skip Huawei metadata + header (7 lines).
        for _ in range(7):
            try:
                next(reader)
            except StopIteration:
                pass

        for row in reader:
            if len(row) < 12:
                continue
            ts = parse_ts(row[0])
            cell_id = (row[3] or "").strip()
            users_max = parse_int(row[11])
            if ts and cell_id and users_max is not None:
                rows.append((users_max, cell_id, ts))

    print(f"[refresh-4g-users-max] parsed {len(rows):,} rows. Applying UPDATEs ...")

    t0 = time.time()
    updated = 0
    with psycopg2.connect(DB_URL) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            # Stage values in a temp table, then UPDATE in one set-based op
            # (way faster than per-row UPDATE for 8.5M target rows).
            cur.execute("""
                CREATE TEMP TABLE _tmp_users_max (
                    users_max INTEGER NOT NULL,
                    cell_id   TEXT    NOT NULL,
                    ts        TIMESTAMPTZ NOT NULL
                ) ON COMMIT DROP;
            """)
            execute_values(
                cur,
                "INSERT INTO _tmp_users_max (users_max, cell_id, ts) VALUES %s",
                rows,
                page_size=BATCH,
            )
            cur.execute("CREATE INDEX ON _tmp_users_max (cell_id, ts);")

            cur.execute("""
                UPDATE oss_cell_kpis o
                   SET active_users_max = t.users_max
                  FROM _tmp_users_max t
                 WHERE o.rat_type  = '4G'
                   AND o.cell_id   = t.cell_id
                   AND o.timestamp = t.ts
                   AND o.active_users_max IS DISTINCT FROM t.users_max;
            """)
            updated = cur.rowcount
        conn.commit()

    elapsed = time.time() - t0
    print(f"[refresh-4g-users-max] DONE — {updated:,} rows updated in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
