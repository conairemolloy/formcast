"""
Stacking ensemble (v2) — extends ensemble.py with the full 48-feature base model.

Stack inputs (12 features):
  home_expected, p_home_g2,
  p_home_dc, p_draw_dc, p_away_dc,
  p_home_xgb, p_draw_xgb, p_away_xgb,
  elo_diff, h2h_goal_diff_avg, h2h_home_win_rate, momentum_diff

Meta-learner: LogisticRegression in a StandardScaler Pipeline.
"""
import json
import math
import os
from collections import defaultdict
from datetime import timedelta

import joblib
import numpy as np
import pandas as pd
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
COLD_START = 200
FORM_WINDOW = 5
EWM_ALPHA = 0.4

G2_SCALE = 173.7178
G2_INITIAL_PHI = 200.0 / G2_SCALE
G2_SIGMA = 0.06
G2_HA = 50.0 / G2_SCALE

DC_WINDOW = 38
DC_HOME_ADV = 0.1
DC_MAX_GOALS = 8

RESULT_MAP = {"A": 0, "D": 1, "H": 2}
RESULT_INV = {0: "A", 1: "D", 2: "H"}

# Full 48-feature set used for XGBoost base model
FEATURE_COLS = [
    "home_elo", "away_elo", "elo_diff", "home_expected",
    "home_g2_rating", "away_g2_rating", "g2_diff", "home_g2_uncertainty",
    "home_form", "away_form", "form_diff",
    "home_goals_scored_avg", "home_goals_conceded_avg",
    "away_goals_scored_avg", "away_goals_conceded_avg",
    "home_xg_avg", "home_xg_conceded_avg", "away_xg_avg",
    "away_xg_conceded_avg", "home_xg_diff_avg", "away_xg_diff_avg",
    "home_result_momentum", "away_result_momentum",
    "home_score_momentum", "away_score_momentum",
    "home_elo_momentum", "away_elo_momentum",
    "home_streak", "away_streak",
    "momentum_diff",
    "home_days_rest", "away_days_rest",
    "home_matches_21d", "away_matches_21d",
    "rest_asymmetry",
    "home_fatigue_score", "away_fatigue_score",
    "h2h_home_win_rate", "h2h_goal_diff_avg",
    "h2h_meetings", "h2h_dominance",
    "revenge_factor",
    "home_unbeaten_run", "away_unbeaten_run",
    "post_loss_bounce", "post_loss_bounce_away",
    "league_encoded", "is_early_season",
]

