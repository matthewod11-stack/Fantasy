from adapters import OpenAIAdapter
from packages.generation.pipelines import generate_content
from packages.agents.packaging_agent import build_caption, build_hashtags


def make_adapter_dry_run():
    return OpenAIAdapter(api_key=None, client=None, dry_run=True)


def test_packaging_agent_used_for_caption_and_hashtags(monkeypatch):
    ad = make_adapter_dry_run()
    out = generate_content("waiver-wire", week=3, player="John Doe", extra=None, adapter=ad)
    # Packaging agent builds caption deterministically; ensure caption matches packaging_agent output
    expected_caption = build_caption(out["script_text"], "waiver-wire", 3, dry_run=True)
    assert out["caption"] == expected_caption
    expected_tags = build_hashtags("waiver-wire", 3)
    assert out["hashtags"] == expected_tags
