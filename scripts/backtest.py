import os
import numpy as np
import pandas as pd

STARTING_RATING = 1500
K = 16  # Optimised via hyperparameter grid search (hyperparameter_search.py)
HOME_ADVANTAGE = 50  # Optimised via hyperparameter grid search (hyperparameter_search.py)
COLD_START = 50


def mov_multiplier(goal_diff: int) -> float:
    return min(2.0, 1 + np.log(1 + abs(goal_diff)) / np.log(10))


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def run_backtest(df: pd.DataFrame) -> pd.DataFrame:
    ratings: dict[str, float] = {}
    records = []

    for i, row in enumerate(df.itertuples(index=False)):
        home = row.home_team
        away = row.away_team

        home_r = ratings.get(home, STARTING_RATING)
        away_r = ratings.get(away, STARTING_RATING)

        home_exp = expected_score(home_r + HOME_ADVANTAGE, away_r)
        away_exp = 1 - home_exp

        result = row.result
        if result == "H":
            home_score, away_score, actual_home_score = 1.0, 0.0, 1.0
        elif result == "D":
            home_score, away_score, actual_home_score = 0.5, 0.5, 0.5
        else:
            home_score, away_score, actual_home_score = 0.0, 1.0, 0.0

        goal_diff = int(row.home_goals) - int(row.away_goals)
        mov = mov_multiplier(goal_diff)

        home_r_new = home_r + K * mov * (home_score - home_exp)
        away_r_new = away_r + K * mov * (away_score - away_exp)

        ratings[home] = home_r_new
        ratings[away] = away_r_new

        if i < COLD_START:
            continue

        predicted = "H" if home_exp > 0.5 else "A"
        correct = None if result == "D" else int(predicted == result)
        brier = (home_exp - actual_home_score) ** 2

        records.append({
            "match_date": row.match_date,
            "season": row.season,
            "league": row.league,
            "home_team": home,
            "away_team": away,
            "home_elo": round(home_r, 2),
            "away_elo": round(away_r, 2),
            "home_expected": round(home_exp, 4),
            "actual_result": result,
            "predicted_result": predicted,
            "correct": correct,
            "actual_home_score": actual_home_score,
            "brier_contribution": round(brier, 6),
        })

    return pd.DataFrame(records)


def print_report(pred: pd.DataFrame) -> None:
    non_draw = pred[pred["correct"].notna()]
    total = len(pred)
    overall_hit = non_draw["correct"].mean()
    overall_brier = pred["brier_contribution"].mean()

    # Favourite baseline: home team is favourite when home_expected > 0.5
    # which is always the predicted result, so baseline == hit rate on non-draws
    fav_won = non_draw["correct"].sum() / len(non_draw)

    print("=" * 55)
    print("BACKTEST ACCURACY REPORT")
    print("=" * 55)
    print(f"Total matches predicted : {total:,}")
    print(f"Non-draw matches        : {len(non_draw):,}")
    print(f"Overall hit rate        : {overall_hit:.4f}  ({overall_hit * 100:.1f}%)")
    print(f"Overall Brier score     : {overall_brier:.6f}")
    print(f"Favourite win rate      : {fav_won:.4f}  ({fav_won * 100:.1f}%)")

    print("\n--- Hit rate by league ---")
    for league, grp in non_draw.groupby("league"):
        hr = grp["correct"].mean()
        print(f"  {league:<12} {hr:.4f}  ({hr * 100:.1f}%)  n={len(grp):,}")

    print("\n--- Brier score by league ---")
    for league, grp in pred.groupby("league"):
        bs = grp["brier_contribution"].mean()
        print(f"  {league:<12} {bs:.6f}  n={len(grp):,}")

    print("\n--- Hit rate by season ---")
    for season, grp in non_draw.groupby("season"):
        hr = grp["correct"].mean()
        print(f"  {season}  {hr:.4f}  ({hr * 100:.1f}%)  n={len(grp):,}")

    print("=" * 55)


def main() -> None:
    base = os.path.dirname(__file__)
    results_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "results.csv"))

    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)

    required = {"home_team", "away_team", "home_goals", "away_goals", "result", "match_date", "season", "league"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])

    print(f"Loaded {len(df):,} matches across {df['league'].nunique()} leagues and {df['season'].nunique()} seasons")
    print(f"Skipping first {COLD_START} matches (cold start)\n")

    pred = run_backtest(df)

    print_report(pred)

    out_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "backtest_predictions.csv"))
    pred.to_csv(out_path, index=False)
    print(f"\nSaved prediction log to {out_path}")


if __name__ == "__main__":
    main()
