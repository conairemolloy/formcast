import math
import os

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
RESULTS_PATH = os.path.join(DATA_DIR, "results.csv")
ORG_PATH = os.path.join(DATA_DIR, "football_data_org.csv")

# Only bring in competitions not already covered by football-data.co.uk
KEEP_LEAGUES = {"CL", "EC", "DED"}

DEDUP_KEY = ["match_date", "home_team", "away_team", "league"]

# Columns that exist in results.csv but not in football_data_org.csv
NULL_COLUMNS = [
    "home_odds", "draw_odds", "away_odds",
    "home_shots", "away_shots", "home_shots_target", "away_shots_target",
    "home_corners", "away_corners",
    "home_yellows", "away_yellows",
    "home_reds", "away_reds",
    "home_fouls", "away_fouls",
]

RESULTS_COLUMN_ORDER = [
    "match_date", "home_team", "away_team", "home_goals", "away_goals",
    "result", "season", "league",
    "home_shots", "away_shots", "home_shots_target", "away_shots_target",
    "home_corners", "away_corners",
    "home_yellows", "away_yellows",
    "home_reds", "away_reds",
    "home_fouls", "away_fouls",
    "home_odds", "draw_odds", "away_odds",
]


def load_org() -> pd.DataFrame:
    df = pd.read_csv(ORG_PATH)
    df = df[df["league"].isin(KEEP_LEAGUES)].copy()
    for col in NULL_COLUMNS:
        df[col] = None
    df = df.drop(columns=["status"], errors="ignore")
    df["match_date"] = pd.to_datetime(df["match_date"]).dt.date
    return df[RESULTS_COLUMN_ORDER]


def load_results() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_PATH, low_memory=False)
    df["match_date"] = pd.to_datetime(df["match_date"]).dt.date
    return df


def upsert_to_supabase(df: pd.DataFrame, batch_size: int = 500) -> None:
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    records = df.copy()
    records["match_date"] = records["match_date"].astype(str)

    rows = []
    for record in records.to_dict(orient="records"):
        clean = {}
        for k, v in record.items():
            if isinstance(v, float) and math.isnan(v):
                clean[k] = None
            elif hasattr(v, "item"):
                clean[k] = v.item()
            else:
                clean[k] = v
        rows.append(clean)

    total = len(rows)
    for i in range(0, total, batch_size):
        batch = rows[i : i + batch_size]
        client.table("matches").upsert(batch).execute()
        print(f"  Uploaded {min(i + batch_size, total)}/{total} rows")

    print(f"  Upsert complete: {total} rows")


def main() -> None:
    print("Loading results.csv...")
    existing = load_results()
    print(f"  {len(existing):,} existing rows")

    print("\nLoading football_data_org.csv...")
    org = load_org()
    print(f"  {len(org):,} rows after filtering to {sorted(KEEP_LEAGUES)}")

    # Build a set of existing keys for fast lookup
    existing_keys = set(
        zip(
            existing["match_date"].astype(str),
            existing["home_team"],
            existing["away_team"],
            existing["league"],
        )
    )

    org_keyed = org.copy()
    org_keyed["_key"] = list(
        zip(
            org_keyed["match_date"].astype(str),
            org_keyed["home_team"],
            org_keyed["away_team"],
            org_keyed["league"],
        )
    )
    new_rows = org_keyed[~org_keyed["_key"].isin(existing_keys)].drop(columns=["_key"])

    print(f"\n  {len(new_rows):,} new rows (not already in results.csv)")

    if new_rows.empty:
        print("Nothing to add.")
        return

    print("\n--- New rows per competition ---")
    for league, count in new_rows["league"].value_counts().sort_index().items():
        print(f"  {league:<6} {count:>6,}")

    combined = pd.concat([existing, new_rows[RESULTS_COLUMN_ORDER]], ignore_index=True)
    combined.to_csv(RESULTS_PATH, index=False)
    print(f"\nSaved {len(combined):,} total rows to results.csv")

    print("\nUpserting new rows to Supabase...")
    upsert_to_supabase(new_rows[RESULTS_COLUMN_ORDER])


if __name__ == "__main__":
    main()
