"""
Batch planner for Fantasy TikTok Engine.

Given a week and optional list of types, produce a deterministic plan of 10-15
items balanced across PRD categories. The planner is offline and deterministic
(uses a seeded PRNG based on week) so repeated runs for the same week produce
the same plan.

Each plan item contains: player, kind, template_path, day_slot (0-6 representing day of week).
"""
from typing import List, Dict, Optional
import os
import random

# Default canonical templates mapping (kept minimal here; planner will look up files)
CANONICAL_DIR = os.path.join("templates", "script_templates")
LEGACY_DIR = os.path.join("prompts", "templates")

# PRD categories (friendly -> canonical filename)
PRD_CATEGORIES = {
    "start-sit": "start_sit.md",
    "waiver-wire": "waiver_wire.md",
    "top-performers": "top-performers.md",
    "biggest-busts": "biggest-busts.md",
    "trade-thermometer": "trade-thermometer.md",
    "injury-pivot": "injury-pivot.md",
}

# Minimal sample players used when no external roster is available
SAMPLE_PLAYERS = [
    "Bijan Robinson",
    "Justin Jefferson",
    "Patrick Mahomes",
    "Christian McCaffrey",
    "Travis Kelce",
    "Ja'Marr Chase",
    "Derrick Henry",
    "Austin Ekeler",
    "Jalen Hurts",
    "Tyreek Hill",
    "Amon-Ra St. Brown",
    "Stefon Diggs",
    "CeeDee Lamb",
    "A.J. Brown",
]


def _choose_template_for_kind(kind: str) -> Optional[str]:
    """Return the canonical template path if present, else fall back to legacy, else None."""
    fname = PRD_CATEGORIES.get(kind)
    if not fname:
        # try mapping from kinds that already look like filenames
        fname = kind + ".md"

    can = os.path.join(CANONICAL_DIR, fname)
    if os.path.exists(can):
        return can
    legacy = os.path.join(LEGACY_DIR, fname)
    if os.path.exists(legacy):
        return legacy
    return None


def plan_week(week: int, types: Optional[List[str]] = None, count: int = 12) -> List[Dict]:
    """Create a deterministic plan for the given week.

    Args:
        week: NFL week (used as seed)
        types: optional list of kinds (friendly aliases like 'performers')
        count: number of items to produce (defaults to 12)

    Returns:
        list of plan items
    """
    if types:
        # normalize aliases to canonical kind keys if possible
        kinds = []
        for t in types:
            t = t.strip()
            # allow comma-separated string elements
            parts = t.split(",") if "," in t else [t]
            for p in parts:
                p = p.strip()
                # map some common aliases
                if p == "performers":
                    kinds.append("top-performers")
                elif p == "busts":
                    kinds.append("biggest-busts")
                elif p == "waiver_wire" or p == "waiver-wire":
                    kinds.append("waiver-wire")
                else:
                    kinds.append(p)
    else:
        kinds = list(PRD_CATEGORIES.keys())

    # Seed deterministic RNG by week
    rnd = random.Random(week)

    plan: List[Dict] = []
    players = list(SAMPLE_PLAYERS)

    # Shuffle but deterministic
    rnd.shuffle(players)

    # Ensure count bounds
    count = max(10, min(15, int(count)))

    # Round-robin assign kinds to players to keep balance
    for i in range(count):
        player = players[i % len(players)]
        kind = kinds[i % len(kinds)]
        template = _choose_template_for_kind(kind)
        day_slot = rnd.randint(0, 6)
        item = {"player": player, "kind": kind, "template": template, "day_slot": day_slot}
        plan.append(item)

    return plan
