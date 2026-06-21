"""
Fetch upcoming fixtures from The Odds API, compute Elo model probabilities,
and identify value bets where our model has edge > 5% vs bookmaker implied odds.

Output: data/processed/live_value_bets.csv
"""

import os
import sys
import math
import requests
import pandas as pd
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ODDS_API_KEY = "9f8647c1b9d7c4cfb5ae36821445e7bb"
ODDS_BASE    = "https://api.the-odds-api.com/v4"
HOME_ADV     = 50    # same as elo_model.py
VALUE_EDGE   = 0.05  # 5% minimum edge

SPORTS = [
    "soccer_england_premier_league",
    "soccer_spain_la_liga",
    "soccer_italy_serie_a",
    "soccer_germany_bundesliga",
    "soccer_france_ligue_one",
    "soccer_england_championship",
    "soccer_fifa_world_cup",
]

LEAGUE_LABELS = {
    "soccer_england_premier_league": "Premier League",
    "soccer_spain_la_liga":          "La Liga",
    "soccer_italy_serie_a":          "Serie A",
    "soccer_germany_bundesliga":     "Bundesliga",
    "soccer_france_ligue_one":       "Ligue 1",
    "soccer_england_championship":   "Championship",
    "soccer_fifa_world_cup":         "FIFA World Cup",
}

# Sports that use international Elo ratings instead of club Elo ratings
INTERNATIONAL_SPORTS = {"soccer_fifa_world_cup"}

HOST_NATIONS: dict[str, set[str]] = {
    "FIFA World Cup": {"United States", "Mexico", "Canada"},
}


def is_tournament_finals(competition: str) -> bool:
    """True for tournament finals proper; False for qualification rounds."""
    if not competition:
        return False
    if "qualification" in competition.lower():
        return False
    return competition in {"FIFA World Cup"}

# ---------------------------------------------------------------------------
# Odds API name -> elo_ratings.csv canonical name
# ---------------------------------------------------------------------------

_ODDS_TO_ELO: dict[str, str] = {
    # England
    "Manchester City":           "Man City",
    "Manchester United":         "Man United",
    "Tottenham Hotspur":         "Tottenham",
    "Tottenham":                 "Tottenham",
    "Newcastle United":          "Newcastle",
    "Wolverhampton Wanderers":   "Wolves",
    "Wolverhampton":             "Wolves",
    "Nottingham Forest":         "Nott'm Forest",
    "West Ham United":           "West Ham",
    "Brighton & Hove Albion":    "Brighton",
    "Brighton":                  "Brighton",
    "Leicester City":            "Leicester",
    "Luton Town":                "Luton",
    "Sheffield United":          "Sheffield United",
    "Crystal Palace":            "Crystal Palace",
    "Aston Villa":               "Aston Villa",
    "Arsenal":                   "Arsenal",
    "Chelsea":                   "Chelsea",
    "Liverpool":                 "Liverpool",
    "Everton":                   "Everton",
    "Fulham":                    "Fulham",
    "Brentford":                 "Brentford",
    "Burnley":                   "Burnley",
    "Bournemouth":               "Bournemouth",
    # Spain
    "Atletico Madrid":           "Ath Madrid",
    "Atlético Madrid":           "Ath Madrid",
    "Athletic Club":             "Ath Bilbao",
    "Real Madrid":               "Real Madrid",
    "Barcelona":                 "Barcelona",
    "Villarreal":                "Villarreal",
    "Real Sociedad":             "Real Sociedad",
    "Sevilla":                   "Sevilla",
    "Real Betis":                "Betis",
    "Valencia":                  "Valencia",
    "Osasuna":                   "Osasuna",
    "Girona":                    "Girona",
    # Italy
    "Internazionale":            "Inter",
    "Inter Milan":               "Inter",
    "AC Milan":                  "Milan",
    "SSC Napoli":                "Napoli",
    "SS Lazio":                  "Lazio",
    "Hellas Verona":             "Verona",
    "Juventus":                  "Juventus",
    "Roma":                      "Roma",
    "AS Roma":                   "Roma",
    "Atalanta":                  "Atalanta",
    "Fiorentina":                "Fiorentina",
    "Torino":                    "Torino",
    "Udinese":                   "Udinese",
    "Cagliari":                  "Cagliari",
    "Salernitana":               "Salernitana",
    "Monza":                     "Monza",
    # Germany
    "Bayern Munich":             "Bayern Munich",
    "Borussia Dortmund":         "Dortmund",
    "Bayer Leverkusen":          "Leverkusen",
    "RB Leipzig":                "RB Leipzig",
    "VfB Stuttgart":             "Stuttgart",
    "Eintracht Frankfurt":       "Ein Frankfurt",
    "Borussia Monchengladbach":  "M'gladbach",
    "Borussia Mönchengladbach":  "M'gladbach",
    "Werder Bremen":             "Werder Bremen",
    "Wolfsburg":                 "Wolfsburg",
    "Augsburg":                  "Augsburg",
    "Freiburg":                  "Freiburg",
    "Hoffenheim":                "Hoffenheim",
    "Mainz":                     "Mainz",
    "Mainz 05":                  "Mainz",
    "Union Berlin":              "Union Berlin",
    "Heidenheim":                "Heidenheim",
    # France
    "Paris Saint Germain":       "Paris SG",
    "Paris Saint-Germain":       "Paris SG",
    "Olympique Lyonnais":        "Lyon",
    "Olympique Marseille":       "Marseille",
    "Stade Rennais":             "Rennes",
    "Monaco":                    "Monaco",
    "Lille":                     "Lille",
    "Lens":                      "Lens",
    "Reims":                     "Reims",
    "Stade de Reims":            "Reims",
    "Nice":                      "Nice",
    "OGC Nice":                  "Nice",
    "Strasbourg":                "Strasbourg",
    "Nantes":                    "Nantes",
    "Toulouse":                  "Toulouse",
    "Brest":                     "Brest",
}

