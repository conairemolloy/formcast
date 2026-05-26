#!/usr/bin/env python3
"""
settle_predictions.py

Loads prediction_log.csv and results.csv. For each unsettled prediction
(no actual_result), looks up the final result and marks it settled.

Run AFTER backtest.py so results.csv is up to date.
"""

import os
from datetime import datetime, timezone

import pandas as pd

BASE_DIR    = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
LOG_CSV     = os.path.join(BASE_DIR, "data", "processed", "prediction_log.csv")
RESULTS_CSV = os.path.join(BASE_DIR, "data", "processed", "results.csv")

LOG_COLS = [
    "match_date", "match_time", "league", "home_team", "away_team",
    "home_elo", "away_elo", "p_home", "p_draw", "p_away",
    "predicted_outcome", "published_at", "hash",
    "actual_result", "correct", "settled_at",
]


def main() -> None:
    if not os.path.exists(LOG_CSV):
        print("No prediction_log.csv found — nothing to settle.")
        return

    log = pd.read_csv(LOG_CSV, dtype=str).fillna("")

    # Ensure settle columns exist for older logs that pre-date them
    for col in ("actual_result", "correct", "settled_at"):
        if col not in log.columns:
            log[col] = ""

    results = pd.read_csv(
        RESULTS_CSV,
        usecols=["match_date", "home_team", "away_team", "result"],
        low_memory=False,
        dtype=str,
    )

    results_index: dict[str, str] = {}
    for _, row in results.iterrows():
        key = f"{row['match_date'].strip()}|{row['home_team'].strip()}|{row['away_team'].strip()}"
        if pd.notna(row["result"]):
            results_index[key] = str(row["result"]).strip()

    unsettled_mask = log["actual_result"] == ""
    settled_count  = 0
    settled_at     = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for idx in log[unsettled_mask].index:
        row = log.loc[idx]
        key = f"{row['match_date'].strip()}|{row['home_team'].strip()}|{row['away_team'].strip()}"
        actual = results_index.get(key)
        if actual:
            log.at[idx, "actual_result"] = actual
            log.at[idx, "correct"]       = "1" if row["predicted_outcome"] == actual else "0"
            log.at[idx, "settled_at"]    = settled_at
            settled_count += 1

    for col in LOG_COLS:
        if col not in log.columns:
            log[col] = ""

    log[LOG_COLS].to_csv(LOG_CSV, index=False)
    print(f"Settled {settled_count} predictions → {LOG_CSV}")


if __name__ == "__main__":
    main()
