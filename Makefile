# ═══════════════════════════════════════════════════════════════════════════════
# Telecom Cloud Intelligence — Makefile
# 
# Usage:
#   make start-nextops    - Start entire stack with auto-pipeline
#   make start-dev        - Start stack without auto-pipeline (dev mode)
#   make stop             - Stop all services
#   make restart          - Restart all services
#   make logs [service]   - View logs (all or specific service)
#   make status           - Show container status
#   make clean            - Stop and remove all containers/volumes
#   make build            - Rebuild all images
#   make test-pipeline    - Test pipeline manually
#   make jupyter-token    - Get Jupyter access token
#   make health           - Check all services health
# ═══════════════════════════════════════════════════════════════════════════════

# ── Configuration ────────────────────────────────────────────────────────────

# Auto-detect project root from Makefile location
PROJECT_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
export PROJECT_ROOT

PROJECT_NAME := telecom-cloud-intelligence
COMPOSE := docker compose -f $(PROJECT_ROOT)/docker-compose.yml
DEFAULT_TAG := latest

# Colors for terminal output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color
BOLD := \033[1m

# ── Helper Functions ──────────────────────────────────────────────────────────

define print_header
	@echo ""
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)$(BOLD)  $(1)$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════════════════════$(NC)"
	@echo ""
endef

define print_status
	@echo "$(GREEN)[✓] $(1)$(NC)"
endef

define print_warning
	@echo "$(YELLOW)[!] $(1)$(NC)"
endef

define print_error
	@echo "$(RED)[✗] $(1)$(NC)"
endef

# ── Targets ──────────────────────────────────────────────────────────────────

# Default target
.PHONY: help
help: 
	@echo ""
	@echo "$(BOLD)Telecom Cloud Intelligence — Available Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Startup:$(NC)"
	@echo "  $(YELLOW)make start-nexops$(NC)     Start full stack with AUTO_PIPELINE enabled + dashboard"
	@echo "  $(YELLOW)make start-dev$(NC)          Start stack in development mode (no auto-pipeline)"
	@echo ""
	@echo "$(GREEN)Control:$(NC)"
	@echo "  $(YELLOW)make stop$(NC)               Stop all services"
	@echo "  $(YELLOW)make restart$(NC)           Restart all services"
	@echo "  $(YELLOW)make svc-status$(NC)         Show container status"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  $(YELLOW)make logs [service]$(NC)     View logs (use service name: notebooks, api-gateway, etc.)"
	@echo "  $(YELLOW)make jupyter-token$(NC)      Get Jupyter access token"
	@echo "  $(YELLOW)make test-pipeline$(NC)      Manually run pipeline in notebooks container"
	@echo ""
	@echo "$(GREEN)Maintenance:$(NC)"
	@echo "  $(YELLOW)make build$(NC)              Rebuild all Docker images"
	@echo "  $(YELLOW)make clean$(NC)              Stop and remove all containers + volumes"
	@echo "  $(YELLOW)make svc-health$(NC)         Check health of all services"
	@echo ""
	@echo "$(GREEN)Database:$(NC)"
	@echo "  $(YELLOW)make db-shell$(NC)          Open PostgreSQL shell"
	@echo "  $(YELLOW)make db-reset$(NC)           Reset database (WARNING: deletes all data)"
	@echo ""
	@echo "$(GREEN)Info:$(NC)"
	@echo "  $(YELLOW)make show-info$(NC)          Show service URLs and credentials"
	@echo ""
	@echo "$(GREEN)Pipeline:$(NC)"
	@echo "  $(YELLOW)make pipeline-logs$(NC)      View pipeline execution logs"
	@echo "  $(YELLOW)make pipeline-force$(NC)     Force run pipeline in running notebooks"
	@echo ""
	@echo "Examples:"
	@echo "  make start-nexops          # Full production-like start with dashboard"
	@echo "  make logs notebooks         # Watch notebooks logs"
	@echo "  make db-shell               # Connect to database"
	@echo ""

# ── Main Startup Commands ────────────────────────────────────────────────────

