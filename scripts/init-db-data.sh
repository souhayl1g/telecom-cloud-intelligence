#!/usr/bin/env bash
# init-db-data.sh — Ensure real TT data is ingested into PostgreSQL.
# Run this after `make start-NeXo` if tables are empty (e.g. after `make nuke`).
# Safe to run multiple times: ingestion scripts use ON CONFLICT DO NOTHING.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
export DATABASE_URL="${DATABASE_URL:-postgresql://telecom:telecom_pw@localhost:5432/telecom_intel}"

echo "[init-db] Checking database connection..."
python3 -c "import psycopg2; psycopg2.connect('$DATABASE_URL')" || {
    echo "[init-db] ERROR: Cannot connect to PostgreSQL. Is the stack running?"
    echo "[init-db] Run: make start-NeXo"
    exit 1
}

# Apply schema migrations on EVERY run (idempotent — IF NOT EXISTS guards).
# Must happen before row-count check so new tables (tickets, notifications_sent,
# churn_interventions, capacity_reports, retrain_runs) exist before app reads them.
MIGRATIONS_DIR="$PROJECT_ROOT/docs/db/migrations"
if [ -d "$MIGRATIONS_DIR" ]; then
    for f in $(ls "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort); do
        echo "[init-db] Applying migration: $(basename "$f") ..."
        python3 - <<PY || echo "[init-db]   warn: migration $(basename "$f") failed (non-fatal)"
import psycopg2
conn = psycopg2.connect("$DATABASE_URL")
conn.autocommit = True
with conn.cursor() as cur, open("$f") as src:
    cur.execute(src.read())
conn.close()
PY
    done
fi

echo "[init-db] Checking existing row counts..."
COUNTS=$(python3 -c "
import psycopg2
conn = psycopg2.connect('$DATABASE_URL')
cur = conn.cursor()
for t in ['bss_subscribers','oss_cell_kpis','subscriber_features']:
    cur.execute(f'SELECT COUNT(*) FROM {t}')
    print(f'{t}:{cur.fetchone()[0]}')
cur.close(); conn.close()
")
echo "[init-db] $COUNTS"

NEED_INGEST=false
for line in $COUNTS; do
    table="${line%:*}"
    count="${line#*:}"
    if [ "$count" -eq 0 ]; then
        echo "[init-db] Table $table is empty."
        NEED_INGEST=true
    fi
done

if [ "$NEED_INGEST" = false ]; then
    echo "[init-db] All tables have data. Nothing to do."
    exit 0
fi

echo "[init-db] Starting ingestion (this takes ~10 minutes)..."

# Activate host venv only outside containers. Sidecar sets SKIP_VENV=1
# because Dockerfile.notebooks already installs deps system-wide.
if [ -z "${SKIP_VENV:-}" ] && [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

python3 "$PROJECT_ROOT/services/data-ingest/ingest_bss.py"
python3 "$PROJECT_ROOT/services/data-ingest/ingest_oss_real.py"
python3 "$PROJECT_ROOT/services/data-ingest/compute_features.py"

# Create dashboard materialized views (idempotent DROP/CREATE inside SQL).
# Dashboard /api/* routes query these directly; missing views = 500 errors.
MV_SQL="$PROJECT_ROOT/docs/db/dashboard_summary.sql"
if [ -f "$MV_SQL" ]; then
    echo "[init-db] Applying materialized views from $MV_SQL ..."
    python3 - <<PY
import psycopg2
conn = psycopg2.connect("$DATABASE_URL")
conn.autocommit = True
with conn.cursor() as cur, open("$MV_SQL") as f:
    cur.execute(f.read())
conn.close()
print("[init-db] Materialized views ready.")
PY
fi

echo "[init-db] Ingestion complete. Row counts now:"
python3 -c "
import psycopg2
conn = psycopg2.connect('$DATABASE_URL')
cur = conn.cursor()
for t in ['bss_subscribers','oss_cell_kpis','subscriber_features']:
    cur.execute(f'SELECT COUNT(*) FROM {t}')
    print(f'  {t}: {cur.fetchone()[0]} rows')
cur.close(); conn.close()
"
