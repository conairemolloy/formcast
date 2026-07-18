"""
predict_upcoming.py

Generates ensemble predictions for upcoming fixtures.

Fetches fixtures from:
  GET https://web-production-eb371.up.railway.app/api/live/upcoming

Replays all historical results to rebuild current rolling state (Elo, Glicko-2,
form, H2H, DC), then computes the same 48 features used during training and runs
them through the saved XGBoost + meta-learner stack.

Output: data/processed/upcoming_predictions.csv
"""

import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta

import httpx
import joblib
import numpy as np
import pandas as pd

# ─── Import shared helpers from ensemble_v2 ──────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ensemble_v2 import (  # noqa: E402
    FEATURE_COLS, STACK_COLS, DRAW_COLS,
    STARTING_ELO, ELO_HA, G2_SCALE,
    DC_HOME_ADV,
    init_state, compute_match_features, update_state,
    _sigmoid,
    _dc_attack, _dc_defence, _dc_probs,
)

# ─── Config ──────────────────────────────────────────────────────────────────
UPCOMING_URL = os.environ.get(
    "FORMCAST_API_URL",
    "https://web-production-eb371.up.railway.app/api/live/upcoming"
)

BASE_DIR   = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR   = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# API competition name → internal league code used in results.csv
COMP_TO_LEAGUE: dict[str, str] = {
    "Premier League":       "EPL",
    "La Liga":              "LaLiga",
    "Serie A":              "SerieA",
    "Bundesliga":           "Bundesliga",
    "Ligue 1":              "Ligue1",
    "Championship":         "Championship",
    # Second tiers and other competitions present in results.csv
    "2. Bundesliga":        "Bundesliga2",
    "Bundesliga 2":         "Bundesliga2",
    "Ligue 2":              "Ligue2",
    "Scottish Premiership": "ScottishPrem",
    "Scottish Premier League": "ScottishPrem",
    "Serie B":              "SerieB",
    "Segunda División":     "Segunda",
    "La Liga 2":            "Segunda",
    "Segunda Division":     "Segunda",
}
DEFAULT_LEAGUE = "EPL"

RESULT_INV = {0: "A", 1: "D", 2: "H"}

_SUFFIX_RE = re.compile(r"\s+(United FC|City FC|FC|AFC|CF|SC|BC)$", re.IGNORECASE)


def _strip_suffix(name: str) -> str:
    return _SUFFIX_RE.sub("", name or "").strip()


INTERNATIONAL_COMPETITIONS = frozenset({
    "FIFA World Cup",
    "UEFA European Championship",
    "Copa América",
    "African Cup of Nations",
    "AFC Asian Cup",
    "UEFA Nations League",
    "CONCACAF Gold Cup",
    "CONCACAF Nations League",
    "OFC Nations Cup",
})

INTL_NAME_ALIASES: dict[str, str] = {
    "Czechia":             "Czech Republic",
    "Bosnia-Herzegovina":  "Bosnia and Herzegovina",
}

# Teams that receive genuine home advantage at a tournament finals
# (i.e. they are the host nation — all other teams play at neutral venues)
HOST_NATIONS: dict[str, set[str]] = {
    "FIFA World Cup": {"United States", "Mexico", "Canada"},
}

_INTL_KEYWORDS = (
    "world cup",
    "european championship",
    "copa america",
    "copa américa",
    "african cup",
    "asian cup",
    "nations league",
    "concacaf",
    "ofc nations",
)


def is_international_competition(competition: str) -> bool:
    """Return True only for confirmed national-team competitions.

    Conservative: anything already in COMP_TO_LEAGUE is club by definition.
    Only flag things we're confident are international; default to club otherwise.
    """
    if not competition:
        return False
    if competition in COMP_TO_LEAGUE:
        return False
    comp_lower = competition.lower()
    for kw in _INTL_KEYWORDS:
        if kw in comp_lower:
            return True
    return False


def is_tournament_finals(competition: str) -> bool:
    """Return True for tournament finals proper (not qualification rounds).

    Distinguishes "FIFA World Cup" (neutral-venue finals) from
    "FIFA World Cup qualification" (genuine home/away matches).
    """
    if not competition:
        return False
    if "qualification" in competition.lower():
        return False
    return competition in INTERNATIONAL_COMPETITIONS


