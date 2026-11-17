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


def season_start_year(d: date) -> int:
    """Calendar year the season containing `d` started in (2026-11-17 -> 2026)."""
    return d.year if d.month >= 7 else d.year - 1


def in_active_season(d: date) -> bool:
    """True when European top-flight league matches are being played.

    Sep 1 – May 31. Excludes June–August so the summer break (and the first
    couple of weeks of a new season, before data has accumulated) never trips
    freshness checks. International breaks (~2 weeks) fit inside a 14-day limit.
    """
    return d.month >= 9 or d.month <= 5


def previous_season(season: str) -> str:
    """'2026-27' -> '2025-26'."""
    start = int(season[:4]) - 1
    return f"{start}-{str(start + 1)[-2:]}"
