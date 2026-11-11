#!/usr/bin/env python3
"""
settle_predictions.py

Loads prediction_log.csv and results.csv. For each unsettled prediction
(no actual_result), looks up the final result and marks it settled.

Run AFTER backtest.py so results.csv is up to date.

Matching rules (a wrong settlement is worse than an unsettled one):
  * The logged team names are NEVER changed — each row's SHA256 hash covers
    them. Names are resolved to results.csv canonical names only to build the
    lookup; only actual_result / correct / settled_at are ever written.
  * Names are resolved strictly (explicit map, exact, suffix strip, accent
    fold — no fuzzy substring guessing).
  * If one team doesn't resolve (e.g. "Manchester" / "Sheffield" from an old
    suffix-stripping bug), the fixture is found by date + league + the OTHER,
    exactly-resolved team, and the loose name must still plausibly be that
    team. Settles only if exactly one fixture fits; otherwise left unsettled.
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
from predict_upcoming import _fold, _resolve_team  # noqa: E402

BASE_DIR    = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
LOG_CSV     = os.path.join(BASE_DIR, "data", "processed", "prediction_log.csv")
RESULTS_CSV = os.path.join(BASE_DIR, "data", "processed", "results.csv")

LOG_COLS = [
    "match_date", "match_time", "league", "home_team", "away_team",
    "home_elo", "away_elo", "p_home", "p_draw", "p_away",
    "predicted_outcome", "published_at", "hash",
    "actual_result", "correct", "settled_at",
]

def _plausibly_same(loose_name: str, canonical: str) -> bool:
    """Loose check that an unresolved logged name could be this canonical team.
    Only used when the opponent is already pinned exactly, so it just needs to
    reject an obviously different club, not pick between candidates."""
    a, b = _fold(loose_name), _fold(canonical)
    if not a or not b:
        return False
    return a in b or b in a or a[:3] == b[:3]


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

    known_teams = set(results["home_team"]) | set(results["away_team"])
    latest_result = results["match_date"].max()

    # (date, league) → list of (home, away, result)
    by_day: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    for r in results.itertuples(index=False):
        by_day.setdefault((r.match_date, r.league), []).append((r.home_team, r.away_team, r.result))

    _strict_cache: dict[str, str | None] = {}

    def strict(name: str) -> str | None:
        if name not in _strict_cache:
            res = _resolve_team(name, known_teams, fuzzy=False)
            _strict_cache[name] = res if res in known_teams else None
        return _strict_cache[name]

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

        home = strict(row["home_team"].strip())
        away = strict(row["away_team"].strip())
        if home is None and away is None:
            note("both_teams_unresolved", row)
            continue

        candidates = [
            (h, a, res) for h, a, res in by_day.get((match_date, lg), [])
            if (h == home if home else _plausibly_same(row["home_team"], h))
            and (a == away if away else _plausibly_same(row["away_team"], a))
        ]
        if len(candidates) > 1:
            note("ambiguous", row)
            continue
        if not candidates:
            note("no_result_found", row)  # postponed, date mismatch, or wrong league
            continue

        actual = candidates[0][2]
        log.at[idx, "actual_result"] = actual
        log.at[idx, "correct"]       = "1" if row["predicted_outcome"] == actual else "0"
        log.at[idx, "settled_at"]    = settled_at
        stats["settled_exact" if home and away else "settled_anchored"] += 1

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
