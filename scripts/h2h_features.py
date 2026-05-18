import os
from collections import defaultdict

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# H2H helpers
# ---------------------------------------------------------------------------

def _h2h_key(a: str, b: str) -> tuple:
    """Canonical key for a pair of teams (order-independent)."""
    return (min(a, b), max(a, b))


def _compute_h2h(records: list, home: str) -> dict:
    """
    Compute H2H features from all prior meetings between home and away team.
    records: list of {home, result, home_goals, away_goals}, oldest first.
    home: the current match's home team name.
    Goals / wins are always expressed from the *current* home team's perspective.
    """
    if not records:
        return {
            "h2h_home_wins":     0,
            "h2h_away_wins":     0,
            "h2h_draws":         0,
            "h2h_home_win_rate": 0.45,
            "h2h_goal_diff_avg": 0.0,
            "h2h_meetings":      0,
            "h2h_dominance":     0.0,
            "revenge_factor":    0,
        }

    recent = records[-10:]
    n = len(recent)
    hw = aw = dw = 0
    gd_total = 0.0

    for rec in recent:
        if rec["home"] == home:
            # Same sides as current match
            gd = rec["home_goals"] - rec["away_goals"]
            if rec["result"] == "H":
                hw += 1
            elif rec["result"] == "A":
                aw += 1
            else:
                dw += 1
        else:
            # Sides reversed — current home was the away team in this meeting
            gd = rec["away_goals"] - rec["home_goals"]
            if rec["result"] == "A":
                hw += 1   # current home won as the away team
            elif rec["result"] == "H":
                aw += 1   # current away won as the home team
            else:
                dw += 1
        gd_total += gd

    home_win_rate = hw / n
    dominance = home_win_rate - 0.45   # vs naive 45% baseline

    # Revenge: did current home team lose the most recent H2H meeting?
    last = records[-1]
    if last["home"] == home:
        revenge = 1 if last["result"] == "A" else 0
    else:
        revenge = 1 if last["result"] == "H" else 0

    return {
        "h2h_home_wins":     hw,
        "h2h_away_wins":     aw,
        "h2h_draws":         dw,
        "h2h_home_win_rate": round(home_win_rate, 6),
        "h2h_goal_diff_avg": round(gd_total / n, 6),
        "h2h_meetings":      n,
        "h2h_dominance":     round(dominance, 6),
        "revenge_factor":    revenge,
    }


# ---------------------------------------------------------------------------
# Situational helpers
# ---------------------------------------------------------------------------

