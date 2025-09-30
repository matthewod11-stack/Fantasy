"""Unit tests for runner step helpers and structured events.

This tests the new step helper functions for deterministic dry-run behavior and
that events are emitted (logged) as JSON records.
"""
import tempfile
import os
import json
from pathlib import Path
import logging

from apps.batch import runner
from apps.batch.runner import generate_step, approve_gate, render_step, publish_step, PlanRecord


def test_generate_and_approve_and_render_publish_dry_run(monkeypatch, caplog):
    # Force dry-run paths
    monkeypatch.setenv("DRY_RUN", "true")
    caplog.set_level(logging.INFO)

    with tempfile.TemporaryDirectory() as outdir:
        week = 5
        # Create a minimal plan item
        item = {"player": "Test Player", "kind": "start-sit", "avatar_id": "av-1", "voice_id": "v1"}

        # Use a minimal fake openai adapter by building from wiring (which respects DRY_RUN)
        env = runner.load_env()
        openai = runner.build_openai(env)

        # Call generate_step
        gen = generate_step(item, week, Path(outdir) / f"week-{week}", openai)
        assert gen.entry_id.endswith("__5")
        assert Path(gen.script_path).exists()

        # Approve gate should record not-approved (no approvals present)
        approve = approve_gate(gen, week, Path(outdir) / f"week-{week}")
        assert not approve.approved

        # Rendering in dry run should create a placeholder video
        heygen = runner.build_heygen(env)
        render = render_step(gen, item, Path(outdir) / f"week-{week}", heygen, env)
        assert render.video_path is not None
        assert Path(render.video_path).exists()

        # Publishing in dry run should succeed and write uploads file
        tiktok = runner.build_tiktok(env)
        pub = publish_step(gen, Path(outdir) / f"week-{week}", tiktok, env)
        uploads = Path(outdir) / f"week-{week}" / "tiktok_uploads.json"
        assert uploads.exists()

        # Ensure events can be emitted and are valid JSON
        rec = PlanRecord(week=week, kinds=["start-sit"], items=[item])
        runner._emit_event("planned", rec)
        # check last log line contains the event
        found = any("\"event\": \"planned\"" in r.message for r in caplog.records)
        assert found, "planned event should be emitted to logs"
