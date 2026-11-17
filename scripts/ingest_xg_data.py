import os
import re
import sys
import time
from collections import Counter
from datetime import date

import requests
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest_guard import Problems, check_fresh, fail  # noqa: E402
from season_utils import season_start_year, in_active_season  # noqa: E402

# Understat exposes match xG data via a JSON endpoint (loaded via AJAX on the league page).
# Endpoint: GET https://understat.com/getLeagueData/{league}/{year}
# Available from 2014 (2014-15 season) onward.

LEAGUES = [
    ("EPL",        "EPL",        "EPL"),       # (label, api_name, ref_slug)
    ("LaLiga",     "La liga",    "La_liga"),
    ("Bundesliga", "Bundesliga", "Bundesliga"),
    ("SerieA",     "Serie A",    "Serie_A"),
    ("Ligue1",     "Ligue 1",    "Ligue_1"),
]

FIRST_YEAR = 2014

# A dataset whose newest row is older than this during an active season fails CI.
STALE_DAYS = 14

BASE_URL = "https://understat.com/getLeagueData/{league}/{year}"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

OUT_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "processed", "xg_data.csv")
)


def season_years(today: date) -> list[int]:
    # Understat labels a season by its start year (2014 = 2014-15). Derive the
    # last year from today's date (July rollover, see season_utils) instead of
    # hard-coding it — a hard-coded end silently stopped fetching after 2024-25.
    return list(range(FIRST_YEAR, season_start_year(today) + 1))


def season_label(year: int) -> str:
    return f"{year}-{str(year + 1)[2:]}"


def _describe_non_json(r: requests.Response) -> str:
    """Short description of a non-JSON body (e.g. a maintenance page served as HTTP 200)."""
    body = r.text or ""
    m = re.search(r"<title>(.*?)</title>", body, re.I | re.S)
    text = " ".join(re.sub(r"<[^>]+>", " ", body).split())[:80]
    return (f"non-JSON response (HTTP {r.status_code}, {r.headers.get('Content-Type', '?')}, "
            f"title={(m.group(1).strip() if m else '')!r}, text={text!r})")


def fetch_season(session: requests.Session, league_label: str, api_name: str,
                 ref_slug: str, year: int) -> tuple[list[dict] | None, str | None]:
    """Return (dates, None) on success or (None, reason) on failure."""
    url = BASE_URL.format(league=api_name, year=year)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://understat.com/league/{ref_slug}/{year}",
    }
    try:
        r = session.get(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        return None, f"request failed ({type(e).__name__}: {e})"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    try:
        data = r.json()
    except ValueError:
        # Understat's outage page is HTTP 200 text/html — status alone can't catch it.
        return None, _describe_non_json(r)
    if not isinstance(data, dict) or "dates" not in data:
        return None, f"unexpected JSON shape (keys: {list(data)[:5] if isinstance(data, dict) else type(data).__name__})"
    return data["dates"] or [], None


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

    print("\nNewest match / avg xG per team per match, by league:")
    for league, group in df.groupby("league"):
        avg = ((group["home_xg"] + group["away_xg"]) / 2).mean()
        print(f"  {league:<12}  newest {group['match_date'].max()}  avg xG {avg:.3f}")

    # Encode result as numeric for correlation
    result_map = {"H": 1, "D": 0, "A": -1}
    df2 = df.copy()
    df2["result_num"] = df2["result"].map(result_map)
    corr = df2["xg_diff"].corr(df2["result_num"])
    print(f"\nCorrelation (xG diff vs result):  {corr:.4f}")


def _load_existing(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"match_id": str})


def main(today: date | None = None, out_path: str = OUT_PATH, sleep_s: float = 1.0) -> None:
    today = today or date.today()
    years = season_years(today)
    cur_year = years[-1]
    active = in_active_season(today)
    problems = Problems("xG ingest (Understat)")

    existing = _load_existing(out_path)
    existing_counts = (existing.groupby(["league", "season"]).size().to_dict()
                       if not existing.empty else {})
    existing_newest = existing["match_date"].max() if not existing.empty else None

    print(f"Fetching seasons {season_label(years[0])} .. {season_label(cur_year)} "
          f"(today {today}, active season: {active})")

    session = requests.Session()
    # Establish a session cookie. A failure here means every fetch below will
    # fail too; let them run so the error summary is complete.
    try:
        session.get("https://understat.com/", headers={"User-Agent": USER_AGENT}, timeout=15)
    except requests.RequestException as e:
        print(f"  Warning: Understat homepage unreachable ({type(e).__name__}: {e})")

    fetched: dict[tuple[str, str], pd.DataFrame] = {}
    failures: list[tuple[str, int, str]] = []

    for league_label, api_name, ref_slug in LEAGUES:
        print(f"\n{league_label}:")
        for year in years:
            dates, err = fetch_season(session, league_label, api_name, ref_slug, year)
            if err is None:
                df = parse_matches(dates, league_label, year)
                if df.empty:
                    err = "0 completed matches"
                else:
                    print(f"    {season_label(year)}: {len(df)} matches")
                    fetched[(league_label, season_label(year))] = df
            if err is not None:
                print(f"    Warning: {league_label} {season_label(year)} failed: {err}")
                failures.append((league_label, year, err))
            time.sleep(sleep_s)

    if not fetched:
        reasons = Counter(e for _, _, e in failures).most_common(2)
        fail(
            "xG ingest (Understat)",
            f"No xG data fetched for any of {len(failures)} league-seasons.\n"
            + "\n".join(f"  {n}x {r}" for r, n in reasons)
            + f"\n{out_path} left untouched (newest row: {existing_newest})."
        )

    # --- Classify per-season failures --------------------------------------
    for league_label, year, err in failures:
        season = season_label(year)
        kept = existing_counts.get((league_label, season), 0)
        if year == cur_year:
            if active:
                problems.add(f"{league_label} {season} (CURRENT season) fetched nothing "
                             f"mid-season: {err}")
            else:
                print(f"  note: {league_label} {season} empty — off-season, not an error")
        elif kept:
            print(f"  note: {league_label} {season} fetch failed — kept {kept} existing rows")
        else:
            problems.add(f"{league_label} {season}: fetch failed and no rows on file "
                         f"(history gap): {err}")

    # --- Merge: fetched seasons replace their rows; everything else is kept ---
    # A completed season that comes back smaller than what's on file is
    # suspicious (partial response) — keep the larger existing copy.
    for (league_label, season), df in list(fetched.items()):
        kept = existing_counts.get((league_label, season), 0)
        if season != season_label(cur_year) and len(df) < kept:
            print(f"  Warning: {league_label} {season} returned {len(df)} rows < {kept} on file "
                  f"— keeping existing rows")
            del fetched[(league_label, season)]

    frames = list(fetched.values())
    if not existing.empty:
        replaced = existing.set_index(["league", "season"]).index.isin(list(fetched))
        frames.insert(0, existing[~replaced])
    combined = pd.concat(frames, ignore_index=True)
    combined.sort_values(["match_date", "league"], inplace=True)

    tmp = out_path + ".tmp"
    combined.to_csv(tmp, index=False)
    os.replace(tmp, out_path)
    print(f"\nSaved {len(combined):,} rows to {out_path} "
          f"({len(fetched)} league-seasons refreshed, {len(failures)} failed)")

    print_summary(combined)

    newest = pd.to_datetime(combined["match_date"]).max().date()
    problems.add(check_fresh(newest, today, STALE_DAYS, active, "xg_data.csv"))
    problems.exit_if_any()


if __name__ == "__main__":
    main()
