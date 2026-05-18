import os
from collections import defaultdict
from datetime import timedelta

import numpy as np
import pandas as pd

# Elo constants — match elo_model.py (K=16, HA=50 optimised via hyperparameter search)
STARTING_RATING = 1500
K = 16
HOME_ADVANTAGE = 50
EWM_ALPHA = 0.4


# ---------------------------------------------------------------------------
# Elo helpers
# ---------------------------------------------------------------------------

def _mov_multiplier(goal_diff: int) -> float:
    return min(2.0, 1.0 + np.log(1.0 + abs(goal_diff)) / np.log(10))


def _expected_score(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


# ---------------------------------------------------------------------------
# Signal helpers
# ---------------------------------------------------------------------------

def _ewm_value(values: list, alpha: float) -> float:
    """EWM with adjust=True (weights normalised). Values are oldest → newest."""
    n = len(values)
    weights = [(1.0 - alpha) ** (n - 1 - i) for i in range(n)]
    total = sum(weights)
    return sum(w * v for w, v in zip(weights, values)) / total


def _ols_slope(y_values: list) -> float:
    """OLS slope of y_values against x = [0, 1, …, n-1]."""
    n = len(y_values)
    x_mean = (n - 1) / 2.0
    y_mean = sum(y_values) / n
    num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(y_values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den != 0.0 else 0.0


def _streak(prior: list) -> int:
    """Current W/L streak: +N won last N, -N lost last N, 0 = drew / mixed."""
    if not prior:
        return 0
    last_res = prior[-1]["result"]
    if last_res == "D":
        return 0
    sign = 1 if last_res == "W" else -1
    count = 0
    for h in reversed(prior):
        if (sign == 1 and h["result"] == "W") or (sign == -1 and h["result"] == "L"):
            count += 1
        else:
            break
    return sign * count


def _elo_28d_ago(elo_hist: list, match_date) -> float | None:
    """Most recent pre-match Elo recorded at or before match_date − 28 days."""
    cutoff = match_date - timedelta(days=28)
    result = None
    for date, rating in elo_hist:   # elo_hist is sorted ascending
        if date <= cutoff:
            result = rating
        else:
            break
    return result


# ---------------------------------------------------------------------------
# Per-team signal computation
# ---------------------------------------------------------------------------

def _compute_signals(
    history: list,
    elo_hist: list,
    current_elo: float,
    match_date,
) -> dict:
    """
    Compute all 8 momentum signals for one team at match_date using only
    prior matches (strict date < match_date filter).
    """
    prior = [h for h in history if h["date"] < match_date]
    n = len(prior)

    # 1. result_momentum — EWM of points (W=3, D=1, L=0), last 5, α=0.4
    if n >= 2:
        pts_vals = [h["points"] for h in prior[-5:]]
        rm = _ewm_value(pts_vals, EWM_ALPHA) / 3.0
    else:
        rm = 0.5

    # 2. score_momentum — EWM of goal diff, last 5, α=0.4, clipped ±5 → [0,1]
    if n >= 2:
        gd_vals = [h["goal_diff"] for h in prior[-5:]]
        sm_raw = float(np.clip(_ewm_value(gd_vals, EWM_ALPHA), -5.0, 5.0))
        sm = (sm_raw + 5.0) / 10.0
    else:
        sm = 0.5

    # 3. elo_momentum — (current Elo − Elo 28 days ago) / 100
    past_elo = _elo_28d_ago(elo_hist, match_date)
    elo_mom = (current_elo - past_elo) / 100.0 if past_elo is not None else 0.0

    # 4. scoring_rate_trend — OLS slope of goals scored, last 8, clipped ±1
    if n >= 3:
        gs_vals = [h["goals_scored"] for h in prior[-8:]]
        srt = float(np.clip(_ols_slope(gs_vals), -1.0, 1.0))
    else:
        srt = 0.0

    # 5. concession_rate_trend — OLS slope of goals conceded, last 8, negated, clipped ±1
    if n >= 3:
        gc_vals = [h["goals_conceded"] for h in prior[-8:]]
        crt = float(np.clip(-_ols_slope(gc_vals), -1.0, 1.0))
    else:
        crt = 0.0

    # 6. first_half_momentum — unavailable (no H1 data), placeholder 0.0
    # 7. second_half_momentum — unavailable (no H2 data), placeholder 0.0

    # 8. streak — clipped ±5, normalised to [0,1]
    streak_raw = _streak(prior)
    streak = (float(np.clip(streak_raw, -5, 5)) + 5.0) / 10.0

    # composite = mean of 6 available signals (excluding h1/h2)
    composite = (rm + sm + elo_mom + srt + crt + streak) / 6.0

    return {
        "result_momentum": rm,
        "score_momentum": sm,
        "elo_momentum": elo_mom,
        "scoring_trend": srt,
        "concession_trend": crt,
        "streak": streak,
        "composite": composite,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "results.csv"))

    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    print(f"Loaded {len(df)} matches across {df['season'].nunique()} seasons\n")

    team_history: dict[str, list] = defaultdict(list)
    elo_ratings: dict[str, float] = {}
    elo_hist: dict[str, list] = defaultdict(list)

    pts_map = {"W": 3, "D": 1, "L": 0}
    rows = []

    for i, row in df.iterrows():
        if i > 0 and i % 2000 == 0:
            print(f"  Processed {i}/{len(df)} matches...")

        home = row["home_team"]
        away = row["away_team"]
        date = row["match_date"]
        hg = int(row["home_goals"])
        ag = int(row["away_goals"])
        result = row["result"]

        home_elo = elo_ratings.get(home, STARTING_RATING)
        away_elo = elo_ratings.get(away, STARTING_RATING)

        # Record pre-match Elo before computing signals so elo_momentum can
        # compare current pre-match Elo against the value from 28 days ago.
        elo_hist[home].append((date, home_elo))
        elo_hist[away].append((date, away_elo))

        home_sig = _compute_signals(team_history[home], elo_hist[home], home_elo, date)
        away_sig = _compute_signals(team_history[away], elo_hist[away], away_elo, date)

        actual_result = 1.0 if result == "H" else (0.5 if result == "D" else 0.0)

        rows.append({
            "match_date": date,
            "league": row["league"],
            "home_team": home,
            "away_team": away,
            "home_result_momentum": round(home_sig["result_momentum"], 6),
            "home_score_momentum": round(home_sig["score_momentum"], 6),
            "home_elo_momentum": round(home_sig["elo_momentum"], 6),
            "home_scoring_trend": round(home_sig["scoring_trend"], 6),
            "home_concession_trend": round(home_sig["concession_trend"], 6),
            "home_streak": round(home_sig["streak"], 6),
            "away_result_momentum": round(away_sig["result_momentum"], 6),
            "away_score_momentum": round(away_sig["score_momentum"], 6),
            "away_elo_momentum": round(away_sig["elo_momentum"], 6),
            "away_scoring_trend": round(away_sig["scoring_trend"], 6),
            "away_concession_trend": round(away_sig["concession_trend"], 6),
            "away_streak": round(away_sig["streak"], 6),
            "momentum_diff": round(home_sig["composite"] - away_sig["composite"], 6),
            "actual_result": actual_result,
        })

        # Update Elo ratings (post-match)
        home_exp = _expected_score(home_elo + HOME_ADVANTAGE, away_elo)
        away_exp = 1.0 - home_exp
        if result == "H":
            hs, as_ = 1.0, 0.0
        elif result == "D":
            hs, as_ = 0.5, 0.5
        else:
            hs, as_ = 0.0, 1.0
        mov = _mov_multiplier(hg - ag)
        elo_ratings[home] = home_elo + K * mov * (hs - home_exp)
        elo_ratings[away] = away_elo + K * mov * (as_ - away_exp)

        # Update per-team match history
        if result == "D":
            home_res = away_res = "D"
        elif result == "H":
            home_res, away_res = "W", "L"
        else:
            home_res, away_res = "L", "W"

        team_history[home].append({
            "date": date,
            "points": pts_map[home_res],
            "goal_diff": hg - ag,
            "goals_scored": hg,
            "goals_conceded": ag,
            "result": home_res,
        })
        team_history[away].append({
            "date": date,
            "points": pts_map[away_res],
            "goal_diff": ag - hg,
            "goals_scored": ag,
            "goals_conceded": hg,
            "result": away_res,
        })

    print(f"  Processed {len(df)}/{len(df)} matches (complete)\n")

    out_df = pd.DataFrame(rows)

    features = [
        "home_result_momentum", "home_score_momentum", "home_elo_momentum",
        "home_scoring_trend", "home_concession_trend", "home_streak",
        "away_result_momentum", "away_score_momentum", "away_elo_momentum",
        "away_scoring_trend", "away_concession_trend", "away_streak",
        "momentum_diff",
    ]

    print("=== Correlation with actual result (H=1.0, D=0.5, A=0.0) ===")
    for f in features:
        corr = out_df[f].corr(out_df["actual_result"])
        print(f"  {f:<35s}: {corr:+.4f}")

    print("\n=== Mean feature values: Home Win vs Away Win ===")
    hw = out_df[out_df["actual_result"] == 1.0]
    aw = out_df[out_df["actual_result"] == 0.0]
    print(f"  {'Feature':<35s}  {'HomeWin':>8}  {'AwayWin':>8}  {'Diff':>8}")
    print(f"  {'-' * 35}  {'-' * 8}  {'-' * 8}  {'-' * 8}")
    for f in features:
        hw_m = hw[f].mean()
        aw_m = aw[f].mean()
        print(f"  {f:<35s}  {hw_m:8.4f}  {aw_m:8.4f}  {hw_m - aw_m:+8.4f}")

    out_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "momentum_features.csv"))
    out_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(out_df)} rows to {out_path}")


if __name__ == "__main__":
    main()
