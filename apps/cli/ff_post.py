"""
Fantasy football CLI tool for generating TikTok content.

Command-line interface for the Fantasy TikTok Engine API.
"""

import sys
from typing import Literal, Optional, List
import typer
import httpx
import os
import json
import csv
from pathlib import Path
from apps.batch.planner import plan_week
from apps.batch import manifest as manifest_lib
from packages.agents.script_agent import render_script
from apps.export.scheduler_export import generate_scheduler_manifest

# Create Typer app
app = typer.Typer(
    name="ff-post",
    help="Generate fantasy football content for TikTok",
    add_completion=False,
)

# API configuration
API_BASE_URL = "http://127.0.0.1:8000"

# Alias map for PRD-friendly shorthand types -> canonical kinds
# CLI normalization: Accept both hyphenated and underscored inputs,
# store canonical underscored forms, convert to API hyphenated forms
TYPE_ALIASES = {
    "performers": "top-performers",
    "busts": "biggest-busts",
    "start_sit": "start_sit",
    "start-sit": "start_sit",
    "waiver_wire": "waiver_wire",
    "waiver-wire": "waiver_wire",
    "injury_pivot": "injury-pivot",
    "injury-pivot": "injury-pivot",
    "trade_thermometer": "trade-thermometer",
    "trade-thermometer": "trade-thermometer",
    "matchup_exploits": "matchup-exploits",
    "matchup-exploits": "matchup-exploits",
}


def normalize_kind(value: str) -> str:
    """Normalize user-provided kind strings to a canonical form."""
    return (value or "").strip().lower().replace("-", "_")


