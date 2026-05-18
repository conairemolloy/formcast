import os
import io
import requests
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SEASONS = [
    ("2020-21", "2021"),
    ("2021-22", "2122"),
    ("2022-23", "2223"),
    ("2023-24", "2324"),
    ("2024-25", "2425"),
]

BASE_URL = "https://www.football-data.co.uk/mmz4281/{code}/E0.csv"

COLUMN_MAP = {
    "Date": "match_date",
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "FTHG": "home_goals",
    "FTAG": "away_goals",
    "FTR": "result",
    "B365H": "home_odds",
    "B365D": "draw_odds",
    "B365A": "away_odds",
}


def download_season(season_label: str, code: str) -> pd.DataFrame:
    url = BASE_URL.format(code=code)
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    raw = pd.read_csv(io.StringIO(response.text), low_memory=False)

    present = {src: dst for src, dst in COLUMN_MAP.items() if src in raw.columns}
    missing = [src for src in COLUMN_MAP if src not in raw.columns]
    if missing:
        print(f"  Warning: missing columns for {season_label}: {missing}")

    df = raw[list(present.keys())].rename(columns=present)

    if "match_date" in df.columns:
        df["match_date"] = pd.to_datetime(
            df["match_date"], dayfirst=True, format="mixed"
        ).dt.date

    df["season"] = season_label
    df["league"] = "EPL"

    df = df.dropna(subset=["home_team", "away_team"])

    print(f"  {season_label}: {len(df)} rows downloaded")
    return df


def upsert_to_supabase(df: pd.DataFrame, batch_size: int = 500) -> None:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    client = create_client(url, key)

    records = df.copy()
    records["match_date"] = records["match_date"].astype(str)

    rows = records.to_dict(orient="records")
    total = len(rows)

    for i in range(0, total, batch_size):
        batch = rows[i : i + batch_size]
        client.table("matches").upsert(batch).execute()
        uploaded = min(i + batch_size, total)
        print(f"  Uploaded {uploaded}/{total} rows")

    print(f"Upload complete: {total} rows upserted to 'matches'")


def main() -> None:
    frames = []

    print("Downloading seasons...")
    for season_label, code in SEASONS:
        df = download_season(season_label, code)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    print(f"\nTotal rows: {len(combined)}")

    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "results.csv")
    out_path = os.path.normpath(out_path)
    combined.to_csv(out_path, index=False)
    print(f"Saved to {out_path}")

    print("\nUploading to Supabase...")
    upsert_to_supabase(combined)


if __name__ == "__main__":
    main()
