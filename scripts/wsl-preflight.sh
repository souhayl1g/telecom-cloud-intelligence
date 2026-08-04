#!/usr/bin/env bash
# wsl-preflight.sh — prevent WSL/Docker memory crashes before they happen.
# Usage: bash scripts/wsl-preflight.sh [--quiet]
#
# Exit codes:
#   0  OK to start
#   1  Hard blocker (not enough RAM, not WSL, etc.)
#   2  Warning only (starts allowed with --quiet)

set -euo pipefail

QUIET=${1:-}
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

log_err()  { echo -e "${RED}[✗]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[✓]${NC} $1"; }

# ── 1. Detect WSL ─────────────────────────────────────────────────────────────
if [[ ! -f /proc/sys/kernel/osrelease ]] && [[ ! -f /proc/version ]]; then
    log_err "Cannot detect runtime environment."
    exit 1
fi

if ! grep -qi microsoft /proc/version 2>/dev/null; then
    log_warn "Not running inside WSL2 — skipping WSL-specific checks."
    exit 0
fi

# ── 2. Check .wslconfig ───────────────────────────────────────────────────────
# Try to resolve the Windows user profile path. Inside WSL $USER is the Linux
# user, which often differs from the Windows user name (e.g. souhayl vs s50057139).
WIN_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r' || true)
if [[ -z "$WIN_USER" ]]; then
    WIN_USER=${USER}
fi

WSLCONFIG="/mnt/c/Users/${WIN_USER}/.wslconfig"

# Fallback: search for an existing .wslconfig under /mnt/c/Users if the
# Windows-username guess is wrong.
if [[ ! -f "$WSLCONFIG" ]]; then
    FOUND=$(find /mnt/c/Users -maxdepth 2 -name '.wslconfig' -type f 2>/dev/null | head -1 || true)
    if [[ -n "$FOUND" ]]; then
        WSLCONFIG="$FOUND"
        WIN_USER=$(basename "$(dirname "$FOUND")")
    fi
fi

if [[ ! -f "$WSLCONFIG" ]]; then
    log_err ".wslconfig missing at ${WSLCONFIG}"
    echo "    Run:  cp .wslconfig.example /mnt/c/Users/<WindowsUser>/.wslconfig"
    echo "    Example for you: cp .wslconfig.example /mnt/c/Users/${WIN_USER}/.wslconfig"
    echo "    Then: wsl.exe --shutdown   (wait 10s)   wsl"
    exit 1
fi

WSL_MEMORY_GB=$(grep -i '^memory=' "$WSLCONFIG" 2>/dev/null | head -1 | sed -E 's/.*=([0-9]+).*/\1/')
if [[ -z "$WSL_MEMORY_GB" ]]; then
    log_warn ".wslconfig exists but has no memory= line."
    WSL_MEMORY_GB=0
fi

# ── 3. Check current WSL memory ───────────────────────────────────────────────
TOTAL_KB=$(awk '/MemTotal:/ {print $2}' /proc/meminfo)
TOTAL_GB=$(( TOTAL_KB / 1024 / 1024 ))
AVAIL_KB=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
AVAIL_GB=$(( AVAIL_KB / 1024 / 1024 ))

# ── 4. Estimate required memory for the default core stack ────────────────────
# Based on docker-compose.yml mem_limits for default-profile services.
# Ollama on Windows host is extra (~4-6GB for 7B model).
REQUIRED_GB=7
REQUIRED_WITH_OLLAMA_GB=12

# ── 5. Report ─────────────────────────────────────────────────────────────────
echo ""
echo "WSL2 preflight check"
echo "──────────────────────────────────────────────────────────────"
log_ok "WSL2 detected"

if [[ "$WSL_MEMORY_GB" -ge 10 ]]; then
    log_ok ".wslconfig memory=${WSL_MEMORY_GB}GB"
else
    log_warn ".wslconfig memory=${WSL_MEMORY_GB}GB (recommend >=10GB for NeXo)"