.PHONY: start-nexops
start-nexops: ## Start entire stack with auto-pipeline enabled + dashboard
	$(call print_header,"STARTING NEXOPS — FULL STACK")

	@echo "$(YELLOW)This will:$(NC)"
	@echo "  • Start all Docker services (postgres, minio, ai-service, pipeline-worker, etc.)"
	@echo "  • Pipeline worker runs in daemon mode (120s cycles)"
	@echo "  • AI service loads latest trained models dynamically"
	@echo "  • Start Jupyter for notebook access"
	@echo "  • Start dashboard with auto-refresh"
	@echo "  • Start Ollama LLM for L4 Agent chat"
	@echo ""

	@$(COMPOSE) up -d --build

	@echo ""
	@echo "$(GREEN)Waiting for services to be healthy...$(NC)"
	@sleep 8

	@$(call print_status,"Docker services started")

	@echo ""
	@echo "$(BOLD)Starting Ollama LLM (background)...$(NC)"
	@(ollama serve > /dev/null 2>&1 &) || echo "$(YELLOW)Ollama already running or not installed$(NC)"
	@sleep 2

	@echo ""
	@echo "$(BOLD)Starting Dashboard...$(NC)"
	@cd $(PROJECT_ROOT)/dashboard && npm run dev > /dev/null 2>&1 &
	@sleep 4
	@xdg-open http://localhost:3001 2>/dev/null || echo "Open http://localhost:3001 in your browser"

	@echo ""
	@echo "$(BOLD)═══════════════════════════════════════════$(NC)"
	@echo "$(GREEN)   NexOps AI is ready!$(NC)"
	@echo "$(BOLD)═══════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(BOLD)Access URLs:$(NC)"
	@echo "  $(GREEN)Dashboard:$(NC)         http://localhost:3001"
	@echo "  $(GREEN)Jupyter Notebook:$(NC)  http://localhost:8888"
	@echo "  $(GREEN)API Gateway:$(NC)       http://localhost:8000"
	@echo "  $(GREEN)AI Service:$(NC)        http://localhost:8001"
	@echo "  $(GREEN)Auth Service:$(NC)      http://localhost:8002"
	@echo "  $(GREEN)MinIO Console:$(NC)     http://localhost:9001"
	@echo "  $(GREEN)Prometheus:$(NC)        http://localhost:9090"
	@echo "  $(GREEN)Grafana:$(NC)           http://localhost:3000"
	@echo "  $(GREEN)Ollama LLM:$(NC)        http://localhost:11434"
	@echo ""
	@echo "$(BOLD)Pipeline:$(NC) Runs every 120s (daemon mode)"
	@echo "$(BOLD)L4 Agent:$(NC) Qwen2.5 via Ollama (local LLM)"
	@echo ""

.PHONY: start-dev
start-dev: ## Start stack in development mode (no auto-pipeline)
	$(call print_header,"STARTING DEVELOPMENT MODE")
	
	@echo "$(YELLOW)This will:$(NC)"
	@echo "  • Start all Docker services"
	@echo "  • Skip auto-pipeline (run notebooks manually)"
	@echo "  • Start Jupyter immediately"
	@echo ""
	
	AUTO_PIPELINE=false $(COMPOSE) up -d --build
	
	@echo ""
	@$(call print_status,"Development stack started")
	@echo ""
	@make jupyter-token

# ── Control Commands ─────────────────────────────────────────────────────────

.PHONY: stop
stop: ## Stop all services
	$(call print_header,"STOPPING SERVICES")
	$(COMPOSE) stop
	$(call print_status,"All services stopped")

.PHONY: restart
restart: ## Restart all services
	$(call print_header,"RESTARTING SERVICES")
	$(COMPOSE) restart
	$(call print_status,"All services restarted")

.PHONY: svc-status
svc-status: ## Show container status
	@echo ""
	@echo "$(BOLD)Container Status:$(NC)"
	@echo ""
	$(COMPOSE) ps
	@echo ""

# ── Logs ─────────────────────────────────────────────────────────────────────

.PHONY: logs
logs: ## View logs (all or specific service: make logs notebooks)
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		$(COMPOSE) logs -f; \
	else \
		$(COMPOSE) logs -f $(filter-out $@,$(MAKECMDGOALS)); \
	fi

