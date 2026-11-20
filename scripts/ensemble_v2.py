"""
Stacking ensemble (v2) — extends ensemble.py with the full 76-feature base model.

Stack inputs (13 features):
  home_expected, p_home_g2,
  p_home_dc, p_draw_dc, p_away_dc,
  p_home_xgb, p_draw_xgb, p_away_xgb,
  elo_diff, h2h_goal_diff_avg, h2h_home_win_rate, momentum_diff,
  draw_prob

Meta-learner: LogisticRegression in a StandardScaler Pipeline.

main() evaluates models fit on the first 80% against the last 20% (holdout),
then refits everything on 100% of the data and saves THOSE as the deployed
models, so serving never lags the most recent ~20% of matches.
"""
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STARTING_ELO = 1500.0
ELO_K = 16
ELO_HA = 50
ELO_HA_HOME = 50        # kept for global Elo compatibility
HOME_ELO_K_SCALE = 1.0  # home/away K same as global for now
COLD_START = 200
FORM_WINDOW = 5
EWM_ALPHA = 0.4
LATE_EWM_ALPHA = 0.6
DECAY = 0.85   # exponential decay weight for rolling windows (xG, goals, clean sheets)
# xG older than this (relative to the match being predicted) is treated as
# missing -> the 1.3 / 0.0 defaults. Stops a data gap (e.g. a dead xG feed, or
# a team returning from a lower league) freezing months-old xG as "current form".
# 120 rather than 90 so the last weeks of the previous season survive the
# summer break (late May -> mid Aug is ~85 days).
XG_MAX_AGE_DAYS = 120

G2_SCALE = 173.7178
G2_INITIAL_PHI = 200.0 / G2_SCALE
G2_SIGMA = 0.06
G2_HA = 50.0 / G2_SCALE

DC_WINDOW = 38
DC_HOME_ADV = 0.1
DC_MAX_GOALS = 8

RESULT_MAP = {"A": 0, "D": 1, "H": 2}
RESULT_INV = {0: "A", 1: "D", 2: "H"}

REGRESSION_FACTOR = 0.75   # fraction of Elo deviation from league mean retained at season start
HA_MIN_MATCHES    = 100    # min league matches before using learned per-league home advantage

DERBY_PAIRS: frozenset = frozenset({
    # Top-flight derbies
    frozenset({"Arsenal", "Tottenham"}),
    frozenset({"Liverpool", "Everton"}),
    frozenset({"Man United", "Man City"}),
    frozenset({"Barcelona", "Real Madrid"}),
    frozenset({"Barcelona", "Espanol"}),
    frozenset({"Real Madrid", "Ath Madrid"}),
    frozenset({"Sevilla", "Betis"}),
    frozenset({"Milan", "Inter"}),
    frozenset({"Roma", "Lazio"}),
    frozenset({"Juventus", "Torino"}),
    frozenset({"Dortmund", "Schalke 04"}),
    frozenset({"Bayern Munich", "M'Gladbach"}),
    frozenset({"Bayern Munich", "M'gladbach"}),   # dataset has both spellings
    frozenset({"Paris SG", "Marseille"}),
    frozenset({"Lyon", "St Etienne"}),
    frozenset({"Celtic", "Rangers"}),
    # Second-tier derbies
    frozenset({"Leeds", "Bradford"}),
    frozenset({"Sunderland", "Middlesbrough"}),
    frozenset({"Derby", "Nott'm Forest"}),
    frozenset({"Sheffield United", "Sheffield Weds"}),
    frozenset({"Hamburg", "St Pauli"}),
    frozenset({"Hannover", "Braunschweig"}),
})

# ---------------------------------------------------------------------------
# Stadium geography — loaded once at import time from data/reference/stadiums.csv
# Both raw and .strip() variants registered so trailing-space artefacts in
# results.csv (e.g. "Kaiserslautern ") still resolve correctly.
# ---------------------------------------------------------------------------

_STADIUMS_CSV = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "reference", "stadiums.csv")
)
_STADIUM_LOOKUP: dict[str, dict] = {}


def _load_stadiums() -> None:
    if not os.path.exists(_STADIUMS_CSV):
        return
    df = pd.read_csv(_STADIUMS_CSV, keep_default_na=False)
    for _, row in df.iterrows():
        raw = str(row["team"])
        try:
            entry = {
                "lat": float(row["latitude"])  if row["latitude"]  != "" else None,
                "lng": float(row["longitude"]) if row["longitude"] != "" else None,
                "alt": float(row["altitude_m"]) if row["altitude_m"] != "" else None,
                "cap": float(row["capacity"])  if row["capacity"]  != "" else None,
            }
        except (ValueError, KeyError):
            entry = {"lat": None, "lng": None, "alt": None, "cap": None}
        _STADIUM_LOOKUP[raw] = entry
        stripped = raw.strip()
        if stripped != raw:
            _STADIUM_LOOKUP.setdefault(stripped, entry)


_load_stadiums()


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(phi1) * math.cos(phi2)
         * math.sin(math.radians(lng2 - lng1) / 2) ** 2)
    return 2.0 * R * math.asin(math.sqrt(a))


# Full 85-feature set used for XGBoost base model
FEATURE_COLS = [
    "home_elo", "away_elo", "elo_diff", "home_expected",
    "home_elo_home", "home_elo_away", "away_elo_home", "away_elo_away", "venue_elo_diff",
    "home_g2_rating", "away_g2_rating", "g2_diff", "home_g2_uncertainty",
    "home_form", "away_form", "form_diff",
    "home_goals_scored_avg", "home_goals_conceded_avg",
    "away_goals_scored_avg", "away_goals_conceded_avg",
    "home_xg_avg", "home_xg_conceded_avg", "away_xg_avg",
    "away_xg_conceded_avg", "home_xg_diff_avg", "away_xg_diff_avg",
    "home_result_momentum", "away_result_momentum",
    "home_score_momentum", "away_score_momentum",
    "home_elo_momentum", "away_elo_momentum",
    "momentum_diff",
    "home_days_rest", "away_days_rest",
    "home_matches_21d", "away_matches_21d",
    "rest_asymmetry",
    "home_fatigue_score", "away_fatigue_score",
    "h2h_home_win_rate", "h2h_goal_diff_avg",
    "home_unbeaten_run", "away_unbeaten_run",
    "league_encoded",
    # Referee
    "ref_avg_yellows", "ref_avg_fouls", "ref_home_bias", "ref_experience",
    # Venue win rates
    "home_win_rate", "away_win_rate", "venue_win_rate_diff",
    # Season phase
    "home_season_matches", "away_season_matches",
    # Clean sheet rate
    "home_cs_rate", "away_cs_rate",
    # Opponent-adjusted form
    "home_opp_adj_form", "away_opp_adj_form",
    # Relegation/title pressure
    "home_pressure", "away_pressure", "pressure_diff",
    # Late-season form (stronger EWM alpha, non-zero only when is_late_season == 1)
    "late_season_form_diff",
    # Shot conversion (goals / shots, last 10 matches with shot data)
    "home_shot_conversion", "away_shot_conversion",
    # H2H all-time dominance (over entire history)
    "h2h_all_time_dominance",
    # Derby fixture flag
    "is_derby",
    # Home/Away Glicko-2 split (venue-specific ratings + away uncertainty)
    "home_g2_home", "away_g2_away", "g2_venue_diff", "away_g2_uncertainty",
    # Feature interactions
    "elo_x_form", "fatigue_x_congestion", "derby_x_h2h",
    # Stadium geography (fallback 0.0 when either stadium unknown)
    "away_travel_km", "altitude_diff", "home_capacity_log",
    # Season edge flags (binary; SHAP undervalues due to rare activation but backtest impact is real)
    "is_early_season", "is_late_season",
]

# 13-feature stack fed into the meta-learner
STACK_COLS = [
    "home_expected",
    "p_home_g2",
    "p_home_dc", "p_draw_dc", "p_away_dc",
    "p_home_xgb", "p_draw_xgb", "p_away_xgb",
    "elo_diff", "h2h_goal_diff_avg", "h2h_home_win_rate", "momentum_diff",
    "draw_prob",
]

DRAW_COLS = [
    "elo_diff", "p_draw_dc", "home_form", "away_form",
    "ref_avg_yellows", "home_win_rate", "away_win_rate",
    "is_late_season", "home_goals_scored_avg", "away_goals_scored_avg",
    "rest_asymmetry", "venue_elo_diff", "h2h_home_win_rate",
]


# ---------------------------------------------------------------------------
# Elo helpers
# ---------------------------------------------------------------------------

def _elo_expected(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def _elo_mov(goal_diff: int) -> float:
    return min(2.0, 1.0 + math.log(1.0 + abs(goal_diff)) / math.log(10.0))


# ---------------------------------------------------------------------------
# Glicko-2 helpers (simplified: constant sigma, no volatility iteration)
# ---------------------------------------------------------------------------

def _g2_g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / (math.pi * math.pi))


def _g2_E(mu: float, opp_mu: float, opp_phi: float) -> float:
    return 1.0 / (1.0 + math.exp(-_g2_g(opp_phi) * (mu - opp_mu)))


