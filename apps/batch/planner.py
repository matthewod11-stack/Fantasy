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

from apps.api.schemas import PRD_CONTENT_KINDS

# Default canonical templates mapping (kept minimal here; planner will look up files)
CANONICAL_DIR = os.path.join("templates", "script_templates")
LEGACY_DIR = os.path.join("prompts", "templates")
DEFAULT_TEMPLATE = "default.md"

# PRD categories (friendly -> canonical filename)
PRD_CATEGORIES = {
    kind: ("start_sit.md" if kind == "start-sit" else "waiver_wire.md" if kind == "waiver-wire" else f"{kind}.md")
    for kind in PRD_CONTENT_KINDS
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
    """Return an existing template path for kind, or a default fallback."""
    fname = PRD_CATEGORIES.get(kind, f"{kind}.md")
    p1 = os.path.join(CANONICAL_DIR, fname)
    if os.path.exists(p1):
        return p1
    p2 = os.path.join(LEGACY_DIR, fname)
    if os.path.exists(p2):
        return p2
    # fallback to default
    p3 = os.path.join(CANONICAL_DIR, DEFAULT_TEMPLATE)
    return p3 if os.path.exists(p3) else p1  # last resort: non-existent, but deterministic


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
