"""Project 1: CSV + JSON ingestion, validation, quarantine and SQLite analytics."""
import csv
import hashlib
import json
import math
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def canonical_time(value):
    instant = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if instant.tzinfo is None:
        raise ValueError('timestamp must include a timezone')
    return instant.astimezone(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ingest(kpi_csv, cells_json, database):
    """Atomically replace the current snapshot; repeated input cannot duplicate rows.

    Structurally invalid source files abort without replacing the prior snapshot.
    Row-level errors are quarantined with original input and a reason.
    """
    kpi_csv, cells_json, database = map(Path, (kpi_csv, cells_json, database))
    dimensions = json.loads(cells_json.read_text(encoding='utf-8'))
    cells = {}
    for cell in dimensions:
        key = str(cell['cell_id']).strip()
        if not key or key in cells or not cell['region'].strip():
            raise ValueError('cell dimension keys must be unique and nonempty')
        cells[key] = cell['region'].strip()
    with kpi_csv.open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'cell_id', 'timestamp', 'throughput_mbps', 'latency_ms'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('missing required KPI columns')
        raw = list(reader)
    accepted, rejected, seen = [], [], set()
    for line, row in enumerate(raw, start=2):
        try:
            cell_id = row['cell_id'].strip()
            if cell_id not in cells:
                raise ValueError('unknown cell_id')
            timestamp = canonical_time(row['timestamp'])
            throughput, latency = float(row['throughput_mbps']), float(row['latency_ms'])
            if not all(math.isfinite(x) and x >= 0 for x in (throughput, latency)):
                raise ValueError('metrics must be finite and nonnegative')
            if (cell_id, timestamp) in seen:
                raise ValueError('duplicate cell/time key')
            seen.add((cell_id, timestamp))
            accepted.append((cell_id, timestamp, throughput, latency))
        except (ValueError, TypeError, AttributeError) as error:
            rejected.append((line, str(error), json.dumps(row, sort_keys=True)))
    lineage = {
        'kpi_sha256': digest(kpi_csv), 'cells_sha256': digest(cells_json),
        'source_rows': len(raw), 'accepted_rows': len(accepted),
        'rejected_rows': len(rejected), 'load_mode': 'atomic_snapshot_replace',
    }
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS cells(cell_id TEXT PRIMARY KEY, region TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS observations(
                cell_id TEXT NOT NULL REFERENCES cells(cell_id), timestamp TEXT NOT NULL,
                throughput_mbps REAL NOT NULL CHECK(throughput_mbps>=0),
                latency_ms REAL NOT NULL CHECK(latency_ms>=0), PRIMARY KEY(cell_id,timestamp));
            CREATE INDEX IF NOT EXISTS observations_time ON observations(timestamp);
            CREATE TABLE IF NOT EXISTS quarantine(line INTEGER, reason TEXT, raw_json TEXT);
            CREATE TABLE IF NOT EXISTS lineage(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE VIEW IF NOT EXISTS daily_region_kpis AS
                SELECT region, substr(timestamp,1,10) AS day, count(*) AS samples,
                    avg(throughput_mbps) AS mean_throughput_mbps, avg(latency_ms) AS mean_latency_ms
                FROM observations JOIN cells USING(cell_id) GROUP BY region, substr(timestamp,1,10);
        ''')
        # Explicit transaction also covers all deletes and inserts on a rerun.
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('DELETE FROM observations')
        conn.execute('DELETE FROM cells')
        conn.execute('DELETE FROM quarantine')
        conn.execute('DELETE FROM lineage')
        conn.executemany('INSERT INTO cells VALUES (?,?)', cells.items())
        conn.executemany('INSERT INTO observations VALUES (?,?,?,?)', accepted)
        conn.executemany('INSERT INTO quarantine VALUES (?,?,?)', rejected)
        conn.executemany('INSERT INTO lineage VALUES (?,?)', [(k,json.dumps(v)) for k,v in lineage.items()])
    return lineage


def monitor(database, now, max_age_hours=48, max_rejection_rate=0.1):
    """Project-local health report; 'now' is explicit for reproducible checks."""
    if max_age_hours < 0 or not 0 <= max_rejection_rate <= 1:
        raise ValueError('invalid monitoring thresholds')
    now = datetime.fromisoformat(canonical_time(now))
    with closing(sqlite3.connect(database)) as conn:
        count, latest = conn.execute('SELECT count(*),max(timestamp) FROM observations').fetchone()
        rejected = conn.execute('SELECT count(*) FROM quarantine').fetchone()[0]
    age = (now-datetime.fromisoformat(latest)).total_seconds()/3600 if latest else None
    ratio = rejected/(count+rejected) if count+rejected else 0
    checks = {'nonempty': count > 0, 'fresh': age is not None and 0 <= age <= max_age_hours,
              'quality': ratio <= max_rejection_rate}
    return {'healthy': all(checks.values()), 'checks': checks, 'accepted_rows': count,
            'rejected_rows': rejected, 'rejection_rate': ratio, 'age_hours': age}
