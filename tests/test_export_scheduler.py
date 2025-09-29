import json
from apps.export.scheduler_export import generate_scheduler_manifest
import csv
from datetime import datetime


def test_scheduler_manifest_distribution(tmp_path):
    out_root = tmp_path
    week = 9
    out_dir = out_root / f"week-{week}"
    out_dir.mkdir(parents=True)

    # Create 14 entries -> should distribute into 2/day for 7 days
    entries = []
    for i in range(14):
        entries.append({"player": f"P{i}", "week": week, "kind": "start-sit", "path": f"P{i}__start-sit.md"})

    manifest = out_dir / "manifest.json"
    with manifest.open("w", encoding="utf-8") as f:
        json.dump(entries, f)

    csv_path = generate_scheduler_manifest(week, start_date="2025-09-29", timezone="America/Los_Angeles", out_root=str(out_root))

    assert csv_path.exists()
    rows = []
    with csv_path.open("r", encoding="utf-8") as cf:
        reader = csv.DictReader(cf)
        for r in reader:
            rows.append(r)

    # Expect 14 scheduled rows
    assert len(rows) == 14

    # Count per day
    counts = {}
    for r in rows:
        dt = datetime.fromisoformat(r["scheduled_datetime"])
        day = dt.date().isoformat()
        counts[day] = counts.get(day, 0) + 1

    # Each day should have 2 entries
    for v in counts.values():
        assert 2 <= v <= 3
