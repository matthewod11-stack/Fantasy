"""CLI for HeyGen avatar rendering with DRY_RUN-friendly defaults."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer
from typer.main import get_command

from adapters.heygen_adapter import HeyGenRenderRequest
from adapters.wiring import build_heygen, load_env

app = typer.Typer(
    name="avatar",
    help="Render avatar videos using HeyGen",
    add_completion=False,
)

_DRY_VIDEO_ID = "dry-video-123"
_DEFAULT_AVATAR_ID = "heygen-default-avatar"


def _validate_week(week: int) -> None:
    if 1 <= week <= 18:
        return
    typer.echo("❌ Week must be between 1 and 18")
    raise typer.Exit(code=1)


def _load_script(path: Path) -> str:
    if not path.exists():
        typer.echo(f"❌ Script file not found: {path}")
        raise typer.Exit(code=1)
    text = path.read_text(encoding="utf-8").strip()
    if text:
        return text
    typer.echo("❌ Script file is empty")
    raise typer.Exit(code=1)


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_placeholder_video(path: Path) -> None:
    path.write_bytes(b"")


@app.command("render")
def render(
    week: int = typer.Option(..., "--week", "-w", help="NFL week (1-18)"),
    kind: str = typer.Option(..., "--kind", "-k", help="Content kind"),
    script: Path = typer.Option(..., "--script", "-s", help="Path to script file"),
    avatar_id: Optional[str] = typer.Option(None, "--avatar-id", "-a", help="HeyGen avatar ID"),
    voice_id: Optional[str] = typer.Option(None, "--voice-id", "-v", help="HeyGen voice ID"),
    outdir: Path = typer.Option(Path(".out"), "--outdir", "-o", help="Output directory"),
) -> None:
    """Render an avatar video from a script, respecting DRY_RUN."""

    _validate_week(week)
    script_text = _load_script(script)

    output_dir = outdir / f"week-{week}" / kind / "avatar"
    _ensure_directory(output_dir)

    typer.echo("🎬 Rendering avatar video...")

    env = load_env()
    adapter = build_heygen(env)
    request = HeyGenRenderRequest(
        script_text=script_text,
        avatar_id=avatar_id or _DEFAULT_AVATAR_ID,
        voice_id=voice_id,
    )

    render_path = output_dir / "render.json"
    video_path = output_dir / "video.mp4"

    if env.DRY_RUN:
        render_data = {
            "video_id": _DRY_VIDEO_ID,
            "avatar_id": request.avatar_id,
            "voice_id": request.voice_id,
            "kind": kind,
            "week": week,
            "dry_run": True,
        }
        _write_json(render_path, render_data)
        _write_placeholder_video(video_path)
        typer.echo("✅ Created dry-run video placeholder")
        typer.echo("✨ Avatar render complete!")
        return

    try:
        render_data = adapter.render_text_to_avatar(request)
    except Exception as exc:  # pragma: no cover - network failure safety
        typer.echo(f"❌ Avatar rendering failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    _write_json(render_path, render_data)
    if not video_path.exists():
        _write_placeholder_video(video_path)

    typer.echo("✨ Avatar render complete!")


@app.command(name="_noop", hidden=True)
def _noop() -> None:
    """Hidden no-op command to retain subcommand style for tests."""


cli = get_command(app)


if __name__ == "__main__":
    cli()
