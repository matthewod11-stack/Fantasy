"""
Tests for the TikTok upload CLI. Verifies DRY_RUN writes upload.json stubs.
"""
import os
import tempfile
import json
from pathlib import Path
from typer.testing import CliRunner
from apps.cli.tiktok_upload import app

runner = CliRunner()


def test_tiktok_upload_dry_run(monkeypatch):
    # Enable dry run via env
    monkeypatch.setenv("DRY_RUN", "true")

    # Create a temporary file to upload
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.mp4', delete=False) as tmp:
        tmp.write(b"\x00\x01\x02")

    try:
        with tempfile.TemporaryDirectory() as outdir:
            result = runner.invoke(
                app,
                [
                    "upload",
                    "--file",
                    tmp.name,
                    "--week",
                    "3",
                    "--kind",
                    "top-performers",
                    "--outdir",
                    outdir,
                ],
            )

            assert result.exit_code == 0, f"CLI failed: {result.output}"

            # Check canonical outdir upload.json
            upload_json = Path(outdir) / "week-3" / "top-performers" / "tiktok" / "upload.json"
            assert upload_json.exists(), "upload.json not created in outdir"

            # Check sidecar next to file
            side_json = Path(tmp.name).parent / (Path(tmp.name).name + ".upload.json")
            assert side_json.exists(), "sidecar upload.json not created next to file"

            # Validate content
            with open(upload_json, 'r') as f:
                data = json.load(f)
                assert data.get("upload_id") == "dry-upload-123"
                assert data.get("status") == "uploaded(dry)"

    finally:
        os.unlink(tmp.name)
