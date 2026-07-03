"""
Market-specific prediction endpoints.

GET /api/markets/corners  — total corners prediction + Over/Under probs
GET /api/markets/cards    — total yellow cards prediction + Over/Under probs
GET /api/markets/btts     — BTTS probability + team scoring/conceding rates
GET /api/markets/goals    — total goals prediction + Over/Under probs
GET /api/markets/preview  — all 4 markets in one response
"""
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Blueprint, jsonify, request
from scipy.stats import norm

markets_bp = Blueprint("markets", __name__)

# ── Data paths ────────────────────────────────────────────────────────────────
_DATA = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

# ── Load prediction CSVs once at module init ──────────────────────────────────
def _load(filename: str) -> pd.DataFrame:
    path = _DATA / filename
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False, dtype={"referee": str})
    if "match_date" in df.columns:
        df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    return df

_corners_df = _load("corners_predictions.csv")
_cards_df   = _load("cards_predictions.csv")
_btts_df    = _load("btts_predictions.csv")
_goals_df   = _load("goals_predictions.csv")
_results_df = _load("results.csv")

# ── Residual std from holdout — used for normal-CDF over/under probs ──────────
def _residual_std(df: pd.DataFrame, pred: str, actual: str, fallback: float) -> float:
    if df.empty or pred not in df.columns or actual not in df.columns:
        return fallback
    resid = df[pred].dropna().values - df[actual].dropna().values
    return float(np.std(resid)) if len(resid) > 1 else fallback

_CORNERS_STD = _residual_std(_corners_df, "predicted_corners", "actual_corners", 3.8)
_CARDS_STD   = _residual_std(_cards_df,   "predicted_yellows", "actual_yellows", 2.1)
_GOALS_STD   = _residual_std(_goals_df,   "predicted_goals",   "actual_goals",   1.6)

# ── Per-league averages (fallback when no exact matchup found) ────────────────
def _league_avgs(df: pd.DataFrame, col: str) -> dict:
    if df.empty or col not in df.columns:
        return {}
    return df.groupby("league")[col].mean().to_dict()

_CORNERS_LEAGUE_AVG  = _league_avgs(_corners_df, "predicted_corners")
_CARDS_LEAGUE_AVG    = _league_avgs(_cards_df,   "predicted_yellows")
_BTTS_LEAGUE_AVG     = _league_avgs(_btts_df,    "btts_prob")
_GOALS_LEAGUE_AVG    = _league_avgs(_goals_df,   "predicted_goals")
_GOALS_OVER15_AVG    = _league_avgs(_goals_df,   "over15_prob")
_GOALS_OVER25_AVG    = _league_avgs(_goals_df,   "over25_prob")
_GOALS_OVER35_AVG    = _league_avgs(_goals_df,   "over35_prob")
_GOALS_OVER45_AVG    = _league_avgs(_goals_df,   "over45_prob")

# Global fallbacks (when league not found either)
_CORNERS_GLOBAL_AVG  = float(_corners_df["predicted_corners"].mean()) if not _corners_df.empty else 10.2
_CARDS_GLOBAL_AVG    = float(_cards_df["predicted_yellows"].mean())   if not _cards_df.empty   else 3.5
_BTTS_GLOBAL_AVG     = float(_btts_df["btts_prob"].mean())            if not _btts_df.empty    else 0.47
_GOALS_GLOBAL_AVG    = float(_goals_df["predicted_goals"].mean())     if not _goals_df.empty   else 2.6

# ── Team stats and referee stats precomputed from results.csv ─────────────────
_WINDOW = 10
_HOME_STATS: dict[str, dict] = {}
_AWAY_STATS: dict[str, dict] = {}
_REF_STATS:  dict[str, dict] = {}


