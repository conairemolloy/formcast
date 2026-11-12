#!/usr/bin/env python3
"""
settle_predictions.py

Loads prediction_log.csv and results.csv. For each unsettled prediction
(no actual_result), looks up the final result and marks it settled.

Run AFTER backtest.py so results.csv is up to date.

Matching rules (a wrong settlement is worse than an unsettled one):
  * The logged team names are NEVER changed — each row's SHA256 hash covers
    them. Only actual_result / correct / settled_at are ever written.
  * Fixtures are found with fixture_matching.FixtureMatcher (strict name
    resolution + opponent-anchored fallback), shared with
    portfolio_analytics.py so both see the same fixture for every row.
  * Leagues results.csv doesn't cover are left unsettled.

Usage: python scripts/settle_predictions.py [--dry-run]
"""

import os
import sys
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from league_coverage import league_code as _league_code  # noqa: E402
from fixture_matching import FixtureMatcher  # noqa: E402

BASE_DIR    = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
LOG_CSV     = os.path.join(BASE_DIR, "data", "processed", "prediction_log.csv")
RESULTS_CSV = os.path.join(BASE_DIR, "data", "processed", "results.csv")

from log_schema import LOG_COLS  # noqa: E402  shared with publish_predictions.py

def main(dry_run: bool = False) -> dict:
    if not os.path.exists(LOG_CSV):
        print("No prediction_log.csv found — nothing to settle.")
        return {}

    log = pd.read_csv(LOG_CSV, dtype=str).fillna("")

    # Ensure settle columns exist for older logs that pre-date them
    for col in ("actual_result", "correct", "settled_at"):
        if col not in log.columns:
            log[col] = ""

    results = pd.read_csv(
        RESULTS_CSV,
        usecols=["match_date", "home_team", "away_team", "result", "league"],
        low_memory=False,
        dtype=str,
    ).dropna(subset=["match_date", "home_team", "away_team", "result"])
    for col in ("match_date", "home_team", "away_team", "result", "league"):
        results[col] = results[col].str.strip()

    latest_result = results["match_date"].max()
    matcher = FixtureMatcher(results)

    stats: Counter = Counter()
    unsettled_examples: dict[str, list[str]] = {}
    settled_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def note(reason: str, row) -> None:
        stats[reason] += 1
        ex = unsettled_examples.setdefault(reason, [])
        if len(ex) < 5:
            ex.append(f"{row['match_date']} [{row['league']}] {row['home_team']} v {row['away_team']}")

    for idx in log[log["actual_result"] == ""].index:
        row = log.loc[idx]
        match_date = row["match_date"].strip()

        lg = _league_code(row["league"])
        if lg is None:
            note("uncovered_league", row)
            continue
        if match_date > latest_result:
            note("not_played_yet", row)
            continue

        status, res_idx = matcher.match(match_date, lg, row["home_team"], row["away_team"])
        if res_idx is None:
            note(status, row)
            continue

        actual = results.at[res_idx, "result"]
        log.at[idx, "actual_result"] = actual
        log.at[idx, "correct"]       = "1" if row["predicted_outcome"] == actual else "0"
        log.at[idx, "settled_at"]    = settled_at
        stats[f"settled_{status}"] += 1

    settled = stats["settled_exact"] + stats["settled_anchored"]
    print(f"Settled {settled} predictions "
          f"({stats['settled_exact']} exact, {stats['settled_anchored']} by date+league+opponent)")
    for reason in ("not_played_yet", "uncovered_league", "no_result_found",
                   "both_teams_unresolved", "ambiguous"):
        if stats[reason]:
            print(f"  left unsettled — {reason}: {stats[reason]}")
            for ex in unsettled_examples.get(reason, []):
                print(f"      e.g. {ex}")

    if dry_run:
        print("Dry run — prediction_log.csv not written.")
        return dict(stats)

    for col in LOG_COLS:
        if col not in log.columns:
            log[col] = ""

    log[LOG_COLS].to_csv(LOG_CSV, index=False)
    print(f"Wrote {LOG_CSV}")
    return dict(stats)


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
