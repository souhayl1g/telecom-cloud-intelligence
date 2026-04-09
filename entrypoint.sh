#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Telecom Cloud Intelligence — Container Entrypoint
# 
# Environment Variables:
#   AUTO_PIPELINE    (true|false)  - Run pipeline on startup (default: false)
#   PIPELINE_TIMEOUT  (seconds)     - Max time for pipeline execution (default: 120)
#   PIPELINE_MODE     (oneshot|daemon) - Pipeline run mode (default: oneshot)
#   JUPYTER_PORT      (port)        - Jupyter port (default: 8888)
#   JUPYTER_TOKEN     (token)       - Jupyter access token (auto-generated if empty)
#   PIPELINE_LOG_DIR  (path)        - Log output directory (default: /app/logs)
#
# Exit Codes:
#   0   - Normal startup (pipeline disabled or succeeded)
#   1   - Pipeline failed (AUTO_PIPELINE=true and pipeline error)
#   2   - Jupyter startup failed
#   130 - SIGINT received
#   143 - SIGTERM received
# ─────────────────────────────────────────────────────────────────────────────

# ── Configuration ────────────────────────────────────────────────────────────
AUTO_PIPELINE="${AUTO_PIPELINE:-false}"
PIPELINE_TIMEOUT="${PIPELINE_TIMEOUT:-120}"
PIPELINE_MODE="${PIPELINE_MODE:-oneshot}"
JUPYTER_PORT="${JUPYTER_PORT:-8888}"
JUPYTER_TOKEN="${JUPYTER_TOKEN:-}"
PIPELINE_LOG_DIR="${PIPELINE_LOG_DIR:-/app/logs}"

# Derived
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PIPELINE_LOG="${PIPELINE_LOG_DIR}/pipeline_${TIMESTAMP}.log"
PIPELINE_PID_FILE="/tmp/pipeline.pid"

# ── Logging ───────────────────────────────────────────────────────────────────
log() {
    local level="$1"
    shift
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*"
    echo "$msg"
    echo "$msg" >> "${PIPELINE_LOG}"
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }

# ── Setup ─────────────────────────────────────────────────────────────────────
setup() {
    mkdir -p "${PIPELINE_LOG_DIR}" /app/models /app/data
    log_info "Container starting..."
    log_info "AUTO_PIPELINE=${AUTO_PIPELINE}"
    log_info "PIPELINE_MODE=${PIPELINE_MODE}"
    log_info "PIPELINE_TIMEOUT=${PIPELINE_TIMEOUT}s"
    log_info "JUPYTER_PORT=${JUPYTER_PORT}"
    log_info "Log file: ${PIPELINE_LOG}"
}

# ── Pipeline Runner (Background) ───────────────────────────────────────────────
run_pipeline_background() {
    log_info "Starting pipeline in background (PID: $$)"
    log_info "Pipeline log: ${PIPELINE_LOG}"
    
    # Start pipeline as background process
    python -m pipeline.worker >> "${PIPELINE_LOG}" 2>&1 &
    local pid=$!
    echo "$pid" > "${PIPELINE_PID_FILE}"
    log_info "Pipeline started with PID: ${pid}"
    
    # Wait for pipeline with timeout
    local elapsed=0
    local interval=1
    
    while kill -0 "$pid" 2>/dev/null; do
        if [ $elapsed -ge ${PIPELINE_TIMEOUT} ]; then
            log_error "Pipeline timeout exceeded (${PIPELINE_TIMEOUT}s)"
            log_error "Killing pipeline PID ${pid}"
            kill -TERM "$pid" 2>/dev/null || true
            sleep 2
            kill -KILL "$pid" 2>/dev/null || true
            return 124
        fi
        sleep $interval
        elapsed=$((elapsed + interval))
        
        # Log progress every 30 seconds
        if [ $((elapsed % 30)) -eq 0 ] && [ $elapsed -lt ${PIPELINE_TIMEOUT} ]; then
            log_info "Pipeline still running... (${elapsed}s/${PIPELINE_TIMEOUT}s)"
        fi
    done
    
    # Get exit code
    wait "$pid"
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_info "Pipeline completed successfully"
    else
        log_error "Pipeline failed with exit code: ${exit_code}"
    fi
    
    return $exit_code
}

