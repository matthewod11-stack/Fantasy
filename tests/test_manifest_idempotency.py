from pathlib import Path

from apps.batch import manifest as manifest_lib


def test_manifest_idempotency(tmp_path: Path):
    out_dir = tmp_path / "week-5"
    out_dir.mkdir(parents=True)

    manifest_json = out_dir / "manifest.json"
    manifest_csv = out_dir / "manifest.csv"

    entry1 = {"player": "CMcCaffrey", "kind": "waiver_wire", "week": 5, "path": "cmccaffrey_v1.md"}

    # First write
    manifest_lib.write_manifest_atomic(manifest_json, [entry1])
    manifest_lib.write_csv_from_entries(manifest_csv, [entry1])

    # Re-render same player/kind/week with a different path
    entry1b = {"player": "CMcCaffrey", "kind": "waiver_wire", "week": 5, "path": "cmccaffrey_v2.md"}
    existing = manifest_lib.read_manifest(manifest_json)
    updated = manifest_lib.upsert(existing, entry1b)
    manifest_lib.write_manifest_atomic(manifest_json, updated)
    manifest_lib.write_csv_from_entries(manifest_csv, updated)

    # Validate JSON has single entry and path updated
    final = manifest_lib.read_manifest(manifest_json)
    assert len(final) == 1
    assert final[0]["path"] == "cmccaffrey_v2.md"

    # Validate CSV contains exactly one row
    csv_text = manifest_csv.read_text(encoding="utf-8")
    lines = [line for line in csv_text.splitlines() if line.strip()]
    # header + one row
    assert len(lines) == 2

    # Add a second distinct entry and ensure both remain
    entry2 = {"player": "Justin Jefferson", "kind": "start-sit", "week": 5, "path": "justin.md"}
    existing = manifest_lib.read_manifest(manifest_json)
    updated2 = manifest_lib.upsert(existing, entry2)
    manifest_lib.write_manifest_atomic(manifest_json, updated2)
    manifest_lib.write_csv_from_entries(manifest_csv, updated2)

    final2 = manifest_lib.read_manifest(manifest_json)
    # Two entries present
    assert len(final2) == 2