.PHONY: logs-all
logs-all: ## View all logs
	$(COMPOSE) logs -f

.PHONY: logs-notebooks
logs-notebooks: ## View notebooks logs
	$(COMPOSE) logs -f notebooks

.PHONY: logs-api
logs-api: ## View API gateway logs
	$(COMPOSE) logs -f api-gateway

.PHONY: logs-ai
logs-ai: ## View AI service logs
	$(COMPOSE) logs -f ai-service

# ── Health & Monitoring ──────────────────────────────────────────────────────

.PHONY: svc-health
svc-health: ## Check health of all services
	$(call print_header,"HEALTH CHECK")
	
	@echo "$(BOLD)Checking services...$(NC)"
	@echo ""
	
	@echo -n "PostgreSQL: " && $(COMPOSE) exec -T postgres pg_isready -U telecom > /dev/null 2>&1 && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo -n "MinIO: " && $(COMPOSE) exec -T minio curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1 && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo -n "AI Service: " && curl -sf http://localhost:8001/health > /dev/null 2>&1 && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo -n "API Gateway: " && curl -sf http://localhost:8000/health > /dev/null 2>&1 && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo -n "Auth Service: " && curl -sf http://localhost:8002/health > /dev/null 2>&1 && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo -n "Notebooks: " && curl -sf http://localhost:8888/api > /dev/null 2>&1 && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo ""

# ── Jupyter ─────────────────────────────────────────────────────────────────

.PHONY: jupyter-token
jupyter-token: ## Get Jupyter access token
	@echo ""
	@echo "$(BOLD)Jupyter Access:$(NC)"
	@echo "  URL: $(GREEN)http://localhost:8888$(NC)"
	@TOKEN=$$($(COMPOSE) exec -T notebooks jupyter server list 2>/dev/null | grep -oP 'token=\K[a-zA-Z0-9_-]+'); \
	if [ -n "$$TOKEN" ]; then \
		echo "  Token: $(GREEN)$$TOKEN$(NC)"; \
	else \
		echo "  Token: $(YELLOW)Not available (check if notebooks is running)$(NC)"; \
	fi
	@echo ""

.PHONY: jupyter-url
jupyter-url: ## Get full Jupyter URL with token
	@$(COMPOSE) exec -T notebooks jupyter server list 2>/dev/null | grep -oP 'http://[^ ]+'

# ── Pipeline ─────────────────────────────────────────────────────────────────

.PHONY: pipeline-logs
pipeline-logs: ## View pipeline execution logs
	@echo "$(BOLD)Pipeline Logs:$(NC)"
	@$(COMPOSE) exec -T notebooks tail -50 /app/logs/pipeline_*.log 2>/dev/null || \
		echo "$(YELLOW)No pipeline logs found$(NC)"

.PHONY: test-pipeline
test-pipeline: ## Manually run pipeline in notebooks container
	$(call print_header,"MANUALLY RUNNING PIPELINE")
	@echo "$(YELLOW)Executing pipeline in notebooks container...$(NC)"
	@$(COMPOSE) exec -T notebooks python -m pipeline.worker

.PHONY: pipeline-force
pipeline-force: ## Force run pipeline in running notebooks
	@echo "$(YELLOW)Starting pipeline with AUTO_PIPELINE=true...$(NC)"
	@docker compose exec -d notebooks bash -c "AUTO_PIPELINE=true /app/entrypoint.sh &"
	@sleep 2
	@$(call print_status,"Pipeline started in background")
	@make logs-notebooks

# ── Database ─────────────────────────────────────────────────────────────────

.PHONY: db-shell
db-shell: ## Open PostgreSQL shell
	$(COMPOSE) exec postgres psql -U telecom -d telecom_intel

.PHONY: db-reset
db-reset: ## Reset database (WARNING: deletes all data)
	$(call print_header,"DATABASE RESET")
	@echo "$(RED)WARNING: This will delete ALL data in the database!$(NC)"
	@echo "$(YELLOW)Press Enter to continue or Ctrl+C to cancel...$(NC)"
	@read
	$(COMPOSE) exec -T postgres psql -U telecom -d telecom_intel -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(call print_status,"Database reset complete")