def _precompute() -> None:
    if _results_df.empty:
        return

    df = _results_df.copy()
    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    df = df.sort_values("match_date")

    # Binary event columns for rate calculations
    df["_home_scored"]   = (df["home_goals"] > 0).astype(float)
    df["_home_conceded"] = (df["away_goals"] > 0).astype(float)
    df["_away_scored"]   = (df["away_goals"] > 0).astype(float)
    df["_away_conceded"] = (df["home_goals"] > 0).astype(float)

    # Home venue: last _WINDOW home matches per team
    home_tail = df.groupby("home_team", sort=False).tail(_WINDOW)
    home_agg_spec: dict = {
        "goals_avg":          ("home_goals",     "mean"),
        "goals_conceded_avg": ("away_goals",     "mean"),
        "scoring_rate":       ("_home_scored",   "mean"),
        "conceding_rate":     ("_home_conceded", "mean"),
    }
    if "home_corners" in df.columns:
        home_agg_spec["corners_avg"] = ("home_corners", "mean")
    if "home_yellows" in df.columns:
        home_agg_spec["yellows_avg"] = ("home_yellows", "mean")

    home_agg = home_tail.groupby("home_team").agg(**home_agg_spec)
    for team, row in home_agg.iterrows():
        _HOME_STATS[team] = row.to_dict()

    # Away venue: last _WINDOW away matches per team
    away_tail = df.groupby("away_team", sort=False).tail(_WINDOW)
    away_agg_spec: dict = {
        "goals_avg":          ("away_goals",     "mean"),
        "goals_conceded_avg": ("home_goals",     "mean"),
        "scoring_rate":       ("_away_scored",   "mean"),
        "conceding_rate":     ("_away_conceded", "mean"),
    }
    if "away_corners" in df.columns:
        away_agg_spec["corners_avg"] = ("away_corners", "mean")
    if "away_yellows" in df.columns:
        away_agg_spec["yellows_avg"] = ("away_yellows", "mean")

    away_agg = away_tail.groupby("away_team").agg(**away_agg_spec)
    for team, row in away_agg.iterrows():
        _AWAY_STATS[team] = row.to_dict()

    # Referee stats
    if "referee" in df.columns and "home_yellows" in df.columns:
        rdf = df[
            df["referee"].notna()
            & (df["referee"].astype(str).str.strip() != "")
            & (df["referee"].astype(str) != "nan")
        ].copy()
        if not rdf.empty:
            rdf["_total_y"] = rdf["home_yellows"].fillna(0) + rdf["away_yellows"].fillna(0)
            ref_agg = rdf.groupby("referee").agg(
                avg_yellows=("_total_y", "mean"),
                matches=("_total_y", "count"),
            )
            for ref, row in ref_agg.iterrows():
                _REF_STATS[ref.strip()] = {
                    "avg_yellows": float(row["avg_yellows"]),
                    "matches":     int(row["matches"]),
                }


_precompute()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _f(val, ndigits: int = 4):
    """Return None for NaN/None, else round to ndigits."""
    if val is None:
        return None
    try:
        v = float(val)
        return None if np.isnan(v) else round(v, ndigits)
    except (TypeError, ValueError):
        return None


def _over_prob(predicted: float, line: float, std: float) -> float:
    """P(actual > line) assuming normal distribution around regression prediction."""
    return float(norm.sf(line, loc=predicted, scale=max(std, 0.01)))


def _fb(avgs: dict, league: str, global_avg: float) -> float:
    """League fallback value, then global fallback."""
    return avgs.get(league, global_avg)


def _lookup(df: pd.DataFrame, home_team: str, away_team: str):
    """Most recent holdout prediction row for this matchup, or None."""
    if df.empty:
        return None
    mask = (df["home_team"] == home_team) & (df["away_team"] == away_team)
    hits = df[mask]
    if hits.empty:
        return None
    return hits.sort_values("match_date", ascending=False).iloc[0]


def _meta() -> dict:
    return {"generated_at": datetime.now(timezone.utc).isoformat()}


def _err(msg: str, code: int = 400):
    return jsonify({"success": False, "error": msg}), code


def _require_teams():
    home = request.args.get("home_team", "").strip()
    away = request.args.get("away_team", "").strip()
    league = request.args.get("league", "").strip()
    if not home or not away:
        return None, None, None, _err("home_team and away_team are required")
    return home, away, league, None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@markets_bp.get("/corners")
def get_corners():
    home, away, league, bad = _require_teams()
    if bad:
        return bad

    row = _lookup(_corners_df, home, away)
    using_fallback = row is None
    predicted = float(row["predicted_corners"]) if not using_fallback else _fb(_CORNERS_LEAGUE_AVG, league, _CORNERS_GLOBAL_AVG)

    h = _HOME_STATS.get(home, {})
    a = _AWAY_STATS.get(away, {})

    return jsonify({
        "success": True,
        "data": {
            "predicted_corners": _f(predicted, 2),
            "over_9_5_prob":     _f(_over_prob(predicted, 9.5,  _CORNERS_STD)),
            "over_10_5_prob":    _f(_over_prob(predicted, 10.5, _CORNERS_STD)),
            "over_11_5_prob":    _f(_over_prob(predicted, 11.5, _CORNERS_STD)),
            "home_corners_avg":  _f(h.get("corners_avg"), 2),
            "away_corners_avg":  _f(a.get("corners_avg"), 2),
            "using_fallback":    using_fallback,
            "league":            league or None,
        },
        "meta": _meta(),
    })


