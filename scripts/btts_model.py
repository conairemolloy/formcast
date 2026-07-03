"""
BTTS prediction model — XGBoost binary classifier for both-teams-to-score.

21 rolling/causal features:
  home_btts_rate, away_btts_rate,
  home_scoring_rate, away_scoring_rate,
  home_conceding_rate, away_conceding_rate,
  home_goals_scored_avg, away_goals_scored_avg,
  home_goals_conceded_avg, away_goals_conceded_avg,
  home_clean_sheet_rate, away_clean_sheet_rate,
  home_failed_to_score_rate, away_failed_to_score_rate,
  elo_diff, league_btts_rate, league_encoded,
  home_form, away_form, is_early_season, referee_avg_yellows
"""
import math
import os
from collections import defaultdict

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STARTING_ELO  = 1500.0
ELO_K         = 16
ELO_HA        = 50
FORM_WINDOW   = 5
EWM_ALPHA     = 0.4
BTTS_WINDOW   = 10   # rolling window for team BTTS/scoring/conceding rates
LEAGUE_WINDOW = 100  # rolling window for league BTTS rate

# Global defaults used before enough data accumulates
DEFAULT_BTTS_RATE      = 0.47
DEFAULT_SCORING_RATE   = 0.70
DEFAULT_CONCEDING_RATE = 0.70
DEFAULT_GOALS_SCORED   = 1.30
DEFAULT_GOALS_CONCEDED = 1.30
DEFAULT_REF_YELLOWS    = 3.50

