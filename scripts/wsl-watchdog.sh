#!/usr/bin/env bash
# wsl-watchdog.sh — keep WSL alive by monitoring memory and killing runaway containers.
# Usage:
#   bash scripts/wsl-watchdog.sh            # one-shot check
#   bash scripts/wsl-watchdog.sh --daemon   # loop every 30s (run in background)
#
# Strategy:
#   1. If available RAM < CRITICAL_MB, log and hard-restart the heaviest Docker container.
#   2. If available RAM < WARN_MB, log a warning.
#   3. Never touch postgres or minio — only stateless-ish containers.

set -uo pipefail

MODE=${1:-oneshot}
WARN_MB=1024
CRITICAL_MB=512
LOG_FILE=${LOG_FILE:-/tmp/nexo-watchdog.log}

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

get_avail_mb() {
    awk '/MemAvailable:/ {print int($2/1024)}' /proc/meminfo
}

# Convert Docker stats memory string to integer MiB.
# Examples: "266.9MiB / 2GiB" -> 266, "1.234GiB / 2GiB" -> 1263
mem_to_mib() {
    local raw=$1
    if [[ "$raw" == *GiB* ]]; then
        # strip "GiB" and anything after, multiply by 1024
        local num=${raw%%GiB*}
        awk -v n="$num" 'BEGIN{printf "%d", n*1024}'
    elif [[ "$raw" == *MiB* ]]; then
        local num=${raw%%MiB*}
        awk -v n="$num" 'BEGIN{printf "%d", n}'
    elif [[ "$raw" == *KiB* ]]; then
        local num=${raw%%KiB*}
        awk -v n="$num" 'BEGIN{printf "%d", n/1024}'
    else
        echo 0
    fi
}

get_heavy_container() {
    docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' 2>/dev/null |
        while IFS=$'\t' read -r NAME USAGE; do
            # skip infrastructure containers
            [[ "$NAME" == *postgres* ]] && continue
            [[ "$NAME" == *minio* ]] && continue
            MIB=$(mem_to_mib "${USAGE%% /*}")
            echo "${MIB}\t${NAME}"
        done |
        sort -t$'\t' -k1 -nr | head -1 | cut -f2
}

restart_container() {
    local NAME=$1
    log "RESTARTING container $NAME to free memory"
    docker restart "$NAME" >/dev/null 2>&1 || true
}

AVAIL=$(get_avail_mb)
log "Memory check: ${AVAIL}MB available"

if [[ "$AVAIL" -lt "$CRITICAL_MB" ]]; then
    log "${RED}CRITICAL: only ${AVAIL}MB available.${NC}"
    HEAVY=$(get_heavy_container)
    if [[ -n "$HEAVY" ]]; then
        restart_container "$HEAVY"
    fi
elif [[ "$AVAIL" -lt "$WARN_MB" ]]; then
    log "${YELLOW}WARNING: only ${AVAIL}MB available.${NC}"
fi

if [[ "$MODE" == "--daemon" ]]; then
    log "Watchdog daemon started (interval 30s)"
    while true; do
        sleep 30
        AVAIL=$(get_avail_mb)
        if [[ "$AVAIL" -lt "$CRITICAL_MB" ]]; then
            log "${RED}CRITICAL: only ${AVAIL}MB available.${NC}"
            HEAVY=$(get_heavy_container)
            [[ -n "$HEAVY" ]] && restart_container "$HEAVY"
        elif [[ "$AVAIL" -lt "$WARN_MB" ]]; then
            log "${YELLOW}WARNING: only ${AVAIL}MB available.${NC}"
        fi
    done
fi
