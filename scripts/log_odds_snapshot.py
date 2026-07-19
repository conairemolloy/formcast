"""
log_odds_snapshot.py

Appends a timestamped snapshot of current bookmaker odds to
data/processed/odds_history.csv (one row per fixture × bookmaker).

Reuses _fetch_odds() from fetch_live_odds.py — no duplication of API logic.

Purpose: accumulate line-movement history so Tier 4 market-intelligence
features (opening vs closing line, steam moves, exchange divergence, etc.)
become buildable in a few months of data.

Run via both weekly and daily international workflows (continue-on-error).
"""

import csv
import os
import sys
from datetime import datetime, timezone

# Reuse fetch logic from fetch_live_odds.py without duplicating it
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_live_odds import SPORTS, LEAGUE_LABELS, _fetch_odds  # noqa: E402

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
OUT_PATH = os.path.join(BASE_DIR, "data", "processed", "odds_history.csv")

COLUMNS = [
    "snapshot_timestamp",
    "sport",
    "league",
    "home_team",
    "away_team",
    "commence_time",
    "bookmaker",
    "best_home_odds",
    "best_draw_odds",
    "best_away_odds",
]


def _best_odds_by_bookmaker(event: dict) -> list[dict]:
    """Return one dict per bookmaker with best home/draw/away odds for that book."""
    home_name = event.get("home_team", "")
    away_name = event.get("away_team", "")
    rows = []
    for bm in event.get("bookmakers", []):
        bm_key = bm.get("key", "unknown")
        h = d = a = None
        for market in bm.get("markets", []):
            if market.get("key") != "h2h":
                continue
            outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
            h = outcomes.get(home_name)
            d = outcomes.get("Draw")
            a = outcomes.get(away_name)
        if h or d or a:
            rows.append({
                "bookmaker":       bm_key,
                "best_home_odds":  h,
                "best_draw_odds":  d,
                "best_away_odds":  a,
            })
    return rows


def main() -> None:
    snapshot_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Ensure output file exists with header
    file_exists = os.path.exists(OUT_PATH)
    out_fh = open(OUT_PATH, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_fh, fieldnames=COLUMNS)
    if not file_exists:
        writer.writeheader()

    total_rows = 0

    for sport in SPORTS:
        league = LEAGUE_LABELS.get(sport, sport)
        print(f"Fetching {league}...")
        try:
            events = _fetch_odds(sport)
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            continue

        for event in events:
            home_raw    = event.get("home_team", "")
            away_raw    = event.get("away_team", "")
            commence    = event.get("commence_time", "")
            bm_rows     = _best_odds_by_bookmaker(event)

            for bm in bm_rows:
                writer.writerow({
                    "snapshot_timestamp": snapshot_ts,
                    "sport":              sport,
                    "league":             league,
                    "home_team":          home_raw,
                    "away_team":          away_raw,
                    "commence_time":      commence,
                    **bm,
                })
                total_rows += 1

    out_fh.close()
    print(f"Appended {total_rows} rows to {OUT_PATH}  [{snapshot_ts}]")


if __name__ == "__main__":
    main()
