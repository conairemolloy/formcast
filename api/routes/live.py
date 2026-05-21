import os
import math
import time
from datetime import date, timedelta
from math import exp, factorial

import pandas as pd
import httpx
from flask import Blueprint, jsonify, request

live_bp = Blueprint("live", __name__)

FDATA_API_KEY = "3edbe9850f784e8a86328acaabfd9561"
FDATA_BASE = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": FDATA_API_KEY}

_ELO_RATINGS: dict[str, float] = {}
_RESULTS_DF: pd.DataFrame | None = None

def _load_elo():
    path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "elo_ratings.csv")
    )
    df = pd.read_csv(path)
    for _, row in df.iterrows():
        _ELO_RATINGS[row["team"].strip()] = float(row["elo_rating"])

def _load_results():
    global _RESULTS_DF
    path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "results.csv")
    )
    df = pd.read_csv(path, low_memory=False)
    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    _RESULTS_DF = df

_load_elo()
_load_results()

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
    elo_diff = home_elo - away_elo + 50  # home advantage
    p_home_raw = 1.0 / (1.0 + 10 ** (-elo_diff / 400))
    p_away_raw = 1.0 / (1.0 + 10 ** (elo_diff / 400))
    # Draw peaks at ~27% for evenly matched teams, shrinks for mismatches
    closeness = 1.0 - abs(p_home_raw - p_away_raw)
    p_draw = 0.30 * closeness
    remainder = 1.0 - p_draw
    p_home = p_home_raw / (p_home_raw + p_away_raw) * remainder
    p_away = p_away_raw / (p_home_raw + p_away_raw) * remainder
    return p_home, p_draw, p_away


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


# ---------------------------------------------------------------------------
# Team name → canonical (results.csv / elo_ratings) resolution
# ---------------------------------------------------------------------------

def _canonical_name(fdo_name: str) -> str:
    if fdo_name in _FDO_TO_ELO:
        return _FDO_TO_ELO[fdo_name]
    if fdo_name in _ELO_RATINGS:
        return fdo_name
    stripped = fdo_name
    for suffix in _STRIP_SUFFIXES:
        if stripped.endswith(suffix):
            stripped = stripped[: -len(suffix)].strip()
            break
    if stripped in _ELO_RATINGS:
        return stripped
    fdo_lower = fdo_name.lower()
    for elo_team in _ELO_RATINGS:
        if elo_team.lower() in fdo_lower or fdo_lower in elo_team.lower():
            return elo_team
    return fdo_name


# ---------------------------------------------------------------------------
# Recent form — last 5 matches for a team
# ---------------------------------------------------------------------------

def _last5_stats(team: str) -> dict:
    df = _RESULTS_DF
    mask = (df["home_team"] == team) | (df["away_team"] == team)
    matches = df[mask].sort_values("match_date", ascending=False).head(5)

    if matches.empty:
        return {
            "avg_scored": None, "avg_conceded": None,
            "avg_corners": None, "avg_yellows": None, "avg_reds": None,
            "form": [],
        }

    scored, conceded, corners, yellows, reds, form = [], [], [], [], [], []

    for _, row in matches.iterrows():
        is_home = row["home_team"] == team
        hg, ag = row.get("home_goals"), row.get("away_goals")
        if is_home:
            if pd.notna(hg): scored.append(float(hg))
            if pd.notna(ag): conceded.append(float(ag))
            c = row.get("home_corners"); y = row.get("home_yellows"); r = row.get("home_reds")
            if pd.notna(hg) and pd.notna(ag):
                form.append("W" if hg > ag else ("D" if hg == ag else "L"))
        else:
            if pd.notna(ag): scored.append(float(ag))
            if pd.notna(hg): conceded.append(float(hg))
            c = row.get("away_corners"); y = row.get("away_yellows"); r = row.get("away_reds")
            if pd.notna(hg) and pd.notna(ag):
                form.append("W" if ag > hg else ("D" if ag == hg else "L"))
        if pd.notna(c): corners.append(float(c))
        if pd.notna(y): yellows.append(float(y))
        if pd.notna(r): reds.append(float(r))

    def _mean(lst):
        return round(sum(lst) / len(lst), 2) if lst else None

    return {
        "avg_scored":   _mean(scored),
        "avg_conceded": _mean(conceded),
        "avg_corners":  _mean(corners),
        "avg_yellows":  _mean(yellows),
        "avg_reds":     _mean(reds),
        "form":         form,
    }


# ---------------------------------------------------------------------------
# Head-to-head — last 10 meetings, summary from home-team perspective
# ---------------------------------------------------------------------------

