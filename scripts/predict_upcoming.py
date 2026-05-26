"""
predict_upcoming.py

Generates ensemble predictions for upcoming fixtures.

Fetches fixtures from:
  GET https://web-production-eb371.up.railway.app/api/live/upcoming

Replays all historical results to rebuild current rolling state (Elo, Glicko-2,
form, H2H, DC), then computes the same 48 features used during training and runs
them through the saved XGBoost + meta-learner stack.

Output: data/processed/upcoming_predictions.csv
"""

import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import httpx
import joblib
import numpy as np
import pandas as pd

# ─── Import shared helpers from ensemble_v2 ──────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ensemble_v2 import (  # noqa: E402
    FEATURE_COLS,
    STARTING_ELO, ELO_K, ELO_HA,
    G2_INITIAL_PHI, G2_SCALE, G2_SIGMA, G2_HA,
    DC_WINDOW, DC_HOME_ADV,
    FORM_WINDOW,
    _elo_expected, _elo_mov, _g2_update,
    _ewm, _streak, _elo_28d_ago, _h2h_key,
    _team_features, _h2h_features, _fatigue_score,
    _dc_attack, _dc_defence, _dc_probs,
    _sigmoid,
)

# ─── Config ──────────────────────────────────────────────────────────────────
UPCOMING_URL = "https://web-production-eb371.up.railway.app/api/live/upcoming"

BASE_DIR   = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR   = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# API competition name → internal league code used in results.csv
COMP_TO_LEAGUE: dict[str, str] = {
    "Premier League": "EPL",
    "La Liga":        "LaLiga",
    "Serie A":        "SerieA",
    "Bundesliga":     "Bundesliga",
    "Ligue 1":        "Ligue1",
    "Championship":   "Championship",
}
DEFAULT_LEAGUE = "EPL"

RESULT_INV = {0: "A", 1: "D", 2: "H"}

_SUFFIX_RE = re.compile(r"\s+(United FC|City FC|FC|AFC|CF|SC|BC)$", re.IGNORECASE)


def _strip_suffix(name: str) -> str:
    return _SUFFIX_RE.sub("", name or "").strip()


def _current_season(date: datetime) -> str:
    """Return season string like '2025-26' for a given match date."""
    y = date.year
    if date.month >= 8:
        return f"{y}-{str(y + 1)[-2:]}"
    return f"{y - 1}-{str(y)[-2:]}"


# ─── Elo probability (same formula as fetch_live_odds.py) ────────────────────
def _prematch_probs(home_elo: float, away_elo: float) -> tuple[float, float, float]:
    elo_diff   = home_elo - away_elo + ELO_HA
    p_home_raw = 1.0 / (1.0 + 10 ** (-elo_diff / 400))
    p_away_raw = 1.0 / (1.0 + 10 ** (elo_diff / 400))
    closeness  = 1.0 - abs(p_home_raw - p_away_raw)
    p_draw     = 0.30 * closeness
    remainder  = 1.0 - p_draw
    p_home     = p_home_raw / (p_home_raw + p_away_raw) * remainder
    p_away     = p_away_raw / (p_home_raw + p_away_raw) * remainder
    return p_home, p_draw, p_away


# ─── History replay ──────────────────────────────────────────────────────────

