"""
Name resolver with optional fuzzy matching.

Behavior:
- Loads an alias CSV from ALIASES_CSV_PATH env (defaults to .cache/resolver/aliases.csv)
- If rapidfuzz is available, uses it for matching. Otherwise falls back to
  simple exact / startswith / contains / SequenceMatcher scoring.

API:
- resolve(name, threshold=75) -> {name: str, score: float (0-100), method: str, warning: Optional[str]}
"""
from typing import Dict, Optional, List, Tuple
import os
import csv
from difflib import SequenceMatcher

# Try import rapidfuzz if available
try:
    from rapidfuzz import process, fuzz  # type: ignore
    _HAS_RAPIDFUZZ = True
except Exception:
    _HAS_RAPIDFUZZ = False


DEFAULT_CACHE = os.path.join(".cache", "resolver", "aliases.csv")


def _ensure_cache_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def load_aliases(path: Optional[str] = None) -> Tuple[Dict[str, str], List[str]]:
    """Load alias CSV of form canonical,alias per line. Returns alias->canonical map and canonical list."""
    path = path or os.getenv("ALIASES_CSV_PATH", DEFAULT_CACHE)
    aliases: Dict[str, str] = {}
    canonicals: List[str] = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                rdr = csv.reader(f)
                for row in rdr:
                    if not row:
                        continue
                    canonical = row[0].strip()
                    if canonical and canonical not in canonicals:
                        canonicals.append(canonical)
                    for alias in row[1:]:
                        a = alias.strip()
                        if a:
                            aliases[a.lower()] = canonical
        except Exception:
            pass
    # If no file, return empty and some reasonable defaults
    return aliases, canonicals


def _simple_score(a: str, b: str) -> float:
    """Return a similarity score 0-100 using SequenceMatcher fallback."""
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return float(ratio * 100)


def resolve(name: str, threshold: float = 75.0, aliases_path: Optional[str] = None) -> Dict[str, Optional[object]]:
    """Resolve an input name to a canonical name.

    Returns a dict: {name, score, method, warning}
    """
    if not name:
        return {"name": None, "score": 0.0, "method": "none", "warning": "empty input"}

    aliases_map, canonicals = load_aliases(aliases_path)

    # First, exact match to canonical
    lname = name.strip()
    if lname in canonicals:
        return {"name": lname, "score": 100.0, "method": "exact", "warning": None}

    # Alias exact match
    akey = lname.lower()
    if akey in aliases_map:
        return {"name": aliases_map[akey], "score": 100.0, "method": "alias", "warning": None}

    # Build candidates list: canonicals + alias keys mapping to canonical
    candidates: List[str] = list(canonicals)
    # add alias keys as candidates (they will map back)
    candidates.extend(list(set(aliases_map.keys())))

    # If rapidfuzz is available prefer it
    if _HAS_RAPIDFUZZ and candidates:
        try:
            match = process.extractOne(lname, candidates, scorer=fuzz.WRatio)
            if match:
                candidate, score, _ = match
                # map alias key back to canonical if needed
                candidate_canonical = aliases_map.get(candidate.lower(), candidate)
                method = "fuzzy_rapidfuzz"
                if score >= threshold:
                    return {"name": candidate_canonical, "score": float(score), "method": method, "warning": None}
                else:
                    return {"name": candidate_canonical, "score": float(score), "method": method, "warning": "low_confidence"}
        except Exception:
            pass

    # Fallback: simple heuristics using SequenceMatcher and substring checks
    best = (None, 0.0, "")
    # Check startswith and contains with high scores
    for c in candidates:
        if lname.lower() == c.lower():
            return {"name": c, "score": 100.0, "method": "exact", "warning": None}
        if c.lower().startswith(lname.lower()) or lname.lower().startswith(c.lower()):
            return {"name": c, "score": 95.0, "method": "startswith", "warning": None}
        if lname.lower() in c.lower() or c.lower() in lname.lower():
            return {"name": c, "score": 85.0, "method": "contains", "warning": None}
        s = _simple_score(lname, c)
        if s > best[1]:
            best = (c, s, "sequence")

    if best[0] and best[1] >= threshold:
        return {"name": best[0], "score": best[1], "method": best[2], "warning": None}

    # Low confidence fallback: if aliases_map had any mapping, return original with warning
    return {"name": name, "score": best[1], "method": "fallback", "warning": "low_confidence"}