def _resolve_intl_team(name: str, intl_elo: dict[str, float]) -> tuple[str, float]:
    """Look up a national team in the international Elo dict.

    Returns (canonical_name, elo_rating). Falls back to 1500 with a printed
    warning if the team isn't found anywhere in the international ratings.
    """
    # Check known naming mismatches between football-data.org and the dataset
    canonical = INTL_NAME_ALIASES.get(name, name)
    if canonical in intl_elo:
        return canonical, intl_elo[canonical]
    if name in intl_elo:
        return name, intl_elo[name]
    name_lower = name.lower()
    for team, rating in intl_elo.items():
        if team.lower() == name_lower:
            return team, rating
    for team, rating in intl_elo.items():
        if team.lower() in name_lower or name_lower in team.lower():
            return team, rating
    print(f"  WARNING: no international Elo for '{name}', using 1500 default")
    return name, STARTING_ELO


def _current_season(date: datetime) -> str:
    """Return season string like '2025-26' for a given match date."""
    y = date.year
    if date.month >= 8:
        return f"{y}-{str(y + 1)[-2:]}"
    return f"{y - 1}-{str(y)[-2:]}"


# ─── Elo probability (same formula as fetch_live_odds.py) ────────────────────
def _prematch_probs(
    home_elo: float,
    away_elo: float,
    apply_home_advantage: bool = True,
) -> tuple[float, float, float]:
    ha         = ELO_HA if apply_home_advantage else 0
    elo_diff   = home_elo - away_elo + ha
    p_home_raw = 1.0 / (1.0 + 10 ** (-elo_diff / 400))
    p_away_raw = 1.0 / (1.0 + 10 ** (elo_diff / 400))
    base_draw       = 0.265
    competitiveness = 1.0 - abs(p_home_raw - p_away_raw)
    p_draw          = base_draw * (0.5 + 0.5 * competitiveness)
    remainder       = 1.0 - p_draw
    p_home          = p_home_raw * remainder / (p_home_raw + p_away_raw)
    p_away          = p_away_raw * remainder / (p_home_raw + p_away_raw)
    return p_home, p_draw, p_away


# ─── Team name resolution ────────────────────────────────────────────────────

def _resolve_team(name: str, known_teams: set[str]) -> str:
    """Map an API team name to the canonical name used in results.csv."""
    if name in known_teams:
        return name
    lower = name.lower()
    for t in known_teams:
        if t.lower() == lower:
            return t
    for t in known_teams:
        if t.lower() in lower or lower in t.lower():
            return t
    return name  # return as-is; will get default ratings


# ─── Club prediction path ────────────────────────────────────────────────────

