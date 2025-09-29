.PHONY: setup up down test fmt lint health
.PHONY: format coverage

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
