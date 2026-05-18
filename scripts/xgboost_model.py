import os
from collections import defaultdict, deque

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

STARTING_RATING = 1500
K = 32
HOME_ADVANTAGE = 100
COLD_START = 200
FORM_WINDOW = 5

FEATURE_COLS = [
    "home_elo", "away_elo", "elo_diff", "home_expected",
    "home_form", "away_form",
    "home_goals_scored_avg", "home_goals_conceded_avg",
    "away_goals_scored_avg", "away_goals_conceded_avg",
    "form_diff", "league_encoded", "is_home_advantage",
]

RESULT_MAP = {"A": 0, "D": 1, "H": 2}
RESULT_INV = {0: "A", 1: "D", 2: "H"}


def mov_multiplier(goal_diff: int) -> float:
    return min(2.0, 1 + np.log(1 + abs(goal_diff)) / np.log(10))


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def _form_stats(history: deque) -> tuple[float, float, float]:
    """Returns (form, goals_scored_avg, goals_conceded_avg) from a team's recent history."""
    if not history:
        return 0.5, 1.5, 1.5
    pts, gs, gc = [], [], []
    for goals_scored, goals_conceded, outcome in history:
        gs.append(goals_scored)
        gc.append(goals_conceded)
        pts.append(3 if outcome == "W" else 1 if outcome == "D" else 0)
    return (sum(pts) / len(pts)) / 3, sum(gs) / len(gs), sum(gc) / len(gc)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    le = LabelEncoder()
    le.fit(df["league"])

    elo: dict[str, float] = defaultdict(lambda: float(STARTING_RATING))
    form: dict[str, deque] = defaultdict(lambda: deque(maxlen=FORM_WINDOW))

    records = []

    for row in df.itertuples(index=False):
        home, away = row.home_team, row.away_team

        home_r = elo[home]
        away_r = elo[away]
        home_exp = expected_score(home_r + HOME_ADVANTAGE, away_r)

        h_form, h_gs, h_gc = _form_stats(form[home])
        a_form, a_gs, a_gc = _form_stats(form[away])

        records.append({
            "match_date": row.match_date,
            "league": row.league,
            "home_team": home,
            "away_team": away,
            "home_elo": home_r,
            "away_elo": away_r,
            "elo_diff": home_r - away_r,
            "home_expected": home_exp,
            "home_form": h_form,
            "away_form": a_form,
            "home_goals_scored_avg": h_gs,
            "home_goals_conceded_avg": h_gc,
            "away_goals_scored_avg": a_gs,
            "away_goals_conceded_avg": a_gc,
            "form_diff": h_form - a_form,
            "league_encoded": int(le.transform([row.league])[0]),
            "is_home_advantage": 1,
            "result": row.result,
        })

        result = row.result
        if result == "H":
            home_score, away_score = 1.0, 0.0
        elif result == "D":
            home_score, away_score = 0.5, 0.5
        else:
            home_score, away_score = 0.0, 1.0

        goal_diff = int(row.home_goals) - int(row.away_goals)
        mov = mov_multiplier(goal_diff)
        away_exp = 1 - home_exp

        elo[home] = home_r + K * mov * (home_score - home_exp)
        elo[away] = away_r + K * mov * (away_score - away_exp)

        home_outcome = "W" if result == "H" else "D" if result == "D" else "L"
        away_outcome = "W" if result == "A" else "D" if result == "D" else "L"
        form[home].append((int(row.home_goals), int(row.away_goals), home_outcome))
        form[away].append((int(row.away_goals), int(row.home_goals), away_outcome))

    return pd.DataFrame(records)


def main() -> None:
    base = os.path.dirname(__file__)
    results_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "results.csv"))

    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])

    print(f"Loaded {len(df):,} matches across {df['league'].nunique()} leagues")

    feat_df = build_features(df)
    feat_df = feat_df.iloc[COLD_START:].reset_index(drop=True)

    feat_df["target"] = feat_df["result"].map(RESULT_MAP)

    n = len(feat_df)
    split = int(n * 0.70)
    train_df = feat_df.iloc[:split]
    test_df = feat_df.iloc[split:].copy()

    X_train = train_df[FEATURE_COLS].values
    y_train = train_df["target"].values
    X_test = test_df[FEATURE_COLS].values
    y_test = test_df["target"].values

    print(f"Train: {len(train_df):,} matches  |  Test: {len(test_df):,} matches")

    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
    )
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)  # columns: P(A), P(D), P(H) for classes 0, 1, 2
    pred_labels = model.predict(X_test)

    test_df["p_away"] = proba[:, 0]
    test_df["p_draw"] = proba[:, 1]
    test_df["p_home"] = proba[:, 2]
    test_df["predicted_result"] = [RESULT_INV[p] for p in pred_labels]
    test_df["actual_result"] = test_df["result"]
    test_df["correct"] = (test_df["predicted_result"] == test_df["actual_result"]).astype(int)

    hit_rate = test_df["correct"].mean()

    actual_home_score = test_df["actual_result"].map({"H": 1.0, "D": 0.5, "A": 0.0})
    brier = ((test_df["p_home"] - actual_home_score) ** 2).mean()

    # Elo-only baseline on the same test matches
    elo_pred = test_df["home_expected"].apply(lambda x: "H" if x > 0.5 else "A")
    elo_hit = (elo_pred == test_df["actual_result"]).mean()

    importances = pd.Series(model.feature_importances_, index=FEATURE_COLS)

    print("\n--- Top 10 Feature Importances ---")
    for feat, imp in importances.nlargest(10).items():
        print(f"  {feat:<32} {imp:.4f}")

    print("\n--- XGBoost Test Set Metrics ---")
    print(f"  Test matches : {len(test_df):,}")
    print(f"  Hit rate     : {hit_rate:.4f}  ({hit_rate * 100:.1f}%)")
    print(f"  Brier score  : {brier:.6f}")

    print("\n--- Elo-only on same test matches ---")
    print(f"  Elo hit rate : {elo_hit:.4f}  ({elo_hit * 100:.1f}%)")
    print(f"  XGB vs Elo   : {hit_rate - elo_hit:+.4f}")

    out_cols = [
        "match_date", "league", "home_team", "away_team",
        "p_home", "p_draw", "p_away",
        "predicted_result", "actual_result", "correct",
    ]
    out_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "xgb_predictions.csv"))
    test_df[out_cols].to_csv(out_path, index=False)
    print(f"\nSaved predictions to {out_path}")


if __name__ == "__main__":
    main()