def _g2_update(
    mu: float, phi: float,
    opp_mu: float, opp_phi: float,
    score: float, ha: float = 0.0,
) -> tuple[float, float]:
    phi_star = math.sqrt(phi * phi + G2_SIGMA * G2_SIGMA)
    g_j = _g2_g(opp_phi)
    E_j = _g2_E(mu + ha, opp_mu, opp_phi)
    v = 1.0 / (g_j * g_j * E_j * (1.0 - E_j))
    phi_new = 1.0 / math.sqrt(1.0 / (phi_star * phi_star) + 1.0 / v)
    mu_new = mu + phi_new * phi_new * g_j * (score - E_j)
    return mu_new, phi_new


# ---------------------------------------------------------------------------
# Momentum / streak helpers
# ---------------------------------------------------------------------------

def _ewm(values: list, alpha: float = EWM_ALPHA) -> float:
    n = len(values)
    weights = [(1.0 - alpha) ** (n - 1 - i) for i in range(n)]
    total = sum(weights)
    return sum(w * v for w, v in zip(weights, values)) / total


def _decay_mean(values: list, decay: float = DECAY) -> float:
    """Exponentially decay-weighted mean: most-recent match has weight 1, oldest DECAY^(n-1)."""
    if not values:
        return 0.0
    n = len(values)
    weights = [decay ** (n - 1 - i) for i in range(n)]
    total = sum(weights)
    return sum(w * v for w, v in zip(weights, values)) / total


def _streak(hist: list) -> int:
    if not hist:
        return 0
    last = hist[-1]["result"]
    if last == "D":
        return 0
    sign = 1 if last == "W" else -1
    count = 0
    for h in reversed(hist):
        if (sign == 1 and h["result"] == "W") or (sign == -1 and h["result"] == "L"):
            count += 1
        else:
            break
    return sign * count


def _elo_28d_ago(elo_hist: list, match_date) -> float | None:
    cutoff = match_date - timedelta(days=28)
    result = None
    for date, rating in elo_hist:
        if date <= cutoff:
            result = rating
        else:
            break
    return result


def _h2h_key(a: str, b: str) -> tuple:
    return (min(a, b), max(a, b))


# ---------------------------------------------------------------------------
# Per-team feature bundle (mirrors full_feature_pipeline.py exactly)
# ---------------------------------------------------------------------------

def _team_features(
    hist: list,
    elo_hist: list,
    current_elo: float,
    match_date,
    season: str,
) -> dict:
    n = len(hist)

    fw = hist[-FORM_WINDOW:]
    if fw:
        nf = len(fw)
        form   = sum(h["points"] for h in fw) / (3.0 * nf)
        gs_avg = _decay_mean([h["goals_scored"]   for h in fw])
        gc_avg = _decay_mean([h["goals_conceded"] for h in fw])
    else:
        form, gs_avg, gc_avg = 0.5, 1.5, 1.5

    rm = _ewm([h["points"] for h in hist[-5:]]) / 3.0 if n >= 2 else 0.5

    if n >= 2:
        sm_raw = float(np.clip(_ewm([h["goal_diff"] for h in hist[-5:]]), -5.0, 5.0))
        sm = (sm_raw + 5.0) / 10.0
    else:
        sm = 0.5

    past_elo = _elo_28d_ago(elo_hist, match_date)
    elo_mom = (current_elo - past_elo) / 100.0 if past_elo is not None else 0.0

    streak = (float(np.clip(_streak(hist), -5, 5)) + 5.0) / 10.0

    cut21 = match_date - timedelta(days=21)
    matches_21d = sum(1 for h in hist if h["date"] > cut21)
    days_rest   = (match_date - hist[-1]["date"]).days if hist else 14

    season_hist = [h for h in hist if h["season"] == season]
    season_pos  = len(season_hist)
    is_early    = 1 if season_pos < 5 else 0
    post_loss   = 1 if (hist and hist[-1]["result"] == "L") else 0

    unbeaten = 0
    for h in reversed(hist):
        if h["result"] in ("W", "D"):
            unbeaten += 1
        else:
            break
    unbeaten = min(unbeaten, 15)

    xg_cut       = match_date - timedelta(days=XG_MAX_AGE_DAYS)
    all_xg_hist  = [h for h in hist if h.get("xg_scored") is not None and h["date"] >= xg_cut]
    home_xg_hist = [h for h in all_xg_hist if h.get("is_home") is True]
    away_xg_hist = [h for h in all_xg_hist if h.get("is_home") is False]

    fw_hxg     = home_xg_hist[-FORM_WINDOW:]
    fw_axg     = away_xg_hist[-FORM_WINDOW:]
    fw_axg_all = all_xg_hist[-FORM_WINDOW:]

    xg_scored_home_avg   = _decay_mean([h["xg_scored"]   for h in fw_hxg])     if fw_hxg     else 1.3
    xg_conceded_home_avg = _decay_mean([h["xg_conceded"] for h in fw_hxg])     if fw_hxg     else 1.3
    xg_scored_away_avg   = _decay_mean([h["xg_scored"]   for h in fw_axg])     if fw_axg     else 1.3
    xg_conceded_away_avg = _decay_mean([h["xg_conceded"] for h in fw_axg])     if fw_axg     else 1.3
    xg_diff_avg          = _decay_mean([h["xg_diff"]     for h in fw_axg_all]) if fw_axg_all else 0.0

    return {
        "form": form, "gs_avg": gs_avg, "gc_avg": gc_avg,
        "result_momentum": rm, "score_momentum": sm,
        "elo_momentum": elo_mom, "streak": streak,
        "days_rest": days_rest, "matches_21d": matches_21d,
        "season_pos": season_pos, "is_early": is_early,
        "post_loss": post_loss, "unbeaten_run": unbeaten,
        "xg_scored_home_avg": xg_scored_home_avg,
        "xg_conceded_home_avg": xg_conceded_home_avg,
        "xg_scored_away_avg": xg_scored_away_avg,
        "xg_conceded_away_avg": xg_conceded_away_avg,
        "xg_diff_avg": xg_diff_avg,
    }


# ---------------------------------------------------------------------------
# H2H features
# ---------------------------------------------------------------------------

def _h2h_features(records: list, home: str) -> dict:
    if not records:
        return {
            "h2h_home_win_rate": 0.45, "h2h_goal_diff_avg": 0.0,
            "h2h_meetings": 0, "h2h_dominance": 0.0, "revenge_factor": 0,
        }
    recent = records[-10:]
    n = len(recent)
    hw = aw = dw = 0
    gd_total = 0.0
    for rec in recent:
        if rec["home"] == home:
            gd = rec["hg"] - rec["ag"]
            if rec["result"] == "H":   hw += 1
            elif rec["result"] == "A": aw += 1
            else:                      dw += 1
        else:
            gd = rec["ag"] - rec["hg"]
            if rec["result"] == "A":   hw += 1
            elif rec["result"] == "H": aw += 1
            else:                      dw += 1
        gd_total += gd
    win_rate = hw / n
    last = records[-1]
    revenge = (1 if last["result"] == "A" else 0) if last["home"] == home \
              else (1 if last["result"] == "H" else 0)
    return {
        "h2h_home_win_rate": win_rate, "h2h_goal_diff_avg": gd_total / n,
        "h2h_meetings": n, "h2h_dominance": win_rate - 0.45, "revenge_factor": revenge,
    }


# ---------------------------------------------------------------------------
# Fatigue score
# ---------------------------------------------------------------------------

def _fatigue_score(days_rest: int, matches_21d: int, asymmetry: float, home: bool) -> float:
    score = 0.0
    if days_rest < 4:
        score -= 40.0
    if matches_21d >= 3:
        score -= 20.0 * (matches_21d - 2)
    score += asymmetry * 5.0 if home else -asymmetry * 5.0
    return score / 100.0


# ---------------------------------------------------------------------------
# Shot-conversion helper
# ---------------------------------------------------------------------------

def _shot_conversion(hist: list) -> float:
    """Rolling goals-per-shot over the last 10 matches that have shot data."""
    recent = [h for h in hist[-10:] if h.get("shots") is not None and h["shots"] > 0]
    if not recent:
        return 0.11
    total_shots = sum(h["shots"] for h in recent)
    total_goals = sum(h["goals_scored"] for h in recent)
    return total_goals / total_shots if total_shots > 0 else 0.11


# ---------------------------------------------------------------------------
# Rolling Dixon-Coles helpers (from ensemble.py)
# ---------------------------------------------------------------------------

def _dc_attack(scored: list) -> float:
    if not scored:
        return 0.0
    return float(np.log(max(np.mean(scored), 0.01)))


def _dc_defence(conceded: list) -> float:
    if not conceded:
        return 0.0
    return float(-np.log(max(np.mean(conceded), 0.01)))


