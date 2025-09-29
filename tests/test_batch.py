from apps.batch.planner import plan_week
from apps.cli import ff_post


def test_plan_size_and_determinism(tmp_path):
    plan1 = plan_week(5, types=["performers", "busts"], count=12)
    plan2 = plan_week(5, types=["performers", "busts"], count=12)
    assert len(plan1) == 12
    assert plan1 == plan2  # deterministic


def test_dry_run_writes_files(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    # Use a temporary directory by monkeypatching .out path behavior via cwd
    monkeypatch.chdir(tmp_path)

    payload = {"player": "Test Player", "week": 7, "kind": "start-sit"}
    ff_post._do_local_render(payload, out_dir=str(out_dir / "week-7"))

    target = out_dir / "week-7"
    assert target.exists()
    # script file exists
    files = list(target.glob("*.md"))
    assert len(files) == 1
    # manifests exist
    assert (target / "manifest.json").exists()
    assert (target / "manifest.csv").exists()
