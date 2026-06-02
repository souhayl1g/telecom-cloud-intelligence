#!/usr/bin/env bash
# run_notebooks.sh — Execute all NeXo training notebooks headless in order.
#
# Run inside notebooks container:
#   docker compose exec -T notebooks bash /app/scripts/run_notebooks.sh
#
# Or from host via Makefile:
#   make nb-run-all
#
# Order:  00 (EDA) → 01 (ETL) → 02 (CEM) → 03 (VAE) → 04 (RAT) → 10 (Granger)
# Output: notebooks are updated in-place (cells executed, outputs saved).
# Models: saved to /app/models → bind-mounted to services/ai-service/models/

set -euo pipefail

NB_DIR="/app/notebooks"
LOG_DIR="/app/logs"
mkdir -p "$LOG_DIR"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'
BOLD='\033[1m'

TIMEOUT=${NB_TIMEOUT:-3600}   # seconds per notebook, override with NB_TIMEOUT=7200

run_nb() {
    local nb="$1"
    local path="$NB_DIR/$nb"

    if [ ! -f "$path" ]; then
        echo -e "${RED}[✗] Not found: $nb — skipping${NC}"
        return 1
    fi

    echo -e "\n${BLUE}${BOLD}▶  $nb${NC}"
    echo -e "   Timeout: ${TIMEOUT}s"

    local log="$LOG_DIR/nb_$(echo "$nb" | tr '/' '_').log"
    local start; start=$(date +%s)

    if jupyter nbconvert \
        --to notebook \
        --execute \
        --inplace \
        --ExecutePreprocessor.timeout="$TIMEOUT" \
        --ExecutePreprocessor.kernel_name=python3 \
        "$path" > "$log" 2>&1; then

        local elapsed=$(( $(date +%s) - start ))
        echo -e "   ${GREEN}[✓] Done in ${elapsed}s${NC}  (log: $log)"
    else
        echo -e "   ${RED}[✗] FAILED — check $log${NC}"
        echo -e "   ${YELLOW}Last 20 lines:${NC}"
        tail -20 "$log" || true
        exit 1
    fi
}

echo -e "\n${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  NeXo Notebook Runner — headless execution${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  DB: ${DATABASE_URL:-not set}"
echo -e "  Notebooks dir: $NB_DIR"
echo ""

TOTAL_START=$(date +%s)

# Phase 1 — EDA (prerequisite for everything)
run_nb "00_data_understanding_eda.ipynb"

# Phase 2 — ETL + feature engineering (builds subscriber_features table)
run_nb "01_etl_feature_engineering.ipynb"

# Phase 3 — Train all three models (order within phase doesn't matter)
run_nb "02_cem_score_training.ipynb"
run_nb "03_oss_vae_anomaly_training.ipynb"
run_nb "04_rat_underservice_training.ipynb"

# Phase 4 — Granger gate (needs features from phase 2)
run_nb "10_granger_feature_selection.ipynb"

TOTAL_ELAPSED=$(( $(date +%s) - TOTAL_START ))
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  All notebooks complete in ${TOTAL_ELAPSED}s${NC}"
echo -e "  Models saved to: /app/models  (→ services/ai-service/models/)"
echo -e "  Granger gate:    $NB_DIR/granger_feature_gate.json"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