def _dc_probs(lam: float, mu: float, rho: float = -0.13) -> tuple[float, float, float]:
    lam = max(lam, 1e-10)
    mu  = max(mu,  1e-10)
    k = np.arange(DC_MAX_GOALS + 1)
    hpmf = np.array([math.exp(-lam) * lam**i / math.factorial(i) for i in k])
    apmf = np.array([math.exp(-mu)  * mu**i  / math.factorial(i) for i in k])
    score = np.outer(hpmf, apmf)
    score[0, 0] *= 1.0 - lam * mu * rho
    score[0, 1] *= 1.0 + lam * rho
    score[1, 0] *= 1.0 + mu * rho
    score[1, 1] *= 1.0 - rho
    ii, jj = np.meshgrid(k, k, indexing="ij")
    return float(score[ii > jj].sum()), float(score[ii == jj].sum()), float(score[ii < jj].sum())


# ---------------------------------------------------------------------------
# Unified single-pass feature builder
# ---------------------------------------------------------------------------
# Walk-forward state: init / pre-match adjust / compute features / post-match update
# ---------------------------------------------------------------------------

def init_state() -> dict:
    """Return a fresh state dict for walk-forward feature computation."""
    return {
        "elo":        defaultdict(lambda: STARTING_ELO),
        "g2":         defaultdict(lambda: (0.0, G2_INITIAL_PHI)),
        "g2_home":    defaultdict(lambda: (0.0, G2_INITIAL_PHI)),
        "g2_away":    defaultdict(lambda: (0.0, G2_INITIAL_PHI)),
        "elo_home":   {},
        "elo_away":   {},
        "team_hist":  defaultdict(list),
        "elo_hist":   defaultdict(list),
        "h2h_hist":   defaultdict(list),
        "h2h_totals": {},
        "dc_scored":  defaultdict(list),
        "dc_conceded": defaultdict(list),
        "ref_stats":  {},
        "global_matches":   0,
        "global_home_wins": 0,
        "team_home_record":   {},
        "team_away_record":   {},
        "team_season_matches": {},
        "team_cs_home": {},
        "team_cs_away": {},
        "team_opp_adj_form": {},
        "team_season_points": {},
        "team_season_gd":     {},
        "league_season_teams": {},
        "team_last_season": {},
        "team_last_league": {},
        "league_elo_tracker": {},
        "league_hw": {},
        "league_nm": {},
    }


def _apply_pre_match_adjustments(
    state: dict,
    home: str,
    away: str,
    season: str,
    league: str,
) -> list:
    """
    Apply season-boundary Elo regression and promotion/relegation shift for home
    and away. Idempotent: a second call with the same (home, away, season, league)
    is a no-op because team_last_season/team_last_league are updated on the first
    call.

    Returns a list of event dicts fired this call (empty when idempotent).
    Each dict has keys: type ('regress' or 'promo'), team, and context fields.
    """
    events = []
    for _team in (home, away):
        _prev_season = state["team_last_season"].get(_team)
        _prev_league = state["team_last_league"].get(_team)

        if _prev_season is not None and _prev_season != season:
            _tracker = state["league_elo_tracker"].get(league, {})
            _lg_mean = float(np.mean(list(_tracker.values()))) if _tracker else STARTING_ELO
            _ha_mean = float(np.mean(list(state["elo_home"].values()))) if state["elo_home"] else STARTING_ELO
            _aa_mean = float(np.mean(list(state["elo_away"].values()))) if state["elo_away"] else STARTING_ELO
            state["elo"][_team]      = _lg_mean + REGRESSION_FACTOR * (state["elo"][_team] - _lg_mean)
            state["elo_home"][_team] = _ha_mean + REGRESSION_FACTOR * (state["elo_home"].get(_team, STARTING_ELO) - _ha_mean)
            state["elo_away"][_team] = _aa_mean + REGRESSION_FACTOR * (state["elo_away"].get(_team, STARTING_ELO) - _aa_mean)
            events.append({
                "type": "regress", "team": _team,
                "from_season": _prev_season, "to_season": season, "league": league,
            })

        if _prev_league is not None and _prev_league != league:
            _old_tracker = state["league_elo_tracker"].get(_prev_league, {})
            _new_tracker = state["league_elo_tracker"].get(league, {})
            _old_lg_mean = float(np.mean(list(_old_tracker.values()))) if _old_tracker else STARTING_ELO
            _new_lg_mean = float(np.mean(list(_new_tracker.values()))) if _new_tracker else STARTING_ELO
            _shift = 0.5 * (_new_lg_mean - _old_lg_mean)
            _old_e = state["elo"][_team]
            state["elo"][_team]      += _shift
            state["elo_home"][_team]  = state["elo_home"].get(_team, STARTING_ELO) + _shift
            state["elo_away"][_team]  = state["elo_away"].get(_team, STARTING_ELO) + _shift
            events.append({
                "type": "promo", "team": _team,
                "from_league": _prev_league, "to_league": league,
                "old_elo": _old_e, "new_elo": state["elo"][_team],
            })

        state["team_last_season"][_team] = season
        state["team_last_league"][_team] = league

    return events


