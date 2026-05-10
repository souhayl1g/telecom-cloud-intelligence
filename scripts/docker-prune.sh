#!/usr/bin/env bash
# Run this INSIDE WSL (Ubuntu-22.04) after Docker is working.
# It removes junk containers/images but preserves NeXoligence project essentials.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=== NeXoligence Docker Cleanup ===${NC}"
echo ""

# Ensure docker is reachable
if ! docker version >/dev/null 2>&1; then
    echo -e "${RED}Docker is not reachable. Run fix-docker-wsl.ps1 first.${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/5] Stopping all running containers...${NC}"
RUNNING=$(docker ps -q 2>/dev/null || true)
if [ -n "$RUNNING" ]; then
    docker stop $RUNNING >/dev/null
    echo -e "${GREEN}  Stopped $(echo "$RUNNING" | wc -w) containers.${NC}"
else
    echo "  No running containers."
fi

echo -e "${YELLOW}[2/5] Removing all containers (including old Signoz/legacy)...${NC}"
ALL=$(docker ps -aq 2>/dev/null || true)
if [ -n "$ALL" ]; then
    docker rm $ALL >/dev/null
    echo -e "${GREEN}  Removed $(echo "$ALL" | wc -w) containers.${NC}"
else
    echo "  No containers to remove."
fi

echo -e "${YELLOW}[3/5] Removing old Signoz / ClickHouse / legacy images...${NC}"
REMOVED=0
while IFS= read -r line; do
    REPO=$(echo "$line" | awk '{print $1":"$2}')
    ID=$(echo "$line" | awk '{print $3}')
    if echo "$REPO" | grep -qiE "signoz|clickhouse|query-service|flattables|zookeeper"; then
        echo "  Removing: $REPO"
        docker rmi -f "$ID" >/dev/null 2>&1 || true
        ((REMOVED++)) || true
    fi
done < <(docker images --format "{{.Repository}} {{.Tag}} {{.ID}}")
echo -e "${GREEN}  Removed $REMOVED junk images.${NC}"

echo -e "${YELLOW}[4/5] Pruning dangling images, networks, and build cache...${NC}"
docker image prune -f >/dev/null
docker network prune -f >/dev/null
docker builder prune -f >/dev/null
echo -e "${GREEN}  Done.${NC}"

echo -e "${YELLOW}[5/5] Checking project image availability...${NC}"
NEEDED=(
    "postgres:16"
    "minio/minio"
    "netdata/netdata"
    "prom/prometheus"
    "grafana/grafana"
    "jaegertracing/jaeger"
    "otel/opentelemetry-collector-contrib"
)
for img in "${NEEDED[@]}"; do
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${img}"; then
        echo -e "${GREEN}  [OK] $img${NC}"
    else
        echo -e "${YELLOW}  [MISSING] $img -- will pull on compose up${NC}"
    fi
done

echo ""
echo -e "${CYAN}=== Cleanup Complete ===${NC}"
echo -e "To start your stack: ${WHITE}docker compose up -d${NC}"
