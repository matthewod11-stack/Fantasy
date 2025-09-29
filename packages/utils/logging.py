"""Minimal structured logger with redaction support.

Provides get_logger(name, redactions=None) that returns a stdlib logger which
emits a JSON-like single-line dictionary per record and supports redacting
sensitive keys from structured `data` passed via the `extra` kwarg.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Iterable


DEFAULT_REDACT_KEYS = ["access_token", "refresh_token", "open_id", "Authorization"]


def _redact_dict(d: dict, keys: Iterable[str]) -> dict:
    out = {}
    kset = {k.lower() for k in keys}
    for k, v in d.items():
        if k.lower() in kset:
            out[k] = "[redacted]"
        else:
            out[k] = v
    return out


class RedactingFilter(logging.Filter):
    def __init__(self, redactions: Iterable[str] | None = None) -> None:
        super().__init__()
        self.redactions = list(redactions) if redactions is not None else DEFAULT_REDACT_KEYS

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - simple logic
        data = getattr(record, "data", None)
        if isinstance(data, dict):
            record.__dict__["data_redacted"] = _redact_dict(data, self.redactions)
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting
        ts = datetime.utcfromtimestamp(record.created).isoformat() + "Z"
        base = {
            "ts": ts,
            "logger": record.name,
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        data = record.__dict__.get("data_redacted") or record.__dict__.get("data")
        if data is not None:
            base["data"] = data
        try:
            return json.dumps(base, default=str, ensure_ascii=False)
        except Exception:
            return str(base)


def get_logger(name: str, redactions: Iterable[str] | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    # Avoid duplicate handlers on repeated calls
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        handler.addFilter(RedactingFilter(redactions))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    else:
        # Ensure a RedactingFilter is present
        found = any(isinstance(f, RedactingFilter) for h in logger.handlers for f in getattr(h, "filters", []))
        if not found:
            for h in logger.handlers:
                h.addFilter(RedactingFilter(redactions))
    return logger


__all__ = ["get_logger", "RedactingFilter", "JSONFormatter"]