def _replay_history(results_path: str, xg_lookup: dict) -> dict:
    """
    Single-pass replay of all historical results to reconstruct the
    current rolling state for every team (identical update logic to
    build_all_features in ensemble_v2.py).
    """
    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])

    elo:       dict[str, float]  = defaultdict(lambda: STARTING_ELO)
    g2:        dict[str, tuple]  = defaultdict(lambda: (0.0, G2_INITIAL_PHI))
    team_hist: dict[str, list]   = defaultdict(list)
    elo_hist:  dict[str, list]   = defaultdict(list)
    h2h_hist:  dict[tuple, list] = defaultdict(list)
    dc_scored:   dict[str, list] = defaultdict(list)
    dc_conceded: dict[str, list] = defaultdict(list)

    pts_map = {"W": 3, "D": 1, "L": 0}
    n_total = len(df)
    print(f"Replaying {n_total:,} historical matches to build current state...")

    for i, row in df.iterrows():
        if i > 0 and i % 5000 == 0:
            print(f"  {i:,}/{n_total:,}")

        home   = row["home_team"]
        away   = row["away_team"]
        date   = row["match_date"]
        season = row["season"]
        hg     = int(row["home_goals"])
        ag     = int(row["away_goals"])
        result = row["result"]

        xg_key  = (date.date(), home, away, row["league"])
        xg_vals = xg_lookup.get(xg_key)
        h_xg    = xg_vals[0] if xg_vals else None
        a_xg    = xg_vals[1] if xg_vals else None
        xg_d    = xg_vals[2] if xg_vals else None

        home_elo_v = elo[home]
        away_elo_v = elo[away]
        home_exp   = _elo_expected(home_elo_v + ELO_HA, away_elo_v)

        home_mu, home_phi = g2[home]
        away_mu, away_phi = g2[away]

        # Pre-match Elo snapshot (used by _elo_28d_ago for momentum)
        elo_hist[home].append((date, home_elo_v))
        elo_hist[away].append((date, away_elo_v))

        # Outcome
        if result == "H":
            hs, as_ = 1.0, 0.0
            home_res, away_res = "W", "L"
        elif result == "D":
            hs, as_ = 0.5, 0.5
            home_res, away_res = "D", "D"
        else:
            hs, as_ = 0.0, 1.0
            home_res, away_res = "L", "W"

        # Update Elo
        mov = _elo_mov(hg - ag)
        elo[home] = home_elo_v + ELO_K * mov * (hs - home_exp)
        elo[away] = away_elo_v + ELO_K * mov * (as_ - (1.0 - home_exp))

        # Update Glicko-2
        g2[home] = _g2_update(home_mu, home_phi, away_mu,         away_phi, hs,  ha=G2_HA)
        g2[away] = _g2_update(away_mu, away_phi, home_mu + G2_HA, home_phi, as_, ha=0.0)

        # Update H2H
        h2h_hist[_h2h_key(home, away)].append(
            {"home": home, "result": result, "hg": hg, "ag": ag}
        )

        # Update team history
        team_hist[home].append({
            "date": date, "season": season, "result": home_res,
            "points": pts_map[home_res],
            "goal_diff": hg - ag, "goals_scored": hg, "goals_conceded": ag,
            "is_home": True, "xg_scored": h_xg, "xg_conceded": a_xg,
            "xg_diff": xg_d,
        })
        team_hist[away].append({
            "date": date, "season": season, "result": away_res,
            "points": pts_map[away_res],
            "goal_diff": ag - hg, "goals_scored": ag, "goals_conceded": hg,
            "is_home": False, "xg_scored": a_xg, "xg_conceded": h_xg,
            "xg_diff": (-xg_d if xg_d is not None else None),
        })

        # Update rolling DC windows
        dc_scored[home]   = dc_scored[home][-(DC_WINDOW - 1):]   + [hg]
        dc_conceded[home] = dc_conceded[home][-(DC_WINDOW - 1):] + [ag]
        dc_scored[away]   = dc_scored[away][-(DC_WINDOW - 1):]   + [ag]
        dc_conceded[away] = dc_conceded[away][-(DC_WINDOW - 1):] + [hg]

    print(f"  Done. Tracked {len(elo)} teams.\n")
    return {
        "elo":        dict(elo),
        "g2":         dict(g2),
        "team_hist":  dict(team_hist),
        "elo_hist":   dict(elo_hist),
        "h2h_hist":   dict(h2h_hist),
        "dc_scored":  dict(dc_scored),
        "dc_conceded": dict(dc_conceded),
    }


# ─── Team name resolution ────────────────────────────────────────────────────

def _resolve_team(name: str, known_teams: set[str]) -> str:
    """Map an API team name to the canonical name used in results.csv."""
    if name in known_teams:
        return name
    lower = name.lower()
    for t in known_teams:
        if t.lower() == lower:
            return t
    for t in known_teams:
        if t.lower() in lower or lower in t.lower():
            return t
    return name  # return as-is; will get default ratings