@app.command()
def generate(
    player: str = typer.Option(None, "--player", "-p", help="Fantasy football player name"),
    week: Optional[int] = typer.Option(None, "--week", "-w", help="NFL week number (1-18)"),
    type: str = typer.Option(..., "--type", "-t", help="Type of content to generate (aliases allowed)"),
    strict: bool = typer.Option(True, "--strict/--no-strict", help="When strict, fail on scripts longer than 70 words; otherwise auto-trim"),
    batch_week: Optional[int] = typer.Option(None, "--batch-week", help="Generate a full batch for a week (produces multiple posts)"),
    players: Optional[str] = typer.Option(None, "--players", help="Comma-separated list of players for batch generation (comma-separated string)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Render templates locally and write outputs to .out/ without calling the API"),
):
    """
    Generate fantasy football content for a specific player and week.
    
    Examples:
        ff-post --player "Bijan Robinson" --week 5 --type start-sit
        ff-post -p "Justin Jefferson" -w 3 -t waiver-wire
    """
    # Resolve type aliases
    kind_input = normalize_kind(type)
    kind = TYPE_ALIASES.get(kind_input, kind_input)
    canonical_kind = kind
    kind_display = canonical_kind.replace("_", "-")

    # If batch_week specified, generate a batch
    if batch_week is not None:
        week_to_use = batch_week
        typer.echo(f"📦 Generating batch for week {week_to_use} (type: {kind_display})")
        # In batch mode, players can be provided as a comma-separated string; fallback to single player if provided
        if players:
            batch_players = [p.strip() for p in players.split(",") if p.strip()]
        else:
            batch_players = ([player] if player else ["Sample Player"])
        for p in batch_players:
            payload = {"player": p.strip(), "week": week_to_use, "kind": canonical_kind, "strict": strict}
            if dry_run:
                _do_local_render(payload, out_dir=f".out/week-{week_to_use}")
            else:
                _call_generate_api(payload, strict=strict)
        typer.echo("✅ Batch generation complete")
        return

    # Validate week number for single-run
    if week is None or not (1 <= week <= 18):
        typer.echo("❌ Week must be between 1 and 18 (or use --batch-week)", err=True)
        sys.exit(1)

    kind = canonical_kind

    # Prepare request payload
    payload = {"player": player, "week": week, "kind": kind, "strict": strict}
    typer.echo(f"🏈 Generating {kind_display} content for {player} (Week {week})...")

    try:
        if dry_run:
            out_dir = f".out/week-{week}"
            _do_local_render(payload, out_dir=out_dir)
        else:
            _call_generate_api(payload, strict=strict)
    except httpx.ConnectError:
        typer.echo("❌ Cannot connect to API server", err=True)
        typer.echo("💡 Is the API running? Try: make up", err=True)
        sys.exit(1)
    except httpx.TimeoutException:
        typer.echo("❌ API request timed out", err=True)
        typer.echo("💡 The server might be overloaded. Try again in a moment.", err=True)
        sys.exit(1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {str(e)}", err=True)
        sys.exit(1)


def _call_generate_api(payload: dict, strict: bool = True):
    """Helper to call the /generate endpoint and print results."""
    try:
        api_payload = dict(payload)
        if "kind" in api_payload and api_payload["kind"]:
            api_payload["kind"] = api_payload["kind"].replace("_", "-")
        with httpx.Client(timeout=30.0) as client:
            # Propagate guardrail preference to the API
            # The API reads GUARDRAILS_LENGTH_MODE env var; we send a hint header for transparency
            headers = {"X-Guardrails-Strict": "1" if strict else "0"}
            response = client.post(f"{API_BASE_URL}/generate", json=api_payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                typer.echo("\n✅ Content generated successfully!\n")
                typer.echo("📝 Generated Script:")
                typer.echo("-" * 50)
                typer.echo(data["script"])
                typer.echo("-" * 50)
            else:
                typer.echo("❌ Content generation failed", err=True)
        else:
            typer.echo(f"❌ API request failed with status {response.status_code}", err=True)
            if response.status_code == 422:
                typer.echo("💡 Check your input parameters", err=True)
            elif response.status_code == 400:
                # Provide friendly guidance on guardrails
                try:
                    detail = response.json().get("detail", "")
                except Exception:
                    detail = response.text
                typer.echo(f"💡 Guardrail blocked generation: {detail}", err=True)
    except httpx.ConnectError:
        typer.echo("❌ Cannot connect to API server", err=True)
        typer.echo("💡 Is the API running? Try: make up", err=True)


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
            sys.exit(1)
            
    except httpx.ConnectError:
        typer.echo("❌ Cannot connect to API server", err=True)
        typer.echo("💡 Start the server with: make up", err=True)
        sys.exit(1)
    except Exception as e:
        typer.echo(f"❌ Health check failed: {str(e)}", err=True)
        sys.exit(1)


@app.command()
def batch(
    action: str = typer.Argument(..., help="Action to perform: plan"),
    week: int = typer.Option(..., "--week", help="Week number to plan for"),
    types: Optional[str] = typer.Option(None, "--types", help="Comma-separated list of types to include"),
):
    """Batch operations: plan

    Examples:
        ff-post batch plan --week 5 --types "performers,busts,waiver-wire"
    """
    if action != "plan":
        typer.echo("Only 'plan' action is supported", err=True)
        raise typer.Exit(code=1)

    types_list = [t.strip() for t in types.split(",")] if types else None
    plan = plan_week(week, types=types_list)

    out_dir = Path(f".out/week-{week}")
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "plan.json"
    with plan_path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    typer.echo(f"Wrote plan to {plan_path}")



def _do_local_render(payload: dict, out_dir: str):
    """Render a template locally (no network) and write script.md.

    Writes:
      - .out/week-<N>/player__kind.md (script content)
      - .out/week-<N>/manifest.json (list of entries)
      - .out/week-<N>/manifest.csv (flat CSV)
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    player = payload.get("player")
    week = payload.get("week")
    kind = payload.get("kind")

    def find_template(kind: str):
        cand = os.path.join("templates", "script_templates", f"{kind}.md")
        if os.path.exists(cand):
            return cand
        legacy = os.path.join("prompts", "templates", f"{kind}.md")
        if os.path.exists(legacy):
            return legacy
        alias_map = {"top-performers": "top-performers.md", "start-sit": "start_sit.md", "waiver-wire": "waiver_wire.md"}
        fname = alias_map.get(kind)
        if fname:
            c2 = os.path.join("templates", "script_templates", fname)
            if os.path.exists(c2):
                return c2
        return None

    template_path = find_template(kind)
    if template_path is None:
        script = f"[No template found for {kind}] {player} — week {week}"
    else:
        context = {"player": player, "week": week, "kind": kind}
        try:
            script = render_script(kind=kind, context=context, template_path=template_path)
        except Exception:
            script = f"[Render failed for {player} / {kind}]"

    safe_player = player.replace(" ", "_") if player else "player"
    filename = f"{safe_player}__{kind}.md"
    file_path = out_path / filename
    with file_path.open("w", encoding="utf-8") as f:
        f.write(script)

    manifest_json = out_path / "manifest.json"
    manifest_csv = out_path / "manifest.csv"

    existing = manifest_lib.read_manifest(manifest_json)
    new_entry = {"player": player, "week": week, "kind": kind, "path": str(file_path.name)}
    # Determine whether this will replace an existing entry
    before_keys = {manifest_lib.make_key(e, ("player", "kind", "week")) for e in existing}
    new_key = manifest_lib.make_key(new_entry, ("player", "kind", "week"))

    entries = manifest_lib.upsert(existing, new_entry, key_fields=("player", "kind", "week"))
    manifest_lib.write_manifest_atomic(manifest_json, entries)
    manifest_lib.write_csv_from_entries(manifest_csv, entries)

    action = "replaced" if new_key in before_keys else "inserted"
    typer.echo(f"manifest: upsert ({action}) — {new_entry.get('player')}, {new_entry.get('kind')}, week {new_entry.get('week')}")
    typer.echo(f"Wrote: {file_path} and updated manifest")



@app.command()
def export_scheduler(
    week: int = typer.Option(..., "--week", help="Week number to export"),
    start_date: str = typer.Option(..., "--start-date", help="YYYY-MM-DD for the first day to schedule"),
    timezone: str = typer.Option(os.getenv("SCHEDULER_TZ", "America/Los_Angeles"), "--timezone", help="Timezone name"),
):
    """Export a scheduler CSV for a planned week."""
    try:
        csvp = generate_scheduler_manifest(week, start_date, timezone)
        typer.echo(f"Wrote scheduler manifest: {csvp}")
    except Exception as e:
        typer.echo(f"Failed to generate scheduler manifest: {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    # Backwards-compatible behavior: allow calling the module with flags
    # (e.g. `python -m apps.cli.ff_post --player X --week 5 --type start-sit`)
    import sys

    if len(sys.argv) > 1:
        first = sys.argv[1]
        # If the first argument is a flag (starts with '-') or a value,
        # assume the user intended to call the default 'generate' command.
        if first.startswith("-") or first not in ("generate", "health", "--help", "-h", "help", "batch", "export-scheduler"):
            sys.argv.insert(1, "generate")

    app()
