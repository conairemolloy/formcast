import os
import time
import requests
import pandas as pd

API_BASE = "https://api.football-data.org/v4"
API_TOKEN = "3edbe9850f784e8a86328acaabfd9561"
SLEEP_BETWEEN_REQUESTS = 7  # stay under 10 req/min

COMPETITIONS = ["CL", "WC", "EC", "ELC", "DED", "PD", "FL1", "BL1"]

START_YEARS = list(range(2015, 2026))  # 2015 through 2025 inclusive

SESSION = requests.Session()
SESSION.headers.update({"X-Auth-Token": API_TOKEN})


def season_label(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def fetch_matches(competition: str, year: int) -> pd.DataFrame | None:
    url = f"{API_BASE}/competitions/{competition}/matches"
    params = {"season": year}

    for attempt in range(3):
        try:
            resp = SESSION.get(url, params=params, timeout=30)
            if resp.status_code == 404:
                return None
            if resp.status_code == 429:
                wait = 60
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break
        except requests.HTTPError as e:
            if attempt == 2:
                print(f"    HTTP error after 3 attempts: {e}")
                return None
            time.sleep(10)
    else:
        return None

    data = resp.json()
    matches = data.get("matches", [])
    if not matches:
        return None

    rows = []
    for m in matches:
        if m.get("status") != "FINISHED":
            continue
        score = m.get("score", {})
        ft = score.get("fullTime", {})
        home_goals = ft.get("home")
        away_goals = ft.get("away")
        if home_goals is None or away_goals is None:
            continue

        if home_goals > away_goals:
            result = "H"
        elif home_goals < away_goals:
            result = "A"
        else:
            result = "D"

        utc_date = m.get("utcDate", "")
        match_date = utc_date[:10] if utc_date else None

        rows.append({
            "match_date": match_date,
            "home_team": m.get("homeTeam", {}).get("name"),
            "away_team": m.get("awayTeam", {}).get("name"),
            "home_goals": int(home_goals),
            "away_goals": int(away_goals),
            "result": result,
            "season": season_label(year),
            "league": competition,
            "status": m.get("status"),
        })

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df["match_date"] = pd.to_datetime(df["match_date"]).dt.date
    return df


def main() -> None:
    frames = []
    competition_counts = {}

    for competition in COMPETITIONS:
        print(f"\n{competition}:")
        comp_frames = []

        for year in START_YEARS:
            print(f"  {year}...", end=" ", flush=True)
            df = fetch_matches(competition, year)
            time.sleep(SLEEP_BETWEEN_REQUESTS)

            if df is None:
                print("skipped")
                continue

            print(f"{len(df)} matches")
            comp_frames.append(df)

        competition_counts[competition] = sum(len(f) for f in comp_frames)
        frames.extend(comp_frames)

    if not frames:
        print("No data fetched.")
        return

    combined = pd.concat(frames, ignore_index=True)

    print("\n--- Rows per competition ---")
    for code, count in competition_counts.items():
        print(f"  {code:<6} {count:>7,}")
    print(f"  {'TOTAL':<6} {len(combined):>7,}")

    out_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "processed", "football_data_org.csv")
    )
    combined.to_csv(out_path, index=False)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
