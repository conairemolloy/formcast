"""Shared season helpers.

Season rollover is July: the 2026-27 data starts 2026-07-31, so any date in
July or later belongs to the season starting that calendar year.
"""

from datetime import date


def current_season(d: date) -> str:
    """Return the season label (e.g. '2026-27') that date `d` falls in."""
    y = d.year
    if d.month >= 7:
        return f"{y}-{str(y + 1)[-2:]}"
    return f"{y - 1}-{str(y)[-2:]}"


def previous_season(season: str) -> str:
    """'2026-27' -> '2025-26'."""
    start = int(season[:4]) - 1
    return f"{start}-{str(start + 1)[-2:]}"
