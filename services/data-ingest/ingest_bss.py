"""
BSS Real Data Ingestion
-----------------------
Loads real Tunisie Telecom BSS subscriber data from TT_data/BSS/
into PostgreSQL bss_subscribers table.

Supported files:
  - smartcare_cem_feb.csv   (Feb 2026, 468K, comma-delimited)
  - smartcare_cem_mars.csv  (Mar 2026, 500K, comma-delimited)
  - request_data_1month_500K.txt (Mar 2026, 500K, pipe-delimited)

Anonymization: IMSI → SHA-256 hash with project salt.
"""

import csv
import hashlib
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

# ── config ───────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "TT_data" / "BSS"
IMSI_SALT = os.getenv("IMSI_SALT", "nexo-tt-salt-2026")
BATCH_SIZE = 5000

# Columns in order (both CSV and pipe-delimited use same schema)
COLUMNS = [
    "imsi", "tac", "model", "brand", "tertype", "generation", "sim_slot",
    "volte_flag", "usim_flag", "area", "area_delegation", "usertype",
    "dou_total", "traffic_2g", "traffic_3g", "traffic_4g", "traffic_5g",
    "duration", "voice_onlinetime_3g", "voice_onlinetime_2g",
    "s1_mme_sr", "iu_attach_sr", "gb_attach_sr",
    "session_flag", "highest_rat", "month_year",
]

DB_COLS = COLUMNS.copy()
DB_COLS[0] = "imsi_hash"  # we store hash, not raw imsi


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(db_url)


def hash_imsi(imsi: str) -> str:
    return hashlib.sha256(f"{imsi}{IMSI_SALT}".encode()).hexdigest()[:32]


def parse_numeric(val, typ=int):
    if val is None or val == "" or val == "NULL":
        return None
    try:
        return typ(val)
    except ValueError:
        return None


def row_to_db(row: dict) -> tuple:
    """Convert a raw CSV/txt row into a database tuple."""
    imsi_hash = hash_imsi(row["imsi"])
    return (
        imsi_hash,
        row.get("tac") or None,
        row.get("model") or None,
        row.get("brand") or None,
        row.get("tertype") or None,
        row.get("generation") or None,
        row.get("sim_slot") or None,
        parse_numeric(row.get("volte_flag")),
        parse_numeric(row.get("usim_flag")),
        row.get("area") or None,
        row.get("area_delegation") or None,
        row.get("usertype") or None,
        parse_numeric(row.get("dou_total")),
        parse_numeric(row.get("traffic_2g")),
        parse_numeric(row.get("traffic_3g")),
        parse_numeric(row.get("traffic_4g")),
        parse_numeric(row.get("traffic_5g")),
        parse_numeric(row.get("duration"), float),
        parse_numeric(row.get("voice_onlinetime_3g"), float),
        parse_numeric(row.get("voice_onlinetime_2g"), float),
        parse_numeric(row.get("s1_mme_sr"), float),
        parse_numeric(row.get("iu_attach_sr"), float),
        parse_numeric(row.get("gb_attach_sr"), float),
        parse_numeric(row.get("session_flag")),
        row.get("highest_rat") or None,
        row.get("month_year") or None,
    )


def ingest_file(filepath: Path, delimiter: str = ",") -> int:
    """Ingest a single BSS file into PostgreSQL. Returns row count."""
    print(f"[ingest] {filepath.name} (delimiter='{delimiter}')")

    rows = []
    count = 0
    skipped = 0

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for raw in reader:
            # skip header-like rows that somehow reappear
            if raw.get("imsi") == "imsi":
                skipped += 1
                continue
            rows.append(row_to_db(raw))
            if len(rows) >= BATCH_SIZE:
                count += _insert_batch(rows)
                rows = []
                print(f"  ... {count} rows inserted")

    if rows:
        count += _insert_batch(rows)

    print(f"[ingest] {filepath.name} complete: {count} rows, {skipped} skipped")
    return count


def _insert_batch(rows: list[tuple]) -> int:
    sql = """
        INSERT INTO bss_subscribers (
            imsi_hash, tac, model, brand, tertype, generation, sim_slot,
            volte_flag, usim_flag, area, area_delegation, usertype,
            dou_total, traffic_2g, traffic_3g, traffic_4g, traffic_5g,
            duration, voice_onlinetime_3g, voice_onlinetime_2g,
            s1_mme_sr, iu_attach_sr, gb_attach_sr,
            session_flag, highest_rat, month_year
        ) VALUES %s
        ON CONFLICT (imsi_hash, month_year) DO NOTHING
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
        conn.commit()
    return len(rows)


def main():
    files_to_ingest = [
        (DATA_DIR / "smartcare_cem_feb.csv", ","),
        (DATA_DIR / "smartcare_cem_mars.csv", ","),
        (DATA_DIR / "smartcare_cem_jan.csv", ","),
        (DATA_DIR / "smartcare_cem_avr.csv", ","),
        (DATA_DIR / "smartcare_cem_mai.csv", ","),
        (DATA_DIR / "smartcare_cem_jun.csv", ","),
        (DATA_DIR / "smartcare_cem_jul.csv", ","),
        (DATA_DIR / "smartcare_cem_aug.csv", ","),
        (DATA_DIR / "smartcare_cem_sep.csv", ","),
        # (DATA_DIR / "request_data_1month_500K.txt", "|"),  -- same as mars csv
    ]

    total = 0
    for fp, delim in files_to_ingest:
        if not fp.exists():
            print(f"[warn] File not found, skipping: {fp}")
            continue
        total += ingest_file(fp, delim)

    print(f"\n[done] Total rows ingested: {total}")


if __name__ == "__main__":
    main()