def _compute_situational(history: list, season: str) -> dict:
    """
    Compute situational features from a team's prior match history.
    history already contains only prior matches (appended after each match).
    """
    # season subset
    season_prior = [h for h in history if h["season"] == season]
    season_position = len(season_prior)       # matches played this season so far
    is_early = 1 if season_position < 5 else 0

    # post_loss_bounce: did they lose their last match?
    post_loss = 1 if (history and history[-1]["result"] == "L") else 0

    # unbeaten run (W or D streak, reset on L), clip to 15
    unbeaten = 0
    for h in reversed(history):
        if h["result"] in ("W", "D"):
            unbeaten += 1
        else:
            break
    unbeaten = min(unbeaten, 15)

    return {
        "season_position": season_position,
        "is_early":        is_early,
        "post_loss":       post_loss,
        "unbeaten_run":    unbeaten,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "results.csv")
    )

    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    print(f"Loaded {len(df)} matches across {df['season'].nunique()} seasons\n")

    h2h_history: dict[tuple, list] = defaultdict(list)   # pair → [{home,result,...}]
    team_history: dict[str, list]  = defaultdict(list)   # team → [{result, season}]

    rows = []

    for i, row in df.iterrows():
        if i > 0 and i % 2000 == 0:
            print(f"  Processed {i}/{len(df)} matches...")

        home   = row["home_team"]
        away   = row["away_team"]
        date   = row["match_date"]
        season = row["season"]
        league = row["league"]
        hg     = int(row["home_goals"])
        ag     = int(row["away_goals"])
        result = row["result"]

        # ---- Compute features (state not yet updated) ----------------------

        key      = _h2h_key(home, away)
        h2h_feat = _compute_h2h(h2h_history[key], home)

        home_sit = _compute_situational(team_history[home], season)
        away_sit = _compute_situational(team_history[away], season)

        actual_result = 1.0 if result == "H" else (0.5 if result == "D" else 0.0)

        rows.append({
            "match_date":            date,
            "season":                season,
            "league":                league,
            "home_team":             home,
            "away_team":             away,
            "h2h_home_wins":         h2h_feat["h2h_home_wins"],
            "h2h_away_wins":         h2h_feat["h2h_away_wins"],
            "h2h_draws":             h2h_feat["h2h_draws"],
            "h2h_home_win_rate":     h2h_feat["h2h_home_win_rate"],
            "h2h_goal_diff_avg":     h2h_feat["h2h_goal_diff_avg"],
            "h2h_meetings":          h2h_feat["h2h_meetings"],
            "h2h_dominance":         h2h_feat["h2h_dominance"],
            "revenge_factor":        h2h_feat["revenge_factor"],
            "post_loss_bounce":      home_sit["post_loss"],
            "post_loss_bounce_away": away_sit["post_loss"],
            "season_position_proxy": home_sit["season_position"],
            "is_early_season":       home_sit["is_early"],
            "home_unbeaten_run":     home_sit["unbeaten_run"],
            "away_unbeaten_run":     away_sit["unbeaten_run"],
            "actual_result":         actual_result,
        })

        # ---- Update state AFTER computing features -------------------------

        if result == "D":
            home_res = away_res = "D"
        elif result == "H":
            home_res, away_res = "W", "L"
        else:
            home_res, away_res = "L", "W"

        h2h_history[key].append({
            "home":       home,
            "result":     result,
            "home_goals": hg,
            "away_goals": ag,
        })
        team_history[home].append({"result": home_res, "season": season})
        team_history[away].append({"result": away_res, "season": season})

    print(f"  Processed {len(df)}/{len(df)} matches (complete)\n")

    out_df = pd.DataFrame(rows)

    features = [
        "h2h_home_wins", "h2h_away_wins", "h2h_draws",
        "h2h_home_win_rate", "h2h_goal_diff_avg", "h2h_meetings",
        "h2h_dominance", "revenge_factor",
        "post_loss_bounce", "post_loss_bounce_away",
        "season_position_proxy", "is_early_season",
        "home_unbeaten_run", "away_unbeaten_run",
    ]

    # -----------------------------------------------------------------------
    # 1. Correlations
    # -----------------------------------------------------------------------
    print("=== Correlation with actual result (H=1.0, D=0.5, A=0.0) ===")
    for f in features:
        corr = out_df[f].corr(out_df["actual_result"])
        print(f"  {f:<28s}: {corr:+.4f}")

    # -----------------------------------------------------------------------
    # 2. Revenge factor analysis
    # -----------------------------------------------------------------------
    print("\n=== Revenge factor analysis ===")
    print(f"  {'Group':<28s}  {'n':>5}  {'HomeWin%':>9}  {'Draw%':>7}  {'AwayWin%':>9}")
    print(f"  {'-'*28}  {'-'*5}  {'-'*9}  {'-'*7}  {'-'*9}")
    for label, mask in [
        ("revenge_factor = 1", out_df["revenge_factor"] == 1),
        ("revenge_factor = 0", out_df["revenge_factor"] == 0),
    ]:
        sub = out_df[mask]
        n = len(sub)
        hw = (sub["actual_result"] == 1.0).sum() / n * 100
        d  = (sub["actual_result"] == 0.5).sum() / n * 100
        aw = (sub["actual_result"] == 0.0).sum() / n * 100
        print(f"  {label:<28s}  {n:>5}  {hw:>8.1f}%  {d:>6.1f}%  {aw:>8.1f}%")

    # -----------------------------------------------------------------------
    # 3. Post-loss bounce (home team)
    # -----------------------------------------------------------------------
    print("\n=== Post-loss bounce analysis (home team) ===")
    print(f"  {'Group':<28s}  {'n':>5}  {'HomeWin%':>9}  {'Draw%':>7}  {'AwayWin%':>9}")
    print(f"  {'-'*28}  {'-'*5}  {'-'*9}  {'-'*7}  {'-'*9}")
    for label, mask in [
        ("After home loss",  out_df["post_loss_bounce"] == 1),
        ("No prior loss",    out_df["post_loss_bounce"] == 0),
    ]:
        sub = out_df[mask]
        n = len(sub)
        hw = (sub["actual_result"] == 1.0).sum() / n * 100
        d  = (sub["actual_result"] == 0.5).sum() / n * 100
        aw = (sub["actual_result"] == 0.0).sum() / n * 100
        print(f"  {label:<28s}  {n:>5}  {hw:>8.1f}%  {d:>6.1f}%  {aw:>8.1f}%")

    # -----------------------------------------------------------------------
    # 4. H2H dominance
    # -----------------------------------------------------------------------
    print("\n=== H2H home win rate vs actual outcome ===")
    print(f"  {'Group':<32s}  {'n':>5}  {'HomeWin%':>9}  {'Draw%':>7}  {'AwayWin%':>9}")
    print(f"  {'-'*32}  {'-'*5}  {'-'*9}  {'-'*7}  {'-'*9}")
    slices = [
        ("h2h_home_win_rate > 0.6",  out_df["h2h_home_win_rate"] > 0.6),
        ("0.4 ≤ h2h_home_win_rate ≤ 0.6",
         (out_df["h2h_home_win_rate"] >= 0.4) & (out_df["h2h_home_win_rate"] <= 0.6)),
        ("h2h_home_win_rate < 0.4",  out_df["h2h_home_win_rate"] < 0.4),
        ("no H2H history",           out_df["h2h_meetings"] == 0),
    ]
    for label, mask in slices:
        sub = out_df[mask]
        n = len(sub)
        if n == 0:
            print(f"  {label:<32s}  {n:>5}  {'—':>9}  {'—':>7}  {'—':>9}")
            continue
        hw = (sub["actual_result"] == 1.0).sum() / n * 100
        d  = (sub["actual_result"] == 0.5).sum() / n * 100
        aw = (sub["actual_result"] == 0.0).sum() / n * 100
        print(f"  {label:<32s}  {n:>5}  {hw:>8.1f}%  {d:>6.1f}%  {aw:>8.1f}%")

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------
    out_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "h2h_features.csv")
    )
    out_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(out_df)} rows to {out_path}")


if __name__ == "__main__":
    main()
