#!/usr/bin/env python3
"""
publish_predictions.py

Fetches upcoming fixtures from our own API (fixture list, team names, Elo
ratings and Elo probabilities), then appends new prediction rows to
data/processed/prediction_log.csv.

Probabilities: each fixture is looked up by match_id in the locally written
data/processed/upcoming_predictions.csv (predict_upcoming.py). If it is there
as a resolved club fixture, its ensemble probabilities are logged
(source=ensemble); otherwise the endpoint's Elo probabilities are logged as
before (source=elo). No fixture is dropped for lack of an ensemble prob.

Must run AFTER predict_upcoming.py so the ensemble CSV is from this run.
"""

import csv
import hashlib
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import pandas as pd
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from league_coverage import is_covered_league  # noqa: E402
from log_schema import LOG_COLS, migrate_log_header  # noqa: E402
from predict_upcoming import _resolve_team  # noqa: E402

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
LOG_CSV  = os.path.join(BASE_DIR, "data", "processed", "prediction_log.csv")
RESULTS_CSV = os.path.join(BASE_DIR, "data", "processed", "results.csv")
UPCOMING_PREDICTIONS_CSV = os.path.join(BASE_DIR, "data", "processed", "upcoming_predictions.csv")

# Ensemble CSV older than this is treated as stale (predict_upcoming runs in
# the same CI job, minutes before publish).
MAX_ENSEMBLE_CSV_AGE = timedelta(hours=48)

# ── API ───────────────────────────────────────────────────────────────────────
UPCOMING_URL = "https://web-production-eb371.up.railway.app/api/live/upcoming"

ENSEMBLE_COLS = ("p_home_ensemble", "p_draw_ensemble", "p_away_ensemble")

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


def _match_id_key(v) -> str:
    """Normalise a match_id to a plain-integer string on both sides of the
    join (565859, "565859" and 565859.0 all -> "565859"); "" if missing."""
    if v is None:
        return ""
    s = str(v).strip()
    if s.lower() in ("", "nan", "none"):
        return ""
    try:
        f = float(s)
    except ValueError:
        return s
    return str(int(f)) if f.is_integer() else s


def _stale_reason(df: pd.DataFrame, path: str) -> str | None:
    """Why the ensemble CSV must not be used this run, or None if it's usable."""
    if df.empty:
        return "file is empty"
    missing = [c for c in ("match_id", "match_date", "teams_resolved", "is_international", *ENSEMBLE_COLS)
               if c not in df.columns]
    if missing:
        return f"missing column(s) {missing} (written by an older predict_upcoming.py)"
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(os.path.getmtime(path), timezone.utc)
    if age > MAX_ENSEMBLE_CSV_AGE:
        return f"file is {age.days}d {age.seconds // 3600}h old (> {MAX_ENSEMBLE_CSV_AGE})"
    # mtime is reset by a git checkout, so also check the content: predict_upcoming
    # only predicts fixtures from today on, so a fixture dated before yesterday
    # means this CSV came from an earlier run.
    oldest = str(df["match_date"].min())
    cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    if oldest < cutoff:
        return f"contains fixtures dated {oldest} (before {cutoff}) — from an earlier run"
    return None


def _load_ensemble_lookup(path: str) -> dict[str, dict]:
    """match_id -> CSV row (ensemble probs + flags) from upcoming_predictions.csv.
    Returns {} (everything falls back to Elo) if the file is missing or stale."""
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found — logging Elo probabilities (source=elo) for ALL fixtures.")
        return {}
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
    except pd.errors.EmptyDataError:
        df = pd.DataFrame()
    reason = _stale_reason(df, path)
    if reason:
        print("  " + "!" * 70)
        print(f"  WARNING: NOT using {os.path.basename(path)}: {reason}.")
        print("  Logging Elo probabilities (source=elo) for ALL fixtures this run.")
        print("  " + "!" * 70)
        return {}
    lookup: dict[str, dict] = {}
    for r in df.to_dict(orient="records"):
        key = _match_id_key(r.get("match_id"))
        if key:
            lookup[key] = r
    return lookup


def _ensemble_probs(row: dict | None) -> tuple[float, float, float] | None:
    """Ensemble (p_home, p_draw, p_away) if the CSV row is a resolved club
    fixture with valid probabilities, else None."""
    if not row:
        return None
    if str(row.get("teams_resolved", "")).strip().lower() != "true":
        return None
    if str(row.get("is_international", "")).strip().lower() != "false":
        return None
    try:
        return tuple(float(row[c]) for c in ENSEMBLE_COLS)  # type: ignore[return-value]
    except (TypeError, ValueError, KeyError):
        return None


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
    added = migrate_log_header(LOG_CSV)
    if added:
        print(f"Migrated {LOG_CSV} header: added {added} column(s) (blank on existing rows)")

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

    print(f"Loading ensemble probabilities from {UPCOMING_PREDICTIONS_CSV}...")
    ensemble_lookup = _load_ensemble_lookup(UPCOMING_PREDICTIONS_CSV)
    print(f"  {len(ensemble_lookup)} fixtures with ensemble probabilities (by match_id)")

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

        ens = _ensemble_probs(ensemble_lookup.get(_match_id_key(m.get("match_id"))))
        if ens is not None:
            p_home, p_draw, p_away = ens
            source = "ensemble"
        else:
            try:
                p_home = float(m.get("p_home", 0))
                p_draw = float(m.get("p_draw", 0))
                p_away = float(m.get("p_away", 0))
            except (TypeError, ValueError):
                print(f"  Skipping {home_team} vs {away_team}: invalid probabilities")
                continue
            source = "elo"

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
            "source":        source,
        })
        existing_keys.add(key)

    if skipped_uncovered:
        print(f"  Skipped {sum(skipped_uncovered.values())} fixtures in uncovered leagues (can't settle):")
        for lg, n in skipped_uncovered.most_common():
            print(f"    {lg}: {n}")

    src_counts = Counter(r["source"] for r in new_rows)
    print(f"  New rows by source: ensemble={src_counts['ensemble']}  elo={src_counts['elo']}")

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
