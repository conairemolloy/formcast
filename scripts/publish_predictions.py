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
import re
from datetime import datetime, timezone

import pandas as pd
import httpx

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
LOG_CSV  = os.path.join(BASE_DIR, "data", "processed", "prediction_log.csv")

# ── API ───────────────────────────────────────────────────────────────────────
UPCOMING_URL = "https://web-production-eb371.up.railway.app/api/live/upcoming"

LOG_COLS = [
    "match_date", "match_time", "league", "home_team", "away_team",
    "home_elo", "away_elo", "p_home", "p_draw", "p_away",
    "predicted_outcome", "published_at", "hash",
    "actual_result", "correct", "settled_at",
]

_SUFFIX_RE = re.compile(r" (United FC|FC|AFC|CF|SC|BC)$", re.IGNORECASE)


def _strip_suffix(name: str) -> str:
    return _SUFFIX_RE.sub("", name or "").strip()


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


def _load_existing_keys() -> set[str]:
    if not os.path.exists(LOG_CSV):
        return set()
    df = pd.read_csv(LOG_CSV, usecols=["match_date", "home_team", "away_team"], dtype=str)
    return {f"{r.match_date}|{r.home_team}|{r.away_team}" for r in df.itertuples()}


def main() -> None:
    print("Loading existing prediction log...")
    existing_keys = _load_existing_keys()
    print(f"  {len(existing_keys)} existing predictions")

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

    for m in matches:
        home_team  = _strip_suffix(m.get("home_team", ""))
        away_team  = _strip_suffix(m.get("away_team", ""))
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