def _h2h_stats(home: str, away: str) -> dict:
    df = _RESULTS_DF
    mask = (
        ((df["home_team"] == home) & (df["away_team"] == away)) |
        ((df["home_team"] == away) & (df["away_team"] == home))
    )
    h2h = df[mask].sort_values("match_date", ascending=False).head(10)

    if h2h.empty:
        return {"home_wins": 0, "draws": 0, "away_wins": 0, "avg_goals": None, "matches": []}

    home_wins = draws = away_wins = 0
    total_goals = []
    recent = []

    for _, row in h2h.iterrows():
        hg, ag = row.get("home_goals"), row.get("away_goals")
        is_home_perspective = row["home_team"] == home
        date_str = row["match_date"].strftime("%Y-%m-%d") if pd.notna(row["match_date"]) else None

        if pd.notna(hg) and pd.notna(ag):
            total_goals.append(float(hg) + float(ag))
            if hg > ag:
                if is_home_perspective: home_wins += 1
                else: away_wins += 1
            elif hg == ag:
                draws += 1
            else:
                if is_home_perspective: away_wins += 1
                else: home_wins += 1

        if len(recent) < 5:
            recent.append({
                "home_team":  row["home_team"],
                "away_team":  row["away_team"],
                "home_goals": int(hg) if pd.notna(hg) else None,
                "away_goals": int(ag) if pd.notna(ag) else None,
                "date":       date_str,
            })

    return {
        "home_wins": home_wins,
        "draws":     draws,
        "away_wins": away_wins,
        "avg_goals": round(sum(total_goals) / len(total_goals), 2) if total_goals else None,
        "matches":   recent,
    }


# ---------------------------------------------------------------------------
# Poisson / Dixon-Coles goals model
# ---------------------------------------------------------------------------

_LEAGUE_AVG_HOME = 1.35
_LEAGUE_AVG_AWAY = 1.05
_MAX_GOALS = 5


def _poisson_p(lam: float, k: int) -> float:
    return exp(-lam) * (lam ** k) / factorial(k)


def _goals_model(home_form: dict, away_form: dict) -> dict:
    home_scored   = home_form.get("avg_scored")   or _LEAGUE_AVG_HOME
    home_conceded = home_form.get("avg_conceded") or _LEAGUE_AVG_AWAY
    away_scored   = away_form.get("avg_scored")   or _LEAGUE_AVG_AWAY
    away_conceded = away_form.get("avg_conceded") or _LEAGUE_AVG_HOME

    # Normalise attack × defence against league baseline
    lam_h = max(0.3, min(4.0, home_scored * away_conceded / _LEAGUE_AVG_AWAY))
    lam_a = max(0.2, min(3.5, away_scored * home_conceded / _LEAGUE_AVG_HOME))

    # Score probability matrix
    score_list = []
    for h in range(_MAX_GOALS + 1):
        for a in range(_MAX_GOALS + 1):
            p = _poisson_p(lam_h, h) * _poisson_p(lam_a, a)
            score_list.append((f"{h}-{a}", round(p, 4)))
    score_matrix = dict(score_list)

    score_list.sort(key=lambda x: -x[1])
    top_scores = [{"score": s, "prob": p} for s, p in score_list[:8]]

    # Over / under
    over_under = {}
    for t in (0.5, 1.5, 2.5, 3.5):
        p_over = sum(
            _poisson_p(lam_h, h) * _poisson_p(lam_a, a)
            for h in range(_MAX_GOALS + 1)
            for a in range(_MAX_GOALS + 1)
            if h + a > t
        )
        over_under[str(t)] = {"over": round(p_over, 4), "under": round(1 - p_over, 4)}

    p_h0 = _poisson_p(lam_h, 0)
    p_a0 = _poisson_p(lam_a, 0)

    return {
        "lambda_home":    round(lam_h, 3),
        "lambda_away":    round(lam_a, 3),
        "score_matrix":   score_matrix,
        "top_scores":     top_scores,
        "over_under":     over_under,
        "btts":           round((1 - p_h0) * (1 - p_a0), 4),
        "home_to_score":  round(1 - p_h0, 4),
        "away_to_score":  round(1 - p_a0, 4),
    }


def _fetch(url: str, params: dict | None = None) -> dict:
    resp = httpx.get(url, headers=HEADERS, params=params, timeout=10)
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
    except (httpx.HTTPError, Exception) as exc:
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
    except (httpx.HTTPError, Exception) as exc:
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
    except (httpx.HTTPError, Exception) as exc:
        return _err(f"football-data.org error: {exc}")

    records = [_parse_match(m, inplay=False) for m in data.get("matches", [])]
    _cache_set("live_upcoming", records)
    return _ok(records)


@live_bp.get("/match/preview")
def match_preview():
    home_team = request.args.get("home_team", "").strip()
    away_team = request.args.get("away_team", "").strip()

    if not home_team or not away_team:
        return _err("home_team and away_team are required", 400)

    home_canon = _canonical_name(home_team)
    away_canon = _canonical_name(away_team)

    home_elo = _resolve_elo(home_team)
    away_elo = _resolve_elo(away_team)
    p_home, p_draw, p_away = _prematch_probs(home_elo, away_elo)

    home_form = _last5_stats(home_canon)
    away_form = _last5_stats(away_canon)
    h2h       = _h2h_stats(home_canon, away_canon)
    goals     = _goals_model(home_form, away_form)

    return jsonify({
        "success": True,
        "data": {
            "home_team":  home_team,
            "away_team":  away_team,
            "home_canon": home_canon,
            "away_canon": away_canon,
            "home_elo":   round(home_elo, 1),
            "away_elo":   round(away_elo, 1),
            "p_home":     round(p_home, 4),
            "p_draw":     round(p_draw, 4),
            "p_away":     round(p_away, 4),
            "home_form":  home_form,
            "away_form":  away_form,
            "h2h":        h2h,
            "goals":      goals,
        },
    }), 200
