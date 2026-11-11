"""Shared league-coverage helpers.

results.csv only holds results for the leagues in COMP_TO_LEAGUE, so only
predictions in those leagues can ever be settled. Everything else (Brazil,
Eredivisie, Primeira Liga, cups, internationals) is "not tracked".

Kept dependency-free so the API can import it without loading model code.
"""

# API competition name → internal league code used in results.csv
COMP_TO_LEAGUE: dict[str, str] = {
    "Premier League":       "EPL",
    "La Liga":              "LaLiga",
    "Primera Division":     "LaLiga",   # football-data.org's name for La Liga
    "Serie A":              "SerieA",
    "Bundesliga":           "Bundesliga",
    "Ligue 1":              "Ligue1",
    "Championship":         "Championship",
    # Second tiers and other competitions present in results.csv
    "2. Bundesliga":        "Bundesliga2",
    "Bundesliga 2":         "Bundesliga2",
    "Ligue 2":              "Ligue2",
    "Scottish Premiership": "ScottishPrem",
    "Scottish Premier League": "ScottishPrem",
    "Serie B":              "SerieB",
    "Segunda División":     "Segunda",
    "La Liga 2":            "Segunda",
    "Segunda Division":     "Segunda",
}

# The league codes results.csv covers — the only settleable leagues.
COVERED_LEAGUE_CODES: frozenset[str] = frozenset(COMP_TO_LEAGUE.values())


def league_code(name: str) -> str | None:
    """results.csv league code for an API competition name or a code, else None."""
    lg = (name or "").strip()
    if lg in COVERED_LEAGUE_CODES:
        return lg
    return COMP_TO_LEAGUE.get(lg)


def is_covered_league(name: str) -> bool:
    """True if predictions in this league can be settled against results.csv."""
    return league_code(name) is not None
