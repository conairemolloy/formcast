import math
import os
from collections import defaultdict
from datetime import timedelta

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
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

G2_SCALE = 173.7178        # Glicko-2 ↔ Elo scale factor
G2_INITIAL_PHI = 200.0 / G2_SCALE   # RD = 200
G2_SIGMA = 0.06            # constant volatility (simplified — no iterative update)
G2_HA = 50.0 / G2_SCALE   # home advantage in Glicko-2 internal scale

RESULT_MAP = {"A": 0, "D": 1, "H": 2}
RESULT_INV = {0: "A", 1: "D", 2: "H"}

FEATURE_COLS = [
    # Elo
    "home_elo", "away_elo", "elo_diff", "home_expected",
    # Glicko-2
    "home_g2_rating", "away_g2_rating", "g2_diff", "home_g2_uncertainty",
    # Form (last 5)
    "home_form", "away_form", "form_diff",
    "home_goals_scored_avg", "home_goals_conceded_avg",
    "away_goals_scored_avg", "away_goals_conceded_avg",
    # Momentum
    "home_result_momentum", "away_result_momentum",
    "home_score_momentum", "away_score_momentum",
    "home_elo_momentum", "away_elo_momentum",
    "home_streak", "away_streak",
    "momentum_diff",
    # Fatigue
    "home_days_rest", "away_days_rest",
    "home_matches_21d", "away_matches_21d",
    "rest_asymmetry",
    "home_fatigue_score", "away_fatigue_score",
    # H2H
    "h2h_home_win_rate", "h2h_goal_diff_avg",
    "h2h_meetings", "h2h_dominance",
    "revenge_factor",
    "home_unbeaten_run", "away_unbeaten_run",
    "post_loss_bounce", "post_loss_bounce_away",
    # Context
    "league_encoded", "is_early_season",
]  # 42 features total


# ---------------------------------------------------------------------------
# Elo helpers
# ---------------------------------------------------------------------------

