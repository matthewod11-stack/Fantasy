"""
Data Agent for Fantasy TikTok Engine.

This module can fetch live player data from the Sleeper API with a lightweight
local cache. It exposes `fetch_player_context(player, week, kind)` which returns
structured context used by the Script Agent.

Behavior and guardrails (per PRD):
- If a player is flagged OUT/IR in Sleeper, the returned context will include
  `blocked: True` and a `block_reason` explaining why generation should be blocked.
- The agent defaults to mocked context when the Sleeper API is disabled or
  network errors occur.

Environment toggles:
- SLEEPER_ENABLED (default: false) — enable live Sleeper calls
- SLEEPER_BASE_URL (default: https://api.sleeper.app)

Caching:
- Player metadata is cached to `.cache/sleeper_players.json` for 24 hours.
- Weekly stats are cached per-player/week for 6 hours.

TODO: Expand guardrails (e.g., rostered_pct thresholds), implement retries/backoff,
and add unit tests that mock Sleeper responses (PRD: Testing & QA).
"""

from typing import Dict, Any, Optional
import os
import json
import time
from datetime import datetime, timedelta

import httpx
from apps.agents import name_resolver

SLEEPER_ENABLED = os.getenv("SLEEPER_ENABLED", "false").lower() == "true"
SLEEPER_BASE_URL = os.getenv("SLEEPER_BASE_URL", "https://api.sleeper.app")