# ── Signal Handlers ────────────────────────────────────────────────────────────
cleanup() {
    log_info "Received shutdown signal, cleaning up..."
    
    # Kill pipeline if running
    if [ -f "${PIPELINE_PID_FILE}" ]; then
        local pid=$(cat "${PIPELINE_PID_FILE}")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Terminating pipeline PID ${pid}..."
            kill -TERM "$pid" 2>/dev/null || true
            sleep 2
            kill -KILL "$pid" 2>/dev/null || true
        fi
        rm -f "${PIPELINE_PID_FILE}"
    fi
    
    log_info "Cleanup complete"
    exit 130
}

trap cleanup SIGINT SIGTERM

# ── Jupyter Server ─────────────────────────────────────────────────────────────
start_jupyter() {
    log_info "Starting Jupyter Notebook server..."
    
    # Generate token if not provided
    if [ -z "${JUPYTER_TOKEN}" ]; then
        JUPYTER_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
        log_info "Generated Jupyter token"
    fi
    
    # Start Jupyter (binds to all interfaces for container networking)
    exec jupyter notebook \
        --ip=0.0.0.0 \
        --port="${JUPYTER_PORT}" \
        --no-browser \
        --allow-root \
        --NotebookApp.token="${JUPYTER_TOKEN}" \
        --NotebookApp.allow_origin='*' \
        --NotebookApp.disable_check_xsrf=True \
        --NotebookApp.quit_button=False \
        --NotebookApp.terminals_enabled=False \
        --ServerApp.root_dir=/app/notebooks
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
    setup
    
    if [ "${AUTO_PIPELINE,,}" = "true" ]; then
        log_info "AUTO_PIPELINE enabled — executing pipeline on startup"
        
        # Run pipeline in background, wait for completion
        run_pipeline_background
        local pipeline_exit=$?
        
        case $pipeline_exit in
            0)
                log_info "Startup pipeline completed successfully"
                ;;
            124)
                log_error "Pipeline timed out after ${PIPELINE_TIMEOUT}s"
                log_error "Check logs: ${PIPELINE_LOG}"
                echo ""
                echo "═══════════════════════════════════════════════════════════════════════════════"
                echo " PIPELINE TIMEOUT FAILURE"
                echo "═══════════════════════════════════════════════════════════════════════════════"
                echo " Timeout: ${PIPELINE_TIMEOUT}s exceeded"
                echo " Log:    ${PIPELINE_LOG}"
                echo "═══════════════════════════════════════════════════════════════════════════════"
                exit 1
                ;;
            *)
                log_error "Pipeline failed with exit code: ${pipeline_exit}"
                log_error "Check logs: ${PIPELINE_LOG}"
                echo ""
                echo "═══════════════════════════════════════════════════════════════════════════════"
                echo " PIPELINE EXECUTION FAILURE"
                echo "═══════════════════════════════════════════════════════════════════════════════"
                echo " Exit code: ${pipeline_exit}"
                echo " Log:      ${PIPELINE_LOG}"
                echo ""
                echo " Last 20 lines of log:"
                tail -20 "${PIPELINE_LOG}" 2>/dev/null || echo "(no log available)"
                echo "═══════════════════════════════════════════════════════════════════════════════"
                exit 1
                ;;
        esac
    else
        log_info "AUTO_PIPELINE disabled — skipping startup pipeline"
    fi
    
    # Always start Jupyter for notebook access
    log_info "Starting Jupyter Notebook server on port ${JUPYTER_PORT}"
    start_jupyter
}

main "$@"
