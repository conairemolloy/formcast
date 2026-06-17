"""
International football Elo rating model.

Completely separate from scripts/elo_model.py (club football) — different
rating space, different input, different output files. Never merge these spaces.

Input:  data/processed/international_results.csv
Output: data/processed/international_elo_ratings.csv

Key differences from the club model:
  - Variable K-factor by tournament importance (see k_factor())
  - Home advantage suppressed to zero when neutral == True (~90% of World Cup)
  - Tracks matches_played and last_match_date per team in ratings output
"""

import os

import numpy as np
import pandas as pd

STARTING_RATING = 1500
HOME_ADVANTAGE = 50  # Applied only when neutral == False; same constant as club model

# K-factors by tournament importance
K_DEFAULT = 20      # Friendlies and minor/regional cups
K_QUALIFIER = 25    # Any qualification round and UEFA Nations League
K_CONTINENTAL = 40  # Major continental championships (Euros, Copa América, AFCON, Asian Cup)
K_WORLD_CUP = 50    # FIFA World Cup proper — highest stakes

CONTINENTAL_TOURNAMENTS = frozenset({
    "UEFA Euro",
    "Copa América",
    "African Cup of Nations",
    "AFC Asian Cup",
})


def k_factor(tournament: str) -> int:
    t = tournament.strip()
    # Qualification check first — "FIFA World Cup qualification" → K_QUALIFIER, not K_WORLD_CUP
    if "qualification" in t.lower():
        return K_QUALIFIER
    if "FIFA World Cup" in t:
        return K_WORLD_CUP
    if t in CONTINENTAL_TOURNAMENTS:
        return K_CONTINENTAL
    if "UEFA Nations League" in t:
        return K_QUALIFIER
    return K_DEFAULT


def mov_multiplier(goal_diff: int) -> float:
    """Same formula as club elo_model.py — goal difference scales K multiplicatively."""
    return min(2.0, 1 + np.log(1 + abs(goal_diff)) / np.log(10))


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def run_elo(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, int]]:
    ratings: dict[str, float] = {}
    matches_played: dict[str, int] = {}
    last_match_date: dict[str, object] = {}
    k_tally: dict[int, int] = {}

    for _, row in df.iterrows():
        home = row["home_team"]
        away = row["away_team"]

        home_r = ratings.get(home, STARTING_RATING)
        away_r = ratings.get(away, STARTING_RATING)

        # Zero home advantage at neutral venues (majority of World Cup matches)
        ha = 0 if bool(row["neutral"]) else HOME_ADVANTAGE
        home_exp = expected_score(home_r + ha, away_r)
        away_exp = 1 - home_exp

        result = row["result"]
        if result == "H":
            home_score, away_score = 1.0, 0.0
        elif result == "D":
            home_score, away_score = 0.5, 0.5
        else:
            home_score, away_score = 0.0, 1.0

        goal_diff = int(row["home_score"]) - int(row["away_score"])
        mov = mov_multiplier(goal_diff)

        k = k_factor(str(row["tournament"]))
        k_tally[k] = k_tally.get(k, 0) + 1

        ratings[home] = home_r + k * mov * (home_score - home_exp)
        ratings[away] = away_r + k * mov * (away_score - away_exp)

        match_date = row["date"]
        matches_played[home] = matches_played.get(home, 0) + 1
        matches_played[away] = matches_played.get(away, 0) + 1
        last_match_date[home] = match_date
        last_match_date[away] = match_date

    teams = sorted(ratings.keys())
    ratings_df = (
        pd.DataFrame({
            "team": teams,
            "elo_rating": [round(ratings[t], 2) for t in teams],
            "matches_played": [matches_played[t] for t in teams],
            "last_match_date": [last_match_date[t] for t in teams],
        })
        .sort_values("elo_rating", ascending=False)
        .reset_index(drop=True)
    )

    return ratings_df, k_tally


def print_summary(ratings_df: pd.DataFrame, k_tally: dict[int, int]) -> None:
    print("=== Top 20 International Elo Ratings ===")
    print(ratings_df.head(20).to_string(index=False))

    total_teams = len(ratings_df)
    total_matches = sum(k_tally.values())

    print(f"\nTeams tracked: {total_teams:,}")
    print(f"\n--- K-factor distribution ({total_matches:,} total matches) ---")

    k_labels = {
        K_DEFAULT:     "K=20  Friendly / minor tournament",
        K_QUALIFIER:   "K=25  Qualification / Nations League",
        K_CONTINENTAL: "K=40  Continental championship (Euros / Copa / AFCON / Asian Cup)",
        K_WORLD_CUP:   "K=50  FIFA World Cup",
    }
    for k in sorted(k_tally.keys()):
        count = k_tally[k]
        label = k_labels.get(k, f"K={k}")
        pct = count / total_matches * 100
        print(f"  {label:<60} {count:>7,}  ({pct:.1f}%)")


def main() -> None:
    base = os.path.dirname(__file__)
    results_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "international_results.csv")
    )

    df = pd.read_csv(results_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    required = {"home_team", "away_team", "home_score", "away_score", "result", "date", "tournament", "neutral"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.dropna(subset=list(required))

    print(f"Loaded {len(df):,} international matches "
          f"({df['date'].min().date()}  →  {df['date'].max().date()})\n")

    ratings_df, k_tally = run_elo(df)

    print_summary(ratings_df, k_tally)

    out_dir = os.path.normpath(os.path.join(base, "..", "data", "processed"))
    ratings_path = os.path.join(out_dir, "international_elo_ratings.csv")

    ratings_df.to_csv(ratings_path, index=False)
    print(f"\nSaved ratings to {ratings_path}")


if __name__ == "__main__":
    main()
