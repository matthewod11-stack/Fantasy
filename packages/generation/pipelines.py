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
from packages.agents import data_agent
from packages.agents.script_agent import render_script

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
    # Build a validated context from Data Agent (live or mock depending on env)
    # The Data Agent provides useful keys used by Jinja templates.
    context = data_agent.fetch_player_context(player=player or "", week=int(week), kind=kind)

    # Merge in any extra planner-provided keys (extra should not overwrite existing
    # validated context unless explicitly provided by the planner)
    if extra:
        merged = dict(context)
        merged.update(extra)
        context = merged

    # Render script via Script Agent (Jinja2 template + optional OpenAI polishing).
    # Prefer to resolve a file-path template when possible so StrictUndefined works
    # with the expected template variables.
    # Try planner resolver first (keeps single source of truth)
    template_path = None
    try:
        # Planner resolver may return a path string
        t = _resolve_template(kind) if callable(_resolve_template) else None
        if t:
            template_path = t
    except Exception:
        template_path = None

    # Render script using the Script Agent. Pass the injected OpenAI adapter so
    # that polishing (if enabled) respects the same adapter/dry-run determinism
    # used by the pipeline. render_script will either return the rendered
    # template (when OPENAI_ENABLED is false) or the adapter-polished result
    # (when OPENAI_ENABLED is true).
    try:
        rendered_or_polished = render_script(kind=kind, context=context, template_path=str(template_path) if template_path else None, openai_adapter=adapter)
    except TypeError:
        rendered_or_polished = render_script(kind=kind, context=context, template_path=str(template_path) if template_path else None)

    # Preserve previous dry-run deterministic behavior: when the pipeline's
    # OpenAI polishing is disabled (OPENAI_ENABLED=false) but the injected
    # adapter is in dry-run mode, pass the rendered template to the adapter to
    # obtain the deterministic stub. If OPENAI is enabled, render_script would
    # already have used the adapter.
    openai_enabled = os.getenv("OPENAI_ENABLED", "false").lower() in ("1", "true", "yes")
    if getattr(adapter, "dry_run", False) and not openai_enabled:
        req = ScriptRequest(prompt=rendered_or_polished, audience="fantasy football", tone="energetic")
        script = adapter.generate_script(req)
    else:
        script = rendered_or_polished

    caption = _build_caption(kind, int(week), dry_run=getattr(adapter, "dry_run", False))
    hashtags = _build_hashtags(kind, int(week))

    return {
        "script_text": script,
        "caption": caption,
        "hashtags": hashtags,
        "meta": {"kind": kind, "week": int(week), "player": player},
    }


__all__ = ["generate_content"]
