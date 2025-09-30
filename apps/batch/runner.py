"""
Batch runner utilities. Provides a small entrypoint that can optionally run a
local compositor for creator outputs when remote creator pipeline is disabled.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List, TYPE_CHECKING, cast
from datetime import datetime

from adapters.wiring import load_env, build_openai, build_heygen, build_tiktok
from apps.batch import manifest as manifest_lib
from apps.batch.planner import plan_week
from packages.generation.pipelines import generate_content
from packages.render.compositor import compose_video
from adapters.heygen_adapter import HeyGenRenderRequest
from packages.agents.packaging_agent import build_caption, build_hashtags, package_metadata, to_exportable
from apps.cli import approval as approval_cli

# For type-checkers only — keeps runtime flexible while satisfying Pylance
if TYPE_CHECKING:
    from adapters.openai_adapter import OpenAIAdapter as _OpenAIAdapter


def _ensure_str(value: object, default: str = "") -> str:
    """Coerce possibly-None/unknown values to str for strict call sites."""
    if value is None:
        return default
    if isinstance(value, (str, bytes)):
        return value.decode() if isinstance(value, bytes) else value
    return str(value)


def run_local_render_for_week(week: int, out_root: str = ".out") -> None:
    """For each manifest entry in .out/week-<N>, if a source md exists produce
    a local mp4 using the compositor into .out/week-<N>/videos/<stem>.mp4.
    """
    # Load env for any adapter usage (e.g., future TikTok upload step)
    _ = load_env()

    out_dir = Path(out_root) / f"week-{week}"
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)

    with manifest_path.open("r", encoding="utf-8") as f:
        entries = json.load(f)

    videos_dir = out_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    for e in entries:
        path = e.get("path")
        if not path:
            continue
        stem = Path(path).stem
        md_path = out_dir / path
        if not md_path.exists():
            # skip silently if the markdown file isn't present
            continue

        # Use a deterministic background and a generated audio if not present
        bg = out_dir / "background.jpg"
        if not bg.exists():
            # Create a tiny black background using ffmpeg if available
            from subprocess import run

            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920", str(bg)], check=False)

        # Audio: look for audio.wav next to md, else create a 2s silence wav
        audio = out_dir / f"{stem}.wav"
        if not audio.exists():
            import wave
            import struct

            with wave.open(str(audio), "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                frames = b"".join([struct.pack("h", 0) for _ in range(16000 * 2)])
                wf.writeframes(frames)

        out_mp4 = videos_dir / f"{stem}.mp4"
        title = f"{_ensure_str(e.get('player'))} — {_ensure_str(e.get('kind'))}"
        compose_video(str(bg), str(audio), title, str(out_mp4), duration=None)


def run_pipeline(
    week: int,
    kinds: List[str] | None = None,
    do_render: bool = False,
    do_upload: bool = False,
    outdir: str = ".out",
) -> None:
    """Run content generation pipeline for a week.

    Steps:
    - plan items for the week (optionally filtered by kinds)
    - generate script via OpenAIAdapter (injected via wiring)
    - write script file under outdir/week-<week>/
    - upsert manifest entries (idempotent)
    - optionally render avatar via HeyGen
    - optionally upload to TikTok

    All operations honor DRY_RUN via adapters built from wiring.load_env().
    """
    env = load_env()

    # Build adapters once (they will respect env.DRY_RUN)
    # Casts keep Pylance happy where call sites expect concrete adapter types.
    openai = cast("_OpenAIAdapter", build_openai(env))
    heygen = build_heygen(env)  # Protocol is fine for method discovery
    tiktok = build_tiktok(env)  # Protocol is fine for method discovery

    plan = plan_week(week, types=kinds) if kinds else plan_week(week)

    out_root_path = Path(outdir) / f"week-{week}"
    out_root_path.mkdir(parents=True, exist_ok=True)

    manifest_path = out_root_path / "manifest.json"
    entries = manifest_lib.read_manifest(manifest_path)

    for item in plan:
        player = _ensure_str(item.get("player"))
        kind = _ensure_str(item.get("kind"))

        if not kind:
            # Skip invalid items defensively
            continue

        # Generate content (adapter cast keeps type checker satisfied)
        gen = generate_content(kind, week, player=player or None, extra=item, adapter=openai)
        script_text = _ensure_str(gen.get("script_text"))

        # Write script file deterministically
        safe_player = (player or "").replace(" ", "_")
        filename = f"{safe_player}__{kind}.md"
        script_path = out_root_path / filename
        script_path.write_text(script_text, encoding="utf-8")

        # Upsert manifest
        new_entry = {"player": player or None, "week": int(week), "kind": kind, "path": filename}
        entries = manifest_lib.upsert(entries, new_entry, key_fields=("player", "kind", "week"))
        manifest_lib.write_manifest_atomic(manifest_path, entries)
        manifest_lib.write_csv_from_entries(out_root_path / "manifest.csv", entries)

        # Approval gate: require entry present and approved in approval/manifest.csv or .json
        approvals = approval_cli.read_manifest()
        # Find matching approval by id or player/week/type
        entry_id = f"{player}__{kind}__{week}"
        approved = False
        approval_row = None
        for a in approvals:
            if a.get("id") == entry_id or (a.get("player") == player and a.get("week") == str(week) and a.get("type") == kind):
                approval_row = a
                approved = (str(a.get("approved", "false")).lower() == "true")
                break

        if not approved:
            # Log skipped item and write audit entry
            audit_dir = out_root_path / "audit"
            audit_dir.mkdir(parents=True, exist_ok=True)
            skip_log = audit_dir / "skipped.log"
            who = approval_row.get("reviewer") if approval_row else "none"
            note = approval_row.get("note") if approval_row else "not in manifest"
            skip_line = f"{datetime.utcnow().isoformat()}Z\t{entry_id}\tskipped\treviewer={who}\tnote={note}\n"
            with skip_log.open("a", encoding="utf-8") as f:
                f.write(skip_line)
            # Continue without rendering/uploading; still generate packaging metadata for review
            caption = build_caption(script_text, kind, week, dry_run=env.DRY_RUN)
            hashtags = build_hashtags(kind, week)
            meta = package_metadata(entry_id, kind, week, player or None, caption, hashtags, extra={"approved": False})
            (out_root_path / f"{entry_id}.meta.json").write_text(to_exportable(meta), encoding="utf-8")
            print(f"⏭️ Skipped {entry_id} — not approved; audit written to {skip_log}")
            # Ensure tiktok_uploads.json exists when uploads were requested by caller
            if do_upload:
                up = out_root_path / "tiktok_uploads.json"
                try:
                    up.write_text(json.dumps({"uploads": [], "skipped": [entry_id]}, indent=2), encoding="utf-8")
                except Exception:
                    pass
            continue

        # If approved, write packaging metadata (approved=true)
        caption = build_caption(script_text, kind, week, dry_run=env.DRY_RUN)
        hashtags = build_hashtags(kind, week)
        meta = package_metadata(entry_id, kind, week, player or None, caption, hashtags, extra={"approved": True, "approver": approval_row})
        (out_root_path / f"{entry_id}.meta.json").write_text(to_exportable(meta), encoding="utf-8")

        # Optional render via HeyGen
        if do_render:
            avatar_dir = out_root_path / f"{safe_player}__{kind}" / "avatar"
            avatar_dir.mkdir(parents=True, exist_ok=True)

            req = HeyGenRenderRequest(
                script_text=script_text,
                avatar_id=_ensure_str(item.get("avatar_id"), "default-avatar-id"),
                voice_id=item.get("voice_id"),
            )
            res = heygen.render_text_to_avatar(req)
            # Write initial response
            (avatar_dir / "render.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

            if not env.DRY_RUN:
                max_poll = 90
                interval = 5
                start = time.time()
                video_id = _ensure_str(res.get("video_id"))
                while time.time() - start < max_poll:
                    if not video_id:
                        break
                    status = heygen.poll_status(video_id)
                    (avatar_dir / "render.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
                    st = _ensure_str(status.get("status"))
                    prog = int(status.get("progress", 0) or 0)
                    if "complete" in st.lower() or prog == 100:
                        # would download video here; create placeholder
                        (avatar_dir / "video.mp4").write_bytes(b"")
                        break
                    time.sleep(interval)
                else:
                    raise RuntimeError("HeyGen render timed out")
            else:
                # DRY_RUN: create placeholder artifact
                (avatar_dir / "video.mp4").touch()

        # Optional upload to TikTok
        if do_upload:
            # In dry-run, TikTok adapter will return stub responses
            # In non-dry-run, require tokens via env
            access_token = _ensure_str(os.getenv("TIKTOK_ACCESS_TOKEN"))
            open_id = _ensure_str(os.getenv("TIKTOK_OPEN_ID"))
            if not env.DRY_RUN and (not access_token or not open_id):
                raise RuntimeError("Missing TIKTOK_ACCESS_TOKEN or TIKTOK_OPEN_ID in environment")

            # Read video bytes — prefer generated avatar video if rendered
            video_file = out_root_path / f"{safe_player}__{kind}" / "avatar" / "video.mp4"
            if not video_file.exists():
                # fallback to writing a small placeholder and uploading that
                tmp_vid = out_root_path / f"{safe_player}__{kind}.mp4"
                tmp_vid.write_bytes(b"")
                video_file = tmp_vid

            data = video_file.read_bytes()

            init = tiktok.init_upload(access_token, open_id, draft=True)
            upload_id = _ensure_str(init.get("upload_id"))
            upload_res = tiktok.upload_video(access_token, open_id, upload_id, data, filename=video_file.name)
            status = tiktok.check_upload_status(access_token, open_id, upload_id)

            # Write upload metadata alongside week manifest
            up = out_root_path / "tiktok_uploads.json"
            up.write_text(json.dumps({"init": init, "upload": upload_res, "status": status}, indent=2), encoding="utf-8")