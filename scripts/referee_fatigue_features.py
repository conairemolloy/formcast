"""
Compute per-team disciplinary tendencies and fatigue features from results.csv.
Output: data/processed/team_tendencies.csv
"""

import os
from datetime import date

import numpy as np
import pandas as pd

TODAY = date.today()
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
RESULTS_PATH = os.path.join(DATA_DIR, "results.csv")
OUTPUT_PATH = os.path.join(DATA_DIR, "team_tendencies.csv")


def load_results() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_PATH, parse_dates=["match_date"], low_memory=False)
    disc_cols = ["home_yellows", "away_yellows", "home_reds", "away_reds", "home_fouls", "away_fouls"]
    df[disc_cols] = df[disc_cols].apply(pd.to_numeric, errors="coerce")
    return df


def build_team_match_view(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape results into one row per team per match."""
    home = df[["match_date", "home_team", "away_team", "league",
               "home_yellows", "home_reds", "home_fouls"]].copy()
    home.columns = ["match_date", "team", "opponent", "league", "yellows", "reds", "fouls"]
    home["venue"] = "home"

    away = df[["match_date", "away_team", "home_team", "league",
               "away_yellows", "away_reds", "away_fouls"]].copy()
    away.columns = ["match_date", "team", "opponent", "league", "yellows", "reds", "fouls"]
    away["venue"] = "away"

    return pd.concat([home, away], ignore_index=True)


def disciplinary_features(tm: pd.DataFrame) -> pd.DataFrame:
    # Only use rows that have disciplinary data
    disc = tm.dropna(subset=["yellows", "reds", "fouls"])

    # Career averages
    career = disc.groupby("team").agg(
        matches_played=("yellows", "count"),
        avg_yellows_per_game=("yellows", "mean"),
        avg_reds_per_game=("reds", "mean"),
        avg_fouls_per_game=("fouls", "mean"),
    )

    # Last-10 yellow trend vs career average
    def yellow_trend(g):
        if len(g) < 2:
            return 0.0
        career_avg = g["yellows"].mean()
        last10 = g.sort_values("match_date").tail(10)["yellows"].mean()
        if career_avg == 0:
            return 0.0
        return round((last10 - career_avg) / career_avg, 4)

    trends = disc.groupby("team").apply(yellow_trend, include_groups=False).rename("yellow_trend")

    # Home / away yellow averages
    home_avg = (
        disc[disc["venue"] == "home"]
        .groupby("team")["yellows"]
        .mean()
        .rename("home_yellow_avg")
    )
    away_avg = (
        disc[disc["venue"] == "away"]
        .groupby("team")["yellows"]
        .mean()
        .rename("away_yellow_avg")
    )

    combined = career.join(trends).join(home_avg).join(away_avg)
    combined["away_card_premium"] = combined["away_yellow_avg"] - combined["home_yellow_avg"]

    # Aggression index: normalise (fouls + 2*yellows + 5*reds) to 0-1
    raw = (
        combined["avg_fouls_per_game"]
        + 2 * combined["avg_yellows_per_game"]
        + 5 * combined["avg_reds_per_game"]
    )
    mn, mx = raw.min(), raw.max()
    combined["aggression_index"] = ((raw - mn) / (mx - mn)).round(4) if mx > mn else 0.0

    return combined.reset_index()


def fatigue_features(tm: pd.DataFrame) -> pd.DataFrame:
    today = pd.Timestamp(TODAY)

    def team_fatigue(g):
        g = g.dropna(subset=["match_date"]).sort_values("match_date")
        if g.empty:
            return pd.Series({
                "last_match_date": None,
                "days_since_last": None,
                "matches_last_21d": 0,
                "matches_last_7d": 0,
            })
        last = g["match_date"].iloc[-1]
        cutoff_21 = today - pd.Timedelta(days=21)
        cutoff_7 = today - pd.Timedelta(days=7)
        return pd.Series({
            "last_match_date": last.date().isoformat(),
            "days_since_last": (today - last).days,
            "matches_last_21d": int((g["match_date"] >= cutoff_21).sum()),
            "matches_last_7d": int((g["match_date"] >= cutoff_7).sum()),
        })

    return tm.groupby("team").apply(team_fatigue, include_groups=False).reset_index()


def league_per_team(tm: pd.DataFrame) -> pd.DataFrame:
    """Return the most recent league for each team."""
    return (
        tm.sort_values("match_date")
        .groupby("team")["league"]
        .last()
        .reset_index()
    )


def print_summaries(df: pd.DataFrame) -> None:
    print("\n=== Top 10 Most Aggressive Teams (aggression_index) ===")
    top_agg = df.nlargest(10, "aggression_index")[["team", "league", "aggression_index", "avg_fouls_per_game"]]
    print(top_agg.to_string(index=False))

    print("\n=== Top 10 Most Disciplined Teams (aggression_index) ===")
    top_disc = df.nsmallest(10, "aggression_index")[["team", "league", "aggression_index", "avg_fouls_per_game"]]
    print(top_disc.to_string(index=False))

    print("\n=== Teams with Most Fixture Congestion (matches_last_21d) ===")
    congested = df.nlargest(10, "matches_last_21d")[["team", "league", "matches_last_21d", "matches_last_7d", "days_since_last"]]
    print(congested.to_string(index=False))

    print("\n=== Average Rest Days by League ===")
    rest = (
        df.dropna(subset=["days_since_last"])
        .groupby("league")["days_since_last"]
        .mean()
        .round(1)
        .sort_values()
        .reset_index()
    )
    rest.columns = ["league", "avg_rest_days"]
    print(rest.to_string(index=False))


def main() -> None:
    print("Loading results...")
    df = load_results()
    print(f"  {len(df):,} matches loaded")

    tm = build_team_match_view(df)

    print("Computing disciplinary features...")
    disc = disciplinary_features(tm)

    print("Computing fatigue features...")
    fat = fatigue_features(tm)

    league_map = league_per_team(tm)

    result = (
        disc
        .merge(fat, on="team", how="outer")
        .merge(league_map, on="team", how="left")
    )

    # Final column order
    cols = [
        "team", "league", "matches_played",
        "avg_yellows_per_game", "avg_reds_per_game", "avg_fouls_per_game",
        "yellow_trend", "aggression_index",
        "home_yellow_avg", "away_yellow_avg", "away_card_premium",
        "last_match_date", "days_since_last", "matches_last_21d", "matches_last_7d",
    ]
    result = result[cols]

    # Round float columns
    float_cols = ["avg_yellows_per_game", "avg_reds_per_game", "avg_fouls_per_game",
                  "home_yellow_avg", "away_yellow_avg", "away_card_premium"]
    result[float_cols] = result[float_cols].round(3)

    print_summaries(result)

    result.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(result)} teams to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
