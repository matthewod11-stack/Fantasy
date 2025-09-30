import json
from pathlib import Path
import os
import tempfile

from apps.batch.runner import run_pipeline
from apps.cli.approval import write_manifest


def _seed_manifest(entries, tmpdir):
    # write manifest to approval/manifest.csv under repo root
    apdir = Path.cwd() / "approval"
    apdir.mkdir(parents=True, exist_ok=True)
    write_manifest(entries, path_csv=apdir / "manifest.csv", path_json=apdir / "manifest.json")


def test_pipeline_fails_when_not_approved(tmp_path, monkeypatch):
    # Ensure no approvals
    ap = Path.cwd() / "approval"
    if ap.exists():
        for f in ap.iterdir():
            f.unlink()
    # Run pipeline for week 1; it should skip items and not raise
    run_pipeline(week=1, kinds=["start-sit"], do_render=False, do_upload=False, outdir=str(tmp_path))
    # Verify that audit skipped log exists
    audit = Path(tmp_path) / "week-1" / "audit" / "skipped.log"
    assert audit.exists(), "Expected skipped audit log when no approvals present"


def test_packaging_outputs_for_approved_rows(tmp_path, monkeypatch):
    # Seed approval manifest with an approval for the first planned item
    # We'll construct an id matching planner: player__kind__week
    week = 2
    # Use planner to generate one item to learn player/kind
    from apps.batch.planner import plan_week
    plan = plan_week(week, count=1)
    item = plan[0]
    entry_id = f"{item['player']}__{item['kind']}__{week}"
    entries = [{"id": entry_id, "type": item['kind'], "player": item['player'], "week": str(week), "approved": "true", "reviewer": "test", "note": "ok", "updated_at": "now"}]
    apdir = Path.cwd() / "approval"
    apdir.mkdir(parents=True, exist_ok=True)
    write_manifest(entries, path_csv=apdir / "manifest.csv", path_json=apdir / "manifest.json")

    # Run pipeline which should produce metadata file for the approved id
    run_pipeline(week=week, kinds=[item['kind']], do_render=False, do_upload=False, outdir=str(tmp_path))
    meta_file = Path(tmp_path) / f"week-{week}" / f"{entry_id}.meta.json"
    assert meta_file.exists(), f"Expected metadata file for approved entry {entry_id}"
    data = json.loads(meta_file.read_text(encoding='utf-8'))
    assert data.get('id') == entry_id
    assert data.get('created_at')
    assert data.get('caption')
