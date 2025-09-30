.PHONY: setup up down test fmt lint health
.PHONY: format coverage
.PHONY: batch-week dry-run export-scheduler metrics-summary
.PHONY: up-api down-api logs-api health-api

.PHONY: doctor

# -----------------------------
# Core (existing behavior)
# -----------------------------

# Setup development environment
setup:
	bash scripts/setup.sh

# Start the API server
up:
	bash scripts/up.sh

# Stop running services
down:
	bash scripts/down.sh

# Run tests
test:
	if [ -x scripts/test.sh ]; then \
		bash scripts/test.sh; \
	else \
		python -m pytest -q; \
	fi

# Format code
fmt:
	bash scripts/fmt.sh

format:
	@echo "Running black (if available) and ruff --fix"
	@black . || true
	@ruff check --fix . || true

# Lint code
lint:
	bash scripts/lint.sh

# Check API health
health:
	bash scripts/health.sh


# Developer preflight checks that validate env, approvals, and local cache health
doctor:
	python -c "from apps.batch.runner import doctor_check; doctor_check()"

coverage:
	@echo "Running pytest with coverage"
	pytest --maxfail=1 --disable-warnings --cov=. --cov-report=term-missing

# Generate a planning batch for a week (uses planner)
batch-week:
	python -m apps.cli.ff_post batch plan --week $(week)

# Run a dry-run rendering for a week (writes .out/week-<N>)
dry-run:
	python -m apps.cli.ff_post --type $(type) --batch-week $(week) --players "$(players)" --dry-run

# Export scheduler CSV for a week
export-scheduler:
	python -m apps.cli.ff_post export-scheduler --week $(week) --start-date $(start_date) --timezone $(timezone)

# Quick metrics summary (CLI)
metrics-summary:
	python -m apps.cli.ff_metrics daily-summary --date $(date)

# -----------------------------
# Dev API convenience (optional)
# -----------------------------

UVICORN ?= .venv/bin/uvicorn
APP     ?= apps.api.main:app   # change if your FastAPI app lives elsewhere
HOST    ?= 127.0.0.1
PORT    ?= 8000
PID_FILE ?= .fantasy_api.pid
LOG_FILE ?= .fantasy_api.log

up-api:
	. .venv/bin/activate 2>/dev/null || true; \
	$(UVICORN) $(APP) --host $(HOST) --port $(PORT) --reload > $(LOG_FILE) 2>&1 & echo $$! > $(PID_FILE); \
	echo "✅ API started on http://$(HOST):$(PORT) (pid $$(cat $(PID_FILE)))"

down-api:
	if [ -f $(PID_FILE) ]; then \
		kill $$(cat $(PID_FILE)) 2>/dev/null || true; \
		rm -f $(PID_FILE); \
		echo "🛑 API stopped"; \
	else \
		echo "ℹ️ No API pid file found ($(PID_FILE))"; \
	fi

logs-api:
	@echo "📜 Tailing $(LOG_FILE) (Ctrl-C to stop)"; \
	tail -n 100 -f $(LOG_FILE)

health-api:
	@echo "🔎 Checking http://$(HOST):$(PORT)/health"
	@for i in 1 2 3 4 5; do \
		if curl -fsS "http://$(HOST):$(PORT)/health" >/dev/null; then \
			echo "✅ Health OK"; exit 0; \
		fi; \
		echo "…retry $$i"; sleep 1; \
	done; \
	echo "❌ Health check failed"; exit 1

logs-api:
	@echo "📜 Tailing $(LOG_FILE) (Ctrl-C to stop)"; \
	tail -n 100 -f $(LOG_FILE)
