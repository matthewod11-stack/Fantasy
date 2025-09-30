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
from dataclasses import dataclass, asdict
import json as _json
import logging
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PlanRecord:
    week: int
    kinds: list | None
    items: list


@dataclass
class GenerateRecord:
    entry_id: str
    player: str | None
    kind: str
    week: int
    script_path: str
    script_text: str


@dataclass
class ApproveRecord:
    entry_id: str
    approved: bool
    approver: dict | None


@dataclass
class RenderRecord:
    entry_id: str
    avatar_dir: str
    video_path: str | None


@dataclass
class PublishRecord:
    entry_id: str
    upload_meta: dict | None


def _emit_event(name: str, payload: Any) -> None:
    """Emit a structured event to logs (JSON)."""
    try:
        if hasattr(payload, "__dataclass_fields__"):
            payload_obj = asdict(payload)
        else:
            payload_obj = payload
        rec = {"event": name, "payload": payload_obj}
        # Use logger.info so it's easy to capture in tests or logs
        logger.info(_json.dumps(rec, ensure_ascii=False))
    except Exception:
        # Best-effort: fallback to plain print
        print(_json.dumps({"event": name, "payload": str(payload)}))

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
    _emit_event("planned", PlanRecord(week=week, kinds=kinds or [], items=plan))

    out_root_path = Path(outdir) / f"week-{week}"
    out_root_path.mkdir(parents=True, exist_ok=True)

    manifest_path = out_root_path / "manifest.json"
    entries = manifest_lib.read_manifest(manifest_path)

    for item in plan:
        # Plan-level values
        player = _ensure_str(item.get("player"))
        kind = _ensure_str(item.get("kind"))

        if not kind:
            continue

        # generate
        gen_rec = generate_step(item, week, out_root_path, openai)
        _emit_event("generated", gen_rec)

        # upsert manifest and write CSV (idempotent)
        new_entry = {"player": gen_rec.player or None, "week": int(week), "kind": gen_rec.kind, "path": Path(gen_rec.script_path).name}
        entries = manifest_lib.upsert(entries, new_entry, key_fields=("player", "kind", "week"))
        manifest_lib.write_manifest_atomic(manifest_path, entries)
        manifest_lib.write_csv_from_entries(out_root_path / "manifest.csv", entries)

        # approval
        approve_rec = approve_gate(gen_rec, week, out_root_path)
        _emit_event("approved", approve_rec)
        if not approve_rec.approved:
            # write metadata for review and continue
            caption = build_caption(gen_rec.script_text, gen_rec.kind, gen_rec.week, dry_run=env.DRY_RUN)
            hashtags = build_hashtags(gen_rec.kind, gen_rec.week)
            meta = package_metadata(approve_rec.entry_id, gen_rec.kind, gen_rec.week, gen_rec.player or None, caption, hashtags, extra={"approved": False})
            (out_root_path / f"{approve_rec.entry_id}.meta.json").write_text(to_exportable(meta), encoding="utf-8")
            # ensure tiktok uploads file present if requested
            if do_upload:
                up = out_root_path / "tiktok_uploads.json"
                try:
                    up.write_text(_json.dumps({"uploads": [], "skipped": [approve_rec.entry_id]}, indent=2), encoding="utf-8")
                except Exception:
                    pass
            continue

        # approved -> package metadata
        caption = build_caption(gen_rec.script_text, gen_rec.kind, gen_rec.week, dry_run=env.DRY_RUN)
        hashtags = build_hashtags(gen_rec.kind, gen_rec.week)
        meta = package_metadata(approve_rec.entry_id, gen_rec.kind, gen_rec.week, gen_rec.player or None, caption, hashtags, extra={"approved": True, "approver": approve_rec.approver})
        (out_root_path / f"{approve_rec.entry_id}.meta.json").write_text(to_exportable(meta), encoding="utf-8")

        # render
        render_rec = None
        if do_render:
            render_rec = render_step(gen_rec, item, out_root_path, heygen, env)
            _emit_event("rendered", render_rec)

        # publish
        publish_rec = None
        if do_upload:
            publish_rec = publish_step(gen_rec, out_root_path, tiktok, env)
            _emit_event("published", publish_rec)


def generate_step(item: dict, week: int, out_root_path: Path, openai_adapter) -> GenerateRecord:
    """Generate script text for a plan item and write deterministic script file.

    Returns a GenerateRecord.
    """
    player = _ensure_str(item.get("player"))
    kind = _ensure_str(item.get("kind"))
    gen = generate_content(kind, week, player=player or None, extra=item, adapter=openai_adapter)
    script_text = _ensure_str(gen.get("script_text"))

    safe_player = (player or "").replace(" ", "_")
    filename = f"{safe_player}__{kind}.md"
    script_path = out_root_path / filename
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_text, encoding="utf-8")

    entry_id = f"{player}__{kind}__{week}"
    return GenerateRecord(entry_id=entry_id, player=player or None, kind=kind, week=int(week), script_path=str(script_path), script_text=script_text)


