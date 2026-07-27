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
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_italy_serie_a",
    "soccer_germany_bundesliga",
    "soccer_france_ligue_one",
    "soccer_efl_champ",
    "soccer_fifa_world_cup",
]

LEAGUE_LABELS = {
    "soccer_epl":                    "Premier League",
    "soccer_spain_la_liga":          "La Liga",
    "soccer_italy_serie_a":          "Serie A",
    "soccer_germany_bundesliga":     "Bundesliga",
    "soccer_france_ligue_one":       "Ligue 1",
    "soccer_efl_champ":              "Championship",
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


def _best_h2h_odds(event: dict) -> tuple[float | None, float | None, float | None, str | None, str | None, str | None]:
    """Return (best_home_odds, best_draw_odds, best_away_odds, bm_home, bm_draw, bm_away) across all bookmakers."""
    best_home = best_draw = best_away = None
    bm_home = bm_draw = bm_away = None

    for bm in event.get("bookmakers", []):
        bm_title = bm.get("title") or bm.get("key")
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
                bm_home = bm_title
            if away_odds and (best_away is None or away_odds > best_away):
                best_away = away_odds
                bm_away = bm_title
            if draw_odds and (best_draw is None or draw_odds > best_draw):
                best_draw = draw_odds
                bm_draw = bm_title

    return best_home, best_draw, best_away, bm_home, bm_draw, bm_away


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _load_ensemble_index(data_dir: str) -> tuple[dict[str, dict], dict]:
    """
    Load upcoming_predictions.csv and index by (match_date, home_team, away_team).
    Returns (index, meta) where meta has total/date_min/date_max; both empty if file absent.
    """
    _no_meta = {"total": 0, "date_min": "N/A", "date_max": "N/A"}
    path = os.path.join(data_dir, "upcoming_predictions.csv")
    if not os.path.exists(path):
        return {}, _no_meta
    df = pd.read_csv(path, dtype=str)
    dates = df["match_date"].dropna().str.strip() if "match_date" in df.columns else pd.Series([], dtype=str)
    meta = {
        "total":    len(df),
        "date_min": dates.min() if len(dates) else "N/A",
        "date_max": dates.max() if len(dates) else "N/A",
    }
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
    return index, meta


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
    ensemble_index, _ens_meta = _load_ensemble_index(data_dir)
    print(f"Loaded {len(ensemble_index)} ensemble predictions")

    rows = []
    remaining_requests = None
    _join_total = 0
    _join_hits  = 0
    _join_misses: list[tuple[str, str]] = []  # (ens_key, match_date_str)

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
            _join_total += 1
            if ens:
                p_home, p_draw, p_away = ens["p_home"], ens["p_draw"], ens["p_away"]
                model_used = "ensemble"
                _join_hits += 1
            else:
                p_home, p_draw, p_away = _prematch_probs(home_elo, away_elo, apply_ha)
                model_used = "elo"
                _join_misses.append((ens_key, match_date or ""))

            # Best bookmaker odds
            best_home_odds, best_draw_odds, best_away_odds, bm_home, bm_draw, bm_away = _best_h2h_odds(event)

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

            value_outcome = value_edge = value_odds = value_p_model = value_bookmaker = None
            if candidates:
                value_outcome, value_edge, value_odds, value_p_model = candidates[0]
                value_p_model = round(value_p_model, 4)
                value_bookmaker = {"H": bm_home, "D": bm_draw, "A": bm_away}.get(value_outcome)

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
                "value_bookmaker":  value_bookmaker,
                "model":            model_used,
            })

    # ---- Ensemble join diagnostics ----------------------------------------
    print(f"\n{'='*60}")
    print("ENSEMBLE JOIN DIAGNOSTICS")
    print(f"{'='*60}")
    print(f"  upcoming_predictions.csv: {_ens_meta['total']} rows  "
          f"({_ens_meta['date_min']} → {_ens_meta['date_max']})")
    if _join_total > 0:
        _pct = _join_hits / _join_total * 100
        print(f"  Ensemble join: {_join_hits}/{_join_total} fixtures matched "
              f"({_pct:.0f}%); {_join_total - _join_hits} fell back to Elo")
    else:
        print("  No fixtures processed.")

    if _join_misses and _ens_meta["total"] > 0:
        # Secondary index: date → list of ensemble keys for that date
        _ens_by_date: dict[str, list[str]] = {}
        for _k in ensemble_index:
            _d = _k.split("|")[0]
            _ens_by_date.setdefault(_d, []).append(_k)

        _detail_cap = 20
        print(f"\n  Misses (showing first {min(_detail_cap, len(_join_misses))} "
              f"of {len(_join_misses)}):")
        for _i, (_ens_key, _mdate) in enumerate(_join_misses):
            if _i >= _detail_cap:
                print(f"  ... and {len(_join_misses) - _detail_cap} more misses not shown")
                break
            _nbrs = _ens_by_date.get(_mdate, [])
            if _nbrs:
                _nbr_str = "; ".join(k.split("|", 1)[1] for k in _nbrs)
                print(f"  MISS  {_ens_key}")
                print(f"        same-date preds → {_nbr_str}")
            else:
                print(f"  MISS  {_ens_key}  (no preds for date {_mdate!r})")
    elif _join_misses and _ens_meta["total"] == 0:
        print(f"\n  All {len(_join_misses)} misses: upcoming_predictions.csv is empty "
              "— run predict_upcoming.py first.")

    if not rows:
        print("\nNo fixtures found — writing empty file")
        out_df = pd.DataFrame(columns=[
            "match_date", "match_time", "league", "home_team", "away_team",
            "home_elo", "away_elo", "p_home", "p_draw", "p_away",
            "best_home_odds", "best_draw_odds", "best_away_odds",
            "edge_home", "edge_draw", "edge_away",
            "value_outcome", "value_edge", "value_odds", "value_p_model", "value_bookmaker", "model",
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
