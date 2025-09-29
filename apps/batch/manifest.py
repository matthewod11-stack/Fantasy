from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List, Tuple


def read_manifest(manifest_json: Path) -> List[dict]:
    """Read manifest JSON and return list of entries. Return [] if missing or invalid."""
    try:
        if not manifest_json.exists():
            return []
        with manifest_json.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def _normalize_player(val: object) -> str:
    return (str(val) if val is not None else "").strip().lower()


def _normalize_kind(val: object) -> str:
    return (str(val) if val is not None else "").strip().lower()


def _normalize_week(val: object) -> int:
    try:
        return int(val)
    except Exception:
        return 0


def make_key(entry: dict, key_fields: Iterable[str]) -> Tuple[str, str, int]:
    """Return normalized key tuple for an entry using key_fields (player, kind, week)."""
    # Support key_fields order but expect at least player, kind, week
    player = entry.get("player") if isinstance(entry, dict) else None
    kind = entry.get("kind") if isinstance(entry, dict) else None
    week = entry.get("week") if isinstance(entry, dict) else None
    return (_normalize_player(player), _normalize_kind(kind), _normalize_week(week))


def upsert(entries: List[dict], new_entry: dict, key_fields: Tuple[str, str, str] = ("player", "kind", "week")) -> List[dict]:
    """Upsert new_entry into entries list by key_fields, normalizing player/kind/week.

    Returns the new entries list.
    """
    # Build map from normalized key -> entry
    mapping = {}
    for e in entries:
        k = make_key(e, key_fields)
        mapping[k] = e

    # Normalize new_entry fields and coerce types
    normalized = dict(new_entry)
    # Ensure canonical fields exist
    normalized["player"] = str(new_entry.get("player", "")).strip()
    normalized["kind"] = str(new_entry.get("kind", "")).strip()
    try:
        normalized["week"] = int(new_entry.get("week", 0))
    except Exception:
        normalized["week"] = 0

    # make key and upsert
    new_key = make_key(normalized, key_fields)
    mapping[new_key] = normalized

    # Return entries as list (preserve insertion order deterministically by sorting keys)
    # Sorting: by week, player, kind to keep stable output
    items = list(mapping.values())
    items.sort(key=lambda e: (int(e.get("week", 0)), _normalize_player(e.get("player")), _normalize_kind(e.get("kind"))))
    return items


def write_manifest_atomic(manifest_json: Path, entries: List[dict]) -> None:
    """Write manifest JSON atomically by writing to .tmp and os.replace.

    Ensures parent directory exists.
    """
    manifest_json.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_json.with_name(manifest_json.name + ".tmp")
    # Write to tmp file
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    # Atomic replace
    os.replace(str(tmp), str(manifest_json))


def write_csv_from_entries(manifest_csv: Path, entries: List[dict]) -> None:
    """Overwrite CSV derived from entries. Header is deterministic: core fields then extras."""
    import csv as _csv

    manifest_csv.parent.mkdir(parents=True, exist_ok=True)

    # Determine headers
    core = ["player", "week", "kind", "path"]
    extras = []
    for e in entries:
        for k in e.keys():
            if k not in core and k not in extras:
                extras.append(k)

    headers = core + sorted(extras)

    tmp = manifest_csv.with_name(manifest_csv.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = _csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for e in entries:
            row = {h: e.get(h, "") for h in headers}
            writer.writerow(row)
        f.flush()
        os.fsync(f.fileno())

    os.replace(str(tmp), str(manifest_csv))
