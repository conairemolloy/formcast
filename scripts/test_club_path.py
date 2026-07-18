#!/usr/bin/env python3
"""
test_club_path.py

Exercises the full club ensemble prediction path without live fixtures.
Loads models and replays results.csv exactly as predict_upcoming.main() does,
then runs 3 synthetic club fixtures through predict_club_fixture() and validates
the outputs.
"""

import json
import os
import sys
from datetime import datetime

import joblib
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ensemble_v2 import FEATURE_COLS, init_state, update_state
from predict_upcoming import (
    BASE_DIR,
    DATA_DIR,
    MODELS_DIR,
    _current_season,
    predict_club_fixture,
)

# Synthetic fixtures: (home, away, date, league_code, display_name)
FIXTURES = [
    ("Arsenal",      "Liverpool",     "2026-08-16", "EPL",          "Premier League"),
    ("Barcelona",    "Real Madrid",   "2026-08-22", "LaLiga",       "La Liga"),
    ("Leeds",        "Middlesbrough", "2026-08-17", "Championship", "Championship"),
]

# Expected team names must exist in results.csv for their league
REQUIRED_TEAMS: dict[str, set[str]] = {
    "EPL":          {"Arsenal", "Liverpool"},
    "LaLiga":       {"Barcelona", "Real Madrid"},
    "Championship": {"Leeds", "Middlesbrough"},
}


