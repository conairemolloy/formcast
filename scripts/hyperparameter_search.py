import os
import time

import numpy as np
import pandas as pd

STARTING_RATING = 1500
COLD_START = 50

K_VALUES = [16, 24, 32, 40, 48]
HOME_ADV_VALUES = [50, 75, 100, 125, 150]
MOV_CAP_VALUES = [1.5, 2.0, 2.5]


def run_backtest(
    home_teams: np.ndarray,
    away_teams: np.ndarray,
    home_goals: np.ndarray,
    away_goals: np.ndarray,
    results: np.ndarray,
    K: float,
    home_adv: float,
    mov_cap: float,
) -> tuple[float, float, int]:
    """Returns (brier, hit_rate, n_predictions)."""
    ratings: dict[str, float] = {}
    brier_sum = 0.0
    hits = 0
    non_draws = 0
    n = 0

    for i in range(len(home_teams)):
        home = home_teams[i]
        away = away_teams[i]

        home_r = ratings.get(home, float(STARTING_RATING))
        away_r = ratings.get(away, float(STARTING_RATING))

        home_exp = 1.0 / (1.0 + 10.0 ** ((away_r - home_r - home_adv) / 400.0))

        result = results[i]
        if result == "H":
            home_score, away_score, actual_hs = 1.0, 0.0, 1.0
        elif result == "D":
            home_score, away_score, actual_hs = 0.5, 0.5, 0.5
        else:
            home_score, away_score, actual_hs = 0.0, 1.0, 0.0

        gd = int(home_goals[i]) - int(away_goals[i])
        mov = min(mov_cap, 1.0 + np.log(1.0 + abs(gd)) / np.log(10.0))

        ratings[home] = home_r + K * mov * (home_score - home_exp)
        ratings[away] = away_r + K * mov * (away_score - (1.0 - home_exp))

        if i < COLD_START:
            continue

        brier_sum += (home_exp - actual_hs) ** 2
        n += 1

        if result != "D":
            predicted = "H" if home_exp > 0.5 else "A"
            hits += int(predicted == result)
            non_draws += 1

    brier = brier_sum / n if n > 0 else float("nan")
    hit_rate = hits / non_draws if non_draws > 0 else float("nan")
    return brier, hit_rate, n


def main() -> None:
    base = os.path.dirname(__file__)
    results_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "results.csv"))

    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])

    print(f"Loaded {len(df):,} matches")

    # Pull arrays once — avoids per-row attribute lookup inside the loop
    home_teams = df["home_team"].values
    away_teams = df["away_team"].values
    home_goals = df["home_goals"].values
    away_goals = df["away_goals"].values
    results = df["result"].values

    combos = [
        (K, ha, mc)
        for K in K_VALUES
        for ha in HOME_ADV_VALUES
        for mc in MOV_CAP_VALUES
    ]
    total = len(combos)
    print(f"Running {total} parameter combinations (cold_start={COLD_START})...\n")

    records = []
    t0 = time.time()

    for idx, (K, ha, mc) in enumerate(combos):
        brier, hit_rate, n_pred = run_backtest(
            home_teams, away_teams, home_goals, away_goals, results,
            K=K, home_adv=ha, mov_cap=mc,
        )
        records.append({"K": K, "home_advantage": ha, "mov_cap": mc,
                         "brier": brier, "hit_rate": hit_rate, "n_predictions": n_pred})

        if (idx + 1) % 10 == 0 or (idx + 1) == total:
            elapsed = time.time() - t0
            print(f"  [{idx + 1:>3}/{total}]  elapsed {elapsed:.1f}s  "
                  f"last: K={K} ha={ha} mc={mc}  brier={brier:.6f}  hit={hit_rate:.4f}")

    elapsed_total = time.time() - t0
    print(f"\nCompleted {total} combos in {elapsed_total:.1f}s")

    results_df = pd.DataFrame(records)

    print("\n" + "=" * 65)
    print("TOP 10 BY BRIER SCORE (lower is better)")
    print("=" * 65)
    top_brier = results_df.nsmallest(10, "brier").reset_index(drop=True)
    print(f"  {'#':<3}  {'K':>4}  {'home_adv':>8}  {'mov_cap':>7}  {'brier':>10}  {'hit_rate':>9}")
    print("  " + "-" * 48)
    for i, row in top_brier.iterrows():
        print(f"  {i + 1:<3}  {int(row.K):>4}  {int(row.home_advantage):>8}  "
              f"{row.mov_cap:>7.1f}  {row.brier:>10.6f}  {row.hit_rate:>9.4f}")

    print("\n" + "=" * 65)
    print("TOP 10 BY HIT RATE (higher is better)")
    print("=" * 65)
    top_hit = results_df.nlargest(10, "hit_rate").reset_index(drop=True)
    print(f"  {'#':<3}  {'K':>4}  {'home_adv':>8}  {'mov_cap':>7}  {'brier':>10}  {'hit_rate':>9}")
    print("  " + "-" * 48)
    for i, row in top_hit.iterrows():
        print(f"  {i + 1:<3}  {int(row.K):>4}  {int(row.home_advantage):>8}  "
              f"{row.mov_cap:>7.1f}  {row.brier:>10.6f}  {row.hit_rate:>9.4f}")

    best = top_brier.iloc[0]
    print("\n" + "=" * 65)
    print("BEST COMBINATION (by Brier score)")
    print("=" * 65)
    print(f"  K              : {int(best.K)}")
    print(f"  home_advantage : {int(best.home_advantage)}")
    print(f"  mov_cap        : {best.mov_cap}")
    print(f"  Brier score    : {best.brier:.6f}")
    print(f"  Hit rate       : {best.hit_rate:.4f}  ({best.hit_rate * 100:.1f}%)")
    print(f"  N predictions  : {int(best.n_predictions):,}")

    # Compare against baseline (K=32, ha=100, mc=2.0)
    baseline = results_df[
        (results_df["K"] == 32) &
        (results_df["home_advantage"] == 100) &
        (results_df["mov_cap"] == 2.0)
    ].iloc[0]
    print(f"\n  vs. baseline (K=32, ha=100, mc=2.0):")
    print(f"    Brier improvement : {baseline.brier - best.brier:+.6f}")
    print(f"    Hit rate change   : {best.hit_rate - baseline.hit_rate:+.4f}")
    print("=" * 65)

    out_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "hyperparam_results.csv"))
    results_df.to_csv(out_path, index=False)
    print(f"\nSaved full results to {out_path}")


if __name__ == "__main__":
    main()
