#!/usr/bin/env python3
"""
publish_predictions.py

Fetches upcoming fixtures from our own API, which already resolves team
names and computes Elo-based probabilities, then appends new prediction
rows to data/processed/prediction_log.csv.

Run BEFORE elo_model.py so predictions are locked in with pre-retrain ratings.
"""

import csv
import hashlib
import os
import sys
from collections import Counter
from datetime import datetime, timezone

import pandas as pd
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from league_coverage import is_covered_league  # noqa: E402
from predict_upcoming import _resolve_team  # noqa: E402

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
LOG_CSV  = os.path.join(BASE_DIR, "data", "processed", "prediction_log.csv")
RESULTS_CSV = os.path.join(BASE_DIR, "data", "processed", "results.csv")

# ── API ───────────────────────────────────────────────────────────────────────
UPCOMING_URL = "https://web-production-eb371.up.railway.app/api/live/upcoming"

LOG_COLS = [
    "match_date", "match_time", "league", "home_team", "away_team",
    "home_elo", "away_elo", "p_home", "p_draw", "p_away",
    "predicted_outcome", "published_at", "hash",
    "actual_result", "correct", "settled_at",
]

def _load_known_teams() -> set[str]:
    """Canonical team names (results.csv) that logged names should resolve to."""
    if not os.path.exists(RESULTS_CSV):
        return set()
    df = pd.read_csv(RESULTS_CSV, usecols=["home_team", "away_team"], dtype=str)
    return set(df["home_team"].dropna()) | set(df["away_team"].dropna())


def _canonical(name: str, known_teams: set[str]) -> str:
    """Resolve an API team name to its results.csv name so the logged (and
    hashed) name is what settlement looks up. Strict: no fuzzy guessing,
    because whatever is written here is permanent. Unresolved names (e.g.
    leagues results.csv doesn't cover) are logged exactly as the API sent them."""
    name = (name or "").strip()
    resolved = _resolve_team(name, known_teams, fuzzy=False)
    return resolved if resolved in known_teams else name


def _make_hash(
    match_date: str, home_team: str, away_team: str,
    p_home: float, p_draw: float, p_away: float,
    predicted_outcome: str, published_at: str,
) -> str:
    raw = (
        f"{match_date}|{home_team}|{away_team}"
        f"|{p_home:.4f}|{p_draw:.4f}|{p_away:.4f}"
        f"|{predicted_outcome}|{published_at}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _fetch_upcoming() -> list[dict]:
    resp = httpx.get(UPCOMING_URL, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def _load_existing_keys(known_teams: set[str]) -> set[str]:
    """Keys of fixtures already logged — both as logged and as resolved, so a
    fixture logged under an old raw name ("Coventry City") isn't logged again
    under its canonical name ("Coventry")."""
    if not os.path.exists(LOG_CSV):
        return set()
    df = pd.read_csv(LOG_CSV, usecols=["match_date", "home_team", "away_team"], dtype=str).fillna("")
    keys: set[str] = set()
    for r in df.itertuples():
        keys.add(f"{r.match_date}|{r.home_team}|{r.away_team}")
        keys.add(f"{r.match_date}|{_canonical(r.home_team, known_teams)}|{_canonical(r.away_team, known_teams)}")
    return keys


def main() -> None:
    print("Loading existing prediction log...")
    known_teams = _load_known_teams()
    existing_keys = _load_existing_keys(known_teams)
    print(f"  {len(existing_keys)} existing fixture keys (logged + canonical names)")

    print(f"Fetching upcoming fixtures from {UPCOMING_URL}...")
    try:
        matches = _fetch_upcoming()
    except Exception as exc:
        print(f"  ERROR: API unavailable — {exc}")
        print("  Skipping prediction publish.")
        return
    print(f"  {len(matches)} fixtures returned")

    published_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_rows: list[dict] = []
    skipped_uncovered: Counter[str] = Counter()

    for m in matches:
        # Only log leagues results.csv covers — anything else can never settle
        # (and is predicted on default ratings), so it would sit as PENDING forever.
        if not is_covered_league(m.get("competition", "")):
            skipped_uncovered[m.get("competition", "") or "(blank)"] += 1
            continue

        # Canonical names are what get logged AND hashed, so settlement can
        # match them directly against results.csv.
        home_team  = _canonical(m.get("home_team", ""), known_teams)
        away_team  = _canonical(m.get("away_team", ""), known_teams)
        match_date = m.get("match_date", "")
        match_time = m.get("match_time", "")
        league     = m.get("competition", "")
        home_elo   = m.get("home_elo", "")
        away_elo   = m.get("away_elo", "")

        try:
            p_home = float(m.get("p_home", 0))
            p_draw = float(m.get("p_draw", 0))
            p_away = float(m.get("p_away", 0))
        except (TypeError, ValueError):
            print(f"  Skipping {home_team} vs {away_team}: invalid probabilities")
            continue

        if not match_date or not home_team or not away_team:
            continue

        key = f"{match_date}|{home_team}|{away_team}"
        if key in existing_keys:
            continue

        predicted_outcome = max({"H": p_home, "D": p_draw, "A": p_away}, key=lambda k: {"H": p_home, "D": p_draw, "A": p_away}[k])

        new_rows.append({
            "match_date":        match_date,
            "match_time":        match_time or "",
            "league":            league,
            "home_team":         home_team,
            "away_team":         away_team,
            "home_elo":          home_elo,
            "away_elo":          away_elo,
            "p_home":            round(p_home, 4),
            "p_draw":            round(p_draw, 4),
            "p_away":            round(p_away, 4),
            "predicted_outcome": predicted_outcome,
            "published_at":      published_at,
            "hash":              _make_hash(
                match_date, home_team, away_team,
                p_home, p_draw, p_away,
                predicted_outcome, published_at,
            ),
            "actual_result": "",
            "correct":       "",
            "settled_at":    "",
        })
        existing_keys.add(key)

    if skipped_uncovered:
        print(f"  Skipped {sum(skipped_uncovered.values())} fixtures in uncovered leagues (can't settle):")
        for lg, n in skipped_uncovered.most_common():
            print(f"    {lg}: {n}")

    if not new_rows:
        print("No new predictions to publish.")
        return

    write_header = not os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLS)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"Published {len(new_rows)} new predictions → {LOG_CSV}")


if __name__ == "__main__":
    main()