def main() -> None:
    failures: list[str] = []

    # ── Load models (identical to predict_upcoming.main()) ────────────────────
    print("Loading models...")
    try:
        xgb_model      = joblib.load(os.path.join(MODELS_DIR, "xgb_ensemble.pkl"))
        meta_model     = joblib.load(os.path.join(MODELS_DIR, "meta_learner.pkl"))
        league_encoder = joblib.load(os.path.join(MODELS_DIR, "league_encoder.pkl"))
        draw_clf       = joblib.load(os.path.join(MODELS_DIR, "draw_classifier.pkl"))
        with open(os.path.join(MODELS_DIR, "feature_cols.json")) as f:
            saved_cols = json.load(f)
    except Exception as exc:
        print(f"FAIL: model load error: {exc}", file=sys.stderr)
        sys.exit(1)

    assert saved_cols == FEATURE_COLS, (
        f"feature_cols.json mismatch: saved {len(saved_cols)} vs "
        f"ensemble_v2.FEATURE_COLS {len(FEATURE_COLS)}"
    )
    feature_cols = saved_cols
    league_enc: dict[str, int] = {
        lg: int(i) for i, lg in enumerate(league_encoder.classes_)
    }
    print(f"  XGBoost ({len(feature_cols)} features), meta expects "
          f"{meta_model.n_features_in_} stack cols\n")

    # ── LSTM / BTL lookups (optional — fall back to global means if absent) ───
    lstm_lookup: dict = {}
    global_mean_home = 0.45
    btl_lookup: dict = {}
    btl_global_mean = 0.45

    _lstm_path = os.path.join(DATA_DIR, "lstm_predictions.csv")
    if os.path.exists(_lstm_path):
        _lstm_df = pd.read_csv(_lstm_path, parse_dates=["match_date"])
        if len(_lstm_df) > 0:
            global_mean_home = float(_lstm_df["p_home"].mean())
        for _, r in _lstm_df.iterrows():
            lstm_lookup[(r["home_team"], r["away_team"], str(r["match_date"].date()))] = float(r["p_home"])
        print(f"  LSTM: {len(lstm_lookup):,} records (mean={global_mean_home:.3f})")

    _btl_path = os.path.join(DATA_DIR, "btl_predictions.csv")
    if os.path.exists(_btl_path):
        _btl_df = pd.read_csv(_btl_path, parse_dates=["match_date"])
        if len(_btl_df) > 0:
            btl_global_mean = float(_btl_df["p_home_btl"].mean())
        for _, r in _btl_df.iterrows():
            btl_lookup[(r["home_team"], r["away_team"], str(r["match_date"].date()))] = float(r["p_home_btl"])
        print(f"  BTL:  {len(btl_lookup):,} records (mean={btl_global_mean:.3f})")
    print()

    # ── xG lookup (identical to predict_upcoming.main()) ─────────────────────
    xg_lookup: dict = {}
    xg_path = os.path.join(DATA_DIR, "results_with_xg.csv")
    if os.path.exists(xg_path):
        xg_df = pd.read_csv(xg_path, parse_dates=["match_date"])
        xg_df = xg_df.dropna(subset=["home_xg", "away_xg", "xg_diff"])
        for _, r in xg_df.iterrows():
            key = (r["match_date"].date(), r["home_team"], r["away_team"], r["league"])
            xg_lookup[key] = (float(r["home_xg"]), float(r["away_xg"]), float(r["xg_diff"]))
        print(f"  xG:   {len(xg_lookup):,} records from results_with_xg.csv")
    else:
        print("  xG:   results_with_xg.csv not found — xG features will use fallback 1.3")
    print()

    # ── Replay historical results (identical to predict_upcoming.main()) ───────
    results_path = os.path.join(DATA_DIR, "results.csv")
    hist_df = pd.read_csv(results_path, parse_dates=["match_date"], low_memory=False)
    hist_df = hist_df.sort_values("match_date").reset_index(drop=True)
    hist_df = hist_df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])

    state = init_state()
    n_total = len(hist_df)
    xg_hit = 0
    print(f"Replaying {n_total:,} historical matches to build state...")
    for i, row in hist_df.iterrows():
        if i > 0 and i % 10000 == 0:
            print(f"  {i:,}/{n_total:,}")
        ref_raw = row["referee"] if "referee" in hist_df.columns else None
        ref_raw = ref_raw if (isinstance(ref_raw, str) and ref_raw.strip()) else None
        xg_key  = (row["match_date"].date(), row["home_team"], row["away_team"], row["league"])
        xg_vals = xg_lookup.get(xg_key)
        if xg_vals is not None:
            xg_hit += 1
        update_state(
            state,
            row["home_team"], row["away_team"],
            row["match_date"], row["season"], row["league"],
            int(row["home_goals"]), int(row["away_goals"]), row["result"],
            xg_vals=xg_vals, ref_name=ref_raw,
            home_yellows=float(row["home_yellows"]) if pd.notna(row.get("home_yellows")) else 0.0,
            away_yellows=float(row["away_yellows"]) if pd.notna(row.get("away_yellows")) else 0.0,
            home_fouls=float(row["home_fouls"])   if pd.notna(row.get("home_fouls"))   else 0.0,
            away_fouls=float(row["away_fouls"])   if pd.notna(row.get("away_fouls"))   else 0.0,
            home_shots=int(row["home_shots"]) if "home_shots" in hist_df.columns and pd.notna(row.get("home_shots")) else None,
            away_shots=int(row["away_shots"]) if "away_shots" in hist_df.columns and pd.notna(row.get("away_shots")) else None,
        )

    known_teams = set(state["team_hist"].keys()) | set(state["elo"].keys())
    xg_miss = n_total - xg_hit
    print(f"  Done. Tracked {len(known_teams)} teams.")
    print(f"  xG coverage: {xg_hit:,}/{n_total:,} matches had real xG  "
          f"({xg_miss:,} used fallback 1.3)\n")

    # ── Validate fixture team names exist in results.csv ──────────────────────
    for league, req_teams in REQUIRED_TEAMS.items():
        league_df = hist_df[hist_df["league"] == league]
        all_league_teams = set(league_df["home_team"]) | set(league_df["away_team"])
        for team in sorted(req_teams):
            if team not in all_league_teams:
                sample = sorted(all_league_teams)[:10]
                msg = (
                    f"ERROR: '{team}' not found in results.csv for league '{league}'. "
                    f"First 10 teams in dataset: {sample}"
                )
                print(msg, file=sys.stderr)
                failures.append(msg)

    if failures:
        sys.exit(1)

    # ── Run each fixture through the club prediction path ────────────────────
    print("=" * 62)
    print("CLUB PREDICTION PATH TEST")
    print("=" * 62)

    for home, away, date_str, league_code, display in FIXTURES:
        print(f"\n{display}: {home} vs {away}  ({date_str})")
        match_date = datetime.strptime(date_str, "%Y-%m-%d")
        season = _current_season(match_date)

        try:
            result = predict_club_fixture(
                state, home, away, match_date, league_code, season,
                xgb_model=xgb_model,
                meta_model=meta_model,
                draw_clf=draw_clf,
                feature_cols=feature_cols,
                league_enc=league_enc,
                lstm_lookup=lstm_lookup,
                btl_lookup=btl_lookup,
                global_mean_home=global_mean_home,
                btl_global_mean=btl_global_mean,
            )
        except AssertionError as exc:
            msg = f"FAIL [{home} vs {away}] guard failed: {exc}"
            print(msg, file=sys.stderr)
            failures.append(msg)
            continue
        except Exception as exc:
            msg = f"FAIL [{home} vs {away}] unexpected error: {exc}"
            print(msg, file=sys.stderr)
            failures.append(msg)
            continue

        ph   = result["p_home_ensemble"]
        pd_  = result["p_draw_ensemble"]
        pa   = result["p_away_ensemble"]
        total = ph + pd_ + pa
        sw    = result["stack_width"]
        sum_ok   = abs(total - 1.0) < 1e-4
        width_ok = sw == meta_model.n_features_in_

        print(f"  Ensemble:    H={ph:.4f}  D={pd_:.4f}  A={pa:.4f}")
        print(f"  Sum:         {total:.6f}  {'OK' if sum_ok else 'FAIL'}")
        print(f"  Stack width: {sw}  (meta expects {meta_model.n_features_in_})  "
              f"{'OK' if width_ok else 'FAIL'}")
        print(f"  Predicted:   {result['predicted_outcome']}")
        print(f"  Guard 1 (feature completeness): PASSED")
        print(f"  Guard 2 (stack width check):    PASSED")

        if not sum_ok:
            failures.append(f"[{home} vs {away}] probs sum to {total:.6f}, expected ~1.0")
        if not width_ok:
            failures.append(f"[{home} vs {away}] stack width {sw} != {meta_model.n_features_in_}")

    print("\n" + "=" * 62)
    if failures:
        print(f"FAILED ({len(failures)} error(s)):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"ALL {len(FIXTURES)} FIXTURES PASSED")


if __name__ == "__main__":
    main()