@markets_bp.get("/cards")
def get_cards():
    home, away, league, bad = _require_teams()
    if bad:
        return bad

    referee = request.args.get("referee", "").strip() or None

    row = _lookup(_cards_df, home, away)
    using_fallback = row is None
    predicted = float(row["predicted_yellows"]) if not using_fallback else _fb(_CARDS_LEAGUE_AVG, league, _CARDS_GLOBAL_AVG)

    ref = _REF_STATS.get(referee, {}) if referee else {}

    return jsonify({
        "success": True,
        "data": {
            "predicted_yellows":  _f(predicted, 2),
            "over_3_5_prob":      _f(_over_prob(predicted, 3.5, _CARDS_STD)),
            "over_4_5_prob":      _f(_over_prob(predicted, 4.5, _CARDS_STD)),
            "over_5_5_prob":      _f(_over_prob(predicted, 5.5, _CARDS_STD)),
            "referee":            referee,
            "referee_avg_yellows": _f(ref.get("avg_yellows"), 2),
            "referee_matches":    ref.get("matches"),
            "using_fallback":     using_fallback,
            "league":             league or None,
        },
        "meta": _meta(),
    })


@markets_bp.get("/btts")
def get_btts():
    home, away, league, bad = _require_teams()
    if bad:
        return bad

    row = _lookup(_btts_df, home, away)
    using_fallback = row is None
    btts_prob = float(row["btts_prob"]) if not using_fallback else _fb(_BTTS_LEAGUE_AVG, league, _BTTS_GLOBAL_AVG)

    h = _HOME_STATS.get(home, {})
    a = _AWAY_STATS.get(away, {})

    return jsonify({
        "success": True,
        "data": {
            "btts_prob":           _f(btts_prob),
            "btts_yes_prob":       _f(btts_prob),
            "btts_no_prob":        _f(1.0 - btts_prob),
            "home_scoring_rate":   _f(h.get("scoring_rate")),
            "away_scoring_rate":   _f(a.get("scoring_rate")),
            "home_conceding_rate": _f(h.get("conceding_rate")),
            "away_conceding_rate": _f(a.get("conceding_rate")),
            "using_fallback":      using_fallback,
            "league":              league or None,
        },
        "meta": _meta(),
    })


@markets_bp.get("/goals")
def get_goals():
    home, away, league, bad = _require_teams()
    if bad:
        return bad

    row = _lookup(_goals_df, home, away)
    using_fallback = row is None

    if not using_fallback:
        predicted = float(row["predicted_goals"])
        over_1_5  = float(row["over15_prob"])
        over_2_5  = float(row["over25_prob"])
        over_3_5  = float(row["over35_prob"])
        over_4_5  = float(row["over45_prob"])
    else:
        predicted = _fb(_GOALS_LEAGUE_AVG, league, _GOALS_GLOBAL_AVG)
        over_1_5  = _fb(_GOALS_OVER15_AVG, league, 0.75)
        over_2_5  = _fb(_GOALS_OVER25_AVG, league, 0.50)
        over_3_5  = _fb(_GOALS_OVER35_AVG, league, 0.28)
        over_4_5  = _fb(_GOALS_OVER45_AVG, league, 0.13)

    h = _HOME_STATS.get(home, {})
    a = _AWAY_STATS.get(away, {})

    return jsonify({
        "success": True,
        "data": {
            "predicted_goals": _f(predicted, 2),
            "over_1_5_prob":   _f(over_1_5),
            "over_2_5_prob":   _f(over_2_5),
            "over_3_5_prob":   _f(over_3_5),
            "over_4_5_prob":   _f(over_4_5),
            "home_goals_avg":  _f(h.get("goals_avg"), 2),
            "away_goals_avg":  _f(a.get("goals_avg"), 2),
            "using_fallback":  using_fallback,
            "league":          league or None,
        },
        "meta": _meta(),
    })