def _elo_expected(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def _elo_mov(goal_diff: int) -> float:
    return min(2.0, 1.0 + math.log(1.0 + abs(goal_diff)) / math.log(10.0))


# ---------------------------------------------------------------------------
# Glicko-2 helpers (simplified: no volatility update, constant sigma)
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
    """
    Single-match Glicko-2 rating update (no sigma iteration).
    ha: home-advantage offset added to this team's mu when computing expected score.
    opp_mu should already include any opponent home-advantage offset.
    """
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
    """EWM with adjust=True (weights normalised), alpha=EWM_ALPHA, oldest→newest."""
    n = len(values)
    weights = [(1.0 - EWM_ALPHA) ** (n - 1 - i) for i in range(n)]
    total = sum(weights)
    return sum(w * v for w, v in zip(weights, values)) / total


def _streak(hist: list) -> int:
    """Current W/L streak length. +N = won last N, -N = lost last N, 0 = drew/mixed."""
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
    """Most recent pre-match Elo recorded at or before match_date − 28 days."""
    cutoff = match_date - timedelta(days=28)
    result = None
    for date, rating in elo_hist:   # sorted ascending
        if date <= cutoff:
            result = rating
        else:
            break
    return result


# ---------------------------------------------------------------------------
# Per-team feature bundle
# ---------------------------------------------------------------------------

def _team_features(
    hist: list,
    elo_hist: list,
    current_elo: float,
    match_date,
    season: str,
) -> dict:
    """
    Compute all per-team signals from prior history.
    hist and elo_hist contain only strictly prior matches
    (state is updated after feature computation each iteration).
    """
    n = len(hist)

    # Form (last FORM_WINDOW matches)
    fw = hist[-FORM_WINDOW:]
    if fw:
        nf = len(fw)
        form = sum(h["points"] for h in fw) / (3.0 * nf)
        gs_avg = sum(h["goals_scored"] for h in fw) / nf
        gc_avg = sum(h["goals_conceded"] for h in fw) / nf
    else:
        form, gs_avg, gc_avg = 0.5, 1.5, 1.5

    # Result momentum (EWM of points, last 5)
    rm = _ewm([h["points"] for h in hist[-5:]]) / 3.0 if n >= 2 else 0.5

    # Score momentum (EWM of goal diff, last 5)
    if n >= 2:
        sm_raw = float(np.clip(_ewm([h["goal_diff"] for h in hist[-5:]]), -5.0, 5.0))
        sm = (sm_raw + 5.0) / 10.0
    else:
        sm = 0.5

    # Elo momentum: (current − 28-days-ago) / 100
    past_elo = _elo_28d_ago(elo_hist, match_date)
    elo_mom = (current_elo - past_elo) / 100.0 if past_elo is not None else 0.0

    # Streak normalised to [0, 1]
    streak = (float(np.clip(_streak(hist), -5, 5)) + 5.0) / 10.0

    # Fatigue
    cut21 = match_date - timedelta(days=21)
    matches_21d = sum(1 for h in hist if h["date"] > cut21)
    days_rest = (match_date - hist[-1]["date"]).days if hist else 14

    # Situational
    season_hist = [h for h in hist if h["season"] == season]
    season_pos = len(season_hist)
    is_early = 1 if season_pos < 5 else 0
    post_loss = 1 if (hist and hist[-1]["result"] == "L") else 0

    # Unbeaten run (W or D streak, clipped at 15)
    unbeaten = 0
    for h in reversed(hist):
        if h["result"] in ("W", "D"):
            unbeaten += 1
        else:
            break
    unbeaten = min(unbeaten, 15)

    return {
        "form": form, "gs_avg": gs_avg, "gc_avg": gc_avg,
        "result_momentum": rm, "score_momentum": sm,
        "elo_momentum": elo_mom, "streak": streak,
        "days_rest": days_rest, "matches_21d": matches_21d,
        "season_pos": season_pos, "is_early": is_early,
        "post_loss": post_loss, "unbeaten_run": unbeaten,
    }


# ---------------------------------------------------------------------------
# H2H features
# ---------------------------------------------------------------------------

def _h2h_key(a: str, b: str) -> tuple:
    return (min(a, b), max(a, b))


def _h2h_features(records: list, home: str) -> dict:
    """Compute H2H features from prior meetings (records already contains only prior matches)."""
    if not records:
        return {
            "h2h_home_wins": 0, "h2h_away_wins": 0, "h2h_draws": 0,
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
            if rec["result"] == "H":
                hw += 1
            elif rec["result"] == "A":
                aw += 1
            else:
                dw += 1
        else:
            gd = rec["ag"] - rec["hg"]
            if rec["result"] == "A":
                hw += 1
            elif rec["result"] == "H":
                aw += 1
            else:
                dw += 1
        gd_total += gd
    win_rate = hw / n
    last = records[-1]
    if last["home"] == home:
        revenge = 1 if last["result"] == "A" else 0
    else:
        revenge = 1 if last["result"] == "H" else 0
    return {
        "h2h_home_wins": hw, "h2h_away_wins": aw, "h2h_draws": dw,
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
# Single-pass feature builder
# ---------------------------------------------------------------------------

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    le = LabelEncoder()
    le.fit(df["league"])
    league_enc = {lg: int(i) for i, lg in enumerate(le.classes_)}

    # Mutable team state (all updated AFTER computing each row's features)
    elo: dict[str, float] = defaultdict(lambda: STARTING_ELO)
    g2: dict[str, tuple]  = defaultdict(lambda: (0.0, G2_INITIAL_PHI))
    team_hist: dict[str, list] = defaultdict(list)
    elo_hist:  dict[str, list] = defaultdict(list)
    h2h_hist:  dict[tuple, list] = defaultdict(list)

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

        # ---- Pre-match ratings -----------------------------------------
        home_elo = elo[home]
        away_elo = elo[away]
        home_exp = _elo_expected(home_elo + ELO_HA, away_elo)

        home_mu, home_phi = g2[home]
        away_mu, away_phi = g2[away]
        home_g2_rat = home_mu * G2_SCALE + 1500.0
        away_g2_rat = away_mu * G2_SCALE + 1500.0

        # Record pre-match Elo before computing features so elo_momentum
        # can compare current rating against the value from 28 days ago.
        elo_hist[home].append((date, home_elo))
        elo_hist[away].append((date, away_elo))

        # ---- Per-team signals ------------------------------------------
        hf = _team_features(team_hist[home], elo_hist[home], home_elo, date, season)
        af = _team_features(team_hist[away], elo_hist[away], away_elo, date, season)

        # ---- H2H signals -----------------------------------------------
        key = _h2h_key(home, away)
        h2h = _h2h_features(h2h_hist[key], home)

        # ---- Derived / combined signals --------------------------------
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
            "h2h_home_win_rate": h2h["h2h_home_win_rate"],
            "h2h_goal_diff_avg": h2h["h2h_goal_diff_avg"],
            "h2h_meetings": h2h["h2h_meetings"],
            "h2h_dominance": h2h["h2h_dominance"],
            "revenge_factor": h2h["revenge_factor"],
            "home_unbeaten_run": hf["unbeaten_run"],
            "away_unbeaten_run": af["unbeaten_run"],
            "post_loss_bounce": hf["post_loss"],
            "post_loss_bounce_away": af["post_loss"],
            # Context
            "league_encoded": league_enc[league],
            "is_early_season": hf["is_early"],
            # Target
            "result": result,
        })

        # ---- Update state (AFTER recording features) -------------------
        if result == "H":
            hs, as_, home_res, away_res = 1.0, 0.0, "W", "L"
        elif result == "D":
            hs, as_, home_res, away_res = 0.5, 0.5, "D", "D"
        else:
            hs, as_, home_res, away_res = 0.0, 1.0, "L", "W"

        mov = _elo_mov(hg - ag)
        elo[home] = home_elo + ELO_K * mov * (hs - home_exp)
        elo[away] = away_elo + ELO_K * mov * (as_ - (1.0 - home_exp))

        # G2 home: +HA applied to its own effective rating
        # G2 away: opponent effective rating is mu_home + G2_HA
        g2[home] = _g2_update(home_mu, home_phi, away_mu,         away_phi, hs,  ha=G2_HA)
        g2[away] = _g2_update(away_mu, away_phi, home_mu + G2_HA, home_phi, as_, ha=0.0)

        h2h_hist[key].append({"home": home, "result": result, "hg": hg, "ag": ag})

        team_hist[home].append({
            "date": date, "season": season, "result": home_res,
            "points": pts_map[home_res],
            "goal_diff": hg - ag, "goals_scored": hg, "goals_conceded": ag,
        })
        team_hist[away].append({
            "date": date, "season": season, "result": away_res,
            "points": pts_map[away_res],
            "goal_diff": ag - hg, "goals_scored": ag, "goals_conceded": hg,
        })

    return pd.DataFrame(rows)


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

    print(f"Building {len(FEATURE_COLS)} features for {len(df):,} matches...")
    feat_df = build_features(df)
    print(f"  Processed {len(df):,}/{len(df):,} matches (complete)\n")

    # Skip cold-start rows from training/test (state still built for all rows)
    model_df = feat_df.iloc[COLD_START:].reset_index(drop=True)
    model_df["target"] = model_df["result"].map(RESULT_MAP)

    n = len(model_df)
    split = int(n * 0.70)
    train_df = model_df.iloc[:split].reset_index(drop=True)
    test_df  = model_df.iloc[split:].copy().reset_index(drop=True)

    print(f"Train: {len(train_df):,} matches  "
          f"({train_df['match_date'].min().date()} → {train_df['match_date'].max().date()})")
    print(f"Test:  {len(test_df):,} matches  "
          f"({test_df['match_date'].min().date()} → {test_df['match_date'].max().date()})\n")

    X_train = train_df[FEATURE_COLS].values
    y_train = train_df["target"].values
    X_test  = test_df[FEATURE_COLS].values

    print("Training XGBClassifier (500 trees, depth=5, lr=0.03)...")
    model = XGBClassifier(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=3,
        eval_metric="mlogloss",
        random_state=42,
    )
    model.fit(X_train, y_train)
    print("Done.\n")

    proba      = model.predict_proba(X_test)   # cols: P(A)=0, P(D)=1, P(H)=2
    pred_int   = model.predict(X_test)

    test_df["p_away"]            = proba[:, 0]
    test_df["p_draw"]            = proba[:, 1]
    test_df["p_home"]            = proba[:, 2]
    test_df["predicted_result"]  = [RESULT_INV[p] for p in pred_int]
    test_df["actual_result"]     = test_df["result"]
    test_df["correct"]           = (test_df["predicted_result"] == test_df["actual_result"]).astype(int)

    hit_rate = test_df["correct"].mean()
    act_home  = test_df["actual_result"].map({"H": 1.0, "D": 0.5, "A": 0.0})
    brier     = ((test_df["p_home"] - act_home) ** 2).mean()

    # ---- Feature importances -------------------------------------------
    importances = pd.Series(model.feature_importances_, index=FEATURE_COLS)
    print("=== Feature Importances (all 43 features ranked) ===")
    for feat, imp in importances.sort_values(ascending=False).items():
        bar = "█" * int(imp * 300)
        print(f"  {feat:<32s} {imp:.4f}  {bar}")

    # ---- Elo baseline on same test matches -----------------------------
    elo_pred = test_df["home_expected"].apply(lambda x: "H" if x > 0.5 else "A")
    elo_hit  = (elo_pred == test_df["actual_result"]).mean()

    # ---- Load old XGBoost for comparison --------------------------------
    xgb_old_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "xgb_predictions.csv")
    )
    old_hit = old_brier = old_n = None
    try:
        xgb_old = pd.read_csv(xgb_old_path)
        old_hit   = xgb_old["correct"].mean()
        old_act   = xgb_old["actual_result"].map({"H": 1.0, "D": 0.5, "A": 0.0})
        old_brier = ((xgb_old["p_home"] - old_act) ** 2).mean()
        old_n     = len(xgb_old)
    except FileNotFoundError:
        pass

    # ---- Summary -------------------------------------------------------
    print("\n=== Model Comparison (test set) ===")
    print(f"  {'Model':<32s}  {'N':>5}  {'HitRate':>8}  {'Brier':>9}")
    print(f"  {'-'*32}  {'-'*5}  {'-'*8}  {'-'*9}")
    print(f"  {'Full XGB (new, 43 features)':<32s}  {len(test_df):>5}  {hit_rate:>7.4f}  {brier:>9.6f}")
    if old_hit is not None:
        print(f"  {'Basic XGB (xgboost_model.py)':<32s}  {old_n:>5}  {old_hit:>7.4f}  {old_brier:>9.6f}")
    print(f"  {'Elo baseline':<32s}  {len(test_df):>5}  {elo_hit:>7.4f}  {'—':>9}")

    print(f"\n  Full XGB vs Elo:  {hit_rate - elo_hit:+.4f} hit rate")
    if old_hit is not None:
        print(f"  Full XGB vs Basic XGB: {hit_rate - old_hit:+.4f} hit rate, "
              f"{brier - old_brier:+.6f} Brier")

    # ---- Save ----------------------------------------------------------
    features_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "full_features.csv")
    )
    feat_df.to_csv(features_path, index=False)
    print(f"\nSaved full feature matrix ({len(feat_df):,} rows) to {features_path}")

    pred_cols = [
        "match_date", "league", "home_team", "away_team",
        "p_home", "p_draw", "p_away",
        "predicted_result", "actual_result", "correct",
    ]
    pred_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "full_xgb_predictions.csv")
    )
    test_df[pred_cols].to_csv(pred_path, index=False)
    print(f"Saved test predictions ({len(test_df):,} rows) to {pred_path}")


if __name__ == "__main__":
    main()
