"""
Cards prediction model — XGBoost regressor for total yellow cards per match.

19 rolling/causal features:
  home_yellows_avg, away_yellows_avg,
  home_yellows_conceded_avg, away_yellows_conceded_avg,
  home_fouls_avg, away_fouls_avg,
  home_aggression, away_aggression,
  referee_avg_yellows, referee_avg_fouls,
  referee_home_bias, referee_experience,
  league_avg_yellows, elo_diff, league_encoded,
  is_derby, home_form, away_form, is_early_season
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
CARD_WINDOW   = 10   # rolling window for team yellow card averages
LEAGUE_WINDOW = 100  # rolling window for league average yellows

# Global defaults used before enough data accumulates
DEFAULT_HOME_Y   = 1.8   # home team yellows per match
DEFAULT_AWAY_Y   = 1.7   # away team yellows per match
DEFAULT_TOTAL_Y  = 3.5   # total yellows per match
DEFAULT_FOULS    = 12.0  # fouls per team per match
DEFAULT_HOME_AGG = 15.6  # fouls + 2*yellows, home
DEFAULT_AWAY_AGG = 15.4  # fouls + 2*yellows, away

FEATURE_COLS = [
    "home_yellows_avg",
    "away_yellows_avg",
    "home_yellows_conceded_avg",
    "away_yellows_conceded_avg",
    "home_fouls_avg",
    "away_fouls_avg",
    "home_aggression",
    "away_aggression",
    "referee_avg_yellows",
    "referee_avg_fouls",
    "referee_home_bias",
    "referee_experience",
    "league_avg_yellows",
    "elo_diff",
    "league_encoded",
    "is_derby",
    "home_form",
    "away_form",
    "is_early_season",
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


# ---------------------------------------------------------------------------
# Single-pass causal feature builder
# ---------------------------------------------------------------------------

def build_cards_features(df: pd.DataFrame) -> tuple[pd.DataFrame, LabelEncoder]:
    league_encoder = LabelEncoder()
    league_encoder.fit(df["league"])
    league_enc = {lg: int(i) for i, lg in enumerate(league_encoder.classes_)}

    elo: dict[str, float] = defaultdict(lambda: STARTING_ELO)

    # Venue-split yellow card histories
    home_y_won:  dict[str, list] = defaultdict(list)  # yellows by team at home
    away_y_won:  dict[str, list] = defaultdict(list)  # yellows by team away
    home_y_conc: dict[str, list] = defaultdict(list)  # yellows conceded at home (opponent's)
    away_y_conc: dict[str, list] = defaultdict(list)  # yellows conceded away

    # Venue-split foul histories
    home_fouls: dict[str, list] = defaultdict(list)
    away_fouls: dict[str, list] = defaultdict(list)

    # Venue-split aggression composite: fouls + 2*yellows
    home_agg: dict[str, list] = defaultdict(list)
    away_agg: dict[str, list] = defaultdict(list)

    # All-match points history for EWM form
    form_hist: dict[str, list] = defaultdict(list)

    league_yellows: dict[str, list] = defaultdict(list)

    # referee → {matches, total_yellows, home_yellows, away_yellows, total_fouls}
    ref_stats: dict[str, dict] = {}

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

        hy_raw = row.get("home_yellows")
        ay_raw = row.get("away_yellows")
        hy = float(hy_raw) if pd.notna(hy_raw) else None
        ay = float(ay_raw) if pd.notna(ay_raw) else None
        has_yellows = hy is not None and ay is not None

        hf_raw = row.get("home_fouls")
        af_raw = row.get("away_fouls")
        hf = float(hf_raw) if pd.notna(hf_raw) else None
        af = float(af_raw) if pd.notna(af_raw) else None

        ref_raw = row.get("referee")
        referee = ref_raw if (isinstance(ref_raw, str) and ref_raw.strip()) else None

        home_elo = elo[home]
        away_elo = elo[away]

        # --- Pre-match rolling features (prior data only) ---
        home_y_avg  = _rolling_mean(home_y_won[home],  CARD_WINDOW, DEFAULT_HOME_Y)
        away_y_avg  = _rolling_mean(away_y_won[away],  CARD_WINDOW, DEFAULT_AWAY_Y)
        home_yc_avg = _rolling_mean(home_y_conc[home], CARD_WINDOW, DEFAULT_AWAY_Y)
        away_yc_avg = _rolling_mean(away_y_conc[away], CARD_WINDOW, DEFAULT_HOME_Y)

        home_f_avg = _rolling_mean(home_fouls[home], CARD_WINDOW, DEFAULT_FOULS)
        away_f_avg = _rolling_mean(away_fouls[away], CARD_WINDOW, DEFAULT_FOULS)

        home_agg_avg = _rolling_mean(home_agg[home], CARD_WINDOW, DEFAULT_HOME_AGG)
        away_agg_avg = _rolling_mean(away_agg[away], CARD_WINDOW, DEFAULT_AWAY_AGG)

        hfh = form_hist[home]
        afh = form_hist[away]
        home_form = _ewm([h["pts"] for h in hfh[-FORM_WINDOW:]]) / 3.0 if len(hfh) >= 2 else 0.5
        away_form = _ewm([h["pts"] for h in afh[-FORM_WINDOW:]]) / 3.0 if len(afh) >= 2 else 0.5

        league_avg_y = _rolling_mean(league_yellows[league], LEAGUE_WINDOW, DEFAULT_TOTAL_Y)

        if referee and referee in ref_stats:
            rs = ref_stats[referee]
            ref_avg_y   = rs["total_yellows"] / rs["matches"]
            ref_avg_f   = rs["total_fouls"]   / rs["matches"] if rs["total_fouls"] > 0 else DEFAULT_FOULS * 2
            home_y_rate = rs["home_yellows"]   / rs["matches"]
            away_y_rate = rs["away_yellows"]   / rs["matches"]
            ref_home_bias  = home_y_rate - away_y_rate
            ref_experience = rs["matches"]
        else:
            ref_avg_y      = DEFAULT_TOTAL_Y
            ref_avg_f      = DEFAULT_FOULS * 2
            ref_home_bias  = 0.0
            ref_experience = 0

        home_sm  = team_season_matches.get((home, season), 0)
        away_sm  = team_season_matches.get((away, season), 0)
        is_early = 1 if min(home_sm, away_sm) < 5 else 0

        rows.append({
            "match_date": date,
            "season":     season,
            "league":     league,
            "home_team":  home,
            "away_team":  away,
            "home_yellows_avg":          home_y_avg,
            "away_yellows_avg":          away_y_avg,
            "home_yellows_conceded_avg": home_yc_avg,
            "away_yellows_conceded_avg": away_yc_avg,
            "home_fouls_avg":            home_f_avg,
            "away_fouls_avg":            away_f_avg,
            "home_aggression":           home_agg_avg,
            "away_aggression":           away_agg_avg,
            "referee_avg_yellows":       ref_avg_y,
            "referee_avg_fouls":         ref_avg_f,
            "referee_home_bias":         ref_home_bias,
            "referee_experience":        ref_experience,
            "league_avg_yellows":        league_avg_y,
            "elo_diff":                  abs(home_elo - away_elo),
            "league_encoded":            league_enc[league],
            "is_derby":                  0,
            "home_form":                 home_form,
            "away_form":                 away_form,
            "is_early_season":           is_early,
            "home_yellows":              hy,
            "away_yellows":              ay,
            "total_yellows":             (hy + ay) if has_yellows else None,
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

        if has_yellows:
            home_y_won[home].append(hy)
            away_y_won[away].append(ay)
            home_y_conc[home].append(ay)   # yellows conceded by home = away team's yellows
            away_y_conc[away].append(hy)
            league_yellows[league].append(hy + ay)
            if referee:
                if referee not in ref_stats:
                    ref_stats[referee] = {
                        "matches": 0,
                        "total_yellows": 0.0,
                        "home_yellows": 0.0,
                        "away_yellows": 0.0,
                        "total_fouls": 0.0,
                    }
                ref_stats[referee]["matches"]       += 1
                ref_stats[referee]["total_yellows"] += hy + ay
                ref_stats[referee]["home_yellows"]  += hy
                ref_stats[referee]["away_yellows"]  += ay

        if hf is not None:
            home_fouls[home].append(hf)
            home_agg[home].append(hf + 2.0 * (hy if hy is not None else DEFAULT_HOME_Y))
            if referee and referee in ref_stats:
                ref_stats[referee]["total_fouls"] += hf
        if af is not None:
            away_fouls[away].append(af)
            away_agg[away].append(af + 2.0 * (ay if ay is not None else DEFAULT_AWAY_Y))
            if referee and referee in ref_stats:
                ref_stats[referee]["total_fouls"] += af

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

    print("Building cards features (single-pass causal loop)...")
    feat_df, league_encoder = build_cards_features(df)
    print(f"  Feature rows built: {len(feat_df):,}\n")

    # Restrict to rows with yellow card data from 2000 onwards
    model_df = feat_df.dropna(subset=["total_yellows"])
    model_df = model_df[model_df["match_date"] >= "2000-01-01"].reset_index(drop=True)
    print(f"Matches with yellow card data (2000+): {len(model_df):,}\n")

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
    y_train = train_df["total_yellows"].values.astype(float)
    X_ho    = holdout_df[FEATURE_COLS].values.astype(float)
    y_ho    = holdout_df["total_yellows"].values.astype(float)

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
    joblib.dump(model, os.path.join(models_dir, "cards_model.pkl"))
    joblib.dump(league_encoder, os.path.join(models_dir, "cards_league_encoder.pkl"))
    print(f"Saved cards_model.pkl and cards_league_encoder.pkl to models/\n")

    # Predictions on holdout
    preds = model.predict(X_ho)
    holdout_df["predicted_yellows"] = preds
    holdout_df["actual_yellows"]    = y_ho

    mae  = float(np.mean(np.abs(preds - y_ho)))
    rmse = float(np.sqrt(np.mean((preds - y_ho) ** 2)))

    # Naive baseline: league mean from training set
    league_means = train_df.groupby("league")["total_yellows"].mean().to_dict()
    global_mean  = float(y_train.mean())
    naive_preds  = holdout_df["league"].map(league_means).fillna(global_mean).values
    mae_naive    = float(np.mean(np.abs(naive_preds - y_ho)))
    rmse_naive   = float(np.sqrt(np.mean((naive_preds - y_ho) ** 2)))

    # Over/Under accuracy
    lines = [3.5, 4.5, 5.5]

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
        "predicted_yellows", "actual_yellows",
        "home_yellows", "away_yellows",
    ]
    out_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "cards_predictions.csv")
    )
    holdout_df[out_cols].to_csv(out_path, index=False)
    print(f"\nSaved holdout predictions ({len(holdout_df):,} rows) to {out_path}")


if __name__ == "__main__":
    main()