.PHONY: db-backup
db-backup: ## Backup database
	@mkdir -p backups
	@FILENAME=backups/db_backup_$$(date +%Y%m%d_%H%M%S).sql
	@$(COMPOSE) exec -T postgres pg_dump -U telecom telecom_intel > $$FILENAME
	$(call print_status,"Database backed up to $$FILENAME")

.PHONY: db-tables
db-tables: ## List database tables
	$(COMPOSE) exec -T postgres psql -U telecom -d telecom_intel -c "\dt"

# ── Maintenance ───────────────────────────────────────────────────────────────

.PHONY: build
build: ## Rebuild all Docker images
	$(call print_header,"REBUILDING DOCKER IMAGES")
	$(COMPOSE) build --no-cache
	$(call print_status,"Build complete")

.PHONY: build-cache
build-cache: ## Rebuild with cache
	$(call print_header,"REBUILDING DOCKER IMAGES (with cache)")
	$(COMPOSE) build
	$(call print_status,"Build complete")

.PHONY: clean
clean: ## Stop and remove all containers + volumes
	$(call print_header,"CLEANING UP")
	@echo "$(YELLOW)Stopping containers...$(NC)"
	$(COMPOSE) down -v --remove-orphans
	$(call print_status,"All containers and volumes removed")

.PHONY: prune
prune: ## Remove unused Docker resources
	$(call print_header,"PRUNING DOCKER RESOURCES")
	@docker system prune -f
	$(call print_status,"Prune complete")

# ── Info ─────────────────────────────────────────────────────────────────────

.PHONY: show-info
show-info: ## Show service URLs and credentials
	$(call print_header,"SERVICE INFORMATION")
	
	@echo "$(BOLD)Service URLs:$(NC)"
	@echo "  $(GREEN)Jupyter Notebook:$(NC)  http://localhost:8888"
	@echo "  $(GREEN)API Gateway:$(NC)       http://localhost:8000/docs"
	@echo "  $(GREEN)AI Service:$(NC)        http://localhost:8001/docs"
	@echo "  $(GREEN)Auth Service:$(NC)       http://localhost:8002/docs"
	@echo "  $(GREEN)MinIO Console:$(NC)      http://localhost:9001"
	@echo "  $(GREEN)MinIO API:$(NC)          http://localhost:9000"
	@echo "  $(GREEN)Prometheus:$(NC)         http://localhost:9090"
	@echo "  $(GREEN)Grafana:$(NC)            http://localhost:3000"
	@echo ""
	@echo "$(BOLD)Default Credentials:$(NC)"
	@echo "  $(YELLOW)PostgreSQL:$(NC)  telecom / telecom_pw"
	@echo "  $(YELLOW)MinIO:$(NC)       minio / minio_pw"
	@echo "  $(YELLOW)Grafana:$(NC)      admin / admin"
	@echo ""
	@echo "$(BOLD)API Authentication:$(NC)"
	@echo "  JWT tokens generated at http://localhost:8002"
	@echo ""

# ── Quick Access ──────────────────────────────────────────────────────────────

.PHONY: open
open: ## Open all URLs in browser (requires xdg-open or similar)
	@xdg-open http://localhost:8888 2>/dev/null || echo "Open http://localhost:8888 manually"
	@xdg-open http://localhost:8000/docs 2>/dev/null || echo "Open http://localhost:8000/docs manually"

.PHONY: api-docs
api-docs: ## Open API documentation
	@xdg-open http://localhost:8000/docs 2>/dev/null || echo "Open http://localhost:8000/docs manually"

.PHONY: minio-console
minio-console: ## Open MinIO console
	@xdg-open http://localhost:9001 2>/dev/null || echo "Open http://localhost:9001 manually"

.PHONY: grafana-dashboards
grafana-dashboards: ## Open Grafana dashboards
	@xdg-open http://localhost:3000/d/overview 2>/dev/null || echo "Open http://localhost:3000 manually"
