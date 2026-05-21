import os
import math
import time
from datetime import date, timedelta

import pandas as pd
import requests
from flask import Blueprint, jsonify

live_bp = Blueprint("live", __name__)

FDATA_API_KEY = "3edbe9850f784e8a86328acaabfd9561"
FDATA_BASE = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": FDATA_API_KEY}

_ELO_RATINGS: dict[str, float] = {}

def _load_elo():
    path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "elo_ratings.csv")
    )
    df = pd.read_csv(path)
    for _, row in df.iterrows():
        _ELO_RATINGS[row["team"].strip()] = float(row["elo_rating"])

_load_elo()

# ---------------------------------------------------------------------------
# Team name normalisation — football-data.org uses long names with suffixes
# ---------------------------------------------------------------------------

_STRIP_SUFFIXES = [
    " FC", " CF", " SC", " AC", " AS", " SS", " SL", " CD", " SD",
    " United", " City", " Town", " Rovers", " Wanderers", " Athletic",
    " Albion", " County", " Palace",
]

# Manual overrides for the most common mismatches
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


def _resolve_elo(fdo_name: str) -> float:
    # 1. Manual override
    if fdo_name in _FDO_TO_ELO:
        mapped = _FDO_TO_ELO[fdo_name]
        if mapped in _ELO_RATINGS:
            return _ELO_RATINGS[mapped]

    # 2. Exact match
    if fdo_name in _ELO_RATINGS:
        return _ELO_RATINGS[fdo_name]

    # 3. Strip common suffixes then try
    stripped = fdo_name
    for suffix in _STRIP_SUFFIXES:
        if stripped.endswith(suffix):
            stripped = stripped[: -len(suffix)].strip()
            break
    if stripped in _ELO_RATINGS:
        return _ELO_RATINGS[stripped]

    # 4. Substring match (ELO key contained in FDO name or vice-versa)
    fdo_lower = fdo_name.lower()
    for elo_team, rating in _ELO_RATINGS.items():
        if elo_team.lower() in fdo_lower or fdo_lower in elo_team.lower():
            return rating

    return 1500.0


# ---------------------------------------------------------------------------
# Probability maths
# ---------------------------------------------------------------------------

def _logit(p: float) -> float:
    p = max(1e-9, min(1 - 1e-9, p))
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _prematch_probs(home_elo: float, away_elo: float) -> tuple[float, float, float]:
    elo_diff = home_elo - away_elo
    p_home = 1.0 / (1.0 + 10 ** (-(elo_diff + 50) / 400))
    # Approximate draw probability using a simple symmetric model
    p_away_win = 1.0 / (1.0 + 10 ** ((elo_diff + 50) / 400))
    p_draw = max(0.0, 1.0 - p_home - p_away_win)
    total = p_home + p_draw + p_away_win
    return p_home / total, p_draw / total, p_away_win / total


def _inplay_probs(
    home_elo: float,
    away_elo: float,
    home_goals: int,
    away_goals: int,
    minute: int,
) -> tuple[float, float, float]:
    p_home_base, _, _ = _prematch_probs(home_elo, away_elo)
    score_diff = home_goals - away_goals
    time_remaining = max(0.0, (90 - minute)) / 90.0

    lead_factor = score_diff * (1.0 - time_remaining) * 2.5
    adjusted = _logit(p_home_base) + lead_factor
    p_home_live = _sigmoid(adjusted)

    p_draw_live = 0.25 * time_remaining * (1.0 / (1.0 + abs(score_diff) * 2))
    p_away_live = max(0.0, 1.0 - p_home_live - p_draw_live)

    total = p_home_live + p_draw_live + p_away_live
    if total > 0:
        p_home_live /= total
        p_draw_live /= total
        p_away_live /= total

    return p_home_live, p_draw_live, p_away_live


# ---------------------------------------------------------------------------
# Simple in-process cache
# ---------------------------------------------------------------------------

