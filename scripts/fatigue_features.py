import os
from collections import defaultdict
from datetime import timedelta

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Per-team signal computation
# ---------------------------------------------------------------------------

def _compute_fatigue(prior: list, match_date, season: str) -> dict:
    """
    Compute fatigue signals for one team at match_date using only prior matches
    (strict date < match_date).

    prior: list of {'date': Timestamp, 'season': str}, sorted ascending.
    """
    # 1. days_since_last_match
    if prior:
        days_rest = (match_date - prior[-1]["date"]).days
    else:
        days_rest = 14

    # 2–6. windowed match counts
    cutoff_21 = match_date - timedelta(days=21)
    cutoff_14 = match_date - timedelta(days=14)
    cutoff_7  = match_date - timedelta(days=7)

    matches_21d = sum(1 for h in prior if h["date"] > cutoff_21)
    matches_14d = sum(1 for h in prior if h["date"] > cutoff_14)
    matches_7d  = sum(1 for h in prior if h["date"] > cutoff_7)

    # 7. season_matches_played (prior matches in current season)
    season_matches = sum(1 for h in prior if h["season"] == season)

    # 8. days_since_season_start
    season_dates = [h["date"] for h in prior if h["season"] == season]
    days_since_start = (match_date - min(season_dates)).days if season_dates else 0

    return {
        "days_rest": days_rest,
        "matches_21d": matches_21d,
        "matches_14d": matches_14d,
        "matches_7d": matches_7d,
        "season_matches": season_matches,
        "days_since_start": days_since_start,
    }


def _fatigue_score(days_rest: int, matches_21d: int, asymmetry: float, home: bool) -> float:
    """
    Cumulative fatigue score (as negative number, worse = more negative).
    Asymmetry term is added from home team's perspective (+) and flipped for away (-).
    Normalised by dividing by 100.
    """
    score = 0.0
    if days_rest < 4:
        score -= 40.0
    if matches_21d >= 3:
        score -= 20.0 * (matches_21d - 2)
    score += asymmetry * 5.0 if home else -asymmetry * 5.0
    return score / 100.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "results.csv"))

    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    print(f"Loaded {len(df)} matches across {df['season'].nunique()} seasons\n")

    team_matches: dict[str, list] = defaultdict(list)   # team -> [{date, season}]
    rows = []

    for i, row in df.iterrows():
        if i > 0 and i % 2000 == 0:
            print(f"  Processed {i}/{len(df)} matches...")

        home      = row["home_team"]
        away      = row["away_team"]
        date      = row["match_date"]
        season    = row["season"]
        league    = row["league"]
        result    = row["result"]

        home_prior = [h for h in team_matches[home] if h["date"] < date]
        away_prior = [h for h in team_matches[away] if h["date"] < date]

        hf = _compute_fatigue(home_prior, date, season)
        af = _compute_fatigue(away_prior, date, season)

        asymmetry = float(np.clip(hf["days_rest"] - af["days_rest"], -10, 10))

        home_score = _fatigue_score(hf["days_rest"], hf["matches_21d"], asymmetry, home=True)
        away_score = _fatigue_score(af["days_rest"], af["matches_21d"], asymmetry, home=False)

        actual_result = 1.0 if result == "H" else (0.5 if result == "D" else 0.0)

        rows.append({
            "match_date":         date,
            "season":             season,
            "league":             league,
            "home_team":          home,
            "away_team":          away,
            "home_days_rest":     hf["days_rest"],
            "home_matches_21d":   hf["matches_21d"],
            "home_matches_7d":    hf["matches_7d"],
            "home_matches_14d":   hf["matches_14d"],
            "home_fatigue_score": round(home_score, 6),
            "home_season_matches":hf["season_matches"],
            "away_days_rest":     af["days_rest"],
            "away_matches_21d":   af["matches_21d"],
            "away_matches_7d":    af["matches_7d"],
            "away_matches_14d":   af["matches_14d"],
            "away_fatigue_score": round(away_score, 6),
            "away_season_matches":af["season_matches"],
            "rest_asymmetry":     asymmetry,
            "actual_result":      actual_result,
        })

        # Update history AFTER computing signals (no leakage)
        team_matches[home].append({"date": date, "season": season})
        team_matches[away].append({"date": date, "season": season})

    print(f"  Processed {len(df)}/{len(df)} matches (complete)\n")

    out_df = pd.DataFrame(rows)

    # -----------------------------------------------------------------------
    # 1. Correlations with actual_result
    # -----------------------------------------------------------------------
    features = [
        "home_days_rest", "home_matches_21d", "home_matches_7d", "home_matches_14d",
        "home_fatigue_score", "home_season_matches",
        "away_days_rest", "away_matches_21d", "away_matches_7d", "away_matches_14d",
        "away_fatigue_score", "away_season_matches",
        "rest_asymmetry",
    ]
    print("=== Correlation with actual result (H=1.0, D=0.5, A=0.0) ===")
    for f in features:
        corr = out_df[f].corr(out_df["actual_result"])
        print(f"  {f:<28s}: {corr:+.4f}")

    # -----------------------------------------------------------------------
    # 2. Mean days_rest by outcome
    # -----------------------------------------------------------------------
    print("\n=== Mean days rest by match outcome ===")
    hw = out_df[out_df["actual_result"] == 1.0]
    draws = out_df[out_df["actual_result"] == 0.5]
    aw = out_df[out_df["actual_result"] == 0.0]
    print(f"  Home wins  — home_days_rest: {hw['home_days_rest'].mean():.2f}  "
          f"away_days_rest: {hw['away_days_rest'].mean():.2f}")
    print(f"  Draws      — home_days_rest: {draws['home_days_rest'].mean():.2f}  "
          f"away_days_rest: {draws['away_days_rest'].mean():.2f}")
    print(f"  Away wins  — home_days_rest: {aw['home_days_rest'].mean():.2f}  "
          f"away_days_rest: {aw['away_days_rest'].mean():.2f}")

    # -----------------------------------------------------------------------
    # 3. Rest asymmetry → outcome analysis
    # -----------------------------------------------------------------------
    home_more_rested = out_df[out_df["rest_asymmetry"] > 0]
    away_more_rested = out_df[out_df["rest_asymmetry"] < 0]
    equal_rest       = out_df[out_df["rest_asymmetry"] == 0]

    def win_rate(subset, col_val):
        if len(subset) == 0:
            return float("nan")
        return (subset["actual_result"] == col_val).sum() / len(subset)

    print("\n=== Outcome rates by rest advantage ===")
    print(f"  {'Group':<28s}  {'n':>5}  {'HomeWin%':>9}  {'Draw%':>7}  {'AwayWin%':>9}")
    print(f"  {'-'*28}  {'-'*5}  {'-'*9}  {'-'*7}  {'-'*9}")
    for label, subset in [
        ("Home more rested (asym > 0)", home_more_rested),
        ("Equal rest (asym = 0)",        equal_rest),
        ("Away more rested (asym < 0)", away_more_rested),
    ]:
        hw_pct = win_rate(subset, 1.0) * 100
        d_pct  = win_rate(subset, 0.5) * 100
        aw_pct = win_rate(subset, 0.0) * 100
        print(f"  {label:<28s}  {len(subset):>5}  {hw_pct:>8.1f}%  {d_pct:>6.1f}%  {aw_pct:>8.1f}%")

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------
    out_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "fatigue_features.csv"))
    out_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(out_df)} rows to {out_path}")


if __name__ == "__main__":
    main()