# 12-feature stack fed into the meta-learner
STACK_COLS = [
    "home_expected",
    "p_home_g2",
    "p_home_dc", "p_draw_dc", "p_away_dc",
    "p_home_xgb", "p_draw_xgb", "p_away_xgb",
    "elo_diff", "h2h_goal_diff_avg", "h2h_home_win_rate", "momentum_diff",
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

def _ewm(values: list) -> float:
    n = len(values)
    weights = [(1.0 - EWM_ALPHA) ** (n - 1 - i) for i in range(n)]
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
        gs_avg = sum(h["goals_scored"] for h in fw) / nf
        gc_avg = sum(h["goals_conceded"] for h in fw) / nf
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

    home_xg_hist = [h for h in hist if h.get("is_home") is True  and h.get("xg_scored") is not None]
    away_xg_hist = [h for h in hist if h.get("is_home") is False and h.get("xg_scored") is not None]
    all_xg_hist  = [h for h in hist if h.get("xg_scored") is not None]

    fw_hxg     = home_xg_hist[-FORM_WINDOW:]
    fw_axg     = away_xg_hist[-FORM_WINDOW:]
    fw_axg_all = all_xg_hist[-FORM_WINDOW:]

    xg_scored_home_avg   = sum(h["xg_scored"]   for h in fw_hxg)     / len(fw_hxg)     if fw_hxg     else 1.3
    xg_conceded_home_avg = sum(h["xg_conceded"] for h in fw_hxg)     / len(fw_hxg)     if fw_hxg     else 1.3
    xg_scored_away_avg   = sum(h["xg_scored"]   for h in fw_axg)     / len(fw_axg)     if fw_axg     else 1.3
    xg_conceded_away_avg = sum(h["xg_conceded"] for h in fw_axg)     / len(fw_axg)     if fw_axg     else 1.3
    xg_diff_avg          = sum(h["xg_diff"]     for h in fw_axg_all) / len(fw_axg_all) if fw_axg_all else 0.0

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

    elo:       dict[str, float] = defaultdict(lambda: STARTING_ELO)
    g2:        dict[str, tuple] = defaultdict(lambda: (0.0, G2_INITIAL_PHI))
    team_hist: dict[str, list]  = defaultdict(list)
    elo_hist:  dict[str, list]  = defaultdict(list)
    h2h_hist:  dict[tuple, list] = defaultdict(list)

    # Rolling DC state (last DC_WINDOW goals)
    dc_scored:   dict[str, list] = defaultdict(list)
    dc_conceded: dict[str, list] = defaultdict(list)

    pts_map = {"W": 3, "D": 1, "L": 0}
    rows = []
    n_total = len(df)

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

        xg_key  = (date.date(), home, away, league)
        xg_vals = xg_lookup.get(xg_key)
        h_xg    = xg_vals[0] if xg_vals else None
        a_xg    = xg_vals[1] if xg_vals else None
        xg_d    = xg_vals[2] if xg_vals else None

        # Pre-match ratings
        home_elo = elo[home]
        away_elo = elo[away]
        home_exp = _elo_expected(home_elo + ELO_HA, away_elo)

        home_mu, home_phi = g2[home]
        away_mu, away_phi = g2[away]
        home_g2_rat = home_mu * G2_SCALE + 1500.0
        away_g2_rat = away_mu * G2_SCALE + 1500.0

        # Rolling DC probabilities
        atk_h = _dc_attack(dc_scored[home])
        def_h = _dc_defence(dc_conceded[home])
        atk_a = _dc_attack(dc_scored[away])
        def_a = _dc_defence(dc_conceded[away])
        lam = math.exp(atk_h - def_a + DC_HOME_ADV)
        mu  = math.exp(atk_a - def_h)
        p_home_dc, p_draw_dc, p_away_dc = _dc_probs(lam, mu)

        # Record pre-match Elo for elo_momentum lookups
        elo_hist[home].append((date, home_elo))
        elo_hist[away].append((date, away_elo))

        hf  = _team_features(team_hist[home], elo_hist[home], home_elo, date, season)
        af  = _team_features(team_hist[away], elo_hist[away], away_elo, date, season)
        h2h = _h2h_features(h2h_hist[_h2h_key(home, away)], home)

        asymmetry = float(np.clip(hf["days_rest"] - af["days_rest"], -10, 10))
        home_fat  = _fatigue_score(hf["days_rest"], hf["matches_21d"], asymmetry, home=True)
        away_fat  = _fatigue_score(af["days_rest"], af["matches_21d"], asymmetry, home=False)

        home_comp = (hf["result_momentum"] + hf["score_momentum"]
                     + hf["elo_momentum"]  + hf["streak"]) / 4.0
        away_comp = (af["result_momentum"] + af["score_momentum"]
                     + af["elo_momentum"]  + af["streak"]) / 4.0

        rows.append({
            # Metadata
            "match_date": date, "season": season, "league": league,
            "home_team": home, "away_team": away,
            # Elo
            "home_elo": home_elo, "away_elo": away_elo,
            "elo_diff": home_elo - away_elo, "home_expected": home_exp,
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
            # xG (from prior matches, no leakage)
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
            "league_encoded": league_enc[league],
            "is_early_season": hf["is_early"],
            # Rolling DC
            "p_home_dc": p_home_dc, "p_draw_dc": p_draw_dc, "p_away_dc": p_away_dc,
            # Target
            "result": result,
        })

        # Update state (AFTER recording features)
        if result == "H":
            hs, as_, home_res, away_res = 1.0, 0.0, "W", "L"
        elif result == "D":
            hs, as_, home_res, away_res = 0.5, 0.5, "D", "D"
        else:
            hs, as_, home_res, away_res = 0.0, 1.0, "L", "W"

        mov = _elo_mov(hg - ag)
        elo[home] = home_elo + ELO_K * mov * (hs - home_exp)
        elo[away] = away_elo + ELO_K * mov * (as_ - (1.0 - home_exp))

        g2[home] = _g2_update(home_mu, home_phi, away_mu,         away_phi, hs,  ha=G2_HA)
        g2[away] = _g2_update(away_mu, away_phi, home_mu + G2_HA, home_phi, as_, ha=0.0)

        h2h_hist[_h2h_key(home, away)].append(
            {"home": home, "result": result, "hg": hg, "ag": ag}
        )
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

        dc_scored[home]   = dc_scored[home][-(DC_WINDOW - 1):] + [hg]
        dc_conceded[home] = dc_conceded[home][-(DC_WINDOW - 1):] + [ag]
        dc_scored[away]   = dc_scored[away][-(DC_WINDOW - 1):] + [ag]
        dc_conceded[away] = dc_conceded[away][-(DC_WINDOW - 1):] + [hg]

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
        max_depth=5,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=3,
        eval_metric="mlogloss",
        random_state=42,
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
    Assemble STACK_COLS (12 features) in the declared order.
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

def _brier(p_home: np.ndarray, actual: pd.Series) -> float:
    ahs = actual.map({"H": 1.0, "D": 0.5, "A": 0.0}).values
    return float(((p_home - ahs) ** 2).mean())


def _hit(pred: np.ndarray, actual: pd.Series) -> float:
    return float((pred == actual.values).mean())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "results.csv")
    )

    df = pd.read_csv(results_path, parse_dates=["match_date"])
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

    print(f"Building features for {len(df):,} matches (48-feature set + rolling DC)...")
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

    X_train_xgb = train_df[FEATURE_COLS].values
    y_train     = train_df["target"].values

    # ------------------------------------------------------------------
    # Step 1: OOF XGBoost predictions (train set only)
    # ------------------------------------------------------------------
    print("Generating OOF XGBoost predictions (5-fold TimeSeriesSplit)...")
    oof_proba = generate_oof_xgb(X_train_xgb, y_train)
    train_stack = _build_stack(train_df, oof_proba)

    # ------------------------------------------------------------------
    # Step 2: Full XGBoost trained on all of train_df (for holdout)
    # ------------------------------------------------------------------
    print("\nTraining full XGBoost on training set...")
    xgb_full = _make_xgb()
    xgb_full.fit(X_train_xgb, y_train)

    X_holdout_xgb   = holdout_df[FEATURE_COLS].values
    holdout_xgb_proba = xgb_full.predict_proba(X_holdout_xgb)
    holdout_stack     = _build_stack(holdout_df, holdout_xgb_proba)

    # ------------------------------------------------------------------
    # Step 3: Meta-learner
    # ------------------------------------------------------------------
    print("Training meta-learner (LogisticRegression + StandardScaler)...")
    meta = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(C=1.0, max_iter=1000, random_state=42)),
    ])
    meta.fit(train_stack, y_train)

    # ------------------------------------------------------------------
    # Save models
    # ------------------------------------------------------------------
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(xgb_full, os.path.join(models_dir, 'xgb_ensemble.pkl'))
    print(f"Saved XGBoost model to models/xgb_ensemble.pkl")
    joblib.dump(meta, os.path.join(models_dir, 'meta_learner.pkl'))
    print(f"Saved meta-learner to models/meta_learner.pkl")
    with open(os.path.join(models_dir, 'feature_cols.json'), 'w') as f:
        json.dump(FEATURE_COLS, f)
    joblib.dump(league_encoder, os.path.join(models_dir, 'league_encoder.pkl'))

    # ------------------------------------------------------------------
    # Step 4: Holdout evaluation
    # ------------------------------------------------------------------
    meta_proba = meta.predict_proba(holdout_stack)   # cols: P(A), P(D), P(H)
    meta_pred  = meta.predict(holdout_stack)

    holdout_df["p_away"] = meta_proba[:, 0]
    holdout_df["p_draw"] = meta_proba[:, 1]
    holdout_df["p_home"] = meta_proba[:, 2]
    holdout_df["predicted_result"] = [RESULT_INV[int(p)] for p in meta_pred]
    holdout_df["actual_result"]    = holdout_df["result"]
    holdout_df["correct"] = (
        holdout_df["predicted_result"] == holdout_df["actual_result"]
    ).astype(int)

    actual = holdout_df["actual_result"]

    ens_hit   = holdout_df["correct"].mean()
    ens_brier = _brier(holdout_df["p_home"].values, actual)

    # Full XGBoost standalone
    xgb_pred_str = np.array([RESULT_INV[int(p)] for p in xgb_full.predict(X_holdout_xgb)])
    xgb_hit      = _hit(xgb_pred_str, actual)
    xgb_brier    = _brier(holdout_xgb_proba[:, 2], actual)

    # Elo baseline
    elo_pred_str = np.where(holdout_df["home_expected"].values > 0.5, "H", "A")
    elo_hit      = _hit(elo_pred_str, actual)
    elo_brier    = _brier(holdout_df["home_expected"].values, actual)

    # Glicko-2 baseline
    p_home_g2_holdout = _sigmoid(holdout_df["g2_diff"].values / G2_SCALE * 1.6)
    g2_pred_str       = np.where(p_home_g2_holdout > 0.5, "H", "A")
    g2_hit            = _hit(g2_pred_str, actual)
    g2_brier          = _brier(p_home_g2_holdout, actual)

    # Dixon-Coles baseline
    dc_cols = np.column_stack([
        holdout_df["p_away_dc"], holdout_df["p_draw_dc"], holdout_df["p_home_dc"],
    ])
    dc_pred_str = np.array([RESULT_INV[int(i)] for i in np.argmax(dc_cols, axis=1)])
    dc_hit      = _hit(dc_pred_str, actual)
    dc_brier    = _brier(holdout_df["p_home_dc"].values, actual)

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
    best_brier = min(elo_brier, g2_brier, xgb_brier, dc_brier)

    print("\n" + "=" * 68)
    print(f"HOLDOUT EVALUATION  ({len(holdout_df):,} matches, "
          f"{holdout_df['match_date'].min().date()} → "
          f"{holdout_df['match_date'].max().date()})")
    print("=" * 68)
    print(f"  {'Model':<20s}  {'Hit Rate':>10}  {'Brier':>10}")
    print(f"  {'-' * 44}")

    rows_table = [
        ("Ensemble v2",  ens_hit,  ens_brier),
        ("Full XGB",     xgb_hit,  xgb_brier),
        ("Elo baseline", elo_hit,  elo_brier),
        ("Glicko-2",     g2_hit,   g2_brier),
        ("Dixon-Coles",  dc_hit,   dc_brier),
    ]
    for name, hr, br in rows_table:
        marker = " ◀ best" if (hr == max(r[1] for r in rows_table) or
                                br == min(r[2] for r in rows_table)) else ""
        print(f"  {name:<20s}  {hr:>10.4f}  {br:>10.6f}{marker}")

    hit_delta   = ens_hit - best_hit
    brier_delta = ens_brier - best_brier
    print(f"\n  Improvement over best single model:")
    print(f"    Hit rate : {hit_delta:+.4f}  ({'✓ better' if hit_delta >= 0 else '✗ worse'})")
    print(f"    Brier    : {brier_delta:+.6f}  ({'✓ better' if brier_delta <= 0 else '✗ worse'})")
    print("=" * 68)

    # ------------------------------------------------------------------
    # Step 6: Save predictions
    # ------------------------------------------------------------------
    out_cols = [
        "match_date", "league", "home_team", "away_team",
        "p_home", "p_draw", "p_away",
        "predicted_result", "actual_result", "correct",
    ]
    out_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "ensemble_v2_predictions.csv")
    )
    holdout_df[out_cols].to_csv(out_path, index=False)
    print(f"\nSaved holdout predictions ({len(holdout_df):,} rows) to {out_path}")


if __name__ == "__main__":
    main()