def compute_match_features(
    state: dict,
    home: str,
    away: str,
    date,
    season: str,
    league: str,
    league_enc: dict,
    *,
    xg_vals: tuple | None = None,
    ref_raw: str | None = None,
) -> dict:
    """
    Compute the full feature dict for one fixture using the current pre-match
    state. Calls _apply_pre_match_adjustments first (idempotent — no-op if
    already applied by the caller). Does NOT update state with the match result;
    call update_state() after this to advance the walk-forward state.

    Returns a dict with all 85 FEATURE_COLS keys plus p_home_dc/p_draw_dc/
    p_away_dc (stack inputs not in FEATURE_COLS),
    and prediction_uncertainty (metadata only, not in FEATURE_COLS).
    """
    _apply_pre_match_adjustments(state, home, away, season, league)

    elo         = state["elo"]
    g2          = state["g2"]
    elo_home    = state["elo_home"]
    elo_away    = state["elo_away"]
    team_hist   = state["team_hist"]
    elo_hist_s  = state["elo_hist"]
    h2h_hist    = state["h2h_hist"]
    dc_scored   = state["dc_scored"]
    dc_conceded = state["dc_conceded"]

    home_elo = elo[home]
    away_elo = elo[away]

    # Per-league home advantage (learned from prior matches)
    _lg_nm        = state["league_nm"].get(league, 0)
    _gm           = state["global_matches"]
    _ghw          = state["global_home_wins"]
    if _lg_nm >= HA_MIN_MATCHES and _gm > 0:
        _global_hw_rate = _ghw / _gm
        _lg_hw_rate     = state["league_hw"].get(league, 0) / _lg_nm
        _ha_league = float(np.clip(
            ELO_HA * (_lg_hw_rate / _global_hw_rate) if _global_hw_rate > 0 else ELO_HA,
            0.5 * ELO_HA, 1.5 * ELO_HA,
        ))
    else:
        _ha_league = ELO_HA
    home_exp = _elo_expected(home_elo + _ha_league, away_elo)

    home_mu, home_phi = g2[home]
    away_mu, away_phi = g2[away]
    home_g2_rat = home_mu * G2_SCALE + 1500.0
    away_g2_rat = away_mu * G2_SCALE + 1500.0

    # Venue-specific G2 ratings (home team's home rating, away team's away rating)
    home_g2h_mu, _ = state["g2_home"][home]
    away_g2a_mu, _ = state["g2_away"][away]
    home_g2h_rating = home_g2h_mu * G2_SCALE + 1500.0
    away_g2a_rating = away_g2a_mu * G2_SCALE + 1500.0

    # Rolling Dixon-Coles probabilities
    atk_h = _dc_attack(dc_scored[home])
    def_h = _dc_defence(dc_conceded[home])
    atk_a = _dc_attack(dc_scored[away])
    def_a = _dc_defence(dc_conceded[away])
    lam   = math.exp(atk_h - def_a + DC_HOME_ADV)
    mu_dc = math.exp(atk_a - def_h)
    p_home_dc, p_draw_dc, p_away_dc = _dc_probs(lam, mu_dc)

    # Include current pre-match Elo in the history snapshot (for momentum)
    h_elo_hist = list(elo_hist_s[home]) + [(date, home_elo)]
    a_elo_hist = list(elo_hist_s[away]) + [(date, away_elo)]

    hf  = _team_features(list(team_hist[home]), h_elo_hist, home_elo, date, season)
    af  = _team_features(list(team_hist[away]), a_elo_hist, away_elo, date, season)
    h2h = _h2h_features(h2h_hist[_h2h_key(home, away)], home)

    asymmetry = float(np.clip(hf["days_rest"] - af["days_rest"], -10, 10))
    home_fat  = _fatigue_score(hf["days_rest"], hf["matches_21d"], asymmetry, home=True)
    away_fat  = _fatigue_score(af["days_rest"], af["matches_21d"], asymmetry, home=False)

    home_comp = (hf["result_momentum"] + hf["score_momentum"]
                 + hf["elo_momentum"]  + hf["streak"]) / 4.0
    away_comp = (af["result_momentum"] + af["score_momentum"]
                 + af["elo_momentum"]  + af["streak"]) / 4.0

    # Referee features (from prior matches only)
    if ref_raw and ref_raw in state["ref_stats"]:
        rs = state["ref_stats"][ref_raw]
        _global_hw_rate_ref = (_ghw / _gm) if _gm > 0 else 0.457
        ref_avg_yellows = rs["yellows_total"] / rs["matches"]
        ref_avg_fouls   = rs["fouls_total"]   / rs["matches"]
        ref_home_bias   = (rs["home_wins"] / rs["matches"]) - _global_hw_rate_ref
        ref_experience  = rs["matches"]
    else:
        ref_avg_yellows = 3.8
        ref_avg_fouls   = 23.0
        ref_home_bias   = 0.0
        ref_experience  = 0

    # Venue win rates
    _hwr = state["team_home_record"].get(home)
    _awr = state["team_away_record"].get(away)
    home_win_rate       = float(np.mean(_hwr)) if _hwr else 0.46
    away_win_rate       = float(np.mean(_awr)) if _awr else 0.28
    venue_win_rate_diff = home_win_rate - away_win_rate

    # Season phase
    home_season_matches = state["team_season_matches"].get((home, season), 0)
    away_season_matches = state["team_season_matches"].get((away, season), 0)
    is_late_season      = 1 if min(home_season_matches, away_season_matches) >= 28 else 0

    # Clean sheet rates (last 10 home/away matches, decay-weighted)
    _hcs = state["team_cs_home"].get(home, [])[-10:]
    _acs = state["team_cs_away"].get(away, [])[-10:]
    home_cs_rate = _decay_mean(_hcs) if _hcs else 0.28
    away_cs_rate = _decay_mean(_acs) if _acs else 0.22

    # Opponent-adjusted form (last 10)
    _WINDOW = 10
    home_opp_adj = float(np.mean(state["team_opp_adj_form"].get(home, [])[-_WINDOW:])) if state["team_opp_adj_form"].get(home) else 0.0
    away_opp_adj = float(np.mean(state["team_opp_adj_form"].get(away, [])[-_WINDOW:])) if state["team_opp_adj_form"].get(away) else 0.0

    # Relegation/title pressure from current season standings
    league_teams = state["league_season_teams"].get((season, league), [])
    if len(league_teams) >= 4:
        all_pts  = [(t, state["team_season_points"].get((t, season, league), 0)) for t in league_teams]
        all_pts.sort(key=lambda x: -x[1])
        n_teams  = len(league_teams)
        home_pos = next((i + 1 for i, (t, _) in enumerate(all_pts) if t == home), n_teams // 2)
        away_pos = next((i + 1 for i, (t, _) in enumerate(all_pts) if t == away), n_teams // 2)
        home_pressure = 1 if home_pos <= 3 else (-1 if home_pos >= n_teams - 2 else 0)
        away_pressure = 1 if away_pos <= 3 else (-1 if away_pos >= n_teams - 2 else 0)
    else:
        home_pressure, away_pressure = 0, 0

    # Late-season form diff (stronger EWM alpha when is_late_season)
    if is_late_season:
        _h5 = list(team_hist[home])[-FORM_WINDOW:]
        _a5 = list(team_hist[away])[-FORM_WINDOW:]
        _hlf = _ewm([h["points"] for h in _h5], alpha=LATE_EWM_ALPHA) / 3.0 if len(_h5) >= 2 else 0.5
        _alf = _ewm([h["points"] for h in _a5], alpha=LATE_EWM_ALPHA) / 3.0 if len(_a5) >= 2 else 0.5
        late_season_form_diff = _hlf - _alf
    else:
        late_season_form_diff = 0.0

    # Shot conversion (goals / shots, last 10 matches per team with shot data)
    home_shot_conv = _shot_conversion(list(team_hist[home]))
    away_shot_conv = _shot_conversion(list(team_hist[away]))

    # H2H all-time dominance (win margin / total meetings, entire history)
    _hkey_all = _h2h_key(home, away)
    _htot = state["h2h_totals"].get(_hkey_all)
    if _htot and _htot["meetings"] > 0:
        _home_wins_all = _htot["wins_a"] if home == _hkey_all[0] else _htot["wins_b"]
        _away_wins_all = _htot["wins_b"] if home == _hkey_all[0] else _htot["wins_a"]
        h2h_all_time_dominance = (_home_wins_all - _away_wins_all) / _htot["meetings"]
    else:
        h2h_all_time_dominance = 0.0

    # Derby flag
    is_derby = 1 if frozenset({home, away}) in DERBY_PAIRS else 0

    # Feature interactions (computed from already-resolved values — no state changes)
    _elo_diff  = home_elo - away_elo
    _form_diff = hf["form"] - af["form"]
    elo_x_form           = _elo_diff * _form_diff / 100.0
    fatigue_x_congestion = asymmetry * (hf["matches_21d"] - af["matches_21d"])
    derby_x_h2h          = is_derby * h2h_all_time_dominance

    # Stadium geography features (haversine distance + altitude differential + capacity)
    _hs = _STADIUM_LOOKUP.get(home) or _STADIUM_LOOKUP.get(home.strip(), {})
    _as = _STADIUM_LOOKUP.get(away) or _STADIUM_LOOKUP.get(away.strip(), {})
    _h_lat, _h_lng = _hs.get("lat"), _hs.get("lng")
    _a_lat, _a_lng = _as.get("lat"), _as.get("lng")
    away_travel_km = (
        _haversine_km(_h_lat, _h_lng, _a_lat, _a_lng)
        if _h_lat is not None and _a_lat is not None
        else 0.0
    )
    altitude_diff    = float((_hs.get("alt") or 0.0) - (_as.get("alt") or 0.0))
    home_capacity_log = math.log10(_hs["cap"]) if _hs.get("cap") else math.log10(20000.0)

    # Prediction uncertainty (metadata — NOT in FEATURE_COLS)
    prediction_uncertainty = (home_phi + away_phi) / (2.0 * G2_INITIAL_PHI)

    return {
        # Elo
        "home_elo": home_elo, "away_elo": away_elo,
        "elo_diff": home_elo - away_elo, "home_expected": home_exp,
        "home_elo_home": elo_home.get(home, STARTING_ELO),
        "home_elo_away": elo_away.get(home, STARTING_ELO),
        "away_elo_home": elo_home.get(away, STARTING_ELO),
        "away_elo_away": elo_away.get(away, STARTING_ELO),
        "venue_elo_diff": elo_home.get(home, STARTING_ELO) - elo_away.get(away, STARTING_ELO),
        # Glicko-2
        "home_g2_rating": home_g2_rat, "away_g2_rating": away_g2_rat,
        "g2_diff": home_g2_rat - away_g2_rat,
        "home_g2_uncertainty": home_phi * G2_SCALE,
        # Form
        "home_form": hf["form"], "away_form": af["form"],
        "form_diff": hf["form"] - af["form"],
        "home_goals_scored_avg": hf["gs_avg"],
        "home_goals_conceded_avg": hf["gc_avg"],
        "away_goals_scored_avg": af["gs_avg"],
        "away_goals_conceded_avg": af["gc_avg"],
        # xG (from prior matches in team_hist — no current-match leakage)
        "home_xg_avg": hf["xg_scored_home_avg"],
        "home_xg_conceded_avg": hf["xg_conceded_home_avg"],
        "away_xg_avg": af["xg_scored_away_avg"],
        "away_xg_conceded_avg": af["xg_conceded_away_avg"],
        "home_xg_diff_avg": hf["xg_diff_avg"],
        "away_xg_diff_avg": af["xg_diff_avg"],
        # Momentum
        "home_result_momentum": hf["result_momentum"],
        "away_result_momentum": af["result_momentum"],
        "home_score_momentum": hf["score_momentum"],
        "away_score_momentum": af["score_momentum"],
        "home_elo_momentum": hf["elo_momentum"],
        "away_elo_momentum": af["elo_momentum"],
        "home_streak": hf["streak"], "away_streak": af["streak"],
        "momentum_diff": home_comp - away_comp,
        # Fatigue
        "home_days_rest": hf["days_rest"], "away_days_rest": af["days_rest"],
        "home_matches_21d": hf["matches_21d"], "away_matches_21d": af["matches_21d"],
        "rest_asymmetry": asymmetry,
        "home_fatigue_score": home_fat, "away_fatigue_score": away_fat,
        # H2H
        "h2h_home_win_rate":  h2h["h2h_home_win_rate"],
        "h2h_goal_diff_avg":  h2h["h2h_goal_diff_avg"],
        "h2h_meetings":       h2h["h2h_meetings"],
        "h2h_dominance":      h2h["h2h_dominance"],
        "revenge_factor":     h2h["revenge_factor"],
        "home_unbeaten_run":  hf["unbeaten_run"],
        "away_unbeaten_run":  af["unbeaten_run"],
        "post_loss_bounce":      hf["post_loss"],
        "post_loss_bounce_away": af["post_loss"],
        # Context
        "league_encoded": league_enc.get(league, 0),
        "is_early_season": hf["is_early"],
        # Referee
        "ref_avg_yellows": ref_avg_yellows,
        "ref_avg_fouls":   ref_avg_fouls,
        "ref_home_bias":   ref_home_bias,
        "ref_experience":  ref_experience,
        # Venue win rates
        "home_win_rate":       home_win_rate,
        "away_win_rate":       away_win_rate,
        "venue_win_rate_diff": venue_win_rate_diff,
        # Season phase
        "home_season_matches": home_season_matches,
        "away_season_matches": away_season_matches,
        "is_late_season":      is_late_season,
        # Clean sheet rate
        "home_cs_rate": home_cs_rate,
        "away_cs_rate": away_cs_rate,
        # Opponent-adjusted form
        "home_opp_adj_form": home_opp_adj,
        "away_opp_adj_form": away_opp_adj,
        # Relegation/title pressure
        "home_pressure": home_pressure,
        "away_pressure": away_pressure,
        "pressure_diff": home_pressure - away_pressure,
        # Late-season form diff
        "late_season_form_diff": late_season_form_diff,
        # Shot conversion
        "home_shot_conversion": home_shot_conv,
        "away_shot_conversion": away_shot_conv,
        # H2H all-time dominance
        "h2h_all_time_dominance": h2h_all_time_dominance,
        # Derby flag
        "is_derby": is_derby,
        # Home/Away Glicko-2 split
        "home_g2_home":       home_g2h_rating,
        "away_g2_away":       away_g2a_rating,
        "g2_venue_diff":      home_g2h_rating - away_g2a_rating,
        "away_g2_uncertainty": away_phi * G2_SCALE,
        # Feature interactions
        "elo_x_form":           elo_x_form,
        "fatigue_x_congestion": fatigue_x_congestion,
        "derby_x_h2h":          derby_x_h2h,
        # Stadium geography
        "away_travel_km":    away_travel_km,
        "altitude_diff":     altitude_diff,
        "home_capacity_log": home_capacity_log,
        # Prediction uncertainty (metadata — NOT a model feature)
        "prediction_uncertainty": prediction_uncertainty,
        # Stack inputs (not in FEATURE_COLS but needed for meta-learner)
        "p_home_dc": p_home_dc, "p_draw_dc": p_draw_dc, "p_away_dc": p_away_dc,
    }


def update_state(
    state: dict,
    home: str,
    away: str,
    date,
    season: str,
    league: str,
    hg: int,
    ag: int,
    result: str,
    *,
    xg_vals: tuple | None = None,
    ref_name: str | None = None,
    home_yellows: float = 0.0,
    away_yellows: float = 0.0,
    home_fouls: float = 0.0,
    away_fouls: float = 0.0,
    home_shots: int | None = None,
    away_shots: int | None = None,
) -> None:
    """
    Apply pre-match adjustments (idempotent) then advance the walk-forward
    state with the match result. Call AFTER compute_match_features() to
    preserve walk-forward integrity (features never see their own result).
    """
    _apply_pre_match_adjustments(state, home, away, season, league)

    if result == "H":
        hs, as_, home_res, away_res = 1.0, 0.0, "W", "L"
    elif result == "D":
        hs, as_, home_res, away_res = 0.5, 0.5, "D", "D"
    else:
        hs, as_, home_res, away_res = 0.0, 1.0, "L", "W"
    pts_map = {"W": 3, "D": 1, "L": 0}

    home_elo = state["elo"][home]
    away_elo = state["elo"][away]

    # Recompute per-league HA (same formula as compute_match_features)
    _lg_nm = state["league_nm"].get(league, 0)
    _gm    = state["global_matches"]
    _ghw   = state["global_home_wins"]
    if _lg_nm >= HA_MIN_MATCHES and _gm > 0:
        _global_hw_rate = _ghw / _gm
        _lg_hw_rate     = state["league_hw"].get(league, 0) / _lg_nm
        _ha_league = float(np.clip(
            ELO_HA * (_lg_hw_rate / _global_hw_rate) if _global_hw_rate > 0 else ELO_HA,
            0.5 * ELO_HA, 1.5 * ELO_HA,
        ))
    else:
        _ha_league = ELO_HA
    home_exp = _elo_expected(home_elo + _ha_league, away_elo)

    home_mu, home_phi = state["g2"][home]
    away_mu, away_phi = state["g2"][away]

    h_xg = xg_vals[0] if xg_vals else None
    a_xg = xg_vals[1] if xg_vals else None
    xg_d = xg_vals[2] if xg_vals else None

    # Record pre-match Elo for momentum lookups
    state["elo_hist"][home].append((date, home_elo))
    state["elo_hist"][away].append((date, away_elo))

    # Elo update
    mov = _elo_mov(hg - ag)
    state["elo"][home] = home_elo + ELO_K * mov * (hs - home_exp)
    state["elo"][away] = away_elo + ELO_K * mov * (as_ - (1.0 - home_exp))

    # Venue Elo update
    home_exp_venue = _elo_expected(
        state["elo_home"].get(home, STARTING_ELO),
        state["elo_away"].get(away, STARTING_ELO),
    )
    state["elo_home"][home] = (state["elo_home"].get(home, STARTING_ELO)
                               + ELO_K * HOME_ELO_K_SCALE * mov * (hs - home_exp_venue))
    state["elo_away"][away] = (state["elo_away"].get(away, STARTING_ELO)
                               + ELO_K * HOME_ELO_K_SCALE * mov * (as_ - (1.0 - home_exp_venue)))

    # Venue-specific G2: capture pre-match state before any update
    _h_g2h = state["g2_home"][home]
    _a_g2a = state["g2_away"][away]

    # Glicko-2 update (global)
    state["g2"][home] = _g2_update(home_mu, home_phi, away_mu,         away_phi, hs,  ha=G2_HA)
    state["g2"][away] = _g2_update(away_mu, away_phi, home_mu + G2_HA, home_phi, as_, ha=0.0)

    # Venue-specific G2 update (home team's home rating; away team's away rating)
    state["g2_home"][home] = _g2_update(_h_g2h[0], _h_g2h[1], away_mu,         away_phi, hs,  ha=G2_HA)
    state["g2_away"][away] = _g2_update(_a_g2a[0], _a_g2a[1], home_mu + G2_HA, home_phi, as_, ha=0.0)

    # H2H and team history
    _hkey_upd = _h2h_key(home, away)
    state["h2h_hist"][_hkey_upd].append(
        {"home": home, "result": result, "hg": hg, "ag": ag}
    )
    _htot_upd = state["h2h_totals"].setdefault(_hkey_upd, {"wins_a": 0, "wins_b": 0, "meetings": 0})
    _htot_upd["meetings"] += 1
    if result != "D":
        _winner = home if result == "H" else away
        if _winner == _hkey_upd[0]:
            _htot_upd["wins_a"] += 1
        else:
            _htot_upd["wins_b"] += 1
    state["team_hist"][home].append({
        "date": date, "season": season, "result": home_res,
        "points": pts_map[home_res],
        "goal_diff": hg - ag, "goals_scored": hg, "goals_conceded": ag,
        "is_home": True, "xg_scored": h_xg, "xg_conceded": a_xg, "xg_diff": xg_d,
        "shots": home_shots,
    })
    state["team_hist"][away].append({
        "date": date, "season": season, "result": away_res,
        "points": pts_map[away_res],
        "goal_diff": ag - hg, "goals_scored": ag, "goals_conceded": hg,
        "is_home": False, "xg_scored": a_xg, "xg_conceded": h_xg,
        "xg_diff": (-xg_d if xg_d is not None else None),
        "shots": away_shots,
    })

    # Rolling DC windows
    state["dc_scored"][home]   = state["dc_scored"][home][-(DC_WINDOW - 1):]   + [hg]
    state["dc_conceded"][home] = state["dc_conceded"][home][-(DC_WINDOW - 1):] + [ag]
    state["dc_scored"][away]   = state["dc_scored"][away][-(DC_WINDOW - 1):]   + [ag]
    state["dc_conceded"][away] = state["dc_conceded"][away][-(DC_WINDOW - 1):] + [hg]

    # Referee rolling stats
    state["global_matches"] += 1
    if result == "H":
        state["global_home_wins"] += 1
    if ref_name:
        if ref_name not in state["ref_stats"]:
            state["ref_stats"][ref_name] = {"matches": 0, "yellows_total": 0.0,
                                             "fouls_total": 0.0, "home_wins": 0}
        rs = state["ref_stats"][ref_name]
        rs["matches"] += 1
        if result == "H":
            rs["home_wins"] += 1
        rs["yellows_total"] += home_yellows + away_yellows
        rs["fouls_total"]   += home_fouls   + away_fouls

    # Venue win rates and season match counts
    state["team_home_record"].setdefault(home, []).append(1 if result == "H" else 0)
    state["team_away_record"].setdefault(away, []).append(1 if result == "A" else 0)
    _hsm = state["team_season_matches"].get((home, season), 0)
    _asm = state["team_season_matches"].get((away, season), 0)
    state["team_season_matches"][(home, season)] = _hsm + 1
    state["team_season_matches"][(away, season)] = _asm + 1

    # Clean sheet records
    state["team_cs_home"].setdefault(home, []).append(1 if ag == 0 else 0)
    state["team_cs_away"].setdefault(away, []).append(1 if hg == 0 else 0)

    # Opponent-adjusted form
    elo_ratio_h  = away_elo / max(home_elo, 1)
    elo_ratio_a  = home_elo / max(away_elo, 1)
    h_result_val = 1.0 if result == "H" else (0.5 if result == "D" else 0.0)
    a_result_val = 1.0 if result == "A" else (0.5 if result == "D" else 0.0)
    state["team_opp_adj_form"].setdefault(home, []).append(h_result_val * elo_ratio_h)
    state["team_opp_adj_form"].setdefault(away, []).append(a_result_val * elo_ratio_a)

    # Season standings
    pts_h = 3 if result == "H" else (1 if result == "D" else 0)
    pts_a = 3 if result == "A" else (1 if result == "D" else 0)
    key_h = (home, season, league)
    key_a = (away, season, league)
    state["team_season_points"][key_h] = state["team_season_points"].get(key_h, 0) + pts_h
    state["team_season_points"][key_a] = state["team_season_points"].get(key_a, 0) + pts_a
    sk = (season, league)
    if home not in state["league_season_teams"].get(sk, []):
        state["league_season_teams"].setdefault(sk, []).append(home)
    if away not in state["league_season_teams"].get(sk, []):
        state["league_season_teams"].setdefault(sk, []).append(away)

    # League Elo tracker and per-league home-advantage stats
    state["league_elo_tracker"].setdefault(league, {})[home] = state["elo"][home]
    state["league_elo_tracker"].setdefault(league, {})[away] = state["elo"][away]
    state["league_nm"][league] = state["league_nm"].get(league, 0) + 1
    if result == "H":
        state["league_hw"][league] = state["league_hw"].get(league, 0) + 1


# ---------------------------------------------------------------------------

def build_all_features(
    df: pd.DataFrame,
    xg_lookup: dict | None = None,
    league_encoder: LabelEncoder | None = None,
) -> "pd.DataFrame | tuple[pd.DataFrame, LabelEncoder]":
    _created_encoder = league_encoder is None
    if _created_encoder:
        league_encoder = LabelEncoder()
        league_encoder.fit(df["league"])
    league_enc = {lg: int(i) for i, lg in enumerate(league_encoder.classes_)}
    xg_lookup = xg_lookup or {}

    # Validate DERBY_PAIRS team names against actual data (warn on typos)
    _all_data_teams = set(df["home_team"]) | set(df["away_team"])
    for _dname in sorted({n for pair in DERBY_PAIRS for n in pair} - _all_data_teams):
        print(f"  WARNING: DERBY_PAIRS name '{_dname}' not found in results.csv")

    state   = init_state()
    rows    = []
    n_total = len(df)
    _n_regress = 0
    _n_promo   = 0

    for i, row in df.iterrows():
        if i > 0 and i % 2000 == 0:
            print(f"  Processed {i}/{n_total} matches...")

        home   = row["home_team"]
        away   = row["away_team"]
        date   = row["match_date"]
        season = row["season"]
        league = row["league"]
        hg     = int(row["home_goals"])
        ag     = int(row["away_goals"])
        result = row["result"]

        ref_raw = row["referee"] if "referee" in df.columns else None
        ref_raw = ref_raw if (isinstance(ref_raw, str) and ref_raw.strip()) else None

        xg_key  = (date.date(), home, away, league)
        xg_vals = xg_lookup.get(xg_key)

        # Pre-match adjustments: season regression and promotion/relegation.
        # Called explicitly here to capture events for logging; compute_match_features
        # and update_state call it again (idempotent — no-op on second call).
        for ev in _apply_pre_match_adjustments(state, home, away, season, league):
            if ev["type"] == "regress":
                _n_regress += 1
                if _n_regress <= 10:
                    print(f"  [Season-Regress] {ev['team']}: "
                          f"{ev['from_season']} → {ev['to_season']} in {ev['league']}")
            else:
                _n_promo += 1
                if _n_promo <= 10:
                    print(f"  [Promo/Rel] {ev['team']}: "
                          f"{ev['from_league']} → {ev['to_league']}  "
                          f"Elo {ev['old_elo']:.0f} → {ev['new_elo']:.0f}")

        feat = compute_match_features(
            state, home, away, date, season, league, league_enc,
            xg_vals=xg_vals, ref_raw=ref_raw,
        )

        rows.append({
            "match_date": date, "season": season, "league": league,
            "home_team": home, "away_team": away,
            **feat,
            "result": result,
        })

        h_yel    = float(row["home_yellows"]) if pd.notna(row.get("home_yellows")) else 0.0
        a_yel    = float(row["away_yellows"]) if pd.notna(row.get("away_yellows")) else 0.0
        h_foul   = float(row["home_fouls"])   if pd.notna(row.get("home_fouls"))   else 0.0
        a_foul   = float(row["away_fouls"])   if pd.notna(row.get("away_fouls"))   else 0.0
        h_shots  = int(row["home_shots"]) if "home_shots" in df.columns and pd.notna(row.get("home_shots")) else None
        a_shots  = int(row["away_shots"]) if "away_shots" in df.columns and pd.notna(row.get("away_shots")) else None

        update_state(
            state, home, away, date, season, league, hg, ag, result,
            xg_vals=xg_vals, ref_name=ref_raw,
            home_yellows=h_yel, away_yellows=a_yel,
            home_fouls=h_foul, away_fouls=a_foul,
            home_shots=h_shots, away_shots=a_shots,
        )

    if _n_regress > 10:
        print(f"  ... and {_n_regress - 10} more season-regression events suppressed.")
    if _n_promo > 10:
        print(f"  ... and {_n_promo - 10} more promotion/relegation events suppressed.")
    print(f"Season regressions applied: {_n_regress} | League-change adjustments: {_n_promo}")

    feat_df = pd.DataFrame(rows)
    if _created_encoder:
        return feat_df, league_encoder
    return feat_df


# ---------------------------------------------------------------------------
# XGBoost factory (same hyperparams as full_feature_pipeline.py)
# ---------------------------------------------------------------------------

def _make_xgb() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=500,
        max_depth=4,
        learning_rate=0.03,
        subsample=0.9,
        colsample_bytree=0.7,
        min_child_weight=1,
        eval_metric="mlogloss",
        random_state=42,
    )


def _make_draw_xgb() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.8,
        eval_metric="logloss", random_state=42, n_jobs=-1,
    )


