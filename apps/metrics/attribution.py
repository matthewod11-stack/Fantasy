"""
Attribution utilities for building UTM parameters.
"""
from typing import Dict


def generate_utm_for_week(week: int) -> Dict[str, str]:
    """Generate UTM params for a given waiver week.

    Example: week=5 -> utm_campaign=waiver-week-5
    """
    campaign = f"waiver-week-{week}"
    return {
        "utm_source": "tiktok",
        "utm_medium": "social",
        "utm_campaign": campaign,
    }


def utm_query_string(params: Dict[str, str]) -> str:
    """Return URL query string for given UTM params (no leading ?)."""
    return "&".join([f"{k}={v}" for k, v in params.items()])
