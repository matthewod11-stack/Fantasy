from adapters import OpenAIAdapter
from packages.generation.pipelines import generate_content


def make_adapter_dry_run():
    # DRY_RUN behavior is controlled by the adapter instance; no env reads here
    return OpenAIAdapter(api_key=None, client=None, dry_run=True)


def test_generate_content_start_sit_dry_run(monkeypatch):
    ad = make_adapter_dry_run()
    out = generate_content("start-sit", week=5, player="Bijan Robinson", extra={"matchup": "ATL vs NO"}, adapter=ad)
    assert isinstance(out, dict)
    assert out["meta"]["kind"] == "start-sit"
    assert out["meta"]["week"] == 5
    assert out["meta"]["player"] == "Bijan Robinson"
    # Script is deterministic and prefixed in dry-run mode
    assert out["script_text"].startswith("[dry-run] script:")
    # Caption should be <= 120 and prefixed
    assert out["caption"].startswith("[dry-run] Start Sit - Week 5")
    assert len(out["caption"]) <= 120
    # Hashtags include normalized kind and week
    assert "#Week5" in out["hashtags"]
    assert "#StartSit" in out["hashtags"]


def test_generate_content_waiver_wire_dry_run():
    ad = make_adapter_dry_run()
    out = generate_content("waiver-wire", week=8, player="Puka Nacua", extra={"projection": "Top 20 WR"}, adapter=ad)
    assert out["meta"]["kind"] == "waiver-wire"
    assert out["meta"]["week"] == 8
    assert out["script_text"].startswith("[dry-run] script:")
    assert out["caption"].startswith("[dry-run] Waiver Wire - Week 8")
    assert "#WaiverWire" in out["hashtags"]
    assert "#NFL" in out["hashtags"]
