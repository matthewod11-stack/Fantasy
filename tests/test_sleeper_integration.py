import os
import json
import httpx
import pytest

from packages.agents import data_agent


class SimpleMockTransport(httpx.MockTransport):
    pass


def make_client(resp_map):
    """Return an httpx.Client with a MockTransport that maps URLs to responses.

    resp_map: dict[url_path -> (status_code, json_body)]
    """
    def handler(request):
        url = request.url.path
        if url in resp_map:
            status, body = resp_map[url]
            return httpx.Response(status_code=status, json=body)
        return httpx.Response(status_code=404, json={})

    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


def test_normal_player_projections(monkeypatch):
    # Enable sleeper for the test
    monkeypatch.setenv("SLEEPER_ENABLED", "true")
    # data_agent reads SLEEPER_ENABLED at import time; set module var too
    monkeypatch.setattr(data_agent, "SLEEPER_ENABLED", True)
    # Ensure no cached players metadata interferes
    try:
        cache_path = os.path.join(data_agent.CACHE_DIR, "sleeper_players.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)
    except Exception:
        pass

    # Build mocked responses for players list and player/meta endpoints
    players_meta = {"p1": {"full_name": "Test Player", "status": "active"}}
    projections = [{"player_id": "p1", "points": 12.3}]
    stats = [{"player_id": "p1", "rushing_yards": 80}]

    resp_map = {
        "/v1/players/nfl": (200, players_meta),
        "/v1/player/p1": (200, players_meta["p1"]),
        f"/v1/projections/nfl/regular/{__import__('datetime').datetime.now().year}/5": (200, projections),
        f"/v1/stats/nfl/regular/{__import__('datetime').datetime.now().year}/5": (200, stats),
    }

    client = make_client(resp_map)

    ctx = data_agent.fetch_player_context("Test Player", 5, "start-sit", client=client)
    assert isinstance(ctx, dict)
    assert ctx.get("blocked") is not True
    # Projection or stats should be in context when successful
    assert "projection" in ctx or "last_game_stats" in ctx


def test_out_player_status(monkeypatch):
    monkeypatch.setenv("SLEEPER_ENABLED", "true")
    monkeypatch.setattr(data_agent, "SLEEPER_ENABLED", True)
    try:
        cache_path = os.path.join(data_agent.CACHE_DIR, "sleeper_players.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)
    except Exception:
        pass

    players_meta = {"p2": {"full_name": "Injured Player", "status": "IR"}}
    resp_map = {
        "/v1/players/nfl": (200, players_meta),
        "/v1/player/p2": (200, players_meta["p2"]),
    }
    client = make_client(resp_map)

    ctx = data_agent.fetch_player_context("Injured Player", 6, "start-sit", client=client)
    assert isinstance(ctx, dict)
    assert ctx.get("blocked") is True
    assert "block_reason" in ctx


def test_network_error_fallback(monkeypatch):
    # When Sleeper is enabled but network errors occur, fetch_player_context should fall back to mock
    monkeypatch.setenv("SLEEPER_ENABLED", "true")
    monkeypatch.setattr(data_agent, "SLEEPER_ENABLED", True)
    try:
        cache_path = os.path.join(data_agent.CACHE_DIR, "sleeper_players.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)
    except Exception:
        pass

    def handler(request):
        raise httpx.TransportError("network down")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    ctx = data_agent.fetch_player_context("Fallback Player", 3, "waiver-wire", client=client)
    assert isinstance(ctx, dict)
    # Should not be blocked and should contain mocked keys like 'matchup' or 'projection' fallback
    assert ctx.get("blocked") is not True
    assert "matchup" in ctx or "summary" in ctx
