import os
import numpy as np
import pandas as pd

STARTING_RATING = 1500
K = 32
HOME_ADVANTAGE = 100


def mov_multiplier(goal_diff: int) -> float:
    return min(2.0, 1 + np.log(1 + abs(goal_diff)) / np.log(10))


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def run_elo(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ratings: dict[str, float] = {}
    predictions = []

    for _, row in df.iterrows():
        home = row["home_team"]
        away = row["away_team"]

        home_r = ratings.get(home, STARTING_RATING)
        away_r = ratings.get(away, STARTING_RATING)

        # Apply home advantage in expected score calculation only
        home_exp = expected_score(home_r + HOME_ADVANTAGE, away_r)
        away_exp = 1 - home_exp

        result = row["result"]
        if result == "H":
            home_score, away_score = 1.0, 0.0
        elif result == "D":
            home_score, away_score = 0.5, 0.5
        else:
            home_score, away_score = 0.0, 1.0

        goal_diff = int(row["home_goals"]) - int(row["away_goals"])
        mov = mov_multiplier(goal_diff)

        home_r_new = home_r + K * mov * (home_score - home_exp)
        away_r_new = away_r + K * mov * (away_score - away_exp)

        predicted = "H" if home_exp > 0.5 else "A"
        correct = None if result == "D" else int(predicted == result)

        predictions.append({
            "match_date": row["match_date"],
            "home_team": home,
            "away_team": away,
            "home_elo_before": round(home_r, 2),
            "away_elo_before": round(away_r, 2),
            "home_expected": round(home_exp, 4),
            "actual_result": result,
            "predicted_result": predicted,
            "correct": correct,
        })

        ratings[home] = home_r_new
        ratings[away] = away_r_new

    pred_df = pd.DataFrame(predictions)

    ratings_df = (
        pd.Series(ratings, name="elo_rating")
        .rename_axis("team")
        .reset_index()
        .sort_values("elo_rating", ascending=False)
        .reset_index(drop=True)
    )
    ratings_df["elo_rating"] = ratings_df["elo_rating"].round(2)

    return pred_df, ratings_df


def print_summary(pred_df: pd.DataFrame, ratings_df: pd.DataFrame) -> None:
    print("=== Final Elo Ratings ===")
    print(ratings_df.to_string(index=False))

    non_draw = pred_df[pred_df["correct"].notna()]
    hit_rate = non_draw["correct"].mean()
    print(f"\nOverall hit rate (non-draw matches): {hit_rate:.4f} ({hit_rate * 100:.1f}%)")

    actual_home_score = pred_df["actual_result"].map({"H": 1.0, "D": 0.5, "A": 0.0})
    brier = ((pred_df["home_expected"] - actual_home_score) ** 2).mean()
    print(f"Brier score: {brier:.6f}")


def main() -> None:
    base = os.path.dirname(__file__)
    results_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "results.csv"))

    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)

    required = {"home_team", "away_team", "home_goals", "away_goals", "result", "match_date"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.dropna(subset=list(required))

    print(f"Loaded {len(df)} matches across {df['season'].nunique()} seasons\n")

    pred_df, ratings_df = run_elo(df)

    print_summary(pred_df, ratings_df)

    out_dir = os.path.normpath(os.path.join(base, "..", "data", "processed"))
    pred_path = os.path.join(out_dir, "elo_predictions.csv")
    ratings_path = os.path.join(out_dir, "elo_ratings.csv")

    pred_df.to_csv(pred_path, index=False)
    ratings_df.to_csv(ratings_path, index=False)

    print(f"\nSaved predictions to {pred_path}")
    print(f"Saved ratings to {ratings_path}")


if __name__ == "__main__":
    main()
