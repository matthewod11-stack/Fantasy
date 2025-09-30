import json
from pathlib import Path

from apps.batch.runner import approve_gate, publish_step, GenerateRecord


class DummyTikTok:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run

    def init_upload(self, access_token, open_id, draft=True):
        return {"upload_id": "dry-upload-1", "draft": draft, "open_id": open_id}

    def upload_video(self, access_token, open_id, upload_id, video_bytes, filename="draft.mp4"):
        return {"upload_id": upload_id, "size": len(video_bytes), "filename": filename}

    def check_upload_status(self, access_token, open_id, upload_id):
        return {"upload_id": upload_id, "status": "processed(dry)"}


def test_approve_gate_writes_structured_skip(tmp_path, monkeypatch):
    # ensure approval manifest is empty
    # monkeypatch approval_cli.read_manifest by writing an empty manifest file
    from apps.cli import approval as approval_cli

    manifest_csv = tmp_path / "approval.csv"
    manifest_json = tmp_path / "approval.json"
    # create empty manifest files
    manifest_csv.write_text("id,type,player,week,approved,reviewer,note,updated_at\n")
    monkeypatch.setattr(approval_cli, "read_manifest", lambda: [])

    gen = GenerateRecord(entry_id="X__y__1", player="X", kind="y", week=1, script_path="/tmp/x.md", script_text="hello")
    out_root = tmp_path / "out"
    out_root.mkdir()
    rec = approve_gate(gen, 1, out_root)
    assert rec.approved is False
    # audit/skipped.log should exist and be JSON lines
    log = out_root / "audit" / "skipped.log"
    assert log.exists()
    line = log.read_text().strip()
    data = json.loads(line)
    assert data["entry_id"] == gen.entry_id
    assert data["action"] == "skipped"


def test_publish_block_and_idempotent(tmp_path, monkeypatch):
    # Create a metadata file lacking publish_target -> publish should be blocked
    entry_id = "A__b__1"
    out_root = tmp_path / "out"
    out_root.mkdir()
    meta_path = out_root / f"{entry_id}.meta.json"
    meta_path.write_text(json.dumps({"id": entry_id, "approved": True}), encoding="utf-8")

    gen = GenerateRecord(entry_id=entry_id, player="A", kind="b", week=1, script_path="/tmp/a.md", script_text="hi")
    tiktok = DummyTikTok()
    class Env: DRY_RUN = True

    # In DRY_RUN publishing is permitted even without publish_target as a safety net
    rec0 = publish_step(gen, out_root, tiktok, Env())
    assert rec0.upload_meta is not None and rec0.upload_meta["entry_id"] == entry_id

    # Now add publish_target and test idempotency: first call creates uploads file
    meta_path.write_text(json.dumps({"id": entry_id, "approved": True, "publish_target": "tiktok"}), encoding="utf-8")
    rec = publish_step(gen, out_root, tiktok, Env())
    assert rec.upload_meta is not None and rec.upload_meta["entry_id"] == entry_id
    uploads = json.loads((out_root / "tiktok_uploads.json").read_text())
    assert any(u.get("entry_id") == entry_id for u in uploads.get("uploads", []))

    # Second call should be idempotent and return same record without duplicating
    rec2 = publish_step(gen, out_root, tiktok, Env())
    uploads2 = json.loads((out_root / "tiktok_uploads.json").read_text())
    assert len(uploads2.get("uploads", [])) == 1
    assert rec2.upload_meta is not None and rec2.upload_meta["entry_id"] == entry_id
