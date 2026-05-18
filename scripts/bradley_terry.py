import math
import os
import time

import numpy as np
import pandas as pd
from scipy.optimize import minimize

# --- BTL parameters ---
LAMBDA = 0.001          # L2 regularisation on betas
INITIAL_HOME_ADV = 0.1  # initial home advantage (Glicko-2 log scale)
WINDOW_WEEKS = 76       # rolling training window
COLD_START = 200        # skip first N matches (need enough data to fit)
REFIT_EVERY = 50        # refit BTL every N prediction matches

SCALE = 173.7178        # converts beta to Elo-style rating

# --- Elo comparison parameters (optimised via hyperparameter_search.py) ---
ELO_K = 16
ELO_HOME_ADV = 50.0
ELO_STARTING = 1500.0


# ---------------------------------------------------------------------------
# BTL core: negative log-likelihood + gradient (returned together for L-BFGS-B)
# ---------------------------------------------------------------------------

def _nll_and_grad(
    params: np.ndarray,
    home_idx: np.ndarray,
    away_idx: np.ndarray,
    scores: np.ndarray,
    n_teams: int,
    lam: float,
) -> tuple[float, np.ndarray]:
    betas = params[:n_teams]
    ha = params[n_teams]

    diff = betas[home_idx] - betas[away_idx] + ha

    # Numerically stable: log P(home) = -logaddexp(0, -diff)
    log_P = -np.logaddexp(0.0, -diff)
    log_1mP = -np.logaddexp(0.0, diff)

    ll = np.dot(scores, log_P) + np.dot(1.0 - scores, log_1mP)
    ll -= (lam / 2.0) * np.dot(betas, betas)

    # Gradient: P = sigmoid(diff), residual = score - P
    P = np.exp(log_P)
    residual = scores - P

    g_betas = (
        np.bincount(home_idx, weights=residual, minlength=n_teams)
        - np.bincount(away_idx, weights=residual, minlength=n_teams)
        - lam * betas
    )
    g_ha = residual.sum()

    return float(-ll), -np.concatenate([g_betas, [g_ha]])


# ---------------------------------------------------------------------------
# Single BTL fit on a window of matches
# ---------------------------------------------------------------------------

def fit_btl(
    window_df: pd.DataFrame,
    prev_betas: dict[str, float] | None = None,
    prev_ha: float | None = None,
    lam: float = LAMBDA,
) -> tuple[dict[str, float], float]:
    """Fit BTL on window_df. Returns (betas_dict, home_adv).

    betas are mean-centred after fitting (identifiability).
    Warm-starts from prev_betas/prev_ha when provided.
    """
    teams = sorted(set(window_df["home_team"]) | set(window_df["away_team"]))
    n_teams = len(teams)
    t_idx = {t: i for i, t in enumerate(teams)}

    home_idx = np.array([t_idx[t] for t in window_df["home_team"]], dtype=np.intp)
    away_idx = np.array([t_idx[t] for t in window_df["away_team"]], dtype=np.intp)
    scores = window_df["score_home"].values.astype(np.float64)

    # Warm start
    x0_betas = np.array([prev_betas.get(t, 0.0) for t in teams]) if prev_betas else np.zeros(n_teams)
    x0_ha = prev_ha if prev_ha is not None else INITIAL_HOME_ADV
    x0 = np.concatenate([x0_betas, [x0_ha]])

    result = minimize(
        _nll_and_grad, x0, jac=True, method="L-BFGS-B",
        args=(home_idx, away_idx, scores, n_teams, lam),
        options={"maxiter": 1000, "ftol": 1e-10, "gtol": 1e-7},
    )

    betas = result.x[:n_teams]
    betas -= betas.mean()   # centre for identifiability

    return {t: float(b) for t, b in zip(teams, betas)}, float(result.x[n_teams])


# ---------------------------------------------------------------------------
# Walk-forward prediction loop
# ---------------------------------------------------------------------------

