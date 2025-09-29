# CLI & Templates Usage

This document explains how to use the repository's CLI tools (generation, avatar rendering, pipeline) and how templates are discovered and named.

Environment and DRY_RUN

- This project reads configuration from environment variables via `adapters.wiring.load_env()`.
- The canonical example env file is `.env.example` at the repository root. Copy it to `.env` or set variables directly in your shell.
- To run the CLIs without calling external services set:

  - `DRY_RUN=true`

  When `DRY_RUN` is true the adapters return deterministic stubs and the CLIs will write placeholder files (for example, an empty `video.mp4` for avatar renders or JSON stubs for uploads).

## Key env vars (see `.env.example` for more)

- `OPENAI_API_KEY` — optional for live OpenAI usage
- `HEYGEN_API_KEY` — optional for live HeyGen usage
- `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI` — OAuth client config used by the TikTok wiring
- `TIKTOK_ACCESS_TOKEN`, `TIKTOK_OPEN_ID` — tokens required for real uploads (can be passed via CLI flags for upload commands)

1) Quick CLI examples

All CLIs are available as Python modules. Examples below assume you run them from the repo root and your environment is configured (or `DRY_RUN=true` for dry-run).

- Single generate (renders a script locally or calls API):

  ```bash
  # local dry-run render
  DRY_RUN=true python -m apps.cli.ff_post generate --player "Bijan Robinson" --week 5 --type start-sit --dry-run

  # call API (requires API server or appropriate env)
  python -m apps.cli.ff_post generate --player "Bijan Robinson" --week 5 --type start-sit
  ```

- Avatar render (HeyGen):

  ```bash
  # dry-run: creates empty video.mp4 and render.json stub
  DRY_RUN=true python -m apps.cli.avatar render --week 5 --kind start-sit --script .out/week-5/Bijan_Robinson__start-sit.md --avatar-id test-avatar --outdir .out

  # live: requires HEYGEN_API_KEY in env or wiring to provide it
  python -m apps.cli.avatar render --week 5 --kind start-sit --script .out/week-5/Bijan_Robinson__start-sit.md --avatar-id real-avatar --outdir .out
  ```

- Full pipeline: generate scripts, optionally render and/or upload

  ```bash
  # Dry-run pipeline: generates scripts and placeholders only
  DRY_RUN=true python -m apps.cli.ff_post pipeline --week 5 --types "top-performers,waiver-wire" --no-upload --outdir .out

  # Pipeline with render but without upload
  DRY_RUN=true python -m apps.cli.ff_post pipeline --week 5 --types "top-performers" --render --no-upload --outdir .out

  # Pipeline with render and upload (live): requires TikTok tokens via env or flags
  python -m apps.cli.ff_post pipeline --week 5 --types "top-performers" --render --upload --outdir .out
  ```

1) Template locations and naming conventions

-------------------------------------------

- Canonical template directory used by the planner and CLI: `templates/script_templates/`.
- Legacy fallback directory: `prompts/templates/` (kept for backward compatibility).
- Template filenames are canonicalized by kind. Example mappings:

  - `start-sit` -> `start_sit.md` or `start-sit.md` in the template directories
  - `waiver-wire` -> `waiver-wire.md`
  - `top-performers` -> `top-performers.md`

- The planner exposes a resolver that prefers `templates/script_templates/<kind>.md` and falls back to `prompts/templates/<kind>.md`. If no file exists, a `default.md` in the canonical templates directory is used as the last-resort fallback.

1) Defaults & safe rendering

- Templates may include simple Python-style `{}` placeholders such as `{week}` and `{player}`. The rendering code uses a safe `.format_map()` helper that will leave missing placeholders blank rather than raising KeyError.
- Generated script filenames are deterministic: `{player_with_underscores}__{kind}.md` and are written under `.out/week-<N>/` by default.

1) Troubleshooting

- If a CLI complains about missing credentials in non-dry-run mode, check the corresponding env var in `.env.example` and set it in your environment or provide the value via CLI flags where supported.
- To inspect templates used for a kind, check:

  - `templates/script_templates/<kind>.md`
  - `prompts/templates/<kind>.md` (legacy)

That's it — use `DRY_RUN=true` liberally during development to avoid network calls while exercising the full file-writing and manifest behavior.