# ─── Per-fixture feature builder ─────────────────────────────────────────────

def _build_fixture_features(
    home: str,
    away: str,
    match_date: datetime,
    league_code: str,
    season: str,
    state: dict,
    league_encoder,
) -> dict:
    """Compute the 48-feature vector for one upcoming fixture."""
    # Wrap state in defaultdicts so unknown teams get sensible defaults
    elo        = defaultdict(lambda: STARTING_ELO,    state["elo"])
    g2         = defaultdict(lambda: (0.0, G2_INITIAL_PHI), state["g2"])
    team_hist  = defaultdict(list, state["team_hist"])
    elo_hist_s = defaultdict(list, state["elo_hist"])
    h2h_hist   = defaultdict(list, state["h2h_hist"])
    dc_scored  = defaultdict(list, state["dc_scored"])
    dc_conceded = defaultdict(list, state["dc_conceded"])

    home_elo = elo[home]
    away_elo = elo[away]
    home_exp = _elo_expected(home_elo + ELO_HA, away_elo)

    home_mu, home_phi = g2[home]
    away_mu, away_phi = g2[away]
    home_g2_rat = home_mu * G2_SCALE + 1500.0
    away_g2_rat = away_mu * G2_SCALE + 1500.0

    # Rolling Dixon-Coles probabilities
    atk_h = _dc_attack(dc_scored[home])
    def_h = _dc_defence(dc_conceded[home])
    atk_a = _dc_attack(dc_scored[away])
    def_a = _dc_defence(dc_conceded[away])
    lam   = math.exp(atk_h - def_a + DC_HOME_ADV)
    mu_dc = math.exp(atk_a - def_h)
    p_home_dc, p_draw_dc, p_away_dc = _dc_probs(lam, mu_dc)

    # Append current post-match Elo so momentum can look back 28 days
    h_elo_hist = elo_hist_s[home] + [(match_date, home_elo)]
    a_elo_hist = elo_hist_s[away] + [(match_date, away_elo)]

    hf  = _team_features(team_hist[home], h_elo_hist, home_elo, match_date, season)
    af  = _team_features(team_hist[away], a_elo_hist, away_elo, match_date, season)
    h2h = _h2h_features(h2h_hist[_h2h_key(home, away)], home)

    asymmetry = float(np.clip(hf["days_rest"] - af["days_rest"], -10, 10))
    home_fat  = _fatigue_score(hf["days_rest"], hf["matches_21d"], asymmetry, home=True)
    away_fat  = _fatigue_score(af["days_rest"], af["matches_21d"], asymmetry, home=False)

    home_comp = (hf["result_momentum"] + hf["score_momentum"]
                 + hf["elo_momentum"]  + hf["streak"]) / 4.0
    away_comp = (af["result_momentum"] + af["score_momentum"]
                 + af["elo_momentum"]  + af["streak"]) / 4.0

    try:
        league_enc_val = int(league_encoder.transform([league_code])[0])
    except Exception:
        league_enc_val = int(league_encoder.transform([DEFAULT_LEAGUE])[0])

    return {
        "home_elo": home_elo, "away_elo": away_elo,
        "elo_diff": home_elo - away_elo, "home_expected": home_exp,
        "home_g2_rating": home_g2_rat, "away_g2_rating": away_g2_rat,
        "g2_diff": home_g2_rat - away_g2_rat,
        "home_g2_uncertainty": home_phi * G2_SCALE,
        "home_form": hf["form"], "away_form": af["form"],
        "form_diff": hf["form"] - af["form"],
        "home_goals_scored_avg": hf["gs_avg"],
        "home_goals_conceded_avg": hf["gc_avg"],
        "away_goals_scored_avg": af["gs_avg"],
        "away_goals_conceded_avg": af["gc_avg"],
        "home_xg_avg": hf["xg_scored_home_avg"],
        "home_xg_conceded_avg": hf["xg_conceded_home_avg"],
        "away_xg_avg": af["xg_scored_away_avg"],
        "away_xg_conceded_avg": af["xg_conceded_away_avg"],
        "home_xg_diff_avg": hf["xg_diff_avg"],
        "away_xg_diff_avg": af["xg_diff_avg"],
        "home_result_momentum": hf["result_momentum"],
        "away_result_momentum": af["result_momentum"],
        "home_score_momentum": hf["score_momentum"],
        "away_score_momentum": af["score_momentum"],
        "home_elo_momentum": hf["elo_momentum"],
        "away_elo_momentum": af["elo_momentum"],
        "home_streak": hf["streak"], "away_streak": af["streak"],
        "momentum_diff": home_comp - away_comp,
        "home_days_rest": hf["days_rest"], "away_days_rest": af["days_rest"],
        "home_matches_21d": hf["matches_21d"], "away_matches_21d": af["matches_21d"],
        "rest_asymmetry": asymmetry,
        "home_fatigue_score": home_fat, "away_fatigue_score": away_fat,
        "h2h_home_win_rate": h2h["h2h_home_win_rate"],
        "h2h_goal_diff_avg": h2h["h2h_goal_diff_avg"],
        "h2h_meetings": h2h["h2h_meetings"],
        "h2h_dominance": h2h["h2h_dominance"],
        "revenge_factor": h2h["revenge_factor"],
        "home_unbeaten_run": hf["unbeaten_run"],
        "away_unbeaten_run": af["unbeaten_run"],
        "post_loss_bounce": hf["post_loss"],
        "post_loss_bounce_away": af["post_loss"],
        "league_encoded": league_enc_val,
        "is_early_season": hf["is_early"],
        # DC probabilities (also used in the stack)
        "p_home_dc": p_home_dc, "p_draw_dc": p_draw_dc, "p_away_dc": p_away_dc,
    }


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    # Load models
    print("Loading models...")
    xgb_model      = joblib.load(os.path.join(MODELS_DIR, "xgb_ensemble.pkl"))
    meta_model     = joblib.load(os.path.join(MODELS_DIR, "meta_learner.pkl"))
    league_encoder = joblib.load(os.path.join(MODELS_DIR, "league_encoder.pkl"))
    with open(os.path.join(MODELS_DIR, "feature_cols.json")) as f:
        feature_cols = json.load(f)
    print(f"  XGBoost ({len(feature_cols)} features), meta-learner, league encoder loaded\n")

    # Load xG lookup
    xg_lookup: dict = {}
    xg_path = os.path.join(DATA_DIR, "results_with_xg.csv")
    if os.path.exists(xg_path):
        xg_df = pd.read_csv(xg_path, parse_dates=["match_date"])
        xg_df = xg_df.dropna(subset=["home_xg", "away_xg", "xg_diff"])
        for _, r in xg_df.iterrows():
            key = (r["match_date"].date(), r["home_team"], r["away_team"], r["league"])
            xg_lookup[key] = (float(r["home_xg"]), float(r["away_xg"]), float(r["xg_diff"]))
        print(f"Loaded {len(xg_lookup):,} xG records\n")
    else:
        print("Warning: results_with_xg.csv not found — xG features will use defaults\n")

    # Replay history to build current state
    results_path = os.path.join(DATA_DIR, "results.csv")
    state = _replay_history(results_path, xg_lookup)
    known_teams = set(state["team_hist"].keys()) | set(state["elo"].keys())

    # Fetch upcoming fixtures
    print(f"Fetching upcoming fixtures from {UPCOMING_URL}...")
    try:
        resp = httpx.get(UPCOMING_URL, timeout=30)
        resp.raise_for_status()
        matches = resp.json().get("data", [])
        print(f"  {len(matches)} fixtures returned\n")
    except Exception as exc:
        print(f"  ERROR fetching fixtures: {exc}", file=sys.stderr)
        sys.exit(1)

    out_path = os.path.join(DATA_DIR, "upcoming_predictions.csv")

    if not matches:
        print("No upcoming fixtures — writing empty file.")
        pd.DataFrame(columns=[
            "match_date", "match_time", "league", "home_team", "away_team",
            "p_home_elo", "p_draw_elo", "p_away_elo",
            "p_home_ensemble", "p_draw_ensemble", "p_away_ensemble",
            "predicted_outcome",
        ]).to_csv(out_path, index=False)
        return

    rows = []

    for m in matches:
        home_raw       = m.get("home_team", "")
        away_raw       = m.get("away_team", "")
        match_date_str = m.get("match_date", "")
        match_time     = m.get("match_time", "")
        competition    = m.get("competition", "")

        if not home_raw or not away_raw or not match_date_str:
            continue

        try:
            match_date = datetime.strptime(match_date_str, "%Y-%m-%d")
        except ValueError:
            continue

        league_code = COMP_TO_LEAGUE.get(competition, DEFAULT_LEAGUE)
        season      = _current_season(match_date)

        home = _resolve_team(_strip_suffix(home_raw), known_teams)
        away = _resolve_team(_strip_suffix(away_raw), known_teams)

        # Elo probabilities
        home_elo_val = state["elo"].get(home, STARTING_ELO)
        away_elo_val = state["elo"].get(away, STARTING_ELO)
        p_home_elo, p_draw_elo, p_away_elo = _prematch_probs(home_elo_val, away_elo_val)

        # 48-feature vector
        feat = _build_fixture_features(
            home, away, match_date, league_code, season, state, league_encoder
        )

        # XGBoost prediction — columns: [P(A)=0, P(D)=1, P(H)=2]
        X = np.array([[feat[c] for c in feature_cols]])
        xgb_proba = xgb_model.predict_proba(X)

        # Assemble 12-feature stack for meta-learner
        p_home_g2 = float(_sigmoid(np.array([feat["g2_diff"]]) / G2_SCALE * 1.6)[0])
        stack_row = np.array([[
            feat["home_expected"],
            p_home_g2,
            feat["p_home_dc"], feat["p_draw_dc"], feat["p_away_dc"],
            xgb_proba[0, 2], xgb_proba[0, 1], xgb_proba[0, 0],   # H, D, A
            feat["elo_diff"],
            feat["h2h_goal_diff_avg"],
            feat["h2h_home_win_rate"],
            feat["momentum_diff"],
        ]])

        # Meta-learner prediction — columns: [P(A)=0, P(D)=1, P(H)=2]
        meta_proba = meta_model.predict_proba(stack_row)
        meta_pred  = int(np.argmax(meta_proba[0]))

        rows.append({
            "match_date":       match_date_str,
            "match_time":       match_time,
            "league":           competition,
            "home_team":        home,
            "away_team":        away,
            "p_home_elo":       round(p_home_elo, 4),
            "p_draw_elo":       round(p_draw_elo, 4),
            "p_away_elo":       round(p_away_elo, 4),
            "p_home_ensemble":  round(float(meta_proba[0, 2]), 4),
            "p_draw_ensemble":  round(float(meta_proba[0, 1]), 4),
            "p_away_ensemble":  round(float(meta_proba[0, 0]), 4),
            "predicted_outcome": RESULT_INV[meta_pred],
        })

    out_df = pd.DataFrame(rows)
    out_df.to_csv(out_path, index=False)
    print(f"Saved {len(out_df)} predictions to {out_path}")

    # Print summary
    print(f"\n{'='*70}")
    print(f"UPCOMING PREDICTIONS  ({len(out_df)} fixtures)")
    print(f"{'='*70}")
    for _, row in out_df.sort_values(["match_date", "match_time"]).iterrows():
        label = {"H": "Home", "D": "Draw", "A": "Away"}.get(row["predicted_outcome"], "?")
        print(
            f"  {row['league']:18s}  {row['home_team']} vs {row['away_team']}\n"
            f"    Predicted: {label:4s}  "
            f"ensemble=[H:{row['p_home_ensemble']:.1%} "
            f"D:{row['p_draw_ensemble']:.1%} "
            f"A:{row['p_away_ensemble']:.1%}]  "
            f"elo=H:{row['p_home_elo']:.1%}  "
            f"[{row['match_date']} {row['match_time']}]"
        )


if __name__ == "__main__":
    main()
