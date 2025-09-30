"""
Fantasy football CLI tool for generating TikTok content.

Command-line interface for the Fantasy TikTok Engine API.
"""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path
from typing import Dict, Optional

import httpx
import typer

from apps.api.schemas import PRD_CONTENT_KINDS
from apps.batch import manifest as manifest_lib
from apps.batch.planner import plan_week
from apps.export.scheduler_export import generate_scheduler_manifest
from packages.agents.script_agent import render_script
from packages.generation.template_resolver import resolve_template, get_runtime_config
from packages.agents import data_agent
from adapters.wiring import load_env  # Ensure wiring is available for building adapters when needed
from apps.batch.runner import run_pipeline
from packages.utils.logging import get_logger

_log = get_logger("cli.ff_post")

app = typer.Typer(
    name="ff-post",
    help="Generate fantasy football content for TikTok",
    add_completion=False,
)

API_BASE_URL = "http://127.0.0.1:8000"


def _kind_alias_map() -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for kind in PRD_CONTENT_KINDS:
        aliases[kind] = kind
        aliases[kind.replace("-", "_")] = kind
        aliases[kind.replace("-", "")] = kind
        aliases[kind.replace("-", " ")] = kind
    # Friendly legacy shorthands and PRD aliases
    aliases["performers"] = "top-performers"
    aliases["busts"] = "biggest-busts"
    aliases["startsit"] = "start-sit"
    aliases["waiverwire"] = "waiver-wire"
    aliases["injurypivot"] = "injury-pivot"
    return aliases


KIND_ALIAS_MAP = _kind_alias_map()


def normalize_kind(value: str) -> str:
    token = (value or "").strip().lower()
    token = " ".join(token.split())  # collapse whitespace
    return KIND_ALIAS_MAP.get(token, token.replace("_", "-") if token else token)


@app.command()
def generate(
    player: str = typer.Option(None, "--player", "-p", help="Fantasy football player name"),
    week: Optional[int] = typer.Option(None, "--week", "-w", help="NFL week number (1-18)"),
    type: str = typer.Option(..., "--type", "-t", help="Type of content to generate (aliases allowed)"),
    strict: bool = typer.Option(False, "--strict/--no-strict", help="When strict, fail on scripts longer than 70 words; otherwise auto-trim"),
    with_stats: bool = typer.Option(os.getenv("SLEEPER_ENABLED", "false").lower() == "true", "--with-stats/--no-stats", help="Enable fetching live Sleeper stats (overrides SLEEPER_ENABLED env)"),
    batch_week: Optional[int] = typer.Option(None, "--batch-week", help="Generate a full batch for a week (produces multiple posts)"),
    players: Optional[str] = typer.Option(None, "--players", help="Comma-separated list of players for batch generation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Render templates locally and write outputs to .out/ without calling the API", envvar="DRY_RUN"),
    outdir: Optional[str] = typer.Option(None, "--outdir", "-o", help="Output root directory (defaults to .out/week-<N> when omitted)"),
):
    """Generate fantasy football content for a specific player and week."""

    # Load env once for any downstream adapter usage (future API or local integrations)
    load_env()

    # Ensure Data Agent honor the CLI override for Sleeper usage
    try:
        data_agent.SLEEPER_ENABLED = bool(with_stats)
    except Exception:
        pass

    # Snapshot runtime config for CLI-driven commands
    cfg = get_runtime_config()
    # Allow CLI flag to override env-derived DRY_RUN
    cfg.DRY_RUN = bool(dry_run)

    canonical_kind = normalize_kind(type)
    if canonical_kind not in PRD_CONTENT_KINDS:
        typer.echo(f"❌ Unsupported kind '{type}'. Try one of: {', '.join(PRD_CONTENT_KINDS)}", err=True)
        raise typer.Exit(code=1)

    if batch_week is not None:
        _generate_batch(
            canonical_kind=canonical_kind,
            batch_week=batch_week,
            players_arg=players,
            strict=strict,
            dry_run=dry_run,
            default_player=player,
        )
        return

    if week is None or not (1 <= week <= 18):
        typer.echo("❌ Week must be between 1 and 18 (or use --batch-week)", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"🏈 Generating {canonical_kind} content for {player} (Week {week})... (with-stats={with_stats})")
    payload = {"player": player, "week": week, "kind": canonical_kind}

    try:
        if dry_run:
            _do_local_render(payload, out_dir=outdir)
        else:
            _call_generate_api(payload, strict=strict)
    except httpx.ConnectError:
        typer.echo("❌ Cannot connect to API server", err=True)
        typer.echo("💡 Is the API running? Try: make up", err=True)
        raise typer.Exit(code=1)
    except httpx.TimeoutException:
        typer.echo("❌ API request timed out", err=True)
        typer.echo("💡 The server might be overloaded. Try again in a moment.", err=True)
        raise typer.Exit(code=1)
    except Exception as exc:  # pragma: no cover - CLI safety net
        typer.echo(f"❌ Unexpected error: {exc}", err=True)
        raise typer.Exit(code=1)