# Odds API national team name variants → international_elo_ratings.csv canonical name
ODDS_NAME_ALIASES: dict[str, str] = {
    "USA":                    "United States",
    "Bosnia & Herzegovina":   "Bosnia and Herzegovina",
}


def _resolve_team(odds_name: str, elo_index: dict[str, float]) -> tuple[str, float]:
    """Return (canonical_name, elo_rating). Falls back to 1500 if not found."""
    # 0. International name aliases
    if odds_name in ODDS_NAME_ALIASES:
        canonical = ODDS_NAME_ALIASES[odds_name]
        if canonical in elo_index:
            return canonical, elo_index[canonical]

    # 1. Manual mapping (club names)
    if odds_name in _ODDS_TO_ELO:
        canonical = _ODDS_TO_ELO[odds_name]
        if canonical in elo_index:
            return canonical, elo_index[canonical]

    # 2. Exact match
    if odds_name in elo_index:
        return odds_name, elo_index[odds_name]

    # 3. Case-insensitive substring match
    lower = odds_name.lower()
    for team, rating in elo_index.items():
        if team.lower() in lower or lower in team.lower():
            return team, rating

    return odds_name, 1500.0


# ---------------------------------------------------------------------------
# Probability model — identical to live.py _prematch_probs
# ---------------------------------------------------------------------------

def _prematch_probs(home_elo: float, away_elo: float, apply_home_advantage: bool = True) -> tuple[float, float, float]:
    ha         = HOME_ADV if apply_home_advantage else 0
    elo_diff   = home_elo - away_elo + ha
    p_home_raw = 1.0 / (1.0 + 10 ** (-elo_diff / 400))
    p_away_raw = 1.0 / (1.0 + 10 ** (elo_diff / 400))
    closeness  = 1.0 - abs(p_home_raw - p_away_raw)
    p_draw     = 0.30 * closeness
    remainder  = 1.0 - p_draw
    p_home     = p_home_raw / (p_home_raw + p_away_raw) * remainder
    p_away     = p_away_raw / (p_home_raw + p_away_raw) * remainder
    return p_home, p_draw, p_away


# ---------------------------------------------------------------------------
# Odds API helpers
# ---------------------------------------------------------------------------

def _fetch_odds(sport: str) -> list[dict]:
    url = f"{ODDS_BASE}/sports/{sport}/odds"
    params = {
        "apiKey":      ODDS_API_KEY,
        "regions":     "eu",
        "markets":     "h2h",
        "oddsFormat":  "decimal",
    }
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code == 401:
        print(f"  [ERROR] Invalid API key — check ODDS_API_KEY", file=sys.stderr)
        return []
    if resp.status_code == 422:
        print(f"  [SKIP] {sport} not available right now", file=sys.stderr)
        return []
    resp.raise_for_status()
    return resp.json()