def walk_forward(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float], float]:
    window_days = WINDOW_WEEKS * 7
    df = df.copy()
    df["score_home"] = df["result"].map({"H": 1.0, "D": 0.5, "A": 0.0})

    betas: dict[str, float] = {}
    home_adv: float = INITIAL_HOME_ADV
    elo: dict[str, float] = {}

    records: list[dict] = []
    n = len(df)
    predictions_made = 0

    for i, row in enumerate(df.itertuples(index=False)):
        home, away = row.home_team, row.away_team
        s_h = float(row.score_home)
        s_a = 1.0 - s_h

        # Elo update (always, for comparison output)
        home_r = elo.get(home, ELO_STARTING)
        away_r = elo.get(away, ELO_STARTING)
        elo_exp = 1.0 / (1.0 + 10.0 ** ((away_r - home_r - ELO_HOME_ADV) / 400.0))
        gd = int(row.home_goals) - int(row.away_goals)
        mov = min(2.0, 1.0 + math.log(1.0 + abs(gd)) / math.log(10.0))
        elo[home] = home_r + ELO_K * mov * (s_h - elo_exp)
        elo[away] = away_r + ELO_K * mov * (s_a - (1.0 - elo_exp))

        if i < COLD_START:
            continue

        # Refit BTL on prior window every REFIT_EVERY predictions
        if predictions_made % REFIT_EVERY == 0:
            cutoff = row.match_date - pd.Timedelta(days=window_days)
            window = df.iloc[:i]
            window = window[window["match_date"] >= cutoff]
            if len(window) >= 20:
                betas, home_adv = fit_btl(window, prev_betas=betas, prev_ha=home_adv)

        # Progress every 200 predictions
        if predictions_made % 200 == 0:
            print(f"  [{predictions_made:>5} / {n - COLD_START}]  "
                  f"match {i:>5}  ha={home_adv:.4f}  "
                  f"n_teams_in_window={len(betas)}")

        # Predict current match using last fitted betas
        b_h = betas.get(home, 0.0)
        b_a = betas.get(away, 0.0)
        p_home = 1.0 / (1.0 + math.exp(-(b_h - b_a + home_adv)))

        result = row.result
        predicted = "H" if p_home > 0.5 else "A"
        correct = int(predicted == result) if result != "D" else None

        records.append({
            "match_date": row.match_date,
            "league": row.league,
            "home_team": home,
            "away_team": away,
            "p_home_btl": round(p_home, 6),
            "actual_result": result,
            "predicted_result": predicted,
            "correct": correct,
            "_elo_exp": elo_exp,
            "_elo_pred": "H" if elo_exp > 0.5 else "A",
        })

        predictions_made += 1

    return pd.DataFrame(records), betas, home_adv


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(__file__)
    results_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "results.csv"))

    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])

    print(f"Loaded {len(df):,} matches | "
          f"{len(set(df['home_team']) | set(df['away_team']))} teams | "
          f"{df['league'].nunique()} leagues")
    print(f"Cold start: {COLD_START} matches | "
          f"Window: {WINDOW_WEEKS} weeks | Refit every: {REFIT_EVERY} matches\n")

    t0 = time.time()
    pred_df, last_betas, last_ha = walk_forward(df)
    elapsed = time.time() - t0
    print(f"\nWalk-forward complete in {elapsed:.1f}s\n")

    # Final full fit on all data for the ratings table
    print("Fitting final BTL on all data for ratings table...")
    df_all = df.copy()
    df_all["score_home"] = df_all["result"].map({"H": 1.0, "D": 0.5, "A": 0.0})
    final_betas, final_ha = fit_btl(df_all, prev_betas=last_betas, prev_ha=last_ha)

    # Build ratings table
    ratings_records = sorted(
        [
            {
                "team": team,
                "beta": round(beta, 6),
                "rating": round(beta * SCALE + 1500.0, 2),
            }
            for team, beta in final_betas.items()
        ],
        key=lambda r: r["rating"],
        reverse=True,
    )
    for rank, rec in enumerate(ratings_records, 1):
        rec["rank"] = rank
    ratings_df = pd.DataFrame(ratings_records)[["team", "beta", "rating", "rank"]]

    # --- Print top 15 by rating ---
    print("\n" + "=" * 55)
    print("TOP 15 TEAMS BY BTL RATING")
    print("=" * 55)
    print(f"  {'#':<3}  {'Team':<25}  {'Beta':>7}  {'Rating':>7}")
    print("  " + "-" * 47)
    for _, row in ratings_df.head(15).iterrows():
        print(f"  {int(row['rank']):<3}  {row['team']:<25}  "
              f"{row['beta']:>7.4f}  {row['rating']:>7.1f}")

    print(f"\n  Learned home advantage : {final_ha:.4f}  "
          f"({final_ha * SCALE:+.1f} Elo-equivalent pts)")

    # --- Metrics ---
    actual_hs = pred_df["actual_result"].map({"H": 1.0, "D": 0.5, "A": 0.0})

    non_draw = pred_df[pred_df["correct"].notna()]
    btl_hit = non_draw["correct"].mean()
    btl_brier = ((pred_df["p_home_btl"] - actual_hs) ** 2).mean()

    elo_nd = pred_df[pred_df["actual_result"] != "D"]
    elo_hit = (elo_nd["_elo_pred"] == elo_nd["actual_result"]).mean()
    elo_brier = ((pred_df["_elo_exp"] - actual_hs) ** 2).mean()

    print("\n" + "=" * 55)
    print("PREDICTION ACCURACY  (walk-forward holdout)")
    print("=" * 55)
    print(f"  Matches predicted : {len(pred_df):,}")
    print(f"  Non-draw matches  : {len(non_draw):,}")
    print(f"\n  {'Model':<10}  {'Hit Rate':>10}  {'Brier':>10}")
    print(f"  {'-' * 34}")
    print(f"  {'BTL':<10}  {btl_hit:>10.4f}  {btl_brier:>10.6f}")
    print(f"  {'Elo':<10}  {elo_hit:>10.4f}  {elo_brier:>10.6f}")
    print(f"\n  BTL vs Elo hit rate : {btl_hit - elo_hit:+.4f}")
    print(f"  BTL vs Elo Brier    : {btl_brier - elo_brier:+.6f}")
    print("=" * 55)

    # --- Save ---
    out_dir = os.path.normpath(os.path.join(base, "..", "data", "processed"))

    ratings_out = os.path.join(out_dir, "btl_ratings.csv")
    ratings_df.to_csv(ratings_out, index=False)
    print(f"\nSaved ratings to {ratings_out}")

    pred_cols = [
        "match_date", "league", "home_team", "away_team",
        "p_home_btl", "actual_result", "predicted_result", "correct",
    ]
    pred_out = os.path.join(out_dir, "btl_predictions.csv")
    pred_df[pred_cols].to_csv(pred_out, index=False)
    print(f"Saved predictions to {pred_out}")


if __name__ == "__main__":
    main()
