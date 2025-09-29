"""
Fantasy football CLI tool for generating TikTok content.

Command-line interface for the Fantasy TikTok Engine API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Optional

import httpx
import typer

from apps.api.schemas import PRD_CONTENT_KINDS
from apps.batch import manifest as manifest_lib
from apps.batch.planner import plan_week
from apps.export.scheduler_export import generate_scheduler_manifest
from packages.agents.script_agent import render_script

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
    strict: bool = typer.Option(True, "--strict/--no-strict", help="When strict, fail on scripts longer than 70 words; otherwise auto-trim"),
    batch_week: Optional[int] = typer.Option(None, "--batch-week", help="Generate a full batch for a week (produces multiple posts)"),
    players: Optional[str] = typer.Option(None, "--players", help="Comma-separated list of players for batch generation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Render templates locally and write outputs to .out/ without calling the API"),
):
    """Generate fantasy football content for a specific player and week."""

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

    typer.echo(f"🏈 Generating {canonical_kind} content for {player} (Week {week})...")
    payload = {"player": player, "week": week, "kind": canonical_kind}

    try:
        if dry_run:
            _do_local_render(payload)
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
    from apps.api.main import TEMPLATE_FILENAME_OVERRIDES, TEMPLATE_ROOT, LEGACY_TEMPLATE_ROOT  # lazy import to avoid CLI start-up cost

    override = TEMPLATE_FILENAME_OVERRIDES.get(kind)
    candidates = []
    if override:
        candidates.append(TEMPLATE_ROOT / override)
    candidates.append(TEMPLATE_ROOT / f"{kind}.md")
    candidates.append(TEMPLATE_ROOT / f"{kind.replace('-', '_')}.md")
    if override:
        candidates.append(LEGACY_TEMPLATE_ROOT / override)
    candidates.append(LEGACY_TEMPLATE_ROOT / f"{kind}.md")
    candidates.append(LEGACY_TEMPLATE_ROOT / f"{kind.replace('-', '_')}.md")

    for path in candidates:
        if path.exists():
            return path
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        first = sys.argv[1]
        if first.startswith("-") or first not in ("generate", "health", "--help", "-h", "help", "batch", "export-scheduler"):
            sys.argv.insert(1, "generate")
    app()
