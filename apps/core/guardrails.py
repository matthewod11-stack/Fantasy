"""
Guardrails utilities for the Fantasy TikTok Engine.

Provides small, well-documented helpers to enforce safety and content rules.

Functions:
- assert_not_out(player_status): check if a player is OUT/IR and return structured result
- enforce_length(script, max_words=70, mode='fail'|'trim'): enforce or trim scripts
- betting_allowed(): read env to determine if betting content is enabled

All functions return a dict with the shape: {"ok": bool, "reason": Optional[str], ...}
"""
from typing import Dict, Any
import os
import re


def _tokenize_words(text: str) -> list:
    """Tokenize text into words for counting.

    This uses a simple non-whitespace tokenization so numbers, punctuation-adjacent
    tokens, and emoji count as words. It's intentionally small dependency-free.
    """
    if text is None:
        return []
    # Split on any whitespace
    tokens = re.findall(r"\S+", text)
    return tokens


def assert_not_out(player_status: Any) -> Dict[str, Any]:
    """Return a structured result indicating whether a player is allowed.

    Args:
        player_status: value describing a player's status (string or object).

    Returns:
        {ok: bool, reason: str}
    """
    # Accept dict-like objects that may include 'status' or 'injury_status'
    status = None
    try:
        if isinstance(player_status, dict):
            status = player_status.get("status") or player_status.get("injury_status")
        else:
            status = str(player_status) if player_status is not None else None
    except Exception:
        status = str(player_status)

    if status is None:
        return {"ok": True, "reason": "status unknown"}

    s = str(status).strip().lower()
    if s in ("out", "ir", "injured reserve"):
        return {"ok": False, "reason": f"Player status = {status}"}

    return {"ok": True, "reason": f"Player status = {status}"}


def enforce_length(script: str, max_words: int = 70, mode: str = "fail") -> Dict[str, Any]:
    """Ensure script is within max_words.

    Args:
        script: input script text
        max_words: maximum allowed words
        mode: 'fail' to return ok=False when too long; 'trim' to return a trimmed script

    Returns:
        dict: {
            "ok": bool,
            "reason": Optional[str],
            "word_count": int,
            "script": str (possibly trimmed when mode='trim'),
            "trimmed": bool
        }
    """
    tokens = _tokenize_words(script)
    count = len(tokens)
    if count <= max_words:
        return {"ok": True, "reason": "within_limit", "word_count": count, "script": script, "trimmed": False}

    if mode not in ("fail", "trim"):
        mode = "fail"

    if mode == "fail":
        return {"ok": False, "reason": f"too_long: {count} words (max {max_words})", "word_count": count, "script": script, "trimmed": False}

    # mode == 'trim'
    trimmed_tokens = tokens[:max_words]
    trimmed_script = " ".join(trimmed_tokens)
    return {"ok": True, "reason": f"trimmed_to_{max_words}", "word_count": max_words, "script": trimmed_script, "trimmed": True}


def betting_allowed() -> Dict[str, Any]:
    """Check environment to see if betting language/features are allowed.

    Controlled via the env var `ENABLE_BETTING`. Defaults to false.
    """
    enabled = os.getenv("ENABLE_BETTING", "false").lower() == "true"
    if enabled:
        return {"ok": True, "reason": "betting enabled"}
    return {"ok": False, "reason": "betting features are disabled by default (set ENABLE_BETTING=true to opt-in)"}