def predict_club_fixture(
    state: dict,
    home: str,
    away: str,
    match_date: datetime,
    league_code: str,
    season: str,
    *,
    xgb_model,
    meta_model,
    draw_clf,
    feature_cols: list[str],
    league_enc: dict[str, int],
    lstm_lookup: dict,
    btl_lookup: dict,
    global_mean_home: float,
    btl_global_mean: float,
) -> dict:
    """Run the full club ensemble prediction path for one fixture.

    Returns a dict with elo probs, ensemble probs, predicted_outcome, and stack_width.
    Raises AssertionError if either guard (feature completeness, stack width) fails.
    """
    home_elo_val = state["elo"].get(home, STARTING_ELO)
    away_elo_val = state["elo"].get(away, STARTING_ELO)
    p_home_elo, p_draw_elo, p_away_elo = _prematch_probs(home_elo_val, away_elo_val)

    feat = compute_match_features(
        state, home, away, match_date, season, league_code, league_enc,
        xg_vals=None, ref_raw=None,
        lstm_lookup=lstm_lookup, btl_lookup=btl_lookup,
        global_mean_home=global_mean_home, btl_global_mean=btl_global_mean,
    )
    assert set(feat.keys()) >= set(feature_cols), (
        f"compute_match_features missing keys: {set(feature_cols) - set(feat.keys())}"
    )

    X = np.array([[feat[c] for c in feature_cols]])
    xgb_proba = xgb_model.predict_proba(X)

    p_home_g2 = float(_sigmoid(np.array([feat["g2_diff"]]) / G2_SCALE * 1.6)[0])
    draw_prob  = float(draw_clf.predict_proba(
        np.array([[feat[c] for c in DRAW_COLS]])
    )[0, 1])
    stack_row = np.array([[
        feat["home_expected"],
        p_home_g2,
        feat["p_home_dc"], feat["p_draw_dc"], feat["p_away_dc"],
        xgb_proba[0, 2], xgb_proba[0, 1], xgb_proba[0, 0],
        feat["elo_diff"],
        feat["h2h_goal_diff_avg"],
        feat["h2h_home_win_rate"],
        feat["momentum_diff"],
        feat["p_home_lstm"],
        feat["p_home_btl"],
        draw_prob,
    ]])
    assert stack_row.shape[1] == meta_model.n_features_in_, (
        f"Stack width {stack_row.shape[1]} != meta_model expects "
        f"{meta_model.n_features_in_}"
    )

    meta_proba = meta_model.predict_proba(stack_row)
    meta_pred  = int(np.argmax(meta_proba[0]))

    return {
        "p_home_elo":        round(p_home_elo, 4),
        "p_draw_elo":        round(p_draw_elo, 4),
        "p_away_elo":        round(p_away_elo, 4),
        "p_home_ensemble":   round(float(meta_proba[0, 2]), 4),
        "p_draw_ensemble":   round(float(meta_proba[0, 1]), 4),
        "p_away_ensemble":   round(float(meta_proba[0, 0]), 4),
        "predicted_outcome": RESULT_INV[meta_pred],
        "stack_width":       int(stack_row.shape[1]),
    }


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    # Load models
    print("Loading models...")
    xgb_model      = joblib.load(os.path.join(MODELS_DIR, "xgb_ensemble.pkl"))
    meta_model     = joblib.load(os.path.join(MODELS_DIR, "meta_learner.pkl"))
    league_encoder = joblib.load(os.path.join(MODELS_DIR, "league_encoder.pkl"))
    draw_clf       = joblib.load(os.path.join(MODELS_DIR, "draw_classifier.pkl"))
    with open(os.path.join(MODELS_DIR, "feature_cols.json")) as f:
        saved_cols = json.load(f)
    assert saved_cols == FEATURE_COLS, (
        f"feature_cols.json has {len(saved_cols)} features but ensemble_v2.py "
        f"FEATURE_COLS has {len(FEATURE_COLS)} features. "
        f"Re-run ensemble_v2.py main() to regenerate the saved model files."
    )
    feature_cols = saved_cols
    print(f"  XGBoost ({len(feature_cols)} features), meta-learner, draw classifier, "
          f"league encoder loaded\n")

    # Build league_enc dict from encoder (safe fallback to 0 for unknown leagues)
    league_enc: dict[str, int] = {
        lg: int(i) for i, lg in enumerate(league_encoder.classes_)
    }

    # Load xG lookup
    xg_lookup: dict = {}
    xg_path = os.path.join(DATA_DIR, "results_with_xg.csv")
    if os.path.exists(xg_path):
        xg_df = pd.read_csv(xg_path, parse_dates=["match_date"])
        xg_df = xg_df.dropna(subset=["home_xg", "away_xg", "xg_diff"])
        for _, r in xg_df.iterrows():
            key = (r["match_date"].date(), r["home_team"], r["away_team"], r["league"])
            xg_lookup[key] = (float(r["home_xg"]), float(r["away_xg"]), float(r["xg_diff"]))
        print(f"Loaded {len(xg_lookup):,} xG records\n")
    else:
        print("Warning: results_with_xg.csv not found — xG features will use defaults\n")

    # Load LSTM lookup (global mean fallback for fixtures not in the CSV)
    lstm_lookup: dict[tuple, float] = {}
    global_mean_home = 0.45
    _lstm_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "processed", "lstm_predictions.csv"))
    if os.path.exists(_lstm_path):
        _lstm_df = pd.read_csv(_lstm_path, parse_dates=["match_date"])
        if len(_lstm_df) > 0:
            global_mean_home = float(_lstm_df["p_home"].mean())
        for _, r in _lstm_df.iterrows():
            lstm_lookup[(r["home_team"], r["away_team"], str(r["match_date"].date()))] = float(r["p_home"])
        print(f"Loaded {len(lstm_lookup):,} LSTM predictions (global mean={global_mean_home:.3f})\n")

    # Load BTL lookup (global mean fallback)
    btl_lookup: dict[tuple, float] = {}
    btl_global_mean = 0.45
    _btl_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "processed", "btl_predictions.csv"))
    if os.path.exists(_btl_path):
        _btl_df = pd.read_csv(_btl_path, parse_dates=["match_date"])
        if len(_btl_df) > 0:
            btl_global_mean = float(_btl_df["p_home_btl"].mean())
        for _, r in _btl_df.iterrows():
            btl_lookup[(r["home_team"], r["away_team"], str(r["match_date"].date()))] = float(r["p_home_btl"])
        print(f"Loaded {len(btl_lookup):,} BTL predictions (global mean={btl_global_mean:.3f})\n")

    # Load international Elo ratings — separate from club state, never merged
    international_elo: dict[str, float] = {}
    intl_ratings_path = os.path.join(DATA_DIR, "international_elo_ratings.csv")
    if os.path.exists(intl_ratings_path):
        intl_df = pd.read_csv(intl_ratings_path)
        international_elo = {row["team"]: float(row["elo_rating"]) for _, row in intl_df.iterrows()}
        print(f"Loaded {len(international_elo):,} international Elo ratings\n")
    else:
        print("Warning: international_elo_ratings.csv not found — international fixtures will use 1500 default\n")

    # Replay all historical results through update_state() to build full current state.
    # Uses init_state() + update_state() from ensemble_v2 — identical update logic to
    # build_all_features(), so season regression and promotion/relegation are applied
    # automatically as part of _apply_pre_match_adjustments inside update_state().
    results_path = os.path.join(DATA_DIR, "results.csv")
    hist_df = pd.read_csv(results_path, parse_dates=["match_date"])
    hist_df = hist_df.sort_values("match_date").reset_index(drop=True)
    hist_df = hist_df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])

    state   = init_state()
    n_total = len(hist_df)
    print(f"Replaying {n_total:,} historical matches to build current state...")
    for i, row in hist_df.iterrows():
        if i > 0 and i % 5000 == 0:
            print(f"  {i:,}/{n_total:,}")
        home   = row["home_team"]
        away   = row["away_team"]
        date   = row["match_date"]
        season = row["season"]
        league = row["league"]
        hg     = int(row["home_goals"])
        ag     = int(row["away_goals"])
        result = row["result"]
        ref_raw = row["referee"] if "referee" in hist_df.columns else None
        ref_raw = ref_raw if (isinstance(ref_raw, str) and ref_raw.strip()) else None
        xg_key  = (date.date(), home, away, league)
        xg_vals = xg_lookup.get(xg_key)
        h_yel   = float(row["home_yellows"]) if pd.notna(row.get("home_yellows")) else 0.0
        a_yel   = float(row["away_yellows"]) if pd.notna(row.get("away_yellows")) else 0.0
        h_foul  = float(row["home_fouls"])   if pd.notna(row.get("home_fouls"))   else 0.0
        a_foul  = float(row["away_fouls"])   if pd.notna(row.get("away_fouls"))   else 0.0
        h_shots = int(row["home_shots"]) if "home_shots" in hist_df.columns and pd.notna(row.get("home_shots")) else None
        a_shots = int(row["away_shots"]) if "away_shots" in hist_df.columns and pd.notna(row.get("away_shots")) else None
        update_state(
            state, home, away, date, season, league, hg, ag, result,
            xg_vals=xg_vals, ref_name=ref_raw,
            home_yellows=h_yel, away_yellows=a_yel,
            home_fouls=h_foul, away_fouls=a_foul,
            home_shots=h_shots, away_shots=a_shots,
        )

    known_teams = set(state["team_hist"].keys()) | set(state["elo"].keys())
    print(f"  Done. Tracked {len(known_teams)} teams.\n")

    # Fetch upcoming fixtures with retry / exponential backoff
    print(f"Fetching upcoming fixtures from {UPCOMING_URL}...")
    _retry_delays = [5, 15, 30]
    matches = None
    for _attempt in range(len(_retry_delays) + 1):
        try:
            resp = httpx.get(UPCOMING_URL, timeout=30)
            resp.raise_for_status()
            matches = resp.json().get("data", [])
            print(f"  {len(matches)} fixtures returned\n")
            break
        except Exception as exc:
            if _attempt < len(_retry_delays):
                _wait = _retry_delays[_attempt]
                print(
                    f"  ERROR fetching fixtures: {exc}",
                    file=sys.stderr,
                )
                print(
                    f"  Retry {_attempt + 1}/{len(_retry_delays)} after {_wait}s...",
                    file=sys.stderr,
                )
                time.sleep(_wait)
            else:
                print(f"  ERROR fetching fixtures: {exc}", file=sys.stderr)
                print("  All retries exhausted — giving up.", file=sys.stderr)
                sys.exit(1)

    out_path = os.path.join(DATA_DIR, "upcoming_predictions.csv")

    if not matches:
        print("No upcoming fixtures — writing empty file.")
        pd.DataFrame(columns=[
            "match_date", "match_time", "league", "home_team", "away_team",
            "p_home_elo", "p_draw_elo", "p_away_elo",
            "p_home_ensemble", "p_draw_ensemble", "p_away_ensemble",
            "predicted_outcome", "is_international",
        ]).to_csv(out_path, index=False)
        return

    rows = []

    for m in matches:
        home_raw       = m.get("home_team", "")
        away_raw       = m.get("away_team", "")
        match_date_str = m.get("match_date", "")
        match_time     = m.get("match_time", "")
        competition    = m.get("competition", "")

        if not home_raw or not away_raw or not match_date_str:
            continue

        try:
            match_date = datetime.strptime(match_date_str, "%Y-%m-%d")
        except ValueError:
            continue

        is_intl = is_international_competition(competition)

        if is_intl:
            # International fixture — use international Elo dict, skip the ensemble
            home_display, home_elo_val = _resolve_intl_team(home_raw, international_elo)
            away_display, away_elo_val = _resolve_intl_team(away_raw, international_elo)

            # Neutral-venue correction: at tournament finals only the host nation(s)
            # get genuine home advantage — every other fixture is neutral
            if is_tournament_finals(competition):
                apply_ha = home_display in HOST_NATIONS.get(competition, set())
            else:
                apply_ha = True  # qualifiers, Nations League, friendlies are real home/away

            p_home_elo, p_draw_elo, p_away_elo = _prematch_probs(home_elo_val, away_elo_val, apply_ha)

            # Use rolling DC probs for ensemble if team has club history; else fall back to Elo
            dc_s = defaultdict(list, state.get("dc_scored", {}))
            dc_c = defaultdict(list, state.get("dc_conceded", {}))
            if dc_s[home_display] and dc_s[away_display]:
                ha_bonus  = DC_HOME_ADV if apply_ha else 0.0
                lam_intl  = math.exp(_dc_attack(dc_s[home_display]) - _dc_defence(dc_c[away_display]) + ha_bonus)
                mu_intl   = math.exp(_dc_attack(dc_s[away_display]) - _dc_defence(dc_c[home_display]))
                p_ens_h, p_ens_d, p_ens_a = _dc_probs(lam_intl, mu_intl)
            else:
                p_ens_h, p_ens_d, p_ens_a = p_home_elo, p_draw_elo, p_away_elo

            probs = {"H": p_ens_h, "D": p_ens_d, "A": p_ens_a}
            rows.append({
                "match_date":        match_date_str,
                "match_time":        match_time,
                "league":            competition,
                "home_team":         home_display,
                "away_team":         away_display,
                "p_home_elo":        round(p_home_elo, 4),
                "p_draw_elo":        round(p_draw_elo, 4),
                "p_away_elo":        round(p_away_elo, 4),
                "p_home_ensemble":   round(p_ens_h, 4),
                "p_draw_ensemble":   round(p_ens_d, 4),
                "p_away_ensemble":   round(p_ens_a, 4),
                "predicted_outcome": max(probs, key=probs.get),
                "is_international":  True,
            })
        else:
            # Club fixture
            if competition not in COMP_TO_LEAGUE:
                print(f"  WARNING: unknown competition '{competition}' — falling back to {DEFAULT_LEAGUE}")
            league_code = COMP_TO_LEAGUE.get(competition, DEFAULT_LEAGUE)
            season      = _current_season(match_date)

            home = _resolve_team(_strip_suffix(home_raw), known_teams)
            away = _resolve_team(_strip_suffix(away_raw), known_teams)

            result = predict_club_fixture(
                state, home, away, match_date, league_code, season,
                xgb_model=xgb_model, meta_model=meta_model, draw_clf=draw_clf,
                feature_cols=feature_cols, league_enc=league_enc,
                lstm_lookup=lstm_lookup, btl_lookup=btl_lookup,
                global_mean_home=global_mean_home, btl_global_mean=btl_global_mean,
            )
            rows.append({
                "match_date":        match_date_str,
                "match_time":        match_time,
                "league":            competition,
                "home_team":         home,
                "away_team":         away,
                "p_home_elo":        result["p_home_elo"],
                "p_draw_elo":        result["p_draw_elo"],
                "p_away_elo":        result["p_away_elo"],
                "p_home_ensemble":   result["p_home_ensemble"],
                "p_draw_ensemble":   result["p_draw_ensemble"],
                "p_away_ensemble":   result["p_away_ensemble"],
                "predicted_outcome": result["predicted_outcome"],
                "is_international":  False,
            })

    out_df = pd.DataFrame(rows)
    out_df.to_csv(out_path, index=False)
    print(f"Saved {len(out_df)} predictions to {out_path}")

    # Print summary grouped by international vs club
    print(f"\n{'='*70}")
    print(f"UPCOMING PREDICTIONS  ({len(out_df)} fixtures)")
    print(f"{'='*70}")

    intl_out = out_df[out_df["is_international"]]
    club_out  = out_df[~out_df["is_international"]]

    if not intl_out.empty:
        print(f"\n  --- International ({len(intl_out)}) — Elo-only, no ensemble ---")
        for _, row in intl_out.sort_values(["match_date", "match_time"]).iterrows():
            label = {"H": "Home", "D": "Draw", "A": "Away"}.get(row["predicted_outcome"], "?")
            is_neutral = (
                is_tournament_finals(row["league"])
                and row["home_team"] not in HOST_NATIONS.get(row["league"], set())
            )
            venue_tag = "  [neutral venue]" if is_neutral else ""
            print(
                f"  {row['league']:30s}  {row['home_team']} vs {row['away_team']}{venue_tag}\n"
                f"    Predicted: {label:4s}  "
                f"elo=[H:{row['p_home_elo']:.1%} "
                f"D:{row['p_draw_elo']:.1%} "
                f"A:{row['p_away_elo']:.1%}]  "
                f"[{row['match_date']} {row['match_time']}]"
            )

    if not club_out.empty:
        print(f"\n  --- Club ({len(club_out)}) ---")
        for _, row in club_out.sort_values(["match_date", "match_time"]).iterrows():
            label = {"H": "Home", "D": "Draw", "A": "Away"}.get(row["predicted_outcome"], "?")
            print(
                f"  {row['league']:18s}  {row['home_team']} vs {row['away_team']}\n"
                f"    Predicted: {label:4s}  "
                f"ensemble=[H:{row['p_home_ensemble']:.1%} "
                f"D:{row['p_draw_ensemble']:.1%} "
                f"A:{row['p_away_ensemble']:.1%}]  "
                f"elo=H:{row['p_home_elo']:.1%}  "
                f"[{row['match_date']} {row['match_time']}]"
            )


if __name__ == "__main__":
    main()