FEATURE_COLS = [
    "home_btts_rate",
    "away_btts_rate",
    "home_scoring_rate",
    "away_scoring_rate",
    "home_conceding_rate",
    "away_conceding_rate",
    "home_goals_scored_avg",
    "away_goals_scored_avg",
    "home_goals_conceded_avg",
    "away_goals_conceded_avg",
    "home_clean_sheet_rate",
    "away_clean_sheet_rate",
    "home_failed_to_score_rate",
    "away_failed_to_score_rate",
    "elo_diff",
    "league_btts_rate",
    "league_encoded",
    "home_form",
    "away_form",
    "is_early_season",
    "referee_avg_yellows",
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

def build_btts_features(df: pd.DataFrame) -> tuple[pd.DataFrame, LabelEncoder]:
    league_encoder = LabelEncoder()
    league_encoder.fit(df["league"])
    league_enc = {lg: int(i) for i, lg in enumerate(league_encoder.classes_)}

    elo: dict[str, float] = defaultdict(lambda: STARTING_ELO)

    # Venue-split binary scoring/conceding histories (1 = yes, 0 = no)
    home_scored_h:   dict[str, list] = defaultdict(list)  # home team scored at home
    away_scored_a:   dict[str, list] = defaultdict(list)  # away team scored away
    home_conceded_h: dict[str, list] = defaultdict(list)  # home team conceded at home
    away_conceded_a: dict[str, list] = defaultdict(list)  # away team conceded away
    home_btts_h:     dict[str, list] = defaultdict(list)  # BTTS in home team's home matches
    away_btts_a:     dict[str, list] = defaultdict(list)  # BTTS in away team's away matches

    # Venue-split goals-per-match histories
    home_gf_h: dict[str, list] = defaultdict(list)  # goals for, home team at home
    away_gf_a: dict[str, list] = defaultdict(list)  # goals for, away team away
    home_ga_h: dict[str, list] = defaultdict(list)  # goals against, home team at home
    away_ga_a: dict[str, list] = defaultdict(list)  # goals against, away team away

    # All-match points history for EWM form
    form_hist: dict[str, list] = defaultdict(list)

    league_btts: dict[str, list] = defaultdict(list)

    # referee → {matches, total_yellows} for referee_avg_yellows feature
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

        ref_raw = row.get("referee")
        referee = ref_raw if (isinstance(ref_raw, str) and ref_raw.strip()) else None

        btts = 1 if (hg > 0 and ag > 0) else 0

        home_elo = elo[home]
        away_elo = elo[away]

        # --- Pre-match rolling features (prior data only) ---
        home_btts_avg  = _rolling_mean(home_btts_h[home],     BTTS_WINDOW, DEFAULT_BTTS_RATE)
        away_btts_avg  = _rolling_mean(away_btts_a[away],     BTTS_WINDOW, DEFAULT_BTTS_RATE)
        home_sc_rate   = _rolling_mean(home_scored_h[home],   BTTS_WINDOW, DEFAULT_SCORING_RATE)
        away_sc_rate   = _rolling_mean(away_scored_a[away],   BTTS_WINDOW, DEFAULT_SCORING_RATE)
        home_conc_rate = _rolling_mean(home_conceded_h[home], BTTS_WINDOW, DEFAULT_CONCEDING_RATE)
        away_conc_rate = _rolling_mean(away_conceded_a[away], BTTS_WINDOW, DEFAULT_CONCEDING_RATE)
        home_gf_avg    = _rolling_mean(home_gf_h[home],       BTTS_WINDOW, DEFAULT_GOALS_SCORED)
        away_gf_avg    = _rolling_mean(away_gf_a[away],       BTTS_WINDOW, DEFAULT_GOALS_SCORED)
        home_ga_avg    = _rolling_mean(home_ga_h[home],       BTTS_WINDOW, DEFAULT_GOALS_CONCEDED)
        away_ga_avg    = _rolling_mean(away_ga_a[away],       BTTS_WINDOW, DEFAULT_GOALS_CONCEDED)

        # Derived from scoring/conceding rates (no extra history needed)
        home_cs_rate  = 1.0 - home_conc_rate
        away_cs_rate  = 1.0 - away_conc_rate
        home_fts_rate = 1.0 - home_sc_rate
        away_fts_rate = 1.0 - away_sc_rate

        hfh = form_hist[home]
        afh = form_hist[away]
        home_form = _ewm([h["pts"] for h in hfh[-FORM_WINDOW:]]) / 3.0 if len(hfh) >= 2 else 0.5
        away_form = _ewm([h["pts"] for h in afh[-FORM_WINDOW:]]) / 3.0 if len(afh) >= 2 else 0.5

        league_btts_rate = _rolling_mean(league_btts[league], LEAGUE_WINDOW, DEFAULT_BTTS_RATE)

        if referee and referee in ref_stats:
            rs = ref_stats[referee]
            ref_avg_y = rs["total_yellows"] / rs["matches"]
        else:
            ref_avg_y = DEFAULT_REF_YELLOWS

        home_sm  = team_season_matches.get((home, season), 0)
        away_sm  = team_season_matches.get((away, season), 0)
        is_early = 1 if min(home_sm, away_sm) < 5 else 0

        rows.append({
            "match_date":               date,
            "season":                   season,
            "league":                   league,
            "home_team":                home,
            "away_team":                away,
            "home_btts_rate":           home_btts_avg,
            "away_btts_rate":           away_btts_avg,
            "home_scoring_rate":        home_sc_rate,
            "away_scoring_rate":        away_sc_rate,
            "home_conceding_rate":      home_conc_rate,
            "away_conceding_rate":      away_conc_rate,
            "home_goals_scored_avg":    home_gf_avg,
            "away_goals_scored_avg":    away_gf_avg,
            "home_goals_conceded_avg":  home_ga_avg,
            "away_goals_conceded_avg":  away_ga_avg,
            "home_clean_sheet_rate":    home_cs_rate,
            "away_clean_sheet_rate":    away_cs_rate,
            "home_failed_to_score_rate": home_fts_rate,
            "away_failed_to_score_rate": away_fts_rate,
            "elo_diff":                 abs(home_elo - away_elo),
            "league_btts_rate":         league_btts_rate,
            "league_encoded":           league_enc[league],
            "home_form":                home_form,
            "away_form":                away_form,
            "is_early_season":          is_early,
            "referee_avg_yellows":      ref_avg_y,
            "home_goals":               hg,
            "away_goals":               ag,
            "btts":                     btts,
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

        home_scored_h[home].append(1 if hg > 0 else 0)
        away_scored_a[away].append(1 if ag > 0 else 0)
        home_conceded_h[home].append(1 if ag > 0 else 0)
        away_conceded_a[away].append(1 if hg > 0 else 0)
        home_btts_h[home].append(btts)
        away_btts_a[away].append(btts)
        home_gf_h[home].append(float(hg))
        away_gf_a[away].append(float(ag))
        home_ga_h[home].append(float(ag))
        away_ga_a[away].append(float(hg))
        league_btts[league].append(btts)

        if has_yellows and referee:
            if referee not in ref_stats:
                ref_stats[referee] = {"matches": 0, "total_yellows": 0.0}
            ref_stats[referee]["matches"]       += 1
            ref_stats[referee]["total_yellows"] += hy + ay

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

    print("Building BTTS features (single-pass causal loop)...")
    feat_df, league_encoder = build_btts_features(df)
    print(f"  Feature rows built: {len(feat_df):,}\n")

    # Goals are always present; filter from 2000 onwards for data quality
    model_df = feat_df[feat_df["match_date"] >= "2000-01-01"].reset_index(drop=True)
    print(f"Matches from 2000+: {len(model_df):,}\n")

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
    y_train = train_df["btts"].values.astype(int)
    X_ho    = holdout_df[FEATURE_COLS].values.astype(float)
    y_ho    = holdout_df["btts"].values.astype(int)

    print("Training XGBoost classifier...")
    model = XGBClassifier(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=3,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train)
    print("Done.\n")

    # Save model and encoder
    models_dir = os.path.normpath(os.path.join(base, "..", "models"))
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(model, os.path.join(models_dir, "btts_model.pkl"))
    joblib.dump(league_encoder, os.path.join(models_dir, "btts_league_encoder.pkl"))
    print(f"Saved btts_model.pkl and btts_league_encoder.pkl to models/\n")

    # Predictions on holdout
    probs       = model.predict_proba(X_ho)[:, 1]
    preds_class = (probs > 0.5).astype(int)

    acc   = float((preds_class == y_ho).mean())
    brier = float(np.mean((probs - y_ho) ** 2))
    auc   = float(roc_auc_score(y_ho, probs))

    holdout_df["btts_prob"]   = probs
    holdout_df["btts_actual"] = y_ho

    # Naive baseline: league BTTS rate from training set
    league_btts_rates = train_df.groupby("league")["btts"].mean().to_dict()
    global_btts_rate  = float(y_train.mean())
    naive_probs       = holdout_df["league"].map(league_btts_rates).fillna(global_btts_rate).values
    naive_class       = (naive_probs > 0.5).astype(int)

    acc_naive   = float((naive_class == y_ho).mean())
    brier_naive = float(np.mean((naive_probs - y_ho) ** 2))
    auc_naive   = float(roc_auc_score(y_ho, naive_probs))

    base_rate = float(y_ho.mean())

    print("=" * 65)
    print(f"HOLDOUT EVALUATION  ({len(holdout_df):,} matches, "
          f"{holdout_df['match_date'].min().date()} → "
          f"{holdout_df['match_date'].max().date()})")
    print(f"  Base BTTS rate: {base_rate:.1%}")
    print("=" * 65)
    print(f"  {'Metric':<32}  {'Model':>8}  {'Naive':>8}")
    print(f"  {'-' * 52}")
    print(f"  {'Accuracy':<32}  {acc:>8.4f}  {acc_naive:>8.4f}")
    print(f"  {'Brier Score (lower=better)':<32}  {brier:>8.4f}  {brier_naive:>8.4f}")
    print(f"  {'ROC-AUC':<32}  {auc:>8.4f}  {auc_naive:>8.4f}")
    print("=" * 65)

    # Calibration
    print("\nCALIBRATION (actual BTTS rate by predicted probability threshold)")
    print(f"  {'Threshold':<18}  {'Actual BTTS%':>14}  {'N Matches':>10}")
    print(f"  {'-' * 46}")
    for thresh in [0.60, 0.70, 0.80]:
        mask = probs > thresh
        if mask.sum() > 0:
            actual_rate = float(y_ho[mask].mean())
            n_matches   = int(mask.sum())
            print(f"  {f'Predicted > {thresh:.0%}':<18}  {actual_rate:>14.1%}  {n_matches:>10,}")
        else:
            print(f"  {f'Predicted > {thresh:.0%}':<18}  {'n/a':>14}  {'0':>10}")

    # Feature importance
    print("\nFEATURE IMPORTANCE (XGBoost gain, descending)")
    importance = model.feature_importances_
    for feat, imp in sorted(zip(FEATURE_COLS, importance), key=lambda x: -x[1]):
        bar = "█" * max(1, int(imp * 300))
        print(f"  {feat:<35}  {imp:.4f}  {bar}")

    # Save holdout predictions
    out_cols = [
        "match_date", "home_team", "away_team", "league",
        "btts_prob", "btts_actual", "home_goals", "away_goals",
    ]
    out_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "btts_predictions.csv")
    )
    holdout_df[out_cols].to_csv(out_path, index=False)
    print(f"\nSaved holdout predictions ({len(holdout_df):,} rows) to {out_path}")


if __name__ == "__main__":
    main()
