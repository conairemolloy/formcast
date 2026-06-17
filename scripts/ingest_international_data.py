"""
Ingest international football results from the martj42/international_results
GitHub repository and save to data/processed/international_results.csv.

IMPORTANT CAVEAT — data freshness:
    This dataset is community-maintained on GitHub, updated "daily, a bit more
    frequently during major tournaments, if the maintainer can manage it" per the
    repo's own description. It is NOT a live API or scores feed. During a
    fast-moving tournament such as the World Cup, it may lag behind actual results
    by hours or days. Treat it as the authoritative source for PRE-TOURNAMENT
    historical Elo calculation only. Live scores and upcoming fixtures continue to
    come from football-data.org as implemented elsewhere in the pipeline.

Output files:
    data/processed/international_results.csv   — normalised match records
    data/processed/international_shootouts.csv — raw shootout records, untransformed

These files are intentionally SEPARATE from data/processed/results.csv (club
football). International and club football occupy different Elo rating spaces
(see Phase 21 of the roadmap) and must never be merged.
"""

import io
import os
from datetime import date

import pandas as pd
import requests

RESULTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
SHOOTOUTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv"

OUT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
RESULTS_OUT = os.path.join(OUT_DIR, "international_results.csv")
SHOOTOUTS_OUT = os.path.join(OUT_DIR, "international_shootouts.csv")


def fetch_csv(url: str, label: str) -> pd.DataFrame:
    print(f"Downloading {label}...")
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text), low_memory=False)
        print(f"  {len(df):,} rows fetched")
        return df
    except requests.HTTPError as e:
        raise SystemExit(f"HTTP error fetching {label}: {e}") from e
    except Exception as e:
        raise SystemExit(f"Failed to fetch {label}: {e}") from e


def derive_result(row: pd.Series) -> str:
    if row["home_score"] > row["away_score"]:
        return "H"
    if row["home_score"] < row["away_score"]:
        return "A"
    return "D"


def normalise_results(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["date"] = pd.to_datetime(df["date"], format="mixed").dt.date

    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce").fillna(0).astype(int)
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce").fillna(0).astype(int)

    df["result"] = df.apply(derive_result, axis=1)

    # Year string — international football has no club-style seasons
    df["season"] = df["date"].apply(lambda d: str(d.year))

    # neutral is already boolean in the source; coerce in case it arrives as string
    df["neutral"] = df["neutral"].astype(bool)

    df = df.dropna(subset=["home_team", "away_team", "date"])

    today = date.today()
    future_mask = df["date"] >= today
    n_dropped = int(future_mask.sum())
    df = df[~future_mask]
    if n_dropped:
        print(f"  Dropped {n_dropped} future/unplayed placeholder row(s) (date >= {today})")

    column_order = [
        "date", "home_team", "away_team", "home_score", "away_score",
        "result", "tournament", "city", "country", "neutral", "season",
    ]
    return df[column_order]


def print_summary(df: pd.DataFrame) -> None:
    most_recent = df["date"].max()
    today = date.today()
    lag_days = (today - most_recent).days

    print("\n--- International results summary (played matches only) ---")
    print(f"  Total matches:   {len(df):,}")
    print(f"  Date range:      {df['date'].min()}  →  {most_recent}  (future rows excluded)")
    print(f"  Unique teams:    {pd.concat([df['home_team'], df['away_team']]).nunique():,}")
    print(f"  Most recent match in dataset: {most_recent}")
    print(f"  Today's date:                 {today}")
    print(f"  Dataset lag:                  {lag_days} day(s)")
    if lag_days > 3:
        print(f"  *** WARNING: dataset is {lag_days} days behind — treat as pre-tournament baseline only ***")

    print("\n  Top 10 tournament types:")
    for tournament, count in df["tournament"].value_counts().head(10).items():
        print(f"    {tournament:<45} {count:>6,}")


def main() -> None:
    results_raw = fetch_csv(RESULTS_URL, "international results")
    shootouts_raw = fetch_csv(SHOOTOUTS_URL, "shootouts")

    print("\nNormalising results...")
    results = normalise_results(results_raw)

    print_summary(results)

    results.to_csv(RESULTS_OUT, index=False)
    print(f"\nSaved results to {RESULTS_OUT}")

    shootouts_raw.to_csv(SHOOTOUTS_OUT, index=False)
    print(f"Saved shootouts to {SHOOTOUTS_OUT}")


if __name__ == "__main__":
    main()
