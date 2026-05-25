#!/usr/bin/env python3
"""
publish_predictions.py

Fetches upcoming fixtures from football-data.org, generates Elo-based
predictions, and appends new rows to data/processed/prediction_log.csv.

Run BEFORE elo_model.py so predictions use pre-retrain ratings.
"""

import csv
import hashlib
import os
from datetime import date, timedelta, datetime, timezone

import pandas as pd
import httpx

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
ELO_CSV  = os.path.join(BASE_DIR, "data", "processed", "elo_ratings.csv")
LOG_CSV  = os.path.join(BASE_DIR, "data", "processed", "prediction_log.csv")

# ── API ───────────────────────────────────────────────────────────────────────
FDATA_API_KEY = "3edbe9850f784e8a86328acaabfd9561"
FDATA_BASE    = "https://api.football-data.org/v4"
HEADERS       = {"X-Auth-Token": FDATA_API_KEY}
DAYS_AHEAD    = 14

HOME_ADVANTAGE = 50

LOG_COLS = [
    "match_date", "match_time", "league", "home_team", "away_team",
    "home_elo", "away_elo", "p_home", "p_draw", "p_away",
    "predicted_outcome", "published_at", "hash",
    "actual_result", "correct", "settled_at",
]

# ── Team name normalisation (mirrors live.py) ─────────────────────────────────
_STRIP_SUFFIXES = [
    " FC", " CF", " SC", " AC", " AS", " SS", " SL", " CD", " SD",
    " United", " City", " Town", " Rovers", " Wanderers", " Athletic",
    " Albion", " County", " Palace",
]

_FDO_TO_ELO: dict[str, str] = {
    "FC Bayern München":          "Bayern Munich",
    "Bayern München":             "Bayern Munich",
    "Paris Saint-Germain FC":     "Paris SG",
    "Paris Saint-Germain":        "Paris SG",
    "Manchester United FC":       "Man United",
    "Manchester United":          "Man United",
    "Manchester City FC":         "Man City",
    "Manchester City":            "Man City",
    "Arsenal FC":                 "Arsenal",
    "Chelsea FC":                 "Chelsea",
    "Liverpool FC":               "Liverpool",
    "Tottenham Hotspur FC":       "Tottenham",
    "Tottenham Hotspur":          "Tottenham",
    "Borussia Dortmund":          "Dortmund",
    "Bayer 04 Leverkusen":        "Leverkusen",
    "Atletico de Madrid":         "Atl. Madrid",
    "Club Atlético de Madrid":    "Atl. Madrid",
    "Atlético de Madrid":         "Atl. Madrid",
    "Real Madrid CF":             "Real Madrid",
    "FC Barcelona":               "Barcelona",
    "Juventus FC":                "Juventus",
    "AC Milan":                   "AC Milan",
    "FC Internazionale Milano":   "Inter",
    "Inter Milan":                "Inter",
    "AFC Ajax":                   "Ajax",
    "Ajax":                       "Ajax",
    "Olympique de Marseille":     "Marseille",
    "Olympique Lyonnais":         "Lyon",
    "Leicester City FC":          "Leicester",
    "Leicester City":             "Leicester",
    "West Ham United FC":         "West Ham",
    "West Ham United":            "West Ham",
    "Wolverhampton Wanderers FC": "Wolves",
    "Wolverhampton Wanderers":    "Wolves",
    "Newcastle United FC":        "Newcastle",
    "Newcastle United":           "Newcastle",
    "Aston Villa FC":             "Aston Villa",
    "Everton FC":                 "Everton",
    "Brighton & Hove Albion FC":  "Brighton",
    "Brighton & Hove Albion":     "Brighton",
    "Fulham FC":                  "Fulham",
    "Brentford FC":               "Brentford",
    "Nottingham Forest FC":       "Nott'm Forest",
    "Nottingham Forest":          "Nott'm Forest",
    "Crystal Palace FC":          "Crystal Palace",
    "Burnley FC":                 "Burnley",
    "Sheffield United FC":        "Sheffield United",
    "Luton Town FC":              "Luton",
    "Luton Town":                 "Luton",
    "VfB Stuttgart":              "Stuttgart",
    "Eintracht Frankfurt":        "Eintr. Frankfurt",
    "RB Leipzig":                 "RB Leipzig",
    "SC Freiburg":                "Freiburg",
    "TSG Hoffenheim":             "Hoffenheim",
    "Borussia Mönchengladbach":   "M'gladbach",
    "FC Augsburg":                "Augsburg",
    "1. FSV Mainz 05":            "Mainz",
    "SV Werder Bremen":           "Werder Bremen",
    "FC Sevilla":                 "Sevilla",
    "Sevilla FC":                 "Sevilla",
    "Real Betis Balompié":        "Betis",
    "Real Sociedad de Fútbol":    "Real Sociedad",
    "Villarreal CF":              "Villarreal",
    "Athletic Club":              "Ath. Bilbao",
    "Valencia CF":                "Valencia",
    "SSC Napoli":                 "Napoli",
    "AS Roma":                    "Roma",
    "SS Lazio":                   "Lazio",
    "Atalanta BC":                "Atalanta",
    "ACF Fiorentina":             "Fiorentina",
    "Torino FC":                  "Torino",
    "Udinese Calcio":             "Udinese",
    "Cagliari Calcio":            "Cagliari",
    "AS Monaco FC":               "Monaco",
    "Stade Rennais FC":           "Rennes",
    "LOSC Lille":                 "Lille",
    "RC Lens":                    "Lens",
    "Stade de Reims":             "Reims",
    "OGC Nice":                   "Nice",
    "RC Strasbourg Alsace":       "Strasbourg",
    "Celtic FC":                  "Celtic",
    "Rangers FC":                 "Rangers",
    "Feyenoord":                  "Feyenoord",
    "PSV":                        "PSV Eindhoven",
    "PSV Eindhoven":              "PSV Eindhoven",
    "AZ Alkmaar":                 "AZ",
}


