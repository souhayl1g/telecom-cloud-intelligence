#!/bin/bash
# NeXo ETL Pipeline — Full Data Foundation Orchestration
# =======================================================
# Usage: DATABASE_URL=postgresql://... bash services/data-ingest/run_etl.sh
# Phase 2: Data Foundation + ETL

set -e

echo "==================================="
echo "  NeXo Phase 2 — Data Foundation"
echo "==================================="
echo ""

if [ -z "$DATABASE_URL" ]; then
    echo "[ERROR] DATABASE_URL is not set."
    echo "  Example: export DATABASE_URL=postgresql://telecom:telecom_pw@localhost:5432/telecom_intel"
    exit 1
fi

echo "[Phase 2.1] BSS Real Data Ingestion"
echo "  → Loading Feb + Mar 2026 (968K subscribers)"
echo ""
python services/data-ingest/ingest_bss.py

echo ""
echo "[Phase 2.2] OSS Cell KPI Simulation"
echo "  → Generating 24 areas × 10 cells × 5 months"
echo ""
python services/data-ingest/simulate_oss.py

echo ""
echo "[Phase 2.3] Feature Engineering"
echo "  → subscriber_features + area_network_health"
echo ""
python services/data-ingest/compute_features.py

echo ""
echo "[Phase 2.4] BSS Month Simulation (Jan/Apr/May)"
echo "  → Bootstrapped from real Feb+Mar data"
echo ""
python services/data-ingest/generate_bss_months.py

echo ""
echo "==================================="
echo "  Phase 2 Complete ✅"
echo "==================================="
