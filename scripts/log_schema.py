"""Shared schema for data/processed/prediction_log.csv.

Imported by publish_predictions.py (appends rows) and settle_predictions.py
(rewrites the file with settle columns filled), so both always agree on the
column set and order.

"source" (elo | ensemble) records which model produced p_home/p_draw/p_away.
It is a plain column, NOT part of the row hash, and is blank on rows logged
before it existed.
"""

import csv
import os

LOG_COLS = [
    "match_date", "match_time", "league", "home_team", "away_team",
    "home_elo", "away_elo", "p_home", "p_draw", "p_away",
    "predicted_outcome", "published_at", "hash",
    "actual_result", "correct", "settled_at",
    "source",
]


def migrate_log_header(path: str) -> int:
    """Idempotently bring an existing log up to LOG_COLS.

    Adds any missing columns (currently just "source") as "" on every row and
    rewrites the file with the full header. Every existing value is carried
    over as the exact string read from disk: nothing is parsed, rounded or
    re-hashed. Returns the number of columns added (0 = already current or no
    file)."""
    if not os.path.exists(path):
        return 0

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing = [c for c in LOG_COLS if c not in header]
        if not missing:
            return 0
        rows = list(reader)

    # Existing columns keep their order; any not in LOG_COLS are kept, after it.
    out_cols = LOG_COLS + [c for c in header if c not in LOG_COLS]
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_cols, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") or "" for c in out_cols})
    os.replace(tmp, path)
    return len(missing)
