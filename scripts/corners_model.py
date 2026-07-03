"""
Corners prediction model — XGBoost regressor for total corners per match.

15 rolling/causal features:
  home_corners_avg, away_corners_avg,
  home_corners_conceded_avg, away_corners_conceded_avg,
  home_attack_pressure, away_attack_pressure,
  home_form, away_form,
  league_avg_corners, elo_diff, league_encoded,
  is_early_season, referee_avg_corners,
  home_corners_trend, away_corners_trend
"""
import math
import os
from collections import defaultdict

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBRegressor

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STARTING_ELO  = 1500.0
ELO_K         = 16
ELO_HA        = 50
FORM_WINDOW   = 5
EWM_ALPHA     = 0.4
CORNER_WINDOW = 10   # rolling window for team corner averages
LEAGUE_WINDOW = 100  # rolling window for league average corners
TREND_WINDOW  = 8    # OLS slope window (venue-specific matches)

# Global defaults used before enough data accumulates
DEFAULT_HOME_C = 5.6
DEFAULT_AWAY_C = 4.6
DEFAULT_TOTAL  = 10.2
DEFAULT_SHOTS  = 13.0

FEATURE_COLS = [
    "home_corners_avg",
    "away_corners_avg",
    "home_corners_conceded_avg",
    "away_corners_conceded_avg",
    "home_attack_pressure",
    "away_attack_pressure",
    "home_form",
    "away_form",
    "league_avg_corners",
    "elo_diff",
    "league_encoded",
    "is_early_season",
    "referee_avg_corners",
    "home_corners_trend",
    "away_corners_trend",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _elo_expected(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def _elo_mov(goal_diff: int) -> float:
    return min(2.0, 1.0 + math.log(1.0 + abs(goal_diff)) / math.log(10.0))


def _ewm(values: list) -> float:
    n = len(values)
    weights = [(1.0 - EWM_ALPHA) ** (n - 1 - i) for i in range(n)]
    total   = sum(weights)
    return sum(w * v for w, v in zip(weights, values)) / total


def _rolling_mean(values: list, window: int, default: float) -> float:
    recent = values[-window:]
    return float(np.mean(recent)) if recent else default


def _ols_slope(values: list) -> float:
    """OLS slope of values against match index — positive = trending up."""
    n = len(values)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    x -= x.mean()
    y = np.array(values, dtype=float)
    y -= y.mean()
    denom = float((x * x).sum())
    return float((x * y).sum() / denom) if denom > 0 else 0.0


# ---------------------------------------------------------------------------
# Single-pass causal feature builder
# ---------------------------------------------------------------------------

def build_corners_features(df: pd.DataFrame) -> tuple[pd.DataFrame, LabelEncoder]:
    league_encoder = LabelEncoder()
    league_encoder.fit(df["league"])
    league_enc = {lg: int(i) for i, lg in enumerate(league_encoder.classes_)}

    elo: dict[str, float] = defaultdict(lambda: STARTING_ELO)

    # Venue-split corner histories
    home_c_won:  dict[str, list] = defaultdict(list)  # corners won by team at home
    away_c_won:  dict[str, list] = defaultdict(list)  # corners won by team away
    home_c_conc: dict[str, list] = defaultdict(list)  # corners conceded at home
    away_c_conc: dict[str, list] = defaultdict(list)  # corners conceded away

    # Shots (venue-split, attack pressure proxy)
    home_sh: dict[str, list] = defaultdict(list)
    away_sh: dict[str, list] = defaultdict(list)

    # All-match points history for EWM form
    form_hist: dict[str, list] = defaultdict(list)

    league_corners: dict[str, list] = defaultdict(list)
    ref_corners:    dict[str, dict] = {}   # referee → {matches, total}
    team_season_matches: dict[tuple, int] = {}

    rows    = []
    n_total = len(df)

    for i, row in df.iterrows():
        if i > 0 and i % 5000 == 0:
            print(f"  Processed {i}/{n_total} matches...")

        home   = row["home_team"]
        away   = row["away_team"]
        date   = row["match_date"]
        season = row["season"]
        league = row["league"]
        hg     = int(row["home_goals"])
        ag     = int(row["away_goals"])
        result = row["result"]

        hc_raw = row.get("home_corners")
        ac_raw = row.get("away_corners")
        hc = float(hc_raw) if pd.notna(hc_raw) else None
        ac = float(ac_raw) if pd.notna(ac_raw) else None
        has_corners = hc is not None and ac is not None

        h_shots_raw = row.get("home_shots")
        a_shots_raw = row.get("away_shots")
        h_shots = float(h_shots_raw) if pd.notna(h_shots_raw) else None
        a_shots = float(a_shots_raw) if pd.notna(a_shots_raw) else None

        ref_raw  = row.get("referee")
        referee  = ref_raw if (isinstance(ref_raw, str) and ref_raw.strip()) else None

        home_elo = elo[home]
        away_elo = elo[away]

        # --- Pre-match rolling features (prior data only) ---
        home_c_avg  = _rolling_mean(home_c_won[home],  CORNER_WINDOW, DEFAULT_HOME_C)
        away_c_avg  = _rolling_mean(away_c_won[away],  CORNER_WINDOW, DEFAULT_AWAY_C)
        home_cc_avg = _rolling_mean(home_c_conc[home], CORNER_WINDOW, DEFAULT_AWAY_C)
        away_cc_avg = _rolling_mean(away_c_conc[away], CORNER_WINDOW, DEFAULT_HOME_C)
        home_press  = _rolling_mean(home_sh[home], CORNER_WINDOW, DEFAULT_SHOTS)
        away_press  = _rolling_mean(away_sh[away], CORNER_WINDOW, DEFAULT_SHOTS)

        hfh = form_hist[home]
        afh = form_hist[away]
        home_form = _ewm([h["pts"] for h in hfh[-FORM_WINDOW:]]) / 3.0 if len(hfh) >= 2 else 0.5
        away_form = _ewm([h["pts"] for h in afh[-FORM_WINDOW:]]) / 3.0 if len(afh) >= 2 else 0.5

        league_avg = _rolling_mean(league_corners[league], LEAGUE_WINDOW, DEFAULT_TOTAL)

        if referee and referee in ref_corners:
            rc = ref_corners[referee]
            ref_avg_c = rc["total"] / rc["matches"]
        else:
            ref_avg_c = DEFAULT_TOTAL

        home_trend = _ols_slope(home_c_won[home][-TREND_WINDOW:])
        away_trend = _ols_slope(away_c_won[away][-TREND_WINDOW:])

        home_sm  = team_season_matches.get((home, season), 0)
        away_sm  = team_season_matches.get((away, season), 0)
        is_early = 1 if min(home_sm, away_sm) < 5 else 0

        rows.append({
            "match_date":  date,
            "season":      season,
            "league":      league,
            "home_team":   home,
            "away_team":   away,
            "home_corners_avg":          home_c_avg,
            "away_corners_avg":          away_c_avg,
            "home_corners_conceded_avg": home_cc_avg,
            "away_corners_conceded_avg": away_cc_avg,
            "home_attack_pressure":      home_press,
            "away_attack_pressure":      away_press,
            "home_form":                 home_form,
            "away_form":                 away_form,
            "league_avg_corners":        league_avg,
            "elo_diff":                  home_elo - away_elo,
            "league_encoded":            league_enc[league],
            "is_early_season":           is_early,
            "referee_avg_corners":       ref_avg_c,
            "home_corners_trend":        home_trend,
            "away_corners_trend":        away_trend,
            "home_corners":  hc,
            "away_corners":  ac,
            "total_corners": (hc + ac) if has_corners else None,
        })

        # Update state AFTER recording features
        if result == "H":
            pts_h, pts_a = 3, 0
        elif result == "D":
            pts_h, pts_a = 1, 1
        else:
            pts_h, pts_a = 0, 3

        form_hist[home].append({"pts": pts_h})
        form_hist[away].append({"pts": pts_a})

        if has_corners:
            home_c_won[home].append(hc)
            away_c_won[away].append(ac)
            home_c_conc[home].append(ac)
            away_c_conc[away].append(hc)
            league_corners[league].append(hc + ac)
            if referee:
                if referee not in ref_corners:
                    ref_corners[referee] = {"matches": 0, "total": 0.0}
                ref_corners[referee]["matches"] += 1
                ref_corners[referee]["total"]   += hc + ac

        if h_shots is not None:
            home_sh[home].append(h_shots)
        if a_shots is not None:
            away_sh[away].append(a_shots)

        h_score  = 1.0 if result == "H" else (0.5 if result == "D" else 0.0)
        mov      = _elo_mov(hg - ag)
        home_exp = _elo_expected(home_elo + ELO_HA, away_elo)
        elo[home] = home_elo + ELO_K * mov * (h_score - home_exp)
        elo[away] = away_elo + ELO_K * mov * ((1.0 - h_score) - (1.0 - home_exp))

        team_season_matches[(home, season)] = home_sm + 1
        team_season_matches[(away, season)] = away_sm + 1

    return pd.DataFrame(rows), league_encoder


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "results.csv")
    )

    df = pd.read_csv(
        results_path,
        parse_dates=["match_date"],
        dtype={"referee": str},
        low_memory=False,
    )
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])
    print(f"Loaded {len(df):,} matches across {df['league'].nunique()} leagues\n")

    print("Building corners features (single-pass causal loop)...")
    feat_df, league_encoder = build_corners_features(df)
    print(f"  Feature rows built: {len(feat_df):,}\n")

    # Restrict to rows with corners data from 2000 onwards
    model_df = feat_df.dropna(subset=["total_corners"])
    model_df = model_df[model_df["match_date"] >= "2000-01-01"].reset_index(drop=True)
    print(f"Matches with corners data (2000+): {len(model_df):,}\n")

    # 80/20 temporal split
    n     = len(model_df)
    split = int(n * 0.80)
    train_df   = model_df.iloc[:split].reset_index(drop=True)
    holdout_df = model_df.iloc[split:].copy().reset_index(drop=True)

    print(f"Train:   {len(train_df):,} matches  "
          f"({train_df['match_date'].min().date()} → {train_df['match_date'].max().date()})")
    print(f"Holdout: {len(holdout_df):,} matches  "
          f"({holdout_df['match_date'].min().date()} → {holdout_df['match_date'].max().date()})\n")

    X_train = train_df[FEATURE_COLS].values.astype(float)
    y_train = train_df["total_corners"].values.astype(float)
    X_ho    = holdout_df[FEATURE_COLS].values.astype(float)
    y_ho    = holdout_df["total_corners"].values.astype(float)

    print("Training XGBoost regressor...")
    model = XGBRegressor(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=3,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(X_train, y_train)
    print("Done.\n")

    # Save model and encoder
    models_dir = os.path.normpath(os.path.join(base, "..", "models"))
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(model, os.path.join(models_dir, "corners_model.pkl"))
    joblib.dump(league_encoder, os.path.join(models_dir, "corners_league_encoder.pkl"))
    print(f"Saved corners_model.pkl and corners_league_encoder.pkl to models/\n")

    # Predictions on holdout
    preds = model.predict(X_ho)
    holdout_df["predicted_corners"] = preds
    holdout_df["actual_corners"]    = y_ho

    mae  = float(np.mean(np.abs(preds - y_ho)))
    rmse = float(np.sqrt(np.mean((preds - y_ho) ** 2)))

    # Naive baseline: league mean from training set
    league_means = train_df.groupby("league")["total_corners"].mean().to_dict()
    global_mean  = float(y_train.mean())
    naive_preds  = holdout_df["league"].map(league_means).fillna(global_mean).values
    mae_naive    = float(np.mean(np.abs(naive_preds - y_ho)))
    rmse_naive   = float(np.sqrt(np.mean((naive_preds - y_ho) ** 2)))

    # Over/Under accuracy
    lines = [9.5, 10.5, 11.5]

    print("=" * 65)
    print(f"HOLDOUT EVALUATION  ({len(holdout_df):,} matches, "
          f"{holdout_df['match_date'].min().date()} → "
          f"{holdout_df['match_date'].max().date()})")
    print("=" * 65)
    print(f"  {'Metric':<32}  {'Model':>8}  {'Naive':>8}")
    print(f"  {'-' * 52}")
    print(f"  {'MAE':<32}  {mae:>8.4f}  {mae_naive:>8.4f}")
    print(f"  {'RMSE':<32}  {rmse:>8.4f}  {rmse_naive:>8.4f}")

    for line in lines:
        actual_over = (y_ho        > line).astype(int)
        model_over  = (preds       > line).astype(int)
        naive_over  = (naive_preds > line).astype(int)
        model_acc   = float((model_over == actual_over).mean())
        naive_acc   = float((naive_over == actual_over).mean())
        pct_over    = float(actual_over.mean())
        print(f"  {f'Over {line} accuracy  ({pct_over:.1%} base rate)':<32}  "
              f"{model_acc:>8.4f}  {naive_acc:>8.4f}")

    print("=" * 65)

    # Feature importance
    print("\nFEATURE IMPORTANCE (XGBoost gain, descending)")
    importance = model.feature_importances_
    for feat, imp in sorted(zip(FEATURE_COLS, importance), key=lambda x: -x[1]):
        bar = "█" * max(1, int(imp * 300))
        print(f"  {feat:<35}  {imp:.4f}  {bar}")

    # Save holdout predictions
    out_cols = [
        "match_date", "home_team", "away_team", "league",
        "predicted_corners", "actual_corners",
        "home_corners", "away_corners",
    ]
    out_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "corners_predictions.csv")
    )
    holdout_df[out_cols].to_csv(out_path, index=False)
    print(f"\nSaved holdout predictions ({len(holdout_df):,} rows) to {out_path}")


if __name__ == "__main__":
    main()
