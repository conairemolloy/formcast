"""Match a logged prediction to its results.csv fixture.

Single implementation shared by settle_predictions.py (to settle) and
portfolio_analytics.py (to attach odds). Rules (a wrong match is worse than
no match):
  * Names are resolved strictly to results.csv canonical names — explicit
    map, exact, suffix strip, accent fold. No fuzzy substring guessing.
  * If one team doesn't resolve (e.g. "Manchester" / "Sheffield" / "Paris"
    from an old suffix-stripping bug), the fixture is found by date + league
    + the OTHER, exactly-resolved team, and the loose name must still
    plausibly be that team. Never matched on a loose name alone: "Paris" is
    plausibly both Paris FC and Paris SG.
  * Exactly one candidate fixture must fit; otherwise no match.

Callers never rewrite the logged names — each log row's SHA-256 hash covers
them. Resolved names are only used to find the results row.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from predict_upcoming import _fold, _resolve_team  # noqa: E402


def _plausibly_same(loose_name: str, canonical: str) -> bool:
    """Loose check that an unresolved logged name could be this canonical team.
    Only used when the opponent is already pinned exactly, so it just needs to
    reject an obviously different club, not pick between candidates."""
    a, b = _fold(loose_name), _fold(canonical)
    if not a or not b:
        return False
    return a in b or b in a or a[:3] == b[:3]


class FixtureMatcher:
    """Index of results.csv fixtures by (match_date, league code).

    `results` needs string columns match_date, home_team, away_team, league.
    match() returns (status, index) where index is the matched row's label in
    `results` (None unless status is "exact" or "anchored").
    """

    def __init__(self, results: pd.DataFrame):
        self.known_teams = set(results["home_team"]) | set(results["away_team"])
        self._by_day: dict[tuple[str, str], list[tuple[str, str, object]]] = {}
        for idx, d, h, a, lg in zip(results.index, results["match_date"],
                                    results["home_team"], results["away_team"],
                                    results["league"]):
            self._by_day.setdefault((d, lg), []).append((h, a, idx))
        self._strict_cache: dict[str, str | None] = {}

    def strict(self, name: str) -> str | None:
        """Canonical results.csv name, or None if it doesn't resolve strictly."""
        name = (name or "").strip()
        if name not in self._strict_cache:
            res = _resolve_team(name, self.known_teams, fuzzy=False)
            self._strict_cache[name] = res if res in self.known_teams else None
        return self._strict_cache[name]

    def match(self, match_date: str, league_code: str,
              home_name: str, away_name: str) -> tuple[str, object]:
        """Find the fixture. Status: exact | anchored | both_teams_unresolved |
        ambiguous | no_result_found."""
        home = self.strict(home_name)
        away = self.strict(away_name)
        if home is None and away is None:
            return "both_teams_unresolved", None

        candidates = [
            idx for h, a, idx in self._by_day.get((match_date.strip(), league_code), [])
            if (h == home if home else _plausibly_same(home_name, h))
            and (a == away if away else _plausibly_same(away_name, a))
        ]
        if len(candidates) > 1:
            return "ambiguous", None
        if not candidates:
            return "no_result_found", None  # postponed, date mismatch, or wrong league
        return ("exact" if home and away else "anchored"), candidates[0]
