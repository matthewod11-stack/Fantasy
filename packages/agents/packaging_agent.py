"""
Packaging Agent

Generates caption, hashtags, and exportable metadata for a generated script.
Deterministic when DRY_RUN is enabled via environment variable.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional


def _deterministic_seed(*parts: object) -> str:
    """Return a short deterministic hex string for given parts."""
    m = hashlib.sha256()
    for p in parts:
        if p is None:
            continue
        if not isinstance(p, (bytes, str)):
            p = str(p)
        m.update(str(p).encode("utf-8"))
    return m.hexdigest()[:10]


def build_caption(script_text: str, kind: str, week: int, dry_run: bool = False) -> str:
    base = f"{kind.replace('-', ' ').title()} — Week {week}"
    if dry_run:
        # include deterministic stub
        seed = _deterministic_seed(kind, week, script_text)
        return f"[dry-run-{seed}] {base}"[:120]
    return base[:120]


def build_hashtags(kind: str, week: int) -> List[str]:
    tags = ["#FantasyFootball", "#NFL", f"#Week{week}"]
    norm = "".join(part.capitalize() for part in kind.split("-"))
    if norm:
        tags.append(f"#{norm}")
    return tags


def package_metadata(
    id: Optional[str], kind: str, week: int, player: Optional[str], caption: str, hashtags: List[str], extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat() + "Z"
    meta: Dict[str, Any] = {
        "id": id or _deterministic_seed(kind, week, player or ""),
        "kind": kind,
        "week": int(week),
        "player": player,
        "caption": caption,
        "hashtags": hashtags,
        "created_at": now,
        "source": "packaging_agent",
    }
    if extra:
        meta["extra"] = extra
    return meta


def to_exportable(metadata: Dict[str, Any]) -> str:
    """Return a compact JSON string for export/storage."""
    return json.dumps(metadata, ensure_ascii=False)


__all__ = ["build_caption", "build_hashtags", "package_metadata", "to_exportable"]