def _best_h2h_odds(event: dict) -> tuple[float | None, float | None, float | None]:
    """Return (best_home_odds, best_draw_odds, best_away_odds) across all bookmakers."""
    best_home = best_draw = best_away = None

    for bm in event.get("bookmakers", []):
        for market in bm.get("markets", []):
            if market.get("key") != "h2h":
                continue
            outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
            home_name = event.get("home_team", "")
            away_name = event.get("away_team", "")

            home_odds = outcomes.get(home_name)
            away_odds = outcomes.get(away_name)
            draw_odds = outcomes.get("Draw")

            if home_odds and (best_home is None or home_odds > best_home):
                best_home = home_odds
            if away_odds and (best_away is None or away_odds > best_away):
                best_away = away_odds
            if draw_odds and (best_draw is None or draw_odds > best_draw):
                best_draw = draw_odds

    return best_home, best_draw, best_away


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _load_ensemble_index(data_dir: str) -> dict[str, dict]:
    """
    Load upcoming_predictions.csv and index by (home_team, away_team, match_date).
    Returns {} if the file doesn't exist.
    """
    path = os.path.join(data_dir, "upcoming_predictions.csv")
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path, dtype=str)
    index: dict[str, dict] = {}
    for _, row in df.iterrows():
        key = f"{row.get('match_date','').strip()}|{row.get('home_team','').strip()}|{row.get('away_team','').strip()}"
        try:
            index[key] = {
                "p_home": float(row["p_home_ensemble"]),
                "p_draw": float(row["p_draw_ensemble"]),
                "p_away": float(row["p_away_ensemble"]),
            }
        except (KeyError, ValueError):
            pass
    return index


