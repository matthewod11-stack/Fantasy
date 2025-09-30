import os
import httpx
from packages.agents import data_agent


def make_client(resp_map):
    def handler(request):
        url = request.url.path
        if url in resp_map:
            status, body = resp_map[url]
            return httpx.Response(status_code=status, json=body)
        return httpx.Response(status_code=404, json={})

    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


def test_pipeline_context_mock_mode(monkeypatch):
    # Ensure sleeper disabled -> mock context
    monkeypatch.setenv("SLEEPER_ENABLED", "false")
    monkeypatch.setattr(data_agent, "SLEEPER_ENABLED", False)

    ctx = data_agent.fetch_player_context("Mock Player", 2, "waiver-wire")
    assert isinstance(ctx, dict)
    assert ctx.get("blocked") is not True
    # Mock context should include projection and summary keys
    assert "projection" in ctx or "summary" in ctx


def test_pipeline_context_live_mode_with_mocktransport(monkeypatch):
    # Enable sleeper for this test
    monkeypatch.setenv("SLEEPER_ENABLED", "true")
    monkeypatch.setattr(data_agent, "SLEEPER_ENABLED", True)

    # Prepare fake players list and stats
    players_meta = {"p10": {"full_name": "Live Player", "status": "active"}}
    projections = [{"player_id": "p10", "points": 9.1}]
    stats = [{"player_id": "p10", "rushing_yards": 45}]

    year = __import__("datetime").datetime.now().year
    resp_map = {
        "/v1/players/nfl": (200, players_meta),
        "/v1/player/p10": (200, players_meta["p10"]),
        f"/v1/projections/nfl/regular/{year}/3": (200, projections),
        f"/v1/stats/nfl/regular/{year}/3": (200, stats),
    }

    client = make_client(resp_map)
    ctx = data_agent.fetch_player_context("Live Player", 3, "start-sit", client=client)
    assert isinstance(ctx, dict)
    assert ctx.get("blocked") is not True
    # Live flow should include projection or last_game_stats
    assert "projection" in ctx or "last_game_stats" in ctx