def approve_gate(gen_rec: GenerateRecord, week: int, out_root_path: Path) -> ApproveRecord:
    """Check approvals and write audit on skip. Returns ApproveRecord.
    This function is deterministic and idempotent.
    """
    approvals = approval_cli.read_manifest()
    entry_id = gen_rec.entry_id
    approved = False
    approval_row = None
    for a in approvals:
        # Accept explicit id match or a row matching player/week/type
        if a.get("id") == entry_id or (a.get("player") == gen_rec.player and a.get("week") == str(week) and a.get("type") == gen_rec.kind):
            approval_row = a
            # Normalize approved values strictly to boolean based on common CSV values
            approved = str(a.get("approved", "false")).strip().lower() in ("1", "true", "yes")
            # normalize/augment approval_row for structured logs
            approval_row = {
                "id": a.get("id", ""),
                "type": a.get("type", ""),
                "player": a.get("player", ""),
                "week": a.get("week", ""),
                "approved": "true" if approved else "false",
                "reviewer": a.get("reviewer") or "",
                "note": a.get("note") or "",
                "updated_at": a.get("updated_at") or "",
            }
            break

    if not approved:
        audit_dir = out_root_path / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        skip_log = audit_dir / "skipped.log"
        who = approval_row.get("reviewer") if approval_row else "none"
        note = approval_row.get("note") if approval_row else "not in manifest"
        # Write structured JSON log line per skip for easier parsing
        skip_entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "entry_id": entry_id,
            "action": "skipped",
            "reviewer": who,
            "note": note,
        }
        with skip_log.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(skip_entry, ensure_ascii=False) + "\n")
    return ApproveRecord(entry_id=entry_id, approved=approved, approver=approval_row)


def render_step(gen_rec: GenerateRecord, item: dict, out_root_path: Path, heygen, env) -> RenderRecord:
    """Render an avatar video from script_text. Returns RenderRecord.
    Creates placeholder artifacts in DRY_RUN.
    """
    player = gen_rec.player or ""
    safe_player = player.replace(" ", "_")
    avatar_dir = out_root_path / f"{safe_player}__{gen_rec.kind}" / "avatar"
    avatar_dir.mkdir(parents=True, exist_ok=True)

    req = HeyGenRenderRequest(
        script_text=gen_rec.script_text,
        avatar_id=_ensure_str(item.get("avatar_id"), "default-avatar-id"),
        voice_id=item.get("voice_id"),
    )
    res = heygen.render_text_to_avatar(req)
    (avatar_dir / "render.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

    video_path = None
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
                (avatar_dir / "video.mp4").write_bytes(b"")
                video_path = str(avatar_dir / "video.mp4")
                break
            time.sleep(interval)
        else:
            raise RuntimeError("HeyGen render timed out")
    else:
        (avatar_dir / "video.mp4").touch()
        video_path = str(avatar_dir / "video.mp4")

    return RenderRecord(entry_id=gen_rec.entry_id, avatar_dir=str(avatar_dir), video_path=video_path)


def publish_step(gen_rec: GenerateRecord, out_root_path: Path, tiktok, env) -> PublishRecord:
    """Upload the video to TikTok (or dry-run stub). Returns PublishRecord.
    Writes tiktok_uploads.json deterministically.
    """
    player = gen_rec.player or ""
    safe_player = player.replace(" ", "_")
    video_file = out_root_path / f"{safe_player}__{gen_rec.kind}" / "avatar" / "video.mp4"
    if not video_file.exists():
        tmp_vid = out_root_path / f"{safe_player}__{gen_rec.kind}.mp4"
        tmp_vid.write_bytes(b"")
        video_file = tmp_vid

    data = video_file.read_bytes()

    # Read generated metadata to confirm explicit publish target is present
    meta_path = out_root_path / f"{gen_rec.entry_id}.meta.json"
    if not meta_path.exists():
        if not env.DRY_RUN:
            raise RuntimeError(f"Missing metadata for {gen_rec.entry_id}; refusing to publish")
        meta = {}
    else:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            raise RuntimeError(f"Malformed metadata for {gen_rec.entry_id}; refusing to publish")
    # If live run, require explicit publish_target in metadata to avoid accidental publishes
    publish_target = meta.get("publish_target") if isinstance(meta, dict) else None
    if not env.DRY_RUN and not publish_target:
        raise RuntimeError(f"No publish_target in metadata for {gen_rec.entry_id}; publishing is blocked")
    # Idempotency: check uploads file and skip if already uploaded
    up = out_root_path / "tiktok_uploads.json"
    existing = {"uploads": [], "skipped": []}
    if up.exists():
        try:
            existing = json.loads(up.read_text(encoding="utf-8"))
        except Exception:
            existing = {"uploads": [], "skipped": []}
    # If an upload record for this entry exists, return it and avoid duplicate upload
    for u in existing.get("uploads", []):
        if u.get("entry_id") == gen_rec.entry_id:
            return PublishRecord(entry_id=gen_rec.entry_id, upload_meta=u)

    access_token = _ensure_str(os.getenv("TIKTOK_ACCESS_TOKEN"))
    open_id = _ensure_str(os.getenv("TIKTOK_OPEN_ID"))
    if not env.DRY_RUN and (not access_token or not open_id):
        raise RuntimeError("Missing TIKTOK_ACCESS_TOKEN or TIKTOK_OPEN_ID in environment")

    init = tiktok.init_upload(access_token, open_id, draft=True)
    upload_id = _ensure_str(init.get("upload_id"))
    upload_res = tiktok.upload_video(access_token, open_id, upload_id, data, filename=video_file.name)
    status = tiktok.check_upload_status(access_token, open_id, upload_id)

    record = {"entry_id": gen_rec.entry_id, "init": init, "upload": upload_res, "status": status}
    existing.setdefault("uploads", []).append(record)
    up.write_text(_json.dumps(existing, indent=2), encoding="utf-8")

    return PublishRecord(entry_id=gen_rec.entry_id, upload_meta=record)