@markets_bp.get("/preview")
def get_preview():
    home, away, league, bad = _require_teams()
    if bad:
        return bad

    referee = request.args.get("referee", "").strip() or None

    # ── Corners ──
    c_row      = _lookup(_corners_df, home, away)
    c_fallback = c_row is None
    c_pred     = float(c_row["predicted_corners"]) if not c_fallback else _fb(_CORNERS_LEAGUE_AVG, league, _CORNERS_GLOBAL_AVG)
    h_s        = _HOME_STATS.get(home, {})
    a_s        = _AWAY_STATS.get(away, {})

    corners = {
        "predicted_corners": _f(c_pred, 2),
        "over_9_5_prob":     _f(_over_prob(c_pred, 9.5,  _CORNERS_STD)),
        "over_10_5_prob":    _f(_over_prob(c_pred, 10.5, _CORNERS_STD)),
        "over_11_5_prob":    _f(_over_prob(c_pred, 11.5, _CORNERS_STD)),
        "home_corners_avg":  _f(h_s.get("corners_avg"), 2),
        "away_corners_avg":  _f(a_s.get("corners_avg"), 2),
        "using_fallback":    c_fallback,
    }

    # ── Cards ──
    k_row      = _lookup(_cards_df, home, away)
    k_fallback = k_row is None
    k_pred     = float(k_row["predicted_yellows"]) if not k_fallback else _fb(_CARDS_LEAGUE_AVG, league, _CARDS_GLOBAL_AVG)
    ref        = _REF_STATS.get(referee, {}) if referee else {}

    cards = {
        "predicted_yellows":   _f(k_pred, 2),
        "over_3_5_prob":       _f(_over_prob(k_pred, 3.5, _CARDS_STD)),
        "over_4_5_prob":       _f(_over_prob(k_pred, 4.5, _CARDS_STD)),
        "over_5_5_prob":       _f(_over_prob(k_pred, 5.5, _CARDS_STD)),
        "referee":             referee,
        "referee_avg_yellows": _f(ref.get("avg_yellows"), 2),
        "referee_matches":     ref.get("matches"),
        "using_fallback":      k_fallback,
    }

    # ── BTTS ──
    b_row      = _lookup(_btts_df, home, away)
    b_fallback = b_row is None
    btts_prob  = float(b_row["btts_prob"]) if not b_fallback else _fb(_BTTS_LEAGUE_AVG, league, _BTTS_GLOBAL_AVG)

    btts = {
        "btts_prob":           _f(btts_prob),
        "btts_yes_prob":       _f(btts_prob),
        "btts_no_prob":        _f(1.0 - btts_prob),
        "home_scoring_rate":   _f(h_s.get("scoring_rate")),
        "away_scoring_rate":   _f(a_s.get("scoring_rate")),
        "home_conceding_rate": _f(h_s.get("conceding_rate")),
        "away_conceding_rate": _f(a_s.get("conceding_rate")),
        "using_fallback":      b_fallback,
    }

    # ── Goals ──
    g_row      = _lookup(_goals_df, home, away)
    g_fallback = g_row is None

    if not g_fallback:
        g_pred   = float(g_row["predicted_goals"])
        over_1_5 = float(g_row["over15_prob"])
        over_2_5 = float(g_row["over25_prob"])
        over_3_5 = float(g_row["over35_prob"])
        over_4_5 = float(g_row["over45_prob"])
    else:
        g_pred   = _fb(_GOALS_LEAGUE_AVG, league, _GOALS_GLOBAL_AVG)
        over_1_5 = _fb(_GOALS_OVER15_AVG, league, 0.75)
        over_2_5 = _fb(_GOALS_OVER25_AVG, league, 0.50)
        over_3_5 = _fb(_GOALS_OVER35_AVG, league, 0.28)
        over_4_5 = _fb(_GOALS_OVER45_AVG, league, 0.13)

    goals = {
        "predicted_goals": _f(g_pred, 2),
        "over_1_5_prob":   _f(over_1_5),
        "over_2_5_prob":   _f(over_2_5),
        "over_3_5_prob":   _f(over_3_5),
        "over_4_5_prob":   _f(over_4_5),
        "home_goals_avg":  _f(h_s.get("goals_avg"), 2),
        "away_goals_avg":  _f(a_s.get("goals_avg"), 2),
        "using_fallback":  g_fallback,
    }

    return jsonify({
        "success": True,
        "data": {
            "home_team": home,
            "away_team": away,
            "league":    league or None,
            "corners":   corners,
            "cards":     cards,
            "btts":      btts,
            "goals":     goals,
        },
        "meta": _meta(),
    })
