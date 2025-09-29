"""
Tests for the batch pipeline end-to-end in DRY_RUN mode.

Verifies that running the pipeline twice is idempotent (no duplicate manifest entries)
and that expected files are created.
"""
import tempfile
from pathlib import Path
from apps.batch.runner import run_pipeline
from apps.batch import manifest as manifest_lib


def test_pipeline_dry_run_idempotent(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")

    with tempfile.TemporaryDirectory() as outdir:
        # Run pipeline once
        run_pipeline(week=4, kinds=["start-sit", "waiver-wire"], do_render=True, do_upload=True, outdir=outdir)

        week_dir = Path(outdir) / "week-4"
        manifest = week_dir / "manifest.json"
        assert manifest.exists()
        entries1 = manifest_lib.read_manifest(manifest)
        assert len(entries1) >= 2

        # Run pipeline second time (should be idempotent)
        run_pipeline(week=4, kinds=["start-sit", "waiver-wire"], do_render=True, do_upload=True, outdir=outdir)
        entries2 = manifest_lib.read_manifest(manifest)
        assert entries1 == entries2, "Manifest entries should be identical after rerun"

        # Ensure script files and avatar placeholders exist
        for e in entries2:
            path = week_dir / e.get("path")
            assert path.exists(), f"Script file missing: {path}"

        # Check tiktok upload manifest
        tiktok_file = week_dir / "tiktok_uploads.json"
        assert tiktok_file.exists()
