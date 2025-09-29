# Fantasy TikTok Engine

A FastAPI-based fantasy football content generation engine that creates automated TikTok content using AI agents.

## Quick Start

````markdown
# Fantasy TikTok Engine

A FastAPI-based fantasy football content generation engine that creates automated TikTok content using AI agents.

## One-command dev experience

The repo is designed so a new developer can get started with a single command:

```bash
make setup && make up && make health
```

Everything below supports that workflow and is idempotent.

## Quick reference commands

- `make setup` — create venv and install dependencies (idempotent)
- `make up` — start the API server (development reload)
- `make down` — stop services
- `make test` — run test suite
- `make fmt` / `make lint` — format and lint
- `make health` — run the API health check

New convenience commands:
- `make batch-week week=5` — generate a planning `plan.json` for week 5
- `make dry-run week=5 type=start-sit players="Player A,Player B"` — render locally to `.out/week-5`
- `make export-scheduler week=5 start_date=2025-09-29 timezone=America/Los_Angeles` — export scheduler CSV
- `make metrics-summary date=2025-09-29` — quick metrics CLI summary

## Batch Tuesday Flow (production-friendly)

Goal: produce a full week's worth of short TikTok scripts each Tuesday.

Steps (developer-friendly):

1. Draft a plan

```bash
# create a deterministic plan for week 5
make batch-week week=5
# Inspect the plan
cat .out/week-5/plan.json
```

2. Render locally (dry-run) — produces `.out/week-5/*.md` and manifests

```bash
make dry-run week=5 type=start-sit players="Bijan Robinson,Justin Jefferson"
ls .out/week-5
cat .out/week-5/manifest.json
```

3. Export for scheduler

```bash
make export-scheduler week=5 start_date=2025-09-29 timezone=America/Los_Angeles
cat .out/week-5/scheduler_manifest.csv
```

4. Upload assets & schedule using your scheduler system (not in this repo). The CSV has columns: `scheduled_datetime,title,caption,video_path,thumbnail_path,tags`.

## Guardrails

# Fantasy TikTok Engine

A FastAPI-based fantasy football content generation engine that creates automated TikTok content using AI agents.

## One-command dev experience

The repo is designed so a new developer can get started with a single command:

```bash
make setup && make up && make health
```

Everything below supports that workflow and is idempotent.

## Quick reference commands

- `make setup` — create venv and install dependencies (idempotent)
- `make up` — start the API server (development reload)
- `make down` — stop services
- `make test` — run test suite
- `make fmt` / `make lint` — format and lint
- `make health` — run the API health check

New convenience commands:

- `make batch-week week=5` — generate a planning `plan.json` for week 5
- `make dry-run week=5 type=start-sit players="Player A,Player B"` — render locally to `.out/week-5`
- `make export-scheduler week=5 start_date=2025-09-29 timezone=America/Los_Angeles` — export scheduler CSV
- `make metrics-summary date=2025-09-29` — quick metrics CLI summary

## Batch Tuesday Flow (production-friendly)

Goal: produce a full week's worth of short TikTok scripts each Tuesday.

Steps (developer-friendly):

1. Draft a plan

```bash
# create a deterministic plan for week 5
make batch-week week=5
# Inspect the plan
cat .out/week-5/plan.json
```

2. Render locally (dry-run) — produces `.out/week-5/*.md` and manifests

```bash
make dry-run week=5 type=start-sit players="Bijan Robinson,Justin Jefferson"
ls .out/week-5
cat .out/week-5/manifest.json
```

3. Export for scheduler

```bash
make export-scheduler week=5 start_date=2025-09-29 timezone=America/Los_Angeles
cat .out/week-5/scheduler_manifest.csv
```

4. Upload assets & schedule using your scheduler system (not in this repo). The CSV has columns: `scheduled_datetime,title,caption,video_path,thumbnail_path,tags`.

## Guardrails

Small, conservative guardrails are applied to generated scripts:

- `GUARDRAILS_LENGTH_MODE` — how length violations are handled:
  - `fail` (default): API responds 422 when script > 70 words
  - `trim`: API trims to 70 words automatically
- CLI flag: `--strict` / `--no-strict` — `--strict` requests fail-on-long, `--no-strict` requests auto-trim
- Player blocking: Data Agent returns `blocked: True` for OUT/IR players and the API responds with HTTP 400 and `block_reason`.

### Strict vs trim length enforcement

- API requests default to *strict* mode (`fail`). Provide `X-Guardrails-Strict: false` to switch a request into trim mode and receive a 200 response with a shortened script when it exceeds 70 words.
- The `ff-post` CLI propagates this header for you: `--strict` keeps fail-fast semantics; `--no-strict` sends `X-Guardrails-Strict: false`.
- Guardrail violations now return HTTP 422 with an explanatory `detail`, making it easier to branch on failures in operators or tests.

Examples:

```bash
# Fail when script is too long
python -m apps.cli.ff_post --player "Bijan Robinson" --week 5 --type start-sit --strict

# Auto-trim long scripts
python -m apps.cli.ff_post --player "Bijan Robinson" --week 5 --type start-sit --no-strict
```

## Tracking & Attribution

Metrics are stored locally by default. To enable Google Sheets sync set the env vars:

- `SHEETS_ENABLED=true`
- `SHEETS_SPREADSHEET_ID=<your-spreadsheet-id>`
- `SHEETS_SERVICE_ACCOUNT_JSON=/path/to/creds.json`

Local CSV path: `.metrics/posts.csv`.

CLI examples:

```bash
# record a post locally
python -m apps.cli.ff_metrics record-post --post-id pid --date 2025-09-28 --player "Bijan" --week 5 --views 12000

# daily summary
python -m apps.cli.ff_metrics daily-summary --date 2025-09-28
```

## Scheduler Export

The exporter reads `.out/week-<N>/manifest.json` and writes `.out/week-<N>/scheduler_manifest.csv`.

CSV columns:
- `scheduled_datetime` (ISO8601)
- `title`
- `caption`
- `video_path`
- `thumbnail_path`
- `tags`

Default timezone: `America/Los_Angeles`. Override via `--timezone` or env `SCHEDULER_TZ`.

Example:

```bash
python -m apps.cli.ff_post export-scheduler --week 5 --start-date 2025-09-29 --timezone America/Los_Angeles
```

## If this fails — quick fixes

1) Scripts not executable / permission errors

```bash
chmod +x scripts/*.sh
```

2) Virtualenv or dependencies missing

```bash
make setup
source .venv/bin/activate
```

3) API port in use

```bash
lsof -ti:8000 | xargs kill -9 || true
make up
```

## Tests

Run the full test suite (fast, network-free by design):

```bash
make test
```

Run a single test file:

```bash
pytest -q tests/test_batch.py
```

## Docs

See `docs/PRD.md` for the product requirements document and template contracts.

*** End of README ***
