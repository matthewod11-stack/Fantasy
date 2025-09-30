"""
CLI utility to manage approval manifest (CSV/JSON).

Columns: id,type,player,week,approved,reviewer,note,updated_at
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


DEFAULT_PATH_CSV = Path("approval/manifest.csv")
DEFAULT_PATH_JSON = Path("approval/manifest.json")


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_manifest(path_csv: Path = DEFAULT_PATH_CSV, path_json: Path = DEFAULT_PATH_JSON) -> List[Dict[str, str]]:
    if path_csv.exists():
        with path_csv.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [r for r in reader]
    if path_json.exists():
        with path_json.open("r", encoding="utf-8") as f:
            return json.load(f)
    return []


def write_manifest(entries: List[Dict[str, str]], path_csv: Path = DEFAULT_PATH_CSV, path_json: Path = DEFAULT_PATH_JSON) -> None:
    _ensure_dir(path_csv)
    fieldnames = ["id", "type", "player", "week", "approved", "reviewer", "note", "updated_at"]
    with path_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for e in entries:
            row = {k: e.get(k, "") for k in fieldnames}
            writer.writerow(row)
    # Also write JSON for tooling convenience
    _ensure_dir(path_json)
    with path_json.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def set_approval(entry_id: str, approved: bool, reviewer: str = "cli", note: str = "") -> None:
    entries = read_manifest()
    found = False
    now = datetime.utcnow().isoformat() + "Z"
    for e in entries:
        if e.get("id") == entry_id:
            e["approved"] = "true" if approved else "false"
            e["reviewer"] = reviewer
            e["note"] = note
            e["updated_at"] = now
            found = True
    if not found:
        # create a new row with minimal data
        entries.append({
            "id": entry_id,
            "type": "",
            "player": "",
            "week": "",
            "approved": "true" if approved else "false",
            "reviewer": reviewer,
            "note": note,
            "updated_at": now,
        })
    write_manifest(entries)


def init_manifest(sample: Optional[List[Dict[str, str]]] = None) -> None:
    if sample is None:
        sample = []
    write_manifest(sample)


def _cli() -> None:
    p = argparse.ArgumentParser("approval")
    sub = p.add_subparsers(dest="cmd")
    sub_init = sub.add_parser("init")
    sub_init.add_argument("--sample-json", help="Optional sample JSON to seed manifest")

    sub_set = sub.add_parser("set")
    sub_set.add_argument("id")
    sub_set.add_argument("--approved", choices=["true", "false"], required=True)
    sub_set.add_argument("--reviewer", default="cli")
    sub_set.add_argument("--note", default="")

    args = p.parse_args()
    if args.cmd == "init":
        sample = None
        if getattr(args, "sample_json", None):
            with open(args.sample_json, "r", encoding="utf-8") as f:
                sample = json.load(f)
        init_manifest(sample)
        print("Initialized approval manifest")
    elif args.cmd == "set":
        set_approval(args.id, args.approved == "true", reviewer=args.reviewer, note=args.note)
        print(f"Set approval {args.id} -> {args.approved}")
    else:
        p.print_help()


if __name__ == "__main__":
    _cli()
