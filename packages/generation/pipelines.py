"""Content generation pipelines using an injected OpenAIAdapter.

Contract:
- generate_content(kind, week, player=None, extra=None, *, adapter) -> dict
  Returns: {
    "script_text": str,
    "caption": str,
    "hashtags": list[str],
    "meta": {"kind": str, "week": int, "player": str | None},
  }

Notes:
- No secrets pulled here. The OpenAI adapter instance must be provided by caller.
- Template lookup reuses apps.batch.planner's private resolver to keep a single
  source of truth for mapping kinds -> template paths.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import os

from adapters import OpenAIAdapter, ScriptRequest  # type: ignore

# Reuse planner's template resolver to avoid duplication
try:
    from apps.batch.planner import _choose_template_for_kind as _resolve_template  # type: ignore
except Exception:  # pragma: no cover - fallback if import path changes
    _resolve_template = None  # type: ignore


def _load_template_text(kind: str) -> str:
    """Load template text for kind using planner resolver or simple fallback.

    Returns the raw template string (may include placeholders like {week}, {player}).
    """
    # Prefer planner's resolver when present
    if callable(_resolve_template):
        path = _resolve_template(kind)  # type: ignore[misc]
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    # Fallback heuristic: try canonical locations
    candidates = [
        os.path.join("templates", "script_templates", f"{kind}.md"),
        os.path.join("prompts", "templates", f"{kind}.md"),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    # Last resort: minimal generic template
    return f"# {kind}\n\nWeek {{week}} update for {{player}}."


def _render_prompt(template: str, *, kind: str, week: int, player: Optional[str], extra: Optional[Dict[str, Any]]) -> str:
    """Very small formatter: Python .format with provided fields.

    Supports {week}, {player}, and any keys from extra.
    Missing keys are replaced with an empty string to avoid KeyError.
    """

    class _SafeDict(dict):
        def __missing__(self, key):  # type: ignore[override]
            return ""

    data: Dict[str, Any] = {"kind": kind, "week": week, "player": player or ""}
    if extra:
        data.update(extra)
    try:
        return template.format_map(_SafeDict(data))
    except Exception:
        # Keep template content even if formatting fails
        return template


def _build_caption(kind: str, week: int, *, dry_run: bool) -> str:
    base = f"{kind.replace('-', ' ').title()} - Week {week}"
    if dry_run:
        base = f"[dry-run] {base}"
    # Ensure <=120 chars
    return base[:120]


def _build_hashtags(kind: str, week: int) -> list[str]:
    tags = [
        "#FantasyFootball",
        "#NFL",
        f"#Week{week}",
    ]
    # Normalize kind to a tag like #StartSit or #WaiverWire
    norm = "".join(part.capitalize() for part in kind.split("-"))
    if norm:
        tags.append(f"#{norm}")
    return tags


def generate_content(
    kind: str,
    week: int,
    player: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    *,
    adapter: OpenAIAdapter,
) -> Dict[str, Any]:
    """Generate content using the provided OpenAIAdapter.

    No environment reads here. The caller wires an adapter configured with
    dry_run or live settings.
    """
    template = _load_template_text(kind)
    prompt = _render_prompt(template, kind=kind, week=int(week), player=player, extra=extra)

    # Tone/audience can be adjusted later; keep minimal here
    req = ScriptRequest(prompt=prompt, audience="fantasy football", tone="energetic")
    script = adapter.generate_script(req)

    caption = _build_caption(kind, int(week), dry_run=getattr(adapter, "dry_run", False))
    hashtags = _build_hashtags(kind, int(week))

    return {
        "script_text": script,
        "caption": caption,
        "hashtags": hashtags,
        "meta": {"kind": kind, "week": int(week), "player": player},
    }


__all__ = ["generate_content"]