fi

echo "    Current WSL total RAM: ${TOTAL_GB}GB"
echo "    Current WSL available: ${AVAIL_GB}GB"
echo "    Core stack needs:      ~${REQUIRED_GB}GB"
echo "    With Ollama 7B host:   ~${REQUIRED_WITH_OLLAMA_GB}GB"
echo ""

# ── 6. Check for port conflicts ───────────────────────────────────────────────
# Ports that docker-compose.yml publishes to the host. A Jupyter kernel,
# another MinIO, or a stale wslrelay binding can squat them and cause
# "address already in use" failures during `docker compose up`.
REQUIRED_PORTS=(5432 5000 8000 8001 8002 8003 8888 9000 9001 3001)
PORT_CONFLICT=0

hex_port() { printf '%04X' "$1"; }

# Ports already published by running NeXo containers are not conflicts.
# Handles both single ports (0.0.0.0:9000->9000/tcp) and ranges (0.0.0.0:9000-9001->9000-9001/tcp).
DOCKER_PORTS=$(docker ps --format '{{.Ports}}' 2>/dev/null |
    grep -oE '[0-9]+(-[0-9]+)?->' |
    sed 's/->//' |
    awk -F'-' '{ if (NF==1) print $1; else for(i=$1;i<=$2;i++) print i }' |
    sort -u || true)

for PORT in "${REQUIRED_PORTS[@]}"; do
    if echo "$DOCKER_PORTS" | grep -qx "$PORT"; then
        continue
    fi
    HEX=$(hex_port "$PORT")
    # /proc/net/tcp columns: local_address is $2, format 0100007F:PORTHEX
    if grep -qiE ":${HEX}\b" /proc/net/tcp 2>/dev/null; then
        log_warn "Port ${PORT} is already listening inside WSL (not a running NeXo container)"
        # Try to get Windows PID for the port via wslrelay/netstat
        WIN_PID=$(cmd.exe /c "netstat -ano | findstr :${PORT}" 2>/dev/null | awk '{print $NF}' | head -1 | tr -d '\r')
        if [[ -n "$WIN_PID" ]]; then
            echo "    Windows PID holding it: ${WIN_PID}"
            echo "    Inspect:  tasklist /FI \"PID eq ${WIN_PID}\""
            echo "    Kill:     taskkill /PID ${WIN_PID} /F"
        fi
        PORT_CONFLICT=1
    fi
done

if [[ "$PORT_CONFLICT" -eq 1 ]]; then
    echo ""
    log_err "Port conflict detected — docker compose will fail."
    echo "    Common culprit: a Jupyter kernel or another MinIO on port 9000."
    echo "    Fix: identify and stop the process, then re-run make start-safe."
    exit 1
fi

# ── 7. Decision ───────────────────────────────────────────────────────────────
if [[ "$TOTAL_GB" -lt "$REQUIRED_GB" ]]; then
    log_err "Not enough WSL RAM to start core stack safely."
    echo "    Increase .wslconfig memory= to at least ${REQUIRED_GB}GB, then:"
    echo "      wsl.exe --shutdown"
    echo "      sleep 10"
    echo "      wsl"
    exit 1
fi

if [[ "$AVAIL_GB" -lt "$REQUIRED_GB" ]]; then
    log_warn "Available RAM (${AVAIL_GB}GB) is below the safe threshold (${REQUIRED_GB}GB)."
    echo "    Free memory or increase .wslconfig memory=."
    [[ "$QUIET" == "--quiet" ]] && exit 0
    exit 2
fi

if [[ "$WSL_MEMORY_GB" -lt 8 ]]; then
    log_warn ".wslconfig memory is under 8GB — stack may still crash under load."
    echo "    Recommended: memory=12GB-16GB in ${WSLCONFIG}"
    [[ "$QUIET" == "--quiet" ]] && exit 0
    exit 2
fi

log_ok "Preflight passed — safe to start."
echo ""
exit 0
