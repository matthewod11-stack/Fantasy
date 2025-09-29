"""CLI for uploading TikTok drafts with DRY_RUN support."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional

import typer
from typer.main import get_command

from adapters.wiring import build_tiktok, load_env

app = typer.Typer(
    name="tiktok-upload",
    help="Upload TikTok drafts using the configured adapter",
    add_completion=False,
)

_DRY_UPLOAD_ID = "dry-upload-123"
_DRY_STATUS = "uploaded(dry)"


def _validate_week(week: int) -> None:
    if 1 <= week <= 18:
        return
    typer.echo("❌ Week must be between 1 and 18")
    raise typer.Exit(code=1)


def _ensure_file_exists(file_path: Path) -> None:
    if file_path.exists() and file_path.is_file():
        return
    typer.echo(f"❌ File not found: {file_path}")
    raise typer.Exit(code=1)


def _extract_upload_id(payload: Mapping[str, Any]) -> str:
    candidate = payload.get("upload_id")
    if isinstance(candidate, str) and candidate:
        return candidate
    data = payload.get("data")
    if isinstance(data, Mapping):
        nested = data.get("upload_id")
        if isinstance(nested, str) and nested:
            return nested
    return ""


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _sidecar_path(file_path: Path) -> Path:
    return file_path.with_name(f"{file_path.name}.upload.json")


@app.command("upload")
def upload(
    file: Path = typer.Option(..., "--file", "-f", help="Path to .mp4 to upload"),
    week: int = typer.Option(..., "--week", "-w", help="NFL week (1-18)"),
    kind: str = typer.Option(..., "--kind", "-k", help="Content kind slug"),
    access_token: Optional[str] = typer.Option(None, "--access-token", help="TikTok OAuth access token"),
    open_id: Optional[str] = typer.Option(None, "--open-id", help="TikTok user open_id"),
    outdir: Path = typer.Option(Path(".out"), "--outdir", "-o", help="Output directory for upload metadata"),
) -> None:
    """Upload a video file as a TikTok draft, respecting DRY_RUN."""

    _validate_week(week)
    _ensure_file_exists(file)

    env = load_env()
    adapter = build_tiktok(env)

    canonical_dir = outdir / f"week-{week}" / kind / "tiktok"
    canonical_path = canonical_dir / "upload.json"
    sidecar_path = _sidecar_path(file)

    if env.DRY_RUN:
        payload = {
            "upload_id": _DRY_UPLOAD_ID,
            "status": _DRY_STATUS,
            "file": str(file),
            "week": week,
            "kind": kind,
            "dry_run": True,
        }
        _write_json(canonical_path, payload)
        _write_json(sidecar_path, payload)
        typer.echo(f"✅ Dry-run upload artifacts → {canonical_path}")
        return

    resolved_access = access_token or os.getenv("TIKTOK_ACCESS_TOKEN")
    resolved_open_id = open_id or os.getenv("TIKTOK_OPEN_ID")
    if not resolved_access or not resolved_open_id:
        typer.echo(
            "❌ Missing --access-token/--open-id (or env TIKTOK_ACCESS_TOKEN/TIKTOK_OPEN_ID)",
            err=True,
        )
        raise typer.Exit(code=1)

    video_bytes = file.read_bytes()

    try:
        typer.echo("🚀 Initializing upload (draft)...")
        init_response = adapter.init_upload(resolved_access, resolved_open_id, draft=True)
        upload_id = _extract_upload_id(init_response)
        if not upload_id:
            typer.echo("❌ Upload init did not return an upload_id", err=True)
            raise typer.Exit(code=1)

        typer.echo(f"⬆️  Uploading {file.name}...")
        upload_response = adapter.upload_video(
            resolved_access,
            resolved_open_id,
            upload_id,
            video_bytes,
            filename=file.name,
        )

        typer.echo("🔍 Checking upload status...")
        status_response = adapter.check_upload_status(resolved_access, resolved_open_id, upload_id)
    except Exception as exc:  # pragma: no cover - network failure safety
        typer.echo(f"❌ TikTok upload failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    payload: Mapping[str, Any] = {
        "upload_id": upload_id,
        "init": init_response,
        "upload": upload_response,
        "status": status_response,
        "file": str(file),
        "week": week,
        "kind": kind,
    }
    _write_json(canonical_path, payload)
    _write_json(sidecar_path, payload)

    typer.echo(f"✅ TikTok upload artifacts → {canonical_path}")


@app.command(name="_noop", hidden=True)
def _noop() -> None:
    """Hidden no-op command to retain subcommand style for tests."""


cli = get_command(app)


if __name__ == "__main__":
    cli()