# ---------------------------------------------------------------------------
# Out-of-fold XGBoost (TimeSeriesSplit)
# ---------------------------------------------------------------------------

def generate_oof_xgb(X: np.ndarray, y: np.ndarray, n_splits: int = 5) -> np.ndarray:
    oof = np.full((len(X), 3), 1.0 / 3)
    tss = TimeSeriesSplit(n_splits=n_splits)
    for fold, (tr_idx, val_idx) in enumerate(tss.split(X)):
        print(f"  XGB fold {fold + 1}/{n_splits}"
              f"  (train={len(tr_idx):,}, val={len(val_idx):,})")
        model = _make_xgb()
        model.fit(X[tr_idx], y[tr_idx])
        oof[val_idx] = model.predict_proba(X[val_idx])
    return oof   # cols: P(A)=0, P(D)=1, P(H)=2


# ---------------------------------------------------------------------------
# Stack matrix assembler
# ---------------------------------------------------------------------------

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _build_stack(df: pd.DataFrame, xgb_proba: np.ndarray) -> np.ndarray:
    """
    Assemble STACK_COLS (excluding draw_prob, which is appended separately) in the declared order.
    xgb_proba columns: [P(A), P(D), P(H)] (XGBoost class order 0,1,2).
    """
    p_home_g2 = _sigmoid(df["g2_diff"].values / G2_SCALE * 1.6)
    return np.column_stack([
        df["home_expected"].values,
        p_home_g2,
        df["p_home_dc"].values, df["p_draw_dc"].values, df["p_away_dc"].values,
        xgb_proba[:, 2], xgb_proba[:, 1], xgb_proba[:, 0],   # H, D, A
        df["elo_diff"].values,
        df["h2h_goal_diff_avg"].values,
        df["h2h_home_win_rate"].values,
        df["momentum_diff"].values,
    ])


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