# Simple cache directory
CACHE_DIR = os.path.join(".cache", "sleeper")
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_load(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _cache_save(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def _get_sleeper_players(ttl_seconds: int = 24 * 3600, client: Optional[httpx.Client] = None) -> Optional[Dict[str, Any]]:
    """Fetch and cache the players metadata from Sleeper."""
    cache_path = os.path.join(CACHE_DIR, "sleeper_players.json")

    # Use cached copy if fresh
    meta = _cache_load(cache_path)
    if meta:
        ts = meta.get("_cached_at", 0)
        if time.time() - ts < ttl_seconds:
            return meta.get("data")

    if not SLEEPER_ENABLED:
        return None

    url = f"{SLEEPER_BASE_URL}/v1/players/nfl"
    try:
        if client is None:
            resp = httpx.get(url, timeout=10.0)
        else:
            resp = client.get(url, timeout=10.0)
        resp.raise_for_status()
        players = resp.json()
        _cache_save(cache_path, {"_cached_at": time.time(), "data": players})
        return players
    except Exception:
        return None


def _find_player_id_by_name(name: str, players_meta: Dict[str, Any]) -> Optional[str]:
    """Find a player_id in the players metadata by a case-insensitive name match.

    This is a best-effort helper; for production you'd want a more robust
    matching strategy (fuzzy matching, aliases, last-name-first, etc.).
    """
    if not players_meta:
        return None
    lower = name.strip().lower()
    for pid, info in players_meta.items():
        if not isinstance(info, dict):
            continue
        full_name = info.get("full_name") or info.get("full_name") or ""
        if full_name and lower == full_name.lower():
            return pid
        # Also try smaller matches
        if lower == info.get("first_name", "").lower() + " " + info.get("last_name", "").lower():
            return pid
    return None


def _get_weekly_stats(player_id: str, year: int, week: int, ttl_seconds: int = 6 * 3600, client: Optional[httpx.Client] = None) -> Optional[Dict[str, Any]]:
    """Fetch weekly stats (cached) from Sleeper for a given player/week.

    For simplicity we fetch the projection/stats endpoints per PRD guidance.
    """
    cache_file = os.path.join(CACHE_DIR, f"{player_id}_stats_{year}_{week}.json")
    cached = _cache_load(cache_file)
    if cached:
        ts = cached.get("_cached_at", 0)
        if time.time() - ts < ttl_seconds:
            return cached.get("data")

    if not SLEEPER_ENABLED:
        return None

    # Example endpoints — use projections/stats as available
    try:
        # Fetch player metadata (for rostered_pct/status)
        if client is None:
            resp_meta = httpx.get(f"{SLEEPER_BASE_URL}/v1/player/{player_id}", timeout=10.0)
        else:
            resp_meta = client.get(f"{SLEEPER_BASE_URL}/v1/player/{player_id}", timeout=10.0)
        resp_meta.raise_for_status()
        meta = resp_meta.json()

        proj_url = f"{SLEEPER_BASE_URL}/v1/projections/nfl/regular/{datetime.now().year}/{week}"
        stats_url = f"{SLEEPER_BASE_URL}/v1/stats/nfl/regular/{datetime.now().year}/{week}"

        proj = None
        try:
            if client is None:
                r = httpx.get(proj_url, timeout=10.0)
            else:
                r = client.get(proj_url, timeout=10.0)
            r.raise_for_status()
            proj = r.json()
        except Exception:
            proj = None

        stats = None
        try:
            if client is None:
                r2 = httpx.get(stats_url, timeout=10.0)
            else:
                r2 = client.get(stats_url, timeout=10.0)
            r2.raise_for_status()
            stats = r2.json()
        except Exception:
            stats = None

        data = {"meta": meta, "projections": proj, "stats": stats}
        _cache_save(cache_file, {"_cached_at": time.time(), "data": data})
        return data
    except Exception:
        return None


def fetch_player_context(player: str, week: int, kind: str, client: Optional[httpx.Client] = None) -> Dict[str, Any]:
    """Public API: return the player context used by the Script Agent.

    If Sleeper is enabled and the player can be resolved, we return real data and
    include guardrails. Otherwise we fall back to a mocked context (keeps app
    functional without secrets).
    """
    # Attempt live flow
    players_meta = _get_sleeper_players(client=client)
    # Resolve player name via resolver (offline-friendly)
    resolved = name_resolver.resolve(player)
    resolved_name = resolved.get("name")
    context: Dict[str, Any] = {"player": player, "week": week, "kind": kind}

    if SLEEPER_ENABLED and players_meta:
        # players_meta is a dict keyed by player_id
        # Prefer resolved canonical name when searching
        player_id = _find_player_id_by_name(str(resolved_name or player), players_meta)
        if player_id:
            # Get player metadata and weekly stats
            player_info = players_meta.get(player_id, {})
            weekly = _get_weekly_stats(player_id, datetime.now().year, week, client=client) or {}

            status = player_info.get("status") or player_info.get("injury_status") or "active"
            rostered_pct = player_info.get("fantasy" , {}).get("ownership", None) if isinstance(player_info.get("fantasy"), dict) else None

            # Simple guardrail: block if player is out/IR
            if isinstance(status, str) and status.lower() in ("out", "ir"):
                return {
                    "player": player,
                    "week": week,
                    "kind": kind,
                    "blocked": True,
                    "block_reason": f"Player status = {status}",
                    "player_info": player_info,
                }

            # Build a rich context
            context.update(
                {
                    "matchup": "TBD",
                    "opponent_def_rank": None,
                    "last_game_stats": weekly.get("stats") if weekly else {},
                    "season_stats": {},
                    "projection": (weekly.get("projections") if weekly else {}),
                    "rostered_pct": rostered_pct or player_info.get("roster_pct") or 0,
                    "start_pct": None,
                    "trend": "steady",
                    "recommendation": "ANALYZE",
                    "confidence": 6,
                    "summary": f"{player} — data from Sleeper",
                    "resolved_name": resolved_name,
                    "resolver_score": resolved.get("score"),
                    "resolver_method": resolved.get("method"),
                    # template vars
                    "factor_1": "Check matchup and snap share",
                    "factor_2": "Check target share",
                    "factor_3": "Check red-zone usage",
                    "add_drop_note": f"Rostered: {rostered_pct}",
                    "upside": "TBD",
                    "priority": 5,
                }
            )

            print(f"🔍 [Data Agent] (Sleeper) Fetched context for {player} (Week {week}, {kind})")
            return context

    # Fallback mock context (same shape as previous mock)
    mock_context = {
        "player": player,
        "week": week,
        "kind": kind,
        "matchup": "vs TB",
        "opponent_def_rank": 15,
        "game_time": "1:00 PM ET",
        "weather": "Dome",
        "last_game_stats": {"rushing_yards": 84, "receiving_yards": 32, "touchdowns": 1},
        "season_stats": {"rushing_yards": 412, "receiving_yards": 156, "touchdowns": 4},
        "projection": {"points": 14.2, "floor": 8.5, "ceiling": 22.1},
        "rostered_pct": 87.3,
        "start_pct": 76.2,
        "trend": "up",
        "recommendation": "STRONG START" if kind == "start-sit" else "ADD IMMEDIATELY",
        "confidence": 8,
        "summary": f"{player} is a must-start this week with an excellent matchup.",
        "factor_1": "Favorable matchup against Tampa Bay's 15th-ranked run defense",
        "factor_2": "Coming off a strong 84-yard rushing performance last week",
        "factor_3": "High usage rate with 18+ touches expected",
        "add_drop_note": f"With only {87.3}% roster rate, {player} is surprisingly available!",
        "upside": "RB1 potential in this matchup",
        "priority": 9,
    }

    print(f"🔍 [Data Agent] (mock) Fetched context for {player} (Week {week}, {kind})")
    return mock_context