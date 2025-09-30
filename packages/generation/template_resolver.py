from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import threading
from typing import List, Optional, Dict, Any

# Template locations (canonical + legacy)
TEMPLATE_ROOT = Path("templates") / "script_templates"
LEGACY_TEMPLATE_ROOT = Path("prompts") / "templates"

TEMPLATE_FILENAME_OVERRIDES: Dict[str, str] = {
    "start-sit": "start_sit.md",
    "waiver-wire": "waiver_wire.md",
}


def resolve_template(kind: str) -> Optional[Path]:
    """Locate a template file for a given content kind.

    Returns the first existing Path or None if nothing found.
    This consolidates the lookup logic used by the API, CLI and pipelines.
    """
    override = TEMPLATE_FILENAME_OVERRIDES.get(kind)
    candidates: List[Path] = []
    if override:
        candidates.append(TEMPLATE_ROOT / override)
    candidates.append(TEMPLATE_ROOT / f"{kind}.md")
    # Allow underscore variant for backward compatibility
    candidates.append(TEMPLATE_ROOT / f"{kind.replace('-', '_')}.md")
    # Legacy fallbacks
    if override:
        candidates.append(LEGACY_TEMPLATE_ROOT / override)
    candidates.append(LEGACY_TEMPLATE_ROOT / f"{kind}.md")
    candidates.append(LEGACY_TEMPLATE_ROOT / f"{kind.replace('-', '_')}.md")

    for path in candidates:
        if path.exists():
            return path
    return None


@dataclass
class RuntimeConfig:
    """Typed runtime configuration object.

    Fields:
      DRY_RUN: whether adapters should operate in dry-run mode
      WEEK: optional week number
      RENDER: whether to render avatars
      PUBLISH: whether to publish/upload
      targets: optional list of target kinds

    This object also keeps a small snapshot of the environment so callers
    can avoid scattered os.getenv calls and be thread-safe via the helpers
    below.
    """

    DRY_RUN: bool = False
    WEEK: Optional[int] = None
    RENDER: bool = True
    PUBLISH: bool = False
    targets: Optional[List[str]] = None
    _env: Optional[Dict[str, str]] = None

    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if self._env is None:
            return os.getenv(key, default)
        return self._env.get(key, default)

    @staticmethod
    def _parse_bool(value: Optional[str], default: bool = False) -> bool:
        if value is None:
            return default
        v = str(value).strip().lower()
        return v in {"1", "true", "t", "yes", "y"}

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None, **overrides: Any) -> "RuntimeConfig":
        env = env or dict(os.environ)
        dry = cls._parse_bool(env.get("DRY_RUN"), False)
        week = None
        week_raw = env.get("WEEK")
        if week_raw is not None:
            try:
                week = int(str(week_raw))
            except Exception:
                week = None
        render = cls._parse_bool(env.get("RENDER"), True)
        publish = cls._parse_bool(env.get("PUBLISH"), False)
        targets_raw = env.get("TARGETS") or env.get("TARGETS_LIST") or ""
        targets = [t.strip() for t in targets_raw.split(",") if t.strip()] if targets_raw else None
        cfg = cls(DRY_RUN=dry, WEEK=week, RENDER=render, PUBLISH=publish, targets=targets, _env=env)
        # apply explicit overrides
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg


# Thread-local holder for RuntimeConfig instances
_tls = threading.local()


def set_runtime_config(cfg: RuntimeConfig) -> None:
    _tls.cfg = cfg


def get_runtime_config() -> RuntimeConfig:
    cfg = getattr(_tls, "cfg", None)
    if cfg is None:
        cfg = RuntimeConfig.from_env()
        set_runtime_config(cfg)
    return cfg


__all__ = ["resolve_template", "TEMPLATE_ROOT", "LEGACY_TEMPLATE_ROOT", "TEMPLATE_FILENAME_OVERRIDES", "RuntimeConfig", "set_runtime_config", "get_runtime_config"]