def _brier_3outcome(proba: np.ndarray, actual: pd.Series) -> float:
    """Multiclass Brier: mean over matches of sum_k (p_k - y_k)^2 over H/D/A.
    Range 0-2, lower is better; a uniform 1/3 guess scores 0.667.
    proba columns must be [P(A), P(D), P(H)] (RESULT_MAP order). Same
    definition as ensemble_backtest._brier_3outcome."""
    onehot = np.column_stack([(actual.values == r).astype(float) for r in ("A", "D", "H")])
    return float(((proba - onehot) ** 2).sum(axis=1).mean())


def _hit(pred: np.ndarray, actual: pd.Series) -> float:
    return float((pred == actual.values).mean())


HOLDOUT_BRIER_SCALE = (
    "multiclass 3-outcome Brier: mean over matches of sum over H/D/A of "
    "(p - outcome)^2; range 0-2, lower is better; uniform 1/3 guess = 0.667. "
    "null for models with no draw probability (Elo, Glicko-2), which have no "
    "3-outcome Brier."
)


def expected_calibration_error(y_true, y_prob, n_bins=10):
    """Compute Expected Calibration Error."""
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i+1])
        if mask.sum() > 0:
            acc = y_true[mask].mean()
            conf = y_prob[mask].mean()
            ece += mask.mean() * abs(acc - conf)
    return ece