def _generate_batch(
    canonical_kind: str,
    batch_week: int,
    players_arg: Optional[str],
    strict: bool,
    dry_run: bool,
    default_player: Optional[str],
) -> None:
    typer.echo(f"📦 Generating batch for week {batch_week} (type: {canonical_kind})")
    if players_arg:
        batch_players = [p.strip() for p in players_arg.split(",") if p.strip()]
    else:
        batch_players = [default_player] if default_player else ["Sample Player"]

    for name in batch_players:
        payload = {"player": name, "week": batch_week, "kind": canonical_kind}
        if dry_run:
            _do_local_render(payload)
        else:
            _call_generate_api(payload, strict=strict)
    typer.echo("✅ Batch generation complete")


def _call_generate_api(payload: Dict[str, object], strict: bool) -> None:
    headers = {"X-Guardrails-Strict": "true" if strict else "false"}
    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{API_BASE_URL}/generate", json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if data.get("ok"):
            typer.echo("\n✅ Content generated successfully!\n")
            typer.echo("📝 Generated Script:")
            typer.echo("-" * 50)
            typer.echo(data.get("script", ""))
            typer.echo("-" * 50)
            return

    if response.status_code == 422:
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = response.text
        typer.echo(f"❌ Guardrail blocked generation: {detail}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"❌ API request failed with status {response.status_code}", err=True)
    try:
        typer.echo(response.json(), err=True)
    except Exception:
        typer.echo(response.text, err=True)
    raise typer.Exit(code=1)


@app.command()
def health():
    """Check if the API server is running and healthy."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            typer.echo("✅ API server is healthy!")
        else:
            typer.echo(f"❌ API health check failed (status: {response.status_code})", err=True)
            raise typer.Exit(code=1)
    except httpx.ConnectError:
        typer.echo("❌ Cannot connect to API server", err=True)
        typer.echo("💡 Start the server with: make up", err=True)
        raise typer.Exit(code=1)


@app.command()
def batch(
    action: str = typer.Argument(..., help="Action to perform: plan"),
    week: int = typer.Option(..., "--week", help="Week number to plan for"),
    types: Optional[str] = typer.Option(None, "--types", help="Comma-separated list of types to include"),
):
    """Batch operations: plan"""
    if action != "plan":
        typer.echo("Only 'plan' action is supported", err=True)
        raise typer.Exit(code=1)

    types_list = [normalize_kind(t) for t in types.split(",")] if types else None
    plan = plan_week(week, types=types_list)

    out_dir = Path(f".out/week-{week}")
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "plan.json"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    typer.echo(f"Wrote plan to {plan_path}")


@app.command()
def pipeline(
    week: int = typer.Option(..., "--week", help="Week number to run the pipeline for"),
    types: Optional[str] = typer.Option(None, "--types", help="Comma-separated list of types to include"),
    render: bool = typer.Option(True, "--render/--no-render", help="Whether to render avatars"),
    upload: bool = typer.Option(False, "--upload/--no-upload", help="Whether to upload to TikTok"),
    outdir: Optional[str] = typer.Option(None, "--outdir", help="Output root directory"),
):
    """Run the content generation pipeline for a week.

    The pipeline will generate scripts for planned items and optionally render
    avatar videos and upload them to TikTok. DRY_RUN is respected via env.
    """
    kinds_list = [normalize_kind(t.strip()) for t in types.split(",")] if types else None
    out = outdir or ".out"
    try:
        _log.info("pipeline.start", extra={"data": {"week": week, "kinds": kinds_list, "render": render, "upload": upload}})
        run_pipeline(week=week, kinds=kinds_list, do_render=render, do_upload=upload, outdir=out)
        _log.info("pipeline.complete", extra={"data": {"week": week}})
        typer.echo("✅ Pipeline completed")
    except Exception as exc:
        typer.echo(f"❌ Pipeline failed: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command()
def export_scheduler(
    week: int = typer.Option(..., "--week", help="Week number to export"),
    start_date: str = typer.Option(..., "--start-date", help="YYYY-MM-DD for the first day to schedule"),
    timezone: str = typer.Option("America/Los_Angeles", "--timezone", help="Timezone name"),
):
    """Export a scheduler CSV for a planned week."""
    try:
        csv_path = generate_scheduler_manifest(week, start_date, timezone)
        typer.echo(f"Wrote scheduler manifest: {csv_path}")
    except Exception as exc:
        typer.echo(f"Failed to generate scheduler manifest: {exc}", err=True)
        raise typer.Exit(code=1)


def _do_local_render(payload: Dict[str, object], out_dir: Optional[str] = None) -> None:
    out_dir_path = Path(out_dir) if out_dir else Path(f".out/week-{payload.get('week')}")
    out_dir_path.mkdir(parents=True, exist_ok=True)

    player = str(payload.get("player") or "Player")
    kind = str(payload.get("kind") or "unknown")

    template = _resolve_template(kind)
    if template is None:
        script = f"[No template found for {kind}] {player} — week {payload.get('week')}"
    else:
        context = {"player": player, "week": payload.get("week"), "kind": kind}
        try:
            script = render_script(kind=kind, context=context, template_path=str(template))
        except Exception:
            script = f"[Render failed for {player} / {kind}]"

    safe_player = player.replace(" ", "_")
    output_file = out_dir_path / f"{safe_player}__{kind}.md"
    output_file.write_text(script, encoding="utf-8")

    manifest_json = out_dir_path / "manifest.json"
    manifest_csv = out_dir_path / "manifest.csv"

    existing = manifest_lib.read_manifest(manifest_json)
    new_entry = {"player": player, "week": payload.get("week"), "kind": kind, "path": output_file.name}
    entries = manifest_lib.upsert(existing, new_entry, key_fields=("player", "kind", "week"))
    manifest_lib.write_manifest_atomic(manifest_json, entries)
    manifest_lib.write_csv_from_entries(manifest_csv, entries)

    typer.echo(f"manifest: upsert — {player}, {kind}, week {payload.get('week')}")
    typer.echo(f"Wrote: {output_file} and updated manifest")


def _resolve_template(kind: str) -> Optional[Path]:
    # Delegate to the shared resolver for deterministic behavior across CLI/API/pipelines
    return resolve_template(kind)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        first = sys.argv[1]
        allowed = {
            "generate",
            "health",
            "batch",
            "pipeline",
            "export-scheduler",
            "help",
            "--help",
            "-h",
        }
        if first.startswith("-") or first not in allowed:
            sys.argv.insert(1, "generate")
    app()
