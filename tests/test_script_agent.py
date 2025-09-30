import os

import pytest

from jinja2 import UndefinedError

from packages.agents import script_agent


def test_waiver_wire_renders_with_all_keys(tmp_path):
    # Use the templates shipped with the package
    context = {
        "player": "D. Player",
        "position": "WR",
        "team": "XYZ",
        "reason": "Increased snaps and targets",
        "stats": {"Targets": 12, "Rec": 8},
        "rostered_pct": 23,
    }

    out = script_agent.render_script("waiver-wire", context)
    assert "WAIVER WIRE ALERT" in out or "[dry-run]" in out
    assert "D. Player" in out


def test_missing_key_raises_undefined_error():
    # Deliberately omit required 'players' and 'week' for top_performers_week
    context = {"players": None}
    with pytest.raises(UndefinedError):
        # top_performers_week expects week and players to be present and usable
        script_agent.render_script("top-performers-week", context)


def test_explicit_template_path(tmp_path):
    # Create a tiny template that requires 'foo' key
    p = tmp_path / "custom.j2"
    p.write_text("Hello {{ foo }}")

    # Missing key should raise
    with pytest.raises(UndefinedError):
        script_agent.render_script("waiver-wire", {}, template_path=str(p))

    # With the key it should succeed
    out = script_agent.render_script("waiver-wire", {"foo": "bar"}, template_path=str(p))
    assert "Hello bar" in out