# ---------------------------------------------------------------------------
# Stack fitting (shared by holdout evaluation and deployment refit)
# ---------------------------------------------------------------------------

def fit_stack_models(fit_df: pd.DataFrame, n_splits: int = 5) -> dict:
    """
    Fit the full stack (XGBoost, draw classifier, meta-learner, calibrated
    meta-learner) on fit_df, which must be sorted by match_date.

    The meta-learner is trained on OUT-OF-FOLD base-model predictions only:
    TimeSeriesSplit over fit_df, so each row's p_*_xgb / draw_prob comes from
    a model trained strictly on earlier rows. The base models that are returned
    (and used for prediction) are then refit on all of fit_df.
    """
    X_xgb = fit_df[FEATURE_COLS].values
    y     = fit_df["target"].values

    # Step 1: OOF XGBoost predictions
    print(f"Generating OOF XGBoost predictions ({n_splits}-fold TimeSeriesSplit)...")
    oof_proba = generate_oof_xgb(X_xgb, y, n_splits=n_splits)
    stack = _build_stack(fit_df, oof_proba)

    # Step 1b: OOF draw classifier (dedicated binary draw model)
    print(f"\nGenerating OOF draw classifier predictions ({n_splits}-fold TimeSeriesSplit)...")
    X_draw        = fit_df[DRAW_COLS].values
    draw_y        = (fit_df["result"] == "D").astype(int).values
    draw_prob_oof = np.zeros(len(fit_df))
    tss_draw = TimeSeriesSplit(n_splits=n_splits)
    for fold, (tr_idx, val_idx) in enumerate(tss_draw.split(X_draw)):
        print(f"  Draw fold {fold + 1}/{n_splits}"
              f"  (train={len(tr_idx):,}, val={len(val_idx):,})")
        dc_model = _make_draw_xgb()
        dc_model.fit(X_draw[tr_idx], draw_y[tr_idx])
        draw_prob_oof[val_idx] = dc_model.predict_proba(X_draw[val_idx])[:, 1]

    draw_clf = _make_draw_xgb()
    draw_clf.fit(X_draw, draw_y)

    stack = np.column_stack([stack, draw_prob_oof])
    assert stack.shape[1] == len(STACK_COLS), (
        f"stack width {stack.shape[1]} != len(STACK_COLS) {len(STACK_COLS)}"
    )

    # Step 2: Full XGBoost on all of fit_df
    print(f"\nTraining full XGBoost on {len(fit_df):,} matches...")
    xgb_full = _make_xgb()
    xgb_full.fit(X_xgb, y)

    # Step 3: Meta-learner on the OOF stack
    print("Training meta-learner (LogisticRegression + StandardScaler)...")
    meta = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(C=1.0, max_iter=5000, random_state=42)),
    ])
    meta.fit(stack, y)

    # Calibrate via 5-fold CV on the OOF stack
    meta_calibrated = CalibratedClassifierCV(
        LogisticRegression(C=0.1, max_iter=5000, random_state=42),
        method='isotonic',
        cv=5,
    )
    meta_calibrated.fit(stack, y)

    return {
        "xgb": xgb_full, "draw_clf": draw_clf,
        "meta": meta, "meta_calibrated": meta_calibrated,
        "oof_stack": stack,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "results.csv")
    )

    df = pd.read_csv(results_path, parse_dates=["match_date"], dtype={"referee": str})
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])
    print(f"Loaded {len(df):,} matches across {df['league'].nunique()} leagues\n")

    xg_lookup: dict = {}
    xg_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "results_with_xg.csv")
    )
    if os.path.exists(xg_path):
        xg_df = pd.read_csv(xg_path, parse_dates=["match_date"])
        xg_df = xg_df.dropna(subset=["home_xg", "away_xg", "xg_diff"])
        for _, r in xg_df.iterrows():
            key = (r["match_date"].date(), r["home_team"], r["away_team"], r["league"])
            xg_lookup[key] = (float(r["home_xg"]), float(r["away_xg"]), float(r["xg_diff"]))
        print(f"Loaded {len(xg_lookup):,} xG records from results_with_xg.csv")
    else:
        print("Warning: results_with_xg.csv not found — xG features will use defaults\n")

    print(f"Building features for {len(df):,} matches (57-feature set + rolling DC)...")
    feat_df, league_encoder = build_all_features(df, xg_lookup)
    print(f"  Processed {len(df):,}/{len(df):,} matches (complete)\n")

    feat_df = feat_df[feat_df["match_date"] >= "2014-08-01"].reset_index(drop=True)
    print(f"Filtered to xG era: {len(feat_df):,} matches (2014-08-01 onwards)\n")

    model_df = feat_df.iloc[COLD_START:].reset_index(drop=True)
    model_df["target"] = model_df["result"].map(RESULT_MAP)

    n = len(model_df)
    holdout_split = int(n * 0.80)
    train_df   = model_df.iloc[:holdout_split].reset_index(drop=True)
    holdout_df = model_df.iloc[holdout_split:].copy().reset_index(drop=True)

    print(f"Train:   {len(train_df):,} matches  "
          f"({train_df['match_date'].min().date()} → {train_df['match_date'].max().date()})")
    print(f"Holdout: {len(holdout_df):,} matches  "
          f"({holdout_df['match_date'].min().date()} → {holdout_df['match_date'].max().date()})\n")

    # ------------------------------------------------------------------
    # Steps 1-3: fit the stack on train_df only (for holdout evaluation)
    # ------------------------------------------------------------------
    eval_models     = fit_stack_models(train_df)
    xgb_full        = eval_models["xgb"]
    draw_clf        = eval_models["draw_clf"]
    meta            = eval_models["meta"]
    meta_calibrated = eval_models["meta_calibrated"]

    X_holdout_xgb   = holdout_df[FEATURE_COLS].values
    holdout_xgb_proba = xgb_full.predict_proba(X_holdout_xgb)
    holdout_stack     = _build_stack(holdout_df, holdout_xgb_proba)
    draw_prob_ho  = draw_clf.predict_proba(holdout_df[DRAW_COLS].values)[:, 1]
    holdout_stack = np.column_stack([holdout_stack, draw_prob_ho])

    # ------------------------------------------------------------------
    # Step 4: Holdout evaluation
    # ------------------------------------------------------------------
    meta_proba = meta.predict_proba(holdout_stack)   # cols: P(A), P(D), P(H)
    meta_pred  = meta.predict(holdout_stack)
    cal_proba  = meta_calibrated.predict_proba(holdout_stack)
    cal_pred   = meta_calibrated.predict(holdout_stack)

    holdout_df["p_away"] = meta_proba[:, 0]
    holdout_df["p_draw"] = meta_proba[:, 1]
    holdout_df["p_home"] = meta_proba[:, 2]
    holdout_df["p_away_cal"] = cal_proba[:, 0]
    holdout_df["p_draw_cal"] = cal_proba[:, 1]
    holdout_df["p_home_cal"] = cal_proba[:, 2]
    holdout_df["predicted_result"] = [RESULT_INV[int(p)] for p in meta_pred]
    holdout_df["actual_result"]    = holdout_df["result"]
    holdout_df["correct"] = (
        holdout_df["predicted_result"] == holdout_df["actual_result"]
    ).astype(int)

    actual = holdout_df["actual_result"]

    # Brier is the multiclass (3-outcome, 0-2) score, and only for models that
    # output H/D/A probabilities. Elo and Glicko-2 give a 2-way home/away
    # probability with no draw, so they have no 3-outcome Brier (None) — the
    # old home-anchored score (draw = 0.5) isn't comparable and isn't reported.
    ens_hit   = float(holdout_df["correct"].mean())
    ens_brier = _brier_3outcome(meta_proba, actual)

    cal_pred_str = np.array([RESULT_INV[int(p)] for p in cal_pred])
    cal_hit   = _hit(cal_pred_str, actual)
    cal_brier = _brier_3outcome(cal_proba, actual)

    # Full XGBoost standalone
    xgb_pred_str = np.array([RESULT_INV[int(p)] for p in xgb_full.predict(X_holdout_xgb)])
    xgb_hit      = _hit(xgb_pred_str, actual)
    xgb_brier    = _brier_3outcome(holdout_xgb_proba, actual)

    # Elo baseline (2-way: never predicts a draw)
    elo_pred_str = np.where(holdout_df["home_expected"].values > 0.5, "H", "A")
    elo_hit      = _hit(elo_pred_str, actual)
    elo_brier    = None

    # Glicko-2 baseline (2-way: never predicts a draw)
    p_home_g2_holdout = _sigmoid(holdout_df["g2_diff"].values / G2_SCALE * 1.6)
    g2_pred_str       = np.where(p_home_g2_holdout > 0.5, "H", "A")
    g2_hit            = _hit(g2_pred_str, actual)
    g2_brier          = None

    # Dixon-Coles baseline
    dc_cols = np.column_stack([
        holdout_df["p_away_dc"], holdout_df["p_draw_dc"], holdout_df["p_home_dc"],
    ])
    dc_pred_str = np.array([RESULT_INV[int(i)] for i in np.argmax(dc_cols, axis=1)])
    dc_hit      = _hit(dc_pred_str, actual)
    dc_brier    = _brier_3outcome(dc_cols, actual)

    # ------------------------------------------------------------------
    # Step 5: Print results
    # ------------------------------------------------------------------
    lr = meta.named_steps["lr"]
    print("\n" + "=" * 68)
    print("META-LEARNER COEFFICIENTS  (standardised feature space)")
    print("=" * 68)
    print(f"  {'Feature':<28s}  {'Away':>8}  {'Draw':>8}  {'Home':>8}  {'|avg|':>7}")
    print("  " + "-" * 60)
    for idx, feat in enumerate(STACK_COLS):
        coefs    = lr.coef_[:, idx]   # [A, D, H]
        mean_abs = float(np.mean(np.abs(coefs)))
        print(f"  {feat:<28s}  {coefs[0]:>8.4f}  {coefs[1]:>8.4f}  {coefs[2]:>8.4f}  {mean_abs:>7.4f}")

    best_hit   = max(elo_hit, g2_hit, xgb_hit, dc_hit)
    best_brier = min(xgb_brier, dc_brier)   # single models with a 3-outcome Brier

    print("\n" + "=" * 68)
    print(f"HOLDOUT EVALUATION  ({len(holdout_df):,} matches, "
          f"{holdout_df['match_date'].min().date()} → "
          f"{holdout_df['match_date'].max().date()})")
    print("=" * 68)
    print(f"  {'Model':<20s}  {'Hit Rate':>10}  {'Brier (3-way, 0-2)':>18}")
    print(f"  {'-' * 52}")

    rows_table = [
        ("Ensemble v2",       ens_hit,  ens_brier),
        ("Ensemble v2 (cal)", cal_hit,  cal_brier),
        ("Full XGB",          xgb_hit,  xgb_brier),
        ("Elo baseline",      elo_hit,  elo_brier),
        ("Glicko-2",          g2_hit,   g2_brier),
        ("Dixon-Coles",       dc_hit,   dc_brier),
    ]
    top_hit   = max(r[1] for r in rows_table)
    top_brier = min(r[2] for r in rows_table if r[2] is not None)
    for name, hr, br in rows_table:
        marker = " ◀ best" if (hr == top_hit or br == top_brier) else ""
        br_s = f"{br:>18.6f}" if br is not None else f"{'— (2-way, no draw)':>18}"
        print(f"  {name:<20s}  {hr:>10.4f}  {br_s}{marker}")

    # Persisted alongside the deployed .pkl files (written in Step 7) so the
    # API always serves the metrics from the same run as the served models.
    # "Ensemble v2 (cal)" is monitoring-only (not served) and is left out.
    holdout_from = str(holdout_df["match_date"].min().date())
    holdout_to   = str(holdout_df["match_date"].max().date())

    def _metric_row(key, name, outputs, hit, brier):
        return {
            "key": key, "name": name, "outputs": outputs,
            "predicts_draws": outputs == "H/D/A",
            "hit_rate": round(float(hit), 4),
            "brier": None if brier is None else round(float(brier), 4),
            "n_matches": len(holdout_df),
            "holdout_from": holdout_from, "holdout_to": holdout_to,
        }

    holdout_metrics = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hit_rate_definition": (
            "share of holdout matches where the model's most likely outcome "
            "(H/D/A) was the actual result; 2-way models never pick a draw, "
            "so every draw counts as a miss for them"
        ),
        "brier_scale": HOLDOUT_BRIER_SCALE,
        "split": {
            "method": "chronological 80/20 (models fit on train only, scored on holdout)",
            "train":   {"from": str(train_df["match_date"].min().date()),
                        "to":   str(train_df["match_date"].max().date()),
                        "n_matches": len(train_df)},
            "holdout": {"from": holdout_from, "to": holdout_to,
                        "n_matches": len(holdout_df)},
        },
        "deployed_models": {
            "trained_through": str(model_df["match_date"].max().date()),
            "n_matches": len(model_df),
            "note": "served models are refit on train + holdout after evaluation",
        },
        "models": [
            _metric_row("ensemble",    "Ensemble",    "H/D/A", ens_hit, ens_brier),
            _metric_row("xgboost",     "XGBoost",     "H/D/A", xgb_hit, xgb_brier),
            _metric_row("dixon_coles", "Dixon-Coles", "H/D/A", dc_hit,  dc_brier),
            _metric_row("elo",         "Elo",         "H/A",   elo_hit, elo_brier),
            _metric_row("glicko2",     "Glicko-2",    "H/A",   g2_hit,  g2_brier),
        ],
    }
    holdout_metrics["n_models"] = len(holdout_metrics["models"])

    hit_delta   = ens_hit - best_hit
    brier_delta = ens_brier - best_brier
    print(f"\n  Improvement over best single model:")
    print(f"    Hit rate : {hit_delta:+.4f}  ({'✓ better' if hit_delta >= 0 else '✗ worse'})")
    print(f"    Brier    : {brier_delta:+.6f}  ({'✓ better' if brier_delta <= 0 else '✗ worse'})")
    print("=" * 68)

    # ------------------------------------------------------------------
    # Calibration quality (ECE on home-win probability)
    # ------------------------------------------------------------------
    y_home_binary = (holdout_df["actual_result"] == "H").astype(int).values
    ece_uncal = expected_calibration_error(y_home_binary, meta_proba[:, 2])
    ece_cal   = expected_calibration_error(y_home_binary, cal_proba[:, 2])
    print(f"\nCALIBRATION  (home-win probability, ECE over {len(holdout_df):,} holdout matches)")
    print(f"  ECE uncalibrated : {ece_uncal:.4f}")
    print(f"  ECE calibrated   : {ece_cal:.4f}")
    print(f"  ECE improvement  : {ece_uncal - ece_cal:+.4f}  "
          f"({'✓ better' if ece_cal < ece_uncal else '✗ worse'})")
    print(f"  NOTE: uncalibrated model (meta_learner.pkl) is the SERVING model.")
    print(f"        Platt layer retired — calibrated variant retained for monitoring only.")
    print("=" * 68)

    # ------------------------------------------------------------------
    # Step 6: Save predictions
    # ------------------------------------------------------------------
    out_cols = [
        "match_date", "league", "home_team", "away_team",
        "p_home", "p_draw", "p_away",
        "predicted_result", "actual_result", "correct",
        "prediction_uncertainty",
    ]
    out_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "ensemble_v2_predictions.csv")
    )
    holdout_df[out_cols].to_csv(out_path, index=False)
    print(f"\nSaved holdout predictions ({len(holdout_df):,} rows) to {out_path}")

    # ------------------------------------------------------------------
    # Step 7: Deployment refit on 100% of model_df
    # ------------------------------------------------------------------
    # The holdout numbers above come from the train-only models. The models
    # we SERVE are refit on every match so they include the most recent ~20%.
    # Same procedure as the evaluation fit (OOF TimeSeriesSplit stack for the
    # meta-learner), just over model_df instead of train_df.
    print("\n" + "=" * 68)
    print(f"DEPLOYMENT REFIT  ({len(model_df):,} matches, "
          f"{model_df['match_date'].min().date()} → "
          f"{model_df['match_date'].max().date()})")
    print("=" * 68)
    deploy = fit_stack_models(model_df)

    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(deploy["xgb"], os.path.join(models_dir, 'xgb_ensemble.pkl'))
    print(f"Saved XGBoost model to models/xgb_ensemble.pkl")
    joblib.dump(deploy["meta"], os.path.join(models_dir, 'meta_learner.pkl'))
    print(f"Saved meta-learner to models/meta_learner.pkl")
    joblib.dump(deploy["meta_calibrated"], os.path.join(models_dir, 'meta_learner_calibrated.pkl'))
    print(f"Saved calibrated meta-learner to models/meta_learner_calibrated.pkl")
    joblib.dump(deploy["draw_clf"], os.path.join(models_dir, 'draw_classifier.pkl'))
    print(f"Saved draw classifier to models/draw_classifier.pkl")
    with open(os.path.join(models_dir, 'feature_cols.json'), 'w') as f:
        json.dump(FEATURE_COLS, f)
    joblib.dump(league_encoder, os.path.join(models_dir, 'league_encoder.pkl'))
    # allow_nan=False: a NaN metric fails the run loudly instead of writing
    # invalid JSON the API would choke on.
    with open(os.path.join(models_dir, 'holdout_metrics.json'), 'w') as f:
        json.dump(holdout_metrics, f, indent=2, allow_nan=False)
        f.write("\n")
    print(f"Saved holdout metrics to models/holdout_metrics.json")
    print(f"Deployed models trained through {model_df['match_date'].max().date()} "
          f"(holdout metrics above are from the train-only fit through "
          f"{train_df['match_date'].max().date()})")


if __name__ == "__main__":
    main()