_CACHE: dict[str, dict] = {}
CACHE_TTL = 60  # seconds


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["timestamp"]) < CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key: str, data):
    _CACHE[key] = {"timestamp": time.time(), "data": data}


# ---------------------------------------------------------------------------
# Shared match serialiser
# ---------------------------------------------------------------------------

def _parse_match(m: dict, inplay: bool) -> dict:
    home = m.get("homeTeam", {})
    away = m.get("awayTeam", {})
    comp = m.get("competition", {})
    score = m.get("score", {})
    full = score.get("fullTime", {})

    home_name = home.get("name", "")
    away_name = away.get("name", "")
    home_goals = full.get("home")
    away_goals = full.get("away")
    minute_raw = m.get("minute")
    minute = int(minute_raw) if minute_raw is not None else None

    home_elo = _resolve_elo(home_name)
    away_elo = _resolve_elo(away_name)

    # Parse date / time
    utc_date = m.get("utcDate", "")
    match_date = utc_date[:10] if utc_date else None
    match_time = utc_date[11:16] if len(utc_date) >= 16 else None

    if inplay and home_goals is not None and away_goals is not None and minute is not None:
        p_home, p_draw, p_away = _inplay_probs(
            home_elo, away_elo, int(home_goals), int(away_goals), minute
        )
    else:
        p_home, p_draw, p_away = _prematch_probs(home_elo, away_elo)

    return {
        "match_id":   m.get("id"),
        "competition": comp.get("name", ""),
        "home_team":  home_name,
        "away_team":  away_name,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "minute":     minute,
        "status":     m.get("status", ""),
        "p_home":     round(p_home, 4),
        "p_draw":     round(p_draw, 4),
        "p_away":     round(p_away, 4),
        "home_elo":   round(home_elo, 1),
        "away_elo":   round(away_elo, 1),
        "match_date": match_date,
        "match_time": match_time,
    }


def _fetch(url: str, params: dict | None = None) -> dict:
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _ok(records: list) -> tuple:
    return jsonify({
        "success": True,
        "data": records,
        "meta": {"count": len(records)},
    }), 200


def _err(msg: str, code: int = 502) -> tuple:
    return jsonify({"success": False, "error": msg}), code


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@live_bp.get("/live/now")
def live_now():
    cached = _cache_get("live_now")
    if cached is not None:
        return _ok(cached)

    try:
        data = _fetch(f"{FDATA_BASE}/matches", params={"status": "LIVE,IN_PLAY,PAUSED"})
    except requests.RequestException as exc:
        return _err(f"football-data.org error: {exc}")

    records = [_parse_match(m, inplay=True) for m in data.get("matches", [])]
    _cache_set("live_now", records)
    return _ok(records)


@live_bp.get("/live/today")
def live_today():
    cached = _cache_get("live_today")
    if cached is not None:
        return _ok(cached)

    today = date.today().isoformat()
    try:
        data = _fetch(f"{FDATA_BASE}/matches", params={"dateFrom": today, "dateTo": today})
    except requests.RequestException as exc:
        return _err(f"football-data.org error: {exc}")

    records = []
    for m in data.get("matches", []):
        status = m.get("status", "")
        inplay = status in ("IN_PLAY", "PAUSED", "LIVE")
        records.append(_parse_match(m, inplay=inplay))

    _cache_set("live_today", records)
    return _ok(records)


@live_bp.get("/live/upcoming")
def live_upcoming():
    cached = _cache_get("live_upcoming")
    if cached is not None:
        return _ok(cached)

    today = date.today()
    date_to = (today + timedelta(days=7)).isoformat()
    try:
        data = _fetch(
            f"{FDATA_BASE}/matches",
            params={"dateFrom": today.isoformat(), "dateTo": date_to, "status": "SCHEDULED,TIMED"},
        )
    except requests.RequestException as exc:
        return _err(f"football-data.org error: {exc}")

    records = [_parse_match(m, inplay=False) for m in data.get("matches", [])]
    _cache_set("live_upcoming", records)
    return _ok(records)
