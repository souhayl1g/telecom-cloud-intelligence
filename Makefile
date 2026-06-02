# ═══════════════════════════════════════════════════════════════════════════════
# Telecom NeXoligence — Makefile
#
# SAFE REBUILD PATTERN (data volumes never touched):
#   make up-dashboard      — rebuild + restart dashboard only
#   make up-api            — rebuild + restart api-gateway only
#   make up-ai             — rebuild + restart ai-service only
#   make up-auth           — rebuild + restart auth-service only
#   make up-worker         — rebuild + restart pipeline-worker only
#   make up-agent          — rebuild + restart agent-service only
#   make up-notebooks      — rebuild + restart notebooks only
#
# DATA SAFETY:
#   make stop / restart / up-<service>  → data volumes UNTOUCHED
#   make clean                          → containers removed, volumes PRESERVED
#   make nuke                           → DESTROYS everything including pgdata
# ═══════════════════════════════════════════════════════════════════════════════

PROJECT_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
export PROJECT_ROOT

PROJECT_NAME := telecom-cloud-intelligence
COMPOSE      := docker compose -f $(PROJECT_ROOT)/docker-compose.yml

BLUE   := \033[0;34m
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
NC     := \033[0m
BOLD   := \033[1m

define print_header
	@echo ""
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)$(BOLD)  $(1)$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
endef

define print_ok
	@echo "$(GREEN)[✓] $(1)$(NC)"
endef

define print_warn
	@echo "$(YELLOW)[!] $(1)$(NC)"
endef

define print_err
	@echo "$(RED)[✗] $(1)$(NC)"
endef

# ── Help ─────────────────────────────────────────────────────────────────────

.PHONY: help
help:
	@echo ""
	@echo "$(BOLD)Telecom NeXoligence — Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Startup:$(NC)"
	@echo "  $(YELLOW)make start$(NC)             Start full stack (daemon pipeline + Jupyter)"
	@echo "  $(YELLOW)make start-dev$(NC)         Start stack, no auto-pipeline"
	@echo ""
	@echo "$(GREEN)Hot-Rebuild (data-safe):$(NC)"
	@echo "  $(YELLOW)make up-dashboard$(NC)      Rebuild + restart dashboard only"
	@echo "  $(YELLOW)make up-api$(NC)            Rebuild + restart api-gateway only"
	@echo "  $(YELLOW)make up-ai$(NC)             Rebuild + restart ai-service only"
	@echo "  $(YELLOW)make up-auth$(NC)           Rebuild + restart auth-service only"
	@echo "  $(YELLOW)make up-worker$(NC)         Rebuild + restart pipeline-worker only"
	@echo "  $(YELLOW)make up-agent$(NC)          Rebuild + restart agent-service only"
	@echo "  $(YELLOW)make up-notebooks$(NC)      Rebuild + restart notebooks only"
	@echo ""
	@echo "$(GREEN)Pipeline (ETL daemon — 120s cycle):$(NC)"
	@echo "  $(YELLOW)make pipeline-status$(NC)   Show last pipeline-worker log lines"
	@echo "  $(YELLOW)make pipeline-logs$(NC)     Follow pipeline-worker logs live"
	@echo "  $(YELLOW)make pipeline-once$(NC)     Run a single pipeline cycle (oneshot)"
	@echo ""
	@echo "$(GREEN)Notebooks (ML training — run once):$(NC)"
	@echo "  $(YELLOW)make jupyter-token$(NC)     Get Jupyter URL + token"
	@echo "  $(YELLOW)make nb-run-all$(NC)        Execute ALL notebooks headless (00→01→02→03→04→10)"
	@echo "  $(YELLOW)make nb-run NB=02$(NC)      Execute a single notebook (e.g. 02_cem_score_training)"
	@echo ""
	@echo "$(GREEN)Control:$(NC)"
	@echo "  $(YELLOW)make stop$(NC)              Stop all services (data preserved)"
	@echo "  $(YELLOW)make restart$(NC)           Restart all services"
	@echo "  $(YELLOW)make svc-status$(NC)        Show container status"
	@echo "  $(YELLOW)make svc-health$(NC)        Health check all services"
	@echo ""
	@echo "$(GREEN)Logs:$(NC)"
	@echo "  $(YELLOW)make logs$(NC)              All logs (follow)"
	@echo "  $(YELLOW)make logs SVC=api-gateway$(NC)  Logs for a specific service"
	@echo "  $(YELLOW)make logs-dashboard$(NC)    Dashboard logs"
	@echo "  $(YELLOW)make logs-api$(NC)          API gateway logs"
	@echo "  $(YELLOW)make logs-ai$(NC)           AI service logs"
	@echo "  $(YELLOW)make logs-worker$(NC)       Pipeline-worker logs"
	@echo "  $(YELLOW)make logs-notebooks$(NC)    Notebooks container logs"
	@echo ""
	@echo "$(GREEN)Database:$(NC)"
	@echo "  $(YELLOW)make db-shell$(NC)          Open PostgreSQL shell"
	@echo "  $(YELLOW)make db-tables$(NC)         List tables + row counts"
	@echo "  $(YELLOW)make db-backup$(NC)         Dump database to backups/"
	@echo "  $(YELLOW)make db-reset$(NC)          Reset schema (WARNING: wipes data)"
	@echo "  $(YELLOW)make ensure-data$(NC)       Ingest data only if tables are empty"
	@echo "  $(YELLOW)make migrate-004$(NC)       Add active_users_max column + create vw_oss_cell_derived view"
	@echo "  $(YELLOW)make refresh-4g-users-max$(NC) Backfill REAL L.Traffic.User.Max from 4G CSV"
	@echo "  $(YELLOW)make generate-oss-months$(NC) Generate 16 monthly OSS CSVs mirroring BSS"
	@echo "  $(YELLOW)make clean-minio-raw$(NC)     Purge MinIO raw/ of non-dataset objects"
	@echo ""
	@echo "$(GREEN)Build / Maintenance:$(NC)"
	@echo "  $(YELLOW)make build$(NC)             Rebuild all images (no-cache)"
	@echo "  $(YELLOW)make build-cache$(NC)       Rebuild all images (with cache)"
	@echo "  $(YELLOW)make clean$(NC)             Remove containers, KEEP volumes"
	@echo "  $(YELLOW)make nuke$(NC)              Remove containers + volumes (DESTROYS DATA)"
	@echo "  $(YELLOW)make prune$(NC)             Remove unused Docker resources"
	@echo "  $(YELLOW)make show-info$(NC)         Show all URLs + credentials"
	@echo ""

# ── Main Startup ─────────────────────────────────────────────────────────────

.PHONY: start
start:
	$(call print_header,STARTING NeXo — FULL STACK) 
	@echo "Services starting:"
	@echo "  • postgres + minio + observability stack"
	@echo "  • api-gateway (8000) · ai-service (8001) · auth-service (8002) · agent-service (8003)"
	@echo "  • pipeline-worker (daemon, 120s cycles)"
	@echo "  • notebooks / Jupyter (8888)"
	@echo "  • dashboard (3001)"
	@echo ""
	@$(COMPOSE) up -d
	@echo ""
	@echo "$(BOLD)Starting Ollama LLM (background)...$(NC)"
	@(OLLAMA_MODELS=/mnt/d/ollama-models ollama serve > /dev/null 2>&1 &) || \
		echo "$(YELLOW)Ollama not available or already running$(NC)"
	@echo ""
	@echo "$(BOLD)Opening dashboard...$(NC)"
	@("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" http://localhost:3001 2>/dev/null || \
	  google-chrome --new-window http://localhost:3001 2>/dev/null || \
	  xdg-open http://localhost:3001 2>/dev/null) || \
	  echo "$(YELLOW)Open http://localhost:3001 manually$(NC)"
	@echo ""
	@make show-info

# Alias kept for muscle memory
.PHONY: start-NeXo
start-NeXo: start

.PHONY: start-dev
start-dev:
	$(call print_header,STARTING — DEV MODE (no auto-pipeline)) 
	@AUTO_PIPELINE=false $(COMPOSE) up -d
	$(call print_ok,Dev stack started) 
	@make jupyter-token

# ── Hot-Rebuild (DATA-SAFE — volumes never touched) ──────────────────────────
#
# Pattern: docker compose up -d --build <service>
#   • Rebuilds the image from source
#   • Recreates ONLY that container
#   • All named volumes (pgdata, miniodata, etc.) are untouched
#   • Other running containers are unaffected

.PHONY: up-dashboard
up-dashboard:
	$(call print_header,REBUILDING dashboard) 
	@$(COMPOSE) up -d --build dashboard
	$(call print_ok,dashboard rebuilt and restarted) 

.PHONY: up-api
up-api:
	$(call print_header,REBUILDING api-gateway) 
	@$(COMPOSE) up -d --build api-gateway
	$(call print_ok,api-gateway rebuilt and restarted) 

.PHONY: up-ai
up-ai:
	$(call print_header,REBUILDING ai-service) 
	@$(COMPOSE) up -d --build ai-service
	$(call print_ok,ai-service rebuilt and restarted) 

.PHONY: up-auth
up-auth:
	$(call print_header,REBUILDING auth-service) 
	@$(COMPOSE) up -d --build auth-service
	$(call print_ok,auth-service rebuilt and restarted) 

.PHONY: up-worker
up-worker:
	$(call print_header,REBUILDING pipeline-worker) 
	@$(COMPOSE) up -d --build pipeline-worker
	$(call print_ok,pipeline-worker rebuilt and restarted) 

.PHONY: up-agent
up-agent:
	$(call print_header,REBUILDING agent-service) 
	@$(COMPOSE) up -d --build agent-service
	$(call print_ok,agent-service rebuilt and restarted) 

.PHONY: up-notebooks
up-notebooks:
	$(call print_header,REBUILDING notebooks)
	@$(COMPOSE) up -d --build notebooks
	$(call print_ok,notebooks rebuilt and restarted)

.PHONY: jupyter-prep
jupyter-prep:
	$(call print_header,RESERVING MinIO PORTS BEFORE JUPYTER)
	@$(COMPOSE) up -d postgres minio
	@sleep 2
	@curl -sSf -m 5 http://localhost:9000/minio/health/live > /dev/null && \
		echo "  MinIO healthy on :9000 — safe to launch Jupyter kernel" || \
		(echo "  MinIO bind failed — port 9000 squatted; restart any local kernels first" && exit 1)

# ── Control ──────────────────────────────────────────────────────────────────

.PHONY: stop
stop:
	$(call print_header,STOPPING SERVICES) 
	@$(COMPOSE) stop
	$(call print_ok,All services stopped — data volumes preserved) 

.PHONY: restart
restart:
	$(call print_header,RESTARTING SERVICES) 
	@$(COMPOSE) restart
	$(call print_ok,All services restarted) 

.PHONY: svc-status
svc-status:
	@echo ""
	@echo "$(BOLD)Container Status:$(NC)"
	@$(COMPOSE) ps
	@echo ""

# ── Logs ─────────────────────────────────────────────────────────────────────

.PHONY: logs
logs:
	@if [ -n "$(SVC)" ]; then \
		$(COMPOSE) logs -f $(SVC); \
	elif [ -n "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		$(COMPOSE) logs -f $(filter-out $@,$(MAKECMDGOALS)); \
	else \
		$(COMPOSE) logs -f; \
	fi

.PHONY: logs-dashboard
logs-dashboard:
	$(COMPOSE) logs -f dashboard

.PHONY: logs-api
logs-api:
	$(COMPOSE) logs -f api-gateway

.PHONY: logs-ai
logs-ai:
	$(COMPOSE) logs -f ai-service

.PHONY: logs-auth
logs-auth:
	$(COMPOSE) logs -f auth-service

.PHONY: logs-worker
logs-worker:
	$(COMPOSE) logs -f pipeline-worker

.PHONY: logs-notebooks
logs-notebooks:
	$(COMPOSE) logs -f notebooks

.PHONY: logs-agent
logs-agent:
	$(COMPOSE) logs -f agent-service

# ── Pipeline (ETL daemon — 120s cycle) ───────────────────────────────────────
#
# The pipeline-worker runs continuously: every 120s it generates 200 BSS +
# 200 OSS records from bootstrap reservoirs, runs ML inference (CEM/VAE/RAT),
# computes correlations, and writes to PostgreSQL.
# This is THE only cyclic pipeline. The L4 agent is event-driven (not cyclic).

.PHONY: pipeline-status
pipeline-status:
	@echo ""
	@echo "$(BOLD)Pipeline-Worker — last 30 lines:$(NC)"
	@echo ""
	@$(COMPOSE) logs --tail=30 pipeline-worker
	@echo ""

.PHONY: pipeline-logs
pipeline-logs:
	$(COMPOSE) logs -f pipeline-worker

.PHONY: pipeline-once
pipeline-once:
	$(call print_header,RUNNING ONE PIPELINE CYCLE) 
	@echo "$(YELLOW)Executing single cycle in pipeline-worker...$(NC)"
	@$(COMPOSE) exec -T pipeline-worker python -m worker oneshot
	$(call print_ok,Pipeline cycle complete) 

# ── Jupyter / Notebooks ──────────────────────────────────────────────────────
#
# HOW NOTEBOOKS WORK:
#   notebooks/ are mounted read-only into the notebooks container.
#   Jupyter runs at http://localhost:8888 — use `make jupyter-token` to get access.
#   Run notebooks IN ORDER:  00 → 01 → 02,03,04 (can be parallel) → 10
#   They pull data FROM PostgreSQL (already ingested by data-init or make ensure-data).
#   Trained models are saved to services/ai-service/models/ (bind-mounted).
#
#   Auto-run headless: `make nb-run-all`  or  `make nb-run NB=02`

.PHONY: jupyter-token
jupyter-token:
	@echo ""
	@echo "$(BOLD)Jupyter Access:$(NC)"
	@echo "  URL: $(GREEN)http://localhost:8888$(NC)"
	@TOKEN=$$($(COMPOSE) exec -T notebooks jupyter server list 2>/dev/null | grep -oP 'token=\K[a-zA-Z0-9_-]+' | head -1); \
	if [ -n "$$TOKEN" ]; then \
		echo "  Token: $(GREEN)$$TOKEN$(NC)"; \
		echo "  Full URL: $(GREEN)http://localhost:8888/?token=$$TOKEN$(NC)"; \
	else \
		echo "  $(YELLOW)Token not available — is notebooks container running?$(NC)"; \
	fi
	@echo ""

.PHONY: jupyter-url
jupyter-url:
	@$(COMPOSE) exec -T notebooks jupyter server list 2>/dev/null | grep -oP 'http://[^ ]+'

# Run ALL notebooks in order (headless, no browser needed).
# Outputs are written back to the notebook files via --inplace.
.PHONY: nb-run-all
nb-run-all:
	$(call print_header,RUNNING ALL NOTEBOOKS — HEADLESS) 
	@echo "Order: 00 (EDA) → 01 (ETL) → 02 (CEM) → 03 (VAE) → 04 (RAT) → 10 (Granger)"
	@echo ""
	@$(COMPOSE) exec -T notebooks bash /app/notebooks/../scripts/run_notebooks.sh
	$(call print_ok,All notebooks complete — models saved to ai-service/models/) 

# Run a single notebook: make nb-run NB=02
# NB can be the prefix number or full filename stem.
.PHONY: nb-run
nb-run:
	@if [ -z "$(NB)" ]; then \
		echo "$(RED)Usage: make nb-run NB=02  (prefix number or full stem)$(NC)"; exit 1; \
	fi
	@NB_FILE=$$(ls /app/notebooks/$(NB)*.ipynb 2>/dev/null | head -1 || \
		$(COMPOSE) exec -T notebooks sh -c "ls /app/notebooks/$(NB)*.ipynb 2>/dev/null | head -1"); \
	echo "$(YELLOW)Running notebook: $(NB)...$(NC)"; \
	$(COMPOSE) exec -T notebooks jupyter nbconvert \
		--to notebook --execute --inplace \
		--ExecutePreprocessor.timeout=3600 \
		--ExecutePreprocessor.kernel_name=python3 \
		"/app/notebooks/$(NB)"*.ipynb
	$(call print_ok,Notebook $(NB) complete) 

# ── Health ────────────────────────────────────────────────────────────────────

.PHONY: svc-health
svc-health:
	$(call print_header,HEALTH CHECK) 
	@echo -n "postgres:         " && $(COMPOSE) exec -T postgres pg_isready -U telecom -q && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo -n "minio:            " && curl -sf http://localhost:9000/minio/health/live > /dev/null && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo -n "api-gateway:      " && curl -sf http://localhost:8000/health > /dev/null && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo -n "ai-service:       " && curl -sf http://localhost:8001/health > /dev/null && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo -n "auth-service:     " && curl -sf http://localhost:8002/health > /dev/null && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo -n "agent-service:    " && curl -sf http://localhost:8003/health > /dev/null && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo -n "dashboard:        " && curl -sf http://localhost:3001/login > /dev/null && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo -n "notebooks:        " && curl -sf http://localhost:8888/api > /dev/null && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo -n "netdata:          " && curl -sf http://localhost:19999/api/v1/info > /dev/null && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo -n "prometheus:       " && curl -sf http://localhost:9090/-/healthy > /dev/null && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo -n "grafana:          " && curl -sf http://localhost:3000/api/health > /dev/null && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo -n "jaeger:           " && curl -sf http://localhost:16686 > /dev/null && echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ down$(NC)"
	@echo ""

# ── Database ──────────────────────────────────────────────────────────────────

.PHONY: db-shell
db-shell:
	$(COMPOSE) exec postgres psql -U telecom -d telecom_intel

.PHONY: db-tables
db-tables:
	@echo ""
	@echo "$(BOLD)Tables + row counts:$(NC)"
	@$(COMPOSE) exec -T postgres psql -U telecom -d telecom_intel -c \
		"SELECT schemaname, tablename, n_live_tup AS rows \
		 FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"
	@echo ""

.PHONY: db-reset
db-reset:
	$(call print_header,DATABASE RESET) 
	@echo "$(RED)WARNING: drops + recreates public schema — ALL data lost!$(NC)"
	@printf "$(YELLOW)Press Enter to continue, Ctrl+C to cancel...$(NC)" && read
	@$(COMPOSE) exec -T postgres psql -U telecom -d telecom_intel \
		-c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(call print_ok,Schema reset — restart pipeline-worker to re-populate) 

.PHONY: db-backup
db-backup:
	@mkdir -p backups
	@FILE=backups/db_$$(date +%Y%m%d_%H%M%S).sql; \
	$(COMPOSE) exec -T postgres pg_dump -U telecom telecom_intel > $$FILE && \
	echo "$(GREEN)[✓] Backed up to $$FILE$(NC)"

.PHONY: ensure-data
ensure-data:
	$(call print_header,ENSURING DATA IS PRESENT) 
	@bash scripts/init-db-data.sh

.PHONY: ingest-data
ingest-data:
	$(call print_header,INGESTING REAL TT DATA (~10 min)) 
	@$(COMPOSE) run --rm data-init
	$(call print_ok,Data ingestion complete) 

.PHONY: migrate-004
migrate-004:
	$(call print_header,APPLYING MIGRATION 004 — Derived OSS view + active_users_max column) 
	@$(COMPOSE) exec -T postgres psql -U telecom -d telecom_intel \
		-f - < docs/db/migrations/004_oss_derived_view.sql
	$(call print_ok,Migration 004 applied) 

.PHONY: refresh-4g-users-max
refresh-4g-users-max:
	$(call print_header,REFRESHING 4G active_users_max from real CSV (~3 min)) 
	@$(COMPOSE) run --rm --entrypoint "" data-init \
		python /app/services/data-ingest/refresh_4g_users_max.py
	$(call print_ok,4G L.Traffic.User.Max landed in oss_cell_kpis.active_users_max) 

.PHONY: generate-oss-months
generate-oss-months:
	$(call print_header,GENERATING 48 monthly OSS CSVs - 3 RATs x 16 months)
	@$(COMPOSE) run --rm --entrypoint "" data-init \
		python /app/services/data-ingest/generate_oss_months.py
	$(call print_ok,OSS month generation complete)

.PHONY: clean-minio-raw
clean-minio-raw:
	$(call print_header,PURGING MinIO raw of non-dataset objects)
	@$(COMPOSE) run --rm --entrypoint "" data-init \
		python /app/services/data-ingest/cleanup_minio_raw.py
	$(call print_ok,raw bucket clean)


# ── Build / Maintenance ───────────────────────────────────────────────────────

.PHONY: build
build:
	$(call print_header,REBUILDING ALL IMAGES (no cache)) 
	@$(COMPOSE) build --no-cache
	$(call print_ok,Build complete) 

.PHONY: build-cache
build-cache:
	$(call print_header,REBUILDING ALL IMAGES (with cache)) 
	@$(COMPOSE) build
	$(call print_ok,Build complete) 

.PHONY: clean
clean:
	$(call print_header,REMOVING CONTAINERS (volumes preserved)) 
	@$(COMPOSE) down --remove-orphans
	$(call print_ok,Containers removed — pgdata + miniodata intact) 

.PHONY: nuke
nuke:
	$(call print_header,NUKING EVERYTHING) 
	@echo "$(RED)WARNING: deletes ALL Docker volumes including pgdata + miniodata!$(NC)"
	@printf "$(YELLOW)Press Enter to continue, Ctrl+C to cancel...$(NC)" && read
	@$(COMPOSE) down -v --remove-orphans
	$(call print_ok,All containers and volumes destroyed) 

.PHONY: prune
prune:
	$(call print_header,PRUNING UNUSED DOCKER RESOURCES) 
	@docker system prune -f
	$(call print_ok,Prune complete) 

# ── Info ─────────────────────────────────────────────────────────────────────

.PHONY: show-info
show-info:
	@echo ""
	@echo "$(BOLD)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ NEXO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "  $(GREEN)Dashboard$(NC)          http://localhost:3001"
	@echo "  $(GREEN)Jupyter Notebooks$(NC)  http://localhost:8888"
	@echo "  $(GREEN)API Gateway$(NC)        http://localhost:8000/docs"
	@echo "  $(GREEN)AI Service$(NC)         http://localhost:8001/docs"
	@echo "  $(GREEN)Auth Service$(NC)       http://localhost:8002/docs"
	@echo "  $(GREEN)Agent Service$(NC)      http://localhost:8003/docs"
	@echo "  $(GREEN)MinIO Console$(NC)      http://localhost:9001"
	@echo "  $(GREEN)Netdata$(NC)            http://localhost:19999"
	@echo "  $(GREEN)Prometheus$(NC)         http://localhost:9090"
	@echo "  $(GREEN)Grafana$(NC)            http://localhost:3000  (admin/admin)"
	@echo "  $(GREEN)Jaeger Traces$(NC)      http://localhost:16686"
	@echo "  $(GREEN)Ollama LLM$(NC)         http://localhost:11434"
	@echo ""
	@echo "  $(YELLOW)PostgreSQL$(NC)  telecom / telecom_pw / telecom_intel"
	@echo "  $(YELLOW)MinIO$(NC)       minio / minio_pw"
	@echo ""
	@echo "  Pipeline-worker: daemon, 120s cycle"
	@echo "  L4 Agent: event-driven (Qwen2.5:7b via Ollama)"
	@echo "$(BOLD)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""

.PHONY: open
open:
	@("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" http://localhost:3001 2>/dev/null || \
	  google-chrome --new-window http://localhost:3001 2>/dev/null || \
	  xdg-open http://localhost:3001 2>/dev/null) || echo "Open http://localhost:3001 manually"

# Suppress "No rule to make target" for bare service-name arguments to `make logs`
%:
	@:
