"""
Goals prediction model — XGBoost regressor for total goals per match,
plus binary classifiers for Over 1.5 / 2.5 / 3.5 / 4.5 lines.

23 rolling/causal features:
  home_goals_scored_avg, away_goals_scored_avg,
  home_goals_conceded_avg, away_goals_conceded_avg,
  home_xg_avg, away_xg_avg,
  home_xg_conceded_avg, away_xg_conceded_avg,
  home_btts_rate, away_btts_rate,
  home_clean_sheet_rate, away_clean_sheet_rate,
  home_scoring_rate, away_scoring_rate,
  home_goals_trend, away_goals_trend,
  league_goals_avg, elo_diff, league_encoded,
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
from xgboost import XGBClassifier, XGBRegressor

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STARTING_ELO  = 1500.0
ELO_K         = 16
ELO_HA        = 50
FORM_WINDOW   = 5
EWM_ALPHA     = 0.4
GOALS_WINDOW  = 10   # rolling window for team goal averages
LEAGUE_WINDOW = 100  # rolling window for league average goals
TREND_WINDOW  = 8    # OLS slope window

# Global defaults used before enough data accumulates
DEFAULT_HOME_GF    = 1.50
DEFAULT_AWAY_GF    = 1.10
DEFAULT_HOME_GA    = 1.10
DEFAULT_AWAY_GA    = 1.50
DEFAULT_XG         = 1.30  # shots-on-target proxy
DEFAULT_TOTAL_G    = 2.60
DEFAULT_BTTS_RATE  = 0.47
DEFAULT_CS_RATE    = 0.28
DEFAULT_SCORE_RATE = 0.70
DEFAULT_REF_YELLOWS = 3.50

FEATURE_COLS = [
    "home_goals_scored_avg",
    "away_goals_scored_avg",
    "home_goals_conceded_avg",
    "away_goals_conceded_avg",
    "home_xg_avg",
    "away_xg_avg",
    "home_xg_conceded_avg",
    "away_xg_conceded_avg",
    "home_btts_rate",
    "away_btts_rate",
    "home_clean_sheet_rate",
    "away_clean_sheet_rate",
    "home_scoring_rate",
    "away_scoring_rate",
    "home_goals_trend",
    "away_goals_trend",
    "league_goals_avg",
    "elo_diff",
    "league_encoded",
    "home_form",
    "away_form",
    "is_early_season",
    "referee_avg_yellows",
]

LINES = [1.5, 2.5, 3.5, 4.5]


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

def build_goals_features(df: pd.DataFrame) -> tuple[pd.DataFrame, LabelEncoder]:
    league_encoder = LabelEncoder()
    league_encoder.fit(df["league"])
    league_enc = {lg: int(i) for i, lg in enumerate(league_encoder.classes_)}

    elo: dict[str, float] = defaultdict(lambda: STARTING_ELO)

    # Venue-split goals histories
    home_gf_h: dict[str, list] = defaultdict(list)  # goals scored by home team at home
    away_gf_a: dict[str, list] = defaultdict(list)  # goals scored by away team away
    home_ga_h: dict[str, list] = defaultdict(list)  # goals conceded by home team at home
    away_ga_a: dict[str, list] = defaultdict(list)  # goals conceded by away team away

    # Venue-split shots-on-target (xG proxy) histories
    home_xg_h:  dict[str, list] = defaultdict(list)  # home team shots-on-target at home
    away_xg_a:  dict[str, list] = defaultdict(list)  # away team shots-on-target away
    home_xgc_h: dict[str, list] = defaultdict(list)  # shots-on-target conceded by home at home
    away_xgc_a: dict[str, list] = defaultdict(list)  # shots-on-target conceded by away away

    # Venue-split binary event histories
    home_btts_h:   dict[str, list] = defaultdict(list)  # BTTS in home team's home matches
    away_btts_a:   dict[str, list] = defaultdict(list)  # BTTS in away team's away matches
    home_scored_h: dict[str, list] = defaultdict(list)  # did home team score at home
    away_scored_a: dict[str, list] = defaultdict(list)  # did away team score away
    home_cs_h:     dict[str, list] = defaultdict(list)  # clean sheet for home team at home
    away_cs_a:     dict[str, list] = defaultdict(list)  # clean sheet for away team away

    # All-match points history for EWM form
    form_hist: dict[str, list] = defaultdict(list)

    league_goals: dict[str, list] = defaultdict(list)

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

        hst_raw = row.get("home_shots_target")
        ast_raw = row.get("away_shots_target")
        hst = float(hst_raw) if pd.notna(hst_raw) else None
        ast = float(ast_raw) if pd.notna(ast_raw) else None

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
        home_gf_avg  = _rolling_mean(home_gf_h[home], GOALS_WINDOW, DEFAULT_HOME_GF)
        away_gf_avg  = _rolling_mean(away_gf_a[away], GOALS_WINDOW, DEFAULT_AWAY_GF)
        home_ga_avg  = _rolling_mean(home_ga_h[home], GOALS_WINDOW, DEFAULT_HOME_GA)
        away_ga_avg  = _rolling_mean(away_ga_a[away], GOALS_WINDOW, DEFAULT_AWAY_GA)

        home_xg_avg  = _rolling_mean(home_xg_h[home],  GOALS_WINDOW, DEFAULT_XG)
        away_xg_avg  = _rolling_mean(away_xg_a[away],  GOALS_WINDOW, DEFAULT_XG)
        home_xgc_avg = _rolling_mean(home_xgc_h[home], GOALS_WINDOW, DEFAULT_XG)
        away_xgc_avg = _rolling_mean(away_xgc_a[away], GOALS_WINDOW, DEFAULT_XG)

        home_btts_avg  = _rolling_mean(home_btts_h[home],   GOALS_WINDOW, DEFAULT_BTTS_RATE)
        away_btts_avg  = _rolling_mean(away_btts_a[away],   GOALS_WINDOW, DEFAULT_BTTS_RATE)
        home_cs_rate   = _rolling_mean(home_cs_h[home],     GOALS_WINDOW, DEFAULT_CS_RATE)
        away_cs_rate   = _rolling_mean(away_cs_a[away],     GOALS_WINDOW, DEFAULT_CS_RATE)
        home_sc_rate   = _rolling_mean(home_scored_h[home], GOALS_WINDOW, DEFAULT_SCORE_RATE)
        away_sc_rate   = _rolling_mean(away_scored_a[away], GOALS_WINDOW, DEFAULT_SCORE_RATE)

        home_trend = _ols_slope(home_gf_h[home][-TREND_WINDOW:])
        away_trend = _ols_slope(away_gf_a[away][-TREND_WINDOW:])

        hfh = form_hist[home]
        afh = form_hist[away]
        home_form = _ewm([h["pts"] for h in hfh[-FORM_WINDOW:]]) / 3.0 if len(hfh) >= 2 else 0.5
        away_form = _ewm([h["pts"] for h in afh[-FORM_WINDOW:]]) / 3.0 if len(afh) >= 2 else 0.5

        league_avg_g = _rolling_mean(league_goals[league], LEAGUE_WINDOW, DEFAULT_TOTAL_G)

        if referee and referee in ref_stats:
            rs = ref_stats[referee]
            ref_avg_y = rs["total_yellows"] / rs["matches"]
        else:
            ref_avg_y = DEFAULT_REF_YELLOWS

        home_sm  = team_season_matches.get((home, season), 0)
        away_sm  = team_season_matches.get((away, season), 0)
        is_early = 1 if min(home_sm, away_sm) < 5 else 0

        rows.append({
            "match_date":              date,
            "season":                  season,
            "league":                  league,
            "home_team":               home,
            "away_team":               away,
            "home_goals_scored_avg":   home_gf_avg,
            "away_goals_scored_avg":   away_gf_avg,
            "home_goals_conceded_avg": home_ga_avg,
            "away_goals_conceded_avg": away_ga_avg,
            "home_xg_avg":             home_xg_avg,
            "away_xg_avg":             away_xg_avg,
            "home_xg_conceded_avg":    home_xgc_avg,
            "away_xg_conceded_avg":    away_xgc_avg,
            "home_btts_rate":          home_btts_avg,
            "away_btts_rate":          away_btts_avg,
            "home_clean_sheet_rate":   home_cs_rate,
            "away_clean_sheet_rate":   away_cs_rate,
            "home_scoring_rate":       home_sc_rate,
            "away_scoring_rate":       away_sc_rate,
            "home_goals_trend":        home_trend,
            "away_goals_trend":        away_trend,
            "league_goals_avg":        league_avg_g,
            "elo_diff":                abs(home_elo - away_elo),
            "league_encoded":          league_enc[league],
            "home_form":               home_form,
            "away_form":               away_form,
            "is_early_season":         is_early,
            "referee_avg_yellows":     ref_avg_y,
            "home_goals":              hg,
            "away_goals":              ag,
            "total_goals":             hg + ag,
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

        home_gf_h[home].append(float(hg))
        away_gf_a[away].append(float(ag))
        home_ga_h[home].append(float(ag))
        away_ga_a[away].append(float(hg))

        if hst is not None:
            home_xg_h[home].append(hst)
            away_xgc_a[away].append(hst)   # home shots-on-target = xG conceded by away
        if ast is not None:
            away_xg_a[away].append(ast)
            home_xgc_h[home].append(ast)   # away shots-on-target = xG conceded by home

        home_btts_h[home].append(btts)
        away_btts_a[away].append(btts)
        home_scored_h[home].append(1 if hg > 0 else 0)
        away_scored_a[away].append(1 if ag > 0 else 0)
        home_cs_h[home].append(1 if ag == 0 else 0)
        away_cs_a[away].append(1 if hg == 0 else 0)

        league_goals[league].append(hg + ag)

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

    print("Building goals features (single-pass causal loop)...")
    feat_df, league_encoder = build_goals_features(df)
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
    y_train = train_df["total_goals"].values.astype(float)
    X_ho    = holdout_df[FEATURE_COLS].values.astype(float)
    y_ho    = holdout_df["total_goals"].values.astype(float)

    # --- Regression model ---
    print("Training XGBoost regressor (total goals)...")
    reg_model = XGBRegressor(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=3,
        objective="reg:squarederror",
        random_state=42,
    )
    reg_model.fit(X_train, y_train)
    print("Done.\n")

    # --- Over/Under classifiers ---
    clf_models: dict[float, XGBClassifier] = {}
    for line in LINES:
        y_bin_train = (train_df["total_goals"] > line).astype(int).values
        clf = XGBClassifier(
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
        clf.fit(X_train, y_bin_train)
        clf_models[line] = clf
        print(f"Trained Over {line} classifier.")

    print()

    # Save models and encoder
    models_dir = os.path.normpath(os.path.join(base, "..", "models"))
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(reg_model,          os.path.join(models_dir, "goals_model.pkl"))
    joblib.dump(clf_models[2.5],    os.path.join(models_dir, "goals_over25_model.pkl"))
    joblib.dump(league_encoder,     os.path.join(models_dir, "goals_league_encoder.pkl"))
    print("Saved goals_model.pkl, goals_over25_model.pkl, goals_league_encoder.pkl to models/\n")

    # --- Regression evaluation ---
    reg_preds = reg_model.predict(X_ho)
    holdout_df["predicted_goals"] = reg_preds
    holdout_df["actual_goals"]    = y_ho

    mae  = float(np.mean(np.abs(reg_preds - y_ho)))
    rmse = float(np.sqrt(np.mean((reg_preds - y_ho) ** 2)))

    # Naive baseline: league mean from training set
    league_means = train_df.groupby("league")["total_goals"].mean().to_dict()
    global_mean  = float(y_train.mean())
    naive_reg    = holdout_df["league"].map(league_means).fillna(global_mean).values
    mae_naive    = float(np.mean(np.abs(naive_reg - y_ho)))
    rmse_naive   = float(np.sqrt(np.mean((naive_reg - y_ho) ** 2)))

    print("=" * 65)
    print(f"HOLDOUT EVALUATION  ({len(holdout_df):,} matches, "
          f"{holdout_df['match_date'].min().date()} → "
          f"{holdout_df['match_date'].max().date()})")
    print("=" * 65)
    print(f"\n  REGRESSION (total goals)")
    print(f"  {'Metric':<32}  {'Model':>8}  {'Naive':>8}")
    print(f"  {'-' * 52}")
    print(f"  {'MAE':<32}  {mae:>8.4f}  {mae_naive:>8.4f}")
    print(f"  {'RMSE':<32}  {rmse:>8.4f}  {rmse_naive:>8.4f}")

    # --- Over/Under classifier evaluation ---
    print(f"\n  OVER/UNDER CLASSIFIERS")
    print(f"  {'Metric':<32}  {'Model':>8}  {'Naive':>8}")
    print(f"  {'-' * 52}")

    league_btts_rates = train_df.groupby("league")["total_goals"].apply(
        lambda x: (x > 2.5).mean()
    ).to_dict()

    over25_probs = None

    for line in LINES:
        y_bin_ho    = (y_ho > line).astype(int)
        clf         = clf_models[line]
        probs       = clf.predict_proba(X_ho)[:, 1]
        preds_class = (probs > 0.5).astype(int)
        acc         = float((preds_class == y_bin_ho).mean())
        auc         = float(roc_auc_score(y_bin_ho, probs))

        # Naive: reg model threshold
        naive_class = (naive_reg > line).astype(int)
        acc_naive   = float((naive_class == y_bin_ho).mean())
        pct_over    = float(y_bin_ho.mean())

        label = f"Over {line}  ({pct_over:.1%} base rate)"
        print(f"  {f'Acc {label}':<32}  {acc:>8.4f}  {acc_naive:>8.4f}")
        print(f"  {f'AUC {label}':<32}  {auc:>8.6f}  {'—':>8}")

        holdout_df[f"over{str(line).replace('.','')}_prob"] = probs

        if line == 2.5:
            over25_probs = probs

    print("=" * 65)

    # --- Over 2.5 calibration ---
    print("\nCALIBRATION — Over 2.5 classifier (actual Over 2.5 rate by threshold)")
    print(f"  {'Threshold':<18}  {'Actual Over%':>14}  {'N Matches':>10}")
    print(f"  {'-' * 46}")
    y_bin_25 = (y_ho > 2.5).astype(int)
    for thresh in [0.55, 0.60, 0.65, 0.70, 0.75]:
        mask = over25_probs > thresh
        if mask.sum() > 0:
            actual_rate = float(y_bin_25[mask].mean())
            n_matches   = int(mask.sum())
            print(f"  {f'Predicted > {thresh:.0%}':<18}  {actual_rate:>14.1%}  {n_matches:>10,}")
        else:
            print(f"  {f'Predicted > {thresh:.0%}':<18}  {'n/a':>14}  {'0':>10}")

    # --- Feature importance (regression model) ---
    print("\nFEATURE IMPORTANCE — regression model (XGBoost gain, descending)")
    importance = reg_model.feature_importances_
    for feat, imp in sorted(zip(FEATURE_COLS, importance), key=lambda x: -x[1]):
        bar = "█" * max(1, int(imp * 300))
        print(f"  {feat:<35}  {imp:.4f}  {bar}")

    # Save holdout predictions
    out_cols = [
        "match_date", "home_team", "away_team", "league",
        "predicted_goals", "actual_goals", "home_goals", "away_goals",
        "over15_prob", "over25_prob", "over35_prob", "over45_prob",
    ]
    out_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "goals_predictions.csv")
    )
    holdout_df[out_cols].to_csv(out_path, index=False)
    print(f"\nSaved holdout predictions ({len(holdout_df):,} rows) to {out_path}")


if __name__ == "__main__":
    main()
