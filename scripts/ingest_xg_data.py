import os
import time
import json
import requests
import pandas as pd
import numpy as np

# Understat exposes match xG data via a JSON endpoint (loaded via AJAX on the league page).
# Endpoint: GET https://understat.com/getLeagueData/{league}/{year}
# Available from 2014 (2014-15 season) onward.

LEAGUES = [
    ("EPL",        "EPL",        "La_liga"),   # (label, api_name, ref_slug)
    ("LaLiga",     "La liga",    "La_liga"),
    ("Bundesliga", "Bundesliga", "Bundesliga"),
    ("SerieA",     "Serie A",    "Serie_A"),
    ("Ligue1",     "Ligue 1",    "Ligue_1"),
]

YEARS = list(range(2014, 2025))  # 2014-15 through 2024-25

BASE_URL = "https://understat.com/getLeagueData/{league}/{year}"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def season_label(year: int) -> str:
    return f"{year}-{str(year + 1)[2:]}"


def fetch_season(session: requests.Session, league_label: str, api_name: str, ref_slug: str, year: int) -> list[dict] | None:
    url = BASE_URL.format(league=api_name, year=year)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://understat.com/league/{ref_slug}/{year}",
    }
    try:
        r = session.get(url, headers=headers, timeout=30)
        if r.status_code == 404:
            print(f"    Warning: {league_label} {season_label(year)} not found (404), skipping")
            return None
        r.raise_for_status()
        data = r.json()
        dates = data.get("dates", [])
        if not dates:
            print(f"    Warning: {league_label} {season_label(year)} returned 0 matches, skipping")
            return None
        return dates
    except requests.HTTPError as e:
        print(f"    Warning: {league_label} {season_label(year)} HTTP error ({e}), skipping")
        return None
    except Exception as e:
        print(f"    Warning: {league_label} {season_label(year)} failed ({e}), skipping")
        return None


def parse_matches(dates: list[dict], league_label: str, year: int) -> pd.DataFrame:
    rows = []
    season = season_label(year)
    for m in dates:
        if not m.get("isResult"):
            continue
        try:
            home_goals = int(m["goals"]["h"])
            away_goals = int(m["goals"]["a"])
            home_xg = float(m["xG"]["h"])
            away_xg = float(m["xG"]["a"])
        except (KeyError, ValueError, TypeError):
            continue

        if home_goals > away_goals:
            result = "H"
        elif home_goals < away_goals:
            result = "A"
        else:
            result = "D"

        rows.append({
            "match_date":  m["datetime"][:10],
            "league":      league_label,
            "season":      season,
            "home_team":   m["h"]["title"],
            "away_team":   m["a"]["title"],
            "home_goals":  home_goals,
            "away_goals":  away_goals,
            "home_xg":     round(home_xg, 4),
            "away_xg":     round(away_xg, 4),
            "xg_diff":     round(home_xg - away_xg, 4),
            "result":      result,
            "match_id":    m.get("id"),
        })
    return pd.DataFrame(rows)


def print_summary(df: pd.DataFrame) -> None:
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Total matches:  {len(df):,}")
    print(f"Date range:     {df['match_date'].min()}  →  {df['match_date'].max()}")

    print("\nAverage xG per team per match by league:")
    for league, group in df.groupby("league"):
        avg = ((group["home_xg"] + group["away_xg"]) / 2).mean()
        print(f"  {league:<12}  {avg:.3f}")

    # Encode result as numeric for correlation
    result_map = {"H": 1, "D": 0, "A": -1}
    df2 = df.copy()
    df2["result_num"] = df2["result"].map(result_map)
    corr = df2["xg_diff"].corr(df2["result_num"])
    print(f"\nCorrelation (xG diff vs result):  {corr:.4f}")


def main() -> None:
    session = requests.Session()
    # Establish a session cookie
    session.get("https://understat.com/", headers={"User-Agent": USER_AGENT}, timeout=15)

    frames = []

    for league_label, api_name, ref_slug in LEAGUES:
        print(f"\n{league_label}:")
        for year in YEARS:
            dates = fetch_season(session, league_label, api_name, ref_slug, year)
            if dates is not None:
                df = parse_matches(dates, league_label, year)
                print(f"    {season_label(year)}: {len(df)} matches")
                frames.append(df)
            time.sleep(1)

    if not frames:
        print("No data collected — exiting.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined.sort_values(["match_date", "league"], inplace=True)

    out_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "processed", "xg_data.csv")
    )
    combined.to_csv(out_path, index=False)
    print(f"\nSaved {len(combined):,} rows to {out_path}")

    print_summary(combined)


if __name__ == "__main__":
    main()