def _load_elo() -> dict[str, float]:
    df = pd.read_csv(ELO_CSV)
    return {row["team"].strip(): float(row["elo_rating"]) for _, row in df.iterrows()}


def _resolve_name(fdo_name: str, elo_ratings: dict[str, float]) -> str:
    if fdo_name in _FDO_TO_ELO:
        return _FDO_TO_ELO[fdo_name]
    if fdo_name in elo_ratings:
        return fdo_name
    stripped = fdo_name
    for suffix in _STRIP_SUFFIXES:
        if stripped.endswith(suffix):
            stripped = stripped[: -len(suffix)].strip()
            break
    if stripped in elo_ratings:
        return stripped
    fdo_lower = fdo_name.lower()
    for elo_team in elo_ratings:
        if elo_team.lower() in fdo_lower or fdo_lower in elo_team.lower():
            return elo_team
    return fdo_name


def _get_elo(name: str, elo_ratings: dict[str, float]) -> float:
    return elo_ratings.get(name, 1500.0)


def _prematch_probs(home_elo: float, away_elo: float) -> tuple[float, float, float]:
    elo_diff = home_elo - away_elo + HOME_ADVANTAGE
    p_home_raw = 1.0 / (1.0 + 10 ** (-elo_diff / 400))
    p_away_raw = 1.0 / (1.0 + 10 ** (elo_diff / 400))
    closeness = 1.0 - abs(p_home_raw - p_away_raw)
    p_draw = 0.30 * closeness
    remainder = 1.0 - p_draw
    p_home = p_home_raw / (p_home_raw + p_away_raw) * remainder
    p_away = p_away_raw / (p_home_raw + p_away_raw) * remainder
    return p_home, p_draw, p_away


def _make_hash(
    match_date: str, home_team: str, away_team: str,
    p_home: float, p_draw: float, p_away: float,
    predicted_outcome: str, published_at: str,
) -> str:
    raw = (
        f"{match_date}|{home_team}|{away_team}"
        f"|{p_home:.4f}|{p_draw:.4f}|{p_away:.4f}"
        f"|{predicted_outcome}|{published_at}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _fetch_upcoming() -> list[dict]:
    today  = date.today()
    end    = (today + timedelta(days=DAYS_AHEAD)).isoformat()
    resp   = httpx.get(
        f"{FDATA_BASE}/matches",
        headers=HEADERS,
        params={"dateFrom": today.isoformat(), "dateTo": end, "status": "SCHEDULED,TIMED"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("matches", [])


def _load_existing_keys() -> set[str]:
    if not os.path.exists(LOG_CSV):
        return set()
    df = pd.read_csv(LOG_CSV, usecols=["match_date", "home_team", "away_team"], dtype=str)
    return {f"{r.match_date}|{r.home_team}|{r.away_team}" for r in df.itertuples()}


def main() -> None:
    print("Loading Elo ratings...")
    elo_ratings = _load_elo()
    print(f"  {len(elo_ratings)} teams loaded")

    print("Loading existing prediction log...")
    existing_keys = _load_existing_keys()
    print(f"  {len(existing_keys)} existing predictions")

    print("Fetching upcoming fixtures...")
    try:
        matches = _fetch_upcoming()
    except Exception as exc:
        print(f"  ERROR fetching fixtures: {exc}")
        return
    print(f"  {len(matches)} fixtures found")

    published_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_rows: list[dict] = []

    for m in matches:
        home_fdo   = m.get("homeTeam", {}).get("name", "")
        away_fdo   = m.get("awayTeam", {}).get("name", "")
        comp_name  = m.get("competition", {}).get("name", "")
        utc_date   = m.get("utcDate", "")
        match_date = utc_date[:10] if utc_date else None
        match_time = utc_date[11:16] if len(utc_date) >= 16 else None

        if not match_date or not home_fdo or not away_fdo:
            continue

        home_team = _resolve_name(home_fdo, elo_ratings)
        away_team = _resolve_name(away_fdo, elo_ratings)

        key = f"{match_date}|{home_team}|{away_team}"
        if key in existing_keys:
            continue

        home_elo = _get_elo(home_team, elo_ratings)
        away_elo = _get_elo(away_team, elo_ratings)

        p_home, p_draw, p_away = _prematch_probs(home_elo, away_elo)
        predicted_outcome = max({"H": p_home, "D": p_draw, "A": p_away}, key=lambda k: {"H": p_home, "D": p_draw, "A": p_away}[k])

        new_rows.append({
            "match_date":        match_date,
            "match_time":        match_time or "",
            "league":            comp_name,
            "home_team":         home_team,
            "away_team":         away_team,
            "home_elo":          round(home_elo, 1),
            "away_elo":          round(away_elo, 1),
            "p_home":            round(p_home, 4),
            "p_draw":            round(p_draw, 4),
            "p_away":            round(p_away, 4),
            "predicted_outcome": predicted_outcome,
            "published_at":      published_at,
            "hash":              _make_hash(
                match_date, home_team, away_team,
                p_home, p_draw, p_away,
                predicted_outcome, published_at,
            ),
            "actual_result": "",
            "correct":       "",
            "settled_at":    "",
        })
        existing_keys.add(key)

    if not new_rows:
        print("No new predictions to publish.")
        return

    write_header = not os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLS)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"Published {len(new_rows)} new predictions → {LOG_CSV}")


if __name__ == "__main__":
    main()
