"""
Scheduler export utility.

Reads `.out/week-<N>/manifest.json` (produced by dry-run/batch) and produces
`scheduler_manifest.csv` with columns:
  scheduled_datetime, title, caption, video_path, thumbnail_path, tags

Times are distributed evenly across the week (aiming for 2-3 per day when possible).
Timezone-aware datetimes are produced using the stdlib zoneinfo.
"""
from typing import List
import json
from pathlib import Path
from datetime import datetime, time, timedelta
import csv
import os

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore


def _load_manifest(manifest_path: Path) -> List[dict]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _day_slots_for_count(count: int):
    """Return a list of time-of-day objects for count slots (evenly spaced).

    Picks sensible poster-friendly times between 09:00 and 20:00.
    """
    start_hour = 9
    end_hour = 20
    if count <= 0:
        return []
    if count == 1:
        return [time(hour=12, minute=0)]
    # even spacing in hours
    span = end_hour - start_hour
    step = span / (count - 1)
    slots = []
    for i in range(count):
        h = start_hour + step * i
        hour = int(h)
        minute = int((h - hour) * 60)
        slots.append(time(hour=hour, minute=minute))
    return slots


def generate_scheduler_manifest(week: int, start_date: str, timezone: str = "America/Los_Angeles", out_root: str = ".out") -> Path:
    """Generate scheduler_manifest.csv for .out/week-<N>.

    Args:
        week: week number (used to locate folder)
        start_date: YYYY-MM-DD (first day of the planning window)
        timezone: tz name (defaults to America/Los_Angeles)
        out_root: root folder where .out is located

    Returns:
        Path to the generated CSV
    """
    out_dir = Path(out_root) / f"week-{week}"
    manifest_path = out_dir / "manifest.json"
    entries = _load_manifest(manifest_path)

    total = len(entries)
    days = 7
    # Desired per-day min/max
    per_day_min = 2
    per_day_max = 3

    # Determine base distribution
    if total >= per_day_min * days and total <= per_day_max * days:
        # Fit into 2-3/day
        # Start with 2 per day, distribute remainder up to 3
        base = [per_day_min] * days
        rem = total - per_day_min * days
        for i in range(rem):
            base[i % days] += 1
    else:
        # Distribute as evenly as possible
        base = [total // days] * days
        rem = total % days
        for i in range(rem):
            base[i] += 1

    # Build scheduled datetimes
    # Parse start_date
    sd = datetime.fromisoformat(start_date)
    tz = None
    if ZoneInfo is not None:
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = None

    scheduled_rows = []
    idx = 0
    for day_offset in range(days):
        day_count = base[day_offset]
        day_date = sd + timedelta(days=day_offset)
        slots = _day_slots_for_count(day_count)
        for s in slots:
            if idx >= total:
                break
            entry = entries[idx]
            # Compose datetime
            dt = datetime.combine(day_date.date(), s)
            if tz is not None:
                dt = dt.replace(tzinfo=tz)
            # Fields
            title = f"{entry.get('kind')} — {entry.get('player')}"
            caption = f"{entry.get('player')} — {entry.get('kind')} (Week {entry.get('week')})"
            fname = entry.get('path') or ''
            video_path = os.path.join("videos", Path(fname).stem + ".mp4")
            thumbnail_path = os.path.join("thumbnails", Path(fname).stem + ".jpg")
            tags = f"{entry.get('player')},{entry.get('kind')}"
            scheduled_rows.append({
                "scheduled_datetime": dt.isoformat(),
                "title": title,
                "caption": caption,
                "video_path": video_path,
                "thumbnail_path": thumbnail_path,
                "tags": tags,
            })
            idx += 1

    # Write CSV
    csv_path = out_dir / "scheduler_manifest.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as cf:
        fieldnames = ["scheduled_datetime", "title", "caption", "video_path", "thumbnail_path", "tags"]
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for r in scheduled_rows:
            writer.writerow(r)

    return csv_path