def main():
    base_dir    = os.path.dirname(os.path.abspath(__file__))
    data_dir    = os.path.normpath(os.path.join(base_dir, "..", "data", "processed"))
    ratings_path = os.path.join(data_dir, "elo_ratings.csv")
    out_path    = os.path.join(data_dir, "live_value_bets.csv")

    # Load club Elo ratings
    ratings_df  = pd.read_csv(ratings_path)
    elo_index   = {row["team"].strip(): float(row["elo_rating"]) for _, row in ratings_df.iterrows()}
    print(f"Loaded {len(elo_index)} club Elo ratings")

    # Load international Elo ratings (national teams)
    intl_ratings_path = os.path.join(data_dir, "international_elo_ratings.csv")
    intl_elo_index: dict[str, float] = {}
    if os.path.exists(intl_ratings_path):
        intl_df = pd.read_csv(intl_ratings_path)
        intl_elo_index = {row["team"].strip(): float(row["elo_rating"]) for _, row in intl_df.iterrows()}
        print(f"Loaded {len(intl_elo_index)} international Elo ratings")

    # Load ensemble predictions (generated by predict_upcoming.py, may not exist yet)
    ensemble_index = _load_ensemble_index(data_dir)
    print(f"Loaded {len(ensemble_index)} ensemble predictions")

    rows = []
    remaining_requests = None

    for sport in SPORTS:
        league = LEAGUE_LABELS[sport]
        print(f"\nFetching {league}...")

        try:
            events = _fetch_odds(sport)
        except requests.HTTPError as exc:
            print(f"  [ERROR] {exc}", file=sys.stderr)
            continue

        print(f"  {len(events)} fixtures returned")

        # Use international Elo index for national-team competitions
        active_elo_index = intl_elo_index if sport in INTERNATIONAL_SPORTS else elo_index

        for event in events:
            home_raw  = event.get("home_team", "")
            away_raw  = event.get("away_team", "")
            commence  = event.get("commence_time", "")

            # Parse date / time (UTC)
            try:
                dt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
                match_date = dt.strftime("%Y-%m-%d")
                match_time = dt.strftime("%H:%M")
            except (ValueError, AttributeError):
                match_date = match_time = None

            # Resolve team names and ratings
            home_canon, home_elo = _resolve_team(home_raw, active_elo_index)
            away_canon, away_elo = _resolve_team(away_raw, active_elo_index)

            # Determine home advantage: neutral venue for World Cup unless host nation
            if sport in INTERNATIONAL_SPORTS and is_tournament_finals(league):
                apply_ha = home_raw in HOST_NATIONS.get(league, set())
            else:
                apply_ha = True  # club football and qualifiers/friendlies are genuine home/away

            # Model probabilities — prefer ensemble if available
            ens_key = f"{match_date}|{home_canon}|{away_canon}"
            ens     = ensemble_index.get(ens_key)
            if ens:
                p_home, p_draw, p_away = ens["p_home"], ens["p_draw"], ens["p_away"]
                model_used = "ensemble"
            else:
                p_home, p_draw, p_away = _prematch_probs(home_elo, away_elo, apply_ha)
                model_used = "elo"

            # Best bookmaker odds
            best_home_odds, best_draw_odds, best_away_odds = _best_h2h_odds(event)

            # Edge calculations (only if odds available)
            edge_home = edge_draw = edge_away = None
            if best_home_odds:
                edge_home = round(p_home - (1.0 / best_home_odds), 4)
            if best_draw_odds:
                edge_draw = round(p_draw - (1.0 / best_draw_odds), 4)
            if best_away_odds:
                edge_away = round(p_away - (1.0 / best_away_odds), 4)

            # Value outcome: highest edge above threshold
            candidates = [
                ("H", edge_home, best_home_odds, p_home),
                ("D", edge_draw, best_draw_odds, p_draw),
                ("A", edge_away, best_away_odds, p_away),
            ]
            candidates = [(o, e, od, p) for o, e, od, p in candidates if e is not None and e > VALUE_EDGE]
            candidates.sort(key=lambda x: -x[1])

            value_outcome = value_edge = value_odds = value_p_model = None
            if candidates:
                value_outcome, value_edge, value_odds, value_p_model = candidates[0]
                value_p_model = round(value_p_model, 4)

            rows.append({
                "match_date":       match_date,
                "match_time":       match_time,
                "league":           league,
                "home_team":        home_raw,
                "away_team":        away_raw,
                "home_elo":         round(home_elo, 1),
                "away_elo":         round(away_elo, 1),
                "p_home":           round(p_home, 4),
                "p_draw":           round(p_draw, 4),
                "p_away":           round(p_away, 4),
                "best_home_odds":   best_home_odds,
                "best_draw_odds":   best_draw_odds,
                "best_away_odds":   best_away_odds,
                "edge_home":        edge_home,
                "edge_draw":        edge_draw,
                "edge_away":        edge_away,
                "value_outcome":    value_outcome,
                "value_edge":       value_edge,
                "value_odds":       value_odds,
                "value_p_model":    value_p_model,
                "model":            model_used,
            })

    if not rows:
        print("\nNo fixtures found — writing empty file")
        out_df = pd.DataFrame(columns=[
            "match_date", "match_time", "league", "home_team", "away_team",
            "home_elo", "away_elo", "p_home", "p_draw", "p_away",
            "best_home_odds", "best_draw_odds", "best_away_odds",
            "edge_home", "edge_draw", "edge_away",
            "value_outcome", "value_edge", "value_odds", "value_p_model", "model",
        ])
        out_df.to_csv(out_path, index=False)
        return

    out_df = pd.DataFrame(rows)
    out_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(out_df)} fixtures to {out_path}")

    # Summary
    value_df = out_df[out_df["value_outcome"].notna()].sort_values("value_edge", ascending=False)
    print(f"\n{'='*60}")
    print(f"VALUE BETS FOUND: {len(value_df)}")
    print(f"{'='*60}")
    if value_df.empty:
        print("No value bets found (edge > 5%) in current fixtures.")
    else:
        for _, row in value_df.iterrows():
            outcome_label = {"H": "Home", "D": "Draw", "A": "Away"}[row["value_outcome"]]
            print(
                f"  {row['league']:18s}  {row['home_team']} vs {row['away_team']}\n"
                f"    {outcome_label} @ {row['value_odds']:.2f}  "
                f"model={row['value_p_model']:.1%}  "
                f"implied={1/row['value_odds']:.1%}  "
                f"edge={row['value_edge']:.1%}  "
                f"[{row['match_date']} {row['match_time']}]"
            )


if __name__ == "__main__":
    main()
