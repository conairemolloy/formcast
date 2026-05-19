"""
Bayesian hierarchical model for soccer match prediction.

Partial pooling: alpha_i ~ Normal(league_mean[league_i], SIGMA_LEAGUE)
MAP estimation via L-BFGS-B.  Walk-forward refit every 100 matches on a
rolling 2-season (~730-day) window.  No PyMC required — pure scipy/numpy.

sigma_league is fixed at SIGMA_LEAGUE (0.5 log-odds) rather than jointly
optimised, because MAP estimation of hierarchical variances collapses to
sigma≈0 when many teams have sparse match histories — a well-known
degenerate mode that makes all team alphas identical.  Fixing sigma at a
realistic value (half of a typical EPL top-vs-bottom log-odds gap) keeps
the partial-pooling prior informative without over-regularising.

Parameter vector layout (packed):
  [alpha_0 … alpha_{T-1} | home_adv | lm_0 … lm_{L-1}]
  where T = n_teams, L = n_leagues.
"""
import math
import os
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COLD_START    = 200
REFIT_EVERY   = 100
WINDOW_DAYS   = 730   # ~2 soccer seasons
SIGMA_LEAGUE  = 0.5   # fixed within-league SD (log-odds); see module docstring

EPS           = 1e-9
STARTING_ELO  = 1500.0
ELO_K         = 16
ELO_HA        = 50


# ---------------------------------------------------------------------------
# Elo helpers (baseline only — not part of Bayes model)
# ---------------------------------------------------------------------------

def _elo_exp(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def _elo_mov(hg: int, ag: int) -> float:
    return min(2.0, 1.0 + math.log(1.0 + abs(hg - ag)) / math.log(10.0))


# ---------------------------------------------------------------------------
# Parameter packing helpers
# ---------------------------------------------------------------------------

def _unpack(params: np.ndarray, n_teams: int, n_leagues: int):
    alpha    = params[:n_teams]
    home_adv = params[n_teams]
    lg_means = params[n_teams + 1 : n_teams + 1 + n_leagues]
    return alpha, home_adv, lg_means


# ---------------------------------------------------------------------------
# Negative log posterior (vectorised, no Python loops over matches)
# ---------------------------------------------------------------------------

def neg_log_posterior(
    params: np.ndarray,
    n_teams: int,
    n_leagues: int,
    home_idx: np.ndarray,
    away_idx: np.ndarray,
    is_H: np.ndarray,
    is_A: np.ndarray,
    is_D: np.ndarray,
    team_league_idx: np.ndarray,
) -> float:
    alpha, home_adv, lg_means = _unpack(params, n_teams, n_leagues)

    # --- Log likelihood ---
    x = alpha[home_idx] - alpha[away_idx] + home_adv
    p = expit(x)

    ll  = np.dot(np.log(np.clip(p,       EPS, 1.0)), is_H)
    ll += np.dot(np.log(np.clip(1.0 - p, EPS, 1.0)), is_A)
    # Approximate draw likelihood: penalises lopsided predictions for draws
    draw_term = 1.0 - np.abs(2.0 * p - 1.0)
    ll += 0.5 * np.dot(np.log(np.clip(draw_term, EPS, 1.0)), is_D)

    # --- Log prior ---
    # alpha_i ~ N(league_mean[league_i], SIGMA_LEAGUE^2)  — partial pooling
    mu = lg_means[team_league_idx]
    lp  = -0.5 * np.sum(((alpha - mu) / SIGMA_LEAGUE) ** 2)

    # league_means ~ N(0, 1)
    lp += -0.5 * np.dot(lg_means, lg_means)

    # home_adv ~ N(0, 1)
    lp += -0.5 * home_adv * home_adv

    return -(ll + lp)


# ---------------------------------------------------------------------------
# MAP fit on a window DataFrame
# ---------------------------------------------------------------------------

def fit_map(
    window_df: pd.DataFrame,
    n_teams: int,
    n_leagues: int,
    team_idx: dict,
    team_league_idx: np.ndarray,
    x0: np.ndarray,
) -> np.ndarray:
    """Return MAP parameter vector; warm-starts from x0."""
    if len(window_df) == 0:
        return x0.copy()

    home_idx = np.array([team_idx[t] for t in window_df["home_team"]], dtype=np.intp)
    away_idx = np.array([team_idx[t] for t in window_df["away_team"]], dtype=np.intp)
    results  = window_df["result"].values

    is_H = (results == "H").astype(np.float64)
    is_A = (results == "A").astype(np.float64)
    is_D = (results == "D").astype(np.float64)

    res = minimize(
        neg_log_posterior,
        x0,
        args=(n_teams, n_leagues, home_idx, away_idx, is_H, is_A, is_D, team_league_idx),
        method="L-BFGS-B",
        options={"maxiter": 300, "ftol": 1e-8, "gtol": 1e-6},
    )
    return res.x


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "results.csv")
    )

    df = pd.read_csv(data_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])
    print(f"Loaded {len(df):,} total matches")

    keep_seasons = {"2020-21", "2021-22", "2022-23", "2023-24", "2024-25"}
    df = df[df["season"].isin(keep_seasons)].reset_index(drop=True)
    print(f"Filtered to 5 seasons (2020-21 → 2024-25): {len(df):,} matches\n")

    # ------------------------------------------------------------------
    # Build global indices (fixed for the entire run)
    # ------------------------------------------------------------------
    all_teams   = sorted({t for col in ("home_team", "away_team") for t in df[col]})
    all_leagues = sorted(df["league"].unique())

    team_idx   = {t: i for i, t in enumerate(all_teams)}
    league_idx = {l: i for i, l in enumerate(all_leagues)}

    # Each team belongs to exactly one league in this dataset
    team_league: dict[str, str] = {}
    for _, row in df[["home_team", "away_team", "league"]].iterrows():
        team_league[row["home_team"]] = row["league"]
        team_league[row["away_team"]] = row["league"]

    n_teams   = len(all_teams)
    n_leagues = len(all_leagues)
    team_league_idx = np.array([league_idx[team_league[t]] for t in all_teams], dtype=np.intp)

    print(f"Teams: {n_teams} | Leagues: {n_leagues} | "
          f"Params: {n_teams + 1 + n_leagues} (sigma_league fixed at {SIGMA_LEAGUE})\n")

    # ------------------------------------------------------------------
    # Initial parameter vector: [alpha × n_teams | home_adv | league_means × n_leagues]
    # ------------------------------------------------------------------
    n_params        = n_teams + 1 + n_leagues
    params          = np.zeros(n_params)
    params[n_teams] = 0.1   # home_adv initial value

    # ------------------------------------------------------------------
    # Elo state (for baseline comparison)
    # ------------------------------------------------------------------
    elo: dict[str, float] = defaultdict(lambda: STARTING_ELO)

    # ------------------------------------------------------------------
    # Walk-forward loop
    # ------------------------------------------------------------------
    pred_rows = []
    n = len(df)

    for i in range(n):
        row  = df.iloc[i]
        date = row["match_date"]
        home = row["home_team"]
        away = row["away_team"]
        hg   = int(row["home_goals"])
        ag   = int(row["away_goals"])
        res  = row["result"]

        # Refit on rolling 2-season window every REFIT_EVERY matches
        if i >= COLD_START and (i - COLD_START) % REFIT_EVERY == 0:
            cutoff = date - pd.Timedelta(days=WINDOW_DAYS)
            window = df[(df["match_date"] >= cutoff) & (df["match_date"] < date)]
            params = fit_map(
                window, n_teams, n_leagues, team_idx, team_league_idx, params
            )

        # Record prediction for non-cold-start matches
        if i >= COLD_START:
            hi = team_idx[home]
            ai = team_idx[away]
            x  = params[hi] - params[ai] + params[n_teams]  # log-odds
            p_home = float(expit(x))

            # Classification via log-odds thresholds
            if x > 0.25:
                pred = "H"
            elif x < -0.25:
                pred = "A"
            else:
                pred = "D"

            # Elo baseline prediction (no margin — just better team wins)
            elo_exp = _elo_exp(elo[home] + ELO_HA, elo[away])
            elo_pred = "H" if elo_exp > 0.5 else "A"

            pred_rows.append({
                "match_date":       date,
                "league":           row["league"],
                "home_team":        home,
                "away_team":        away,
                "p_home_bayes":     p_home,
                "actual_result":    res,
                "predicted_result": pred,
                "correct":          int(pred == res),
                "elo_pred":         elo_pred,
                "elo_correct":      int(elo_pred == res),
            })

        # Update Elo state (always — warms up baseline before cold start ends)
        home_exp = _elo_exp(elo[home] + ELO_HA, elo[away])
        hs  = 1.0 if res == "H" else (0.5 if res == "D" else 0.0)
        mov = _elo_mov(hg, ag)
        elo[home] += ELO_K * mov * (hs - home_exp)
        elo[away] += ELO_K * mov * (home_exp - hs)

        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1:,}/{n:,} matches...")

    print(f"  Processed {n:,}/{n:,} matches (complete)\n")

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    pred_df = pd.DataFrame(pred_rows)

    # Final alpha values from the last fit
    alpha_final, home_adv, lg_means = _unpack(params, n_teams, n_leagues)
    home_adv = float(home_adv)

    team_strength = (
        pd.DataFrame({
            "team":   all_teams,
            "alpha":  alpha_final,
            "league": [team_league[t] for t in all_teams],
        })
        .sort_values("alpha", ascending=False)
        .reset_index(drop=True)
    )

    print("=" * 58)
    print("TOP 15 TEAMS BY POSTERIOR ALPHA (final window)")
    print("=" * 58)
    for _, r in team_strength.head(15).iterrows():
        bar = "█" * max(0, int((r["alpha"] + 2.0) * 10))
        print(f"  {r['team']:<26s}  {r['alpha']:>+.4f}  {r['league']}")

    print(f"\n  Home advantage : {home_adv:+.4f} log-odds  "
          f"(P(home|equal) ≈ {float(expit(home_adv)):.3f})")
    print(f"  Sigma_league   : {SIGMA_LEAGUE:.4f}  (fixed)")

    print("\nLEAGUE STRENGTH RANKINGS (mean alpha)")
    for lg, lm in sorted(zip(all_leagues, lg_means), key=lambda x: -x[1]):
        n_lg = sum(1 for t in all_teams if team_league[t] == lg)
        mean_alpha = float(np.mean(alpha_final[[team_idx[t] for t in all_teams if team_league[t] == lg]]))
        print(f"  {lg:<12s}  league_mean={lm:+.4f}  team_mean_alpha={mean_alpha:+.4f}  ({n_lg} teams)")

    # Evaluation
    hit_bayes = pred_df["correct"].mean()
    hit_elo   = pred_df["elo_correct"].mean()
    actual_01 = pred_df["actual_result"].map({"H": 1.0, "D": 0.5, "A": 0.0})
    brier     = float(((pred_df["p_home_bayes"] - actual_01) ** 2).mean())

    dist = pred_df["predicted_result"].value_counts()
    actual_dist = pred_df["actual_result"].value_counts()

    print(f"\n{'=' * 58}")
    print(f"EVALUATION  ({len(pred_df):,} predictions, "
          f"{pred_df['match_date'].min().date()} → {pred_df['match_date'].max().date()})")
    print(f"{'=' * 58}")
    print(f"  {'Model':<22s}  {'Hit Rate':>9}  {'Brier':>9}")
    print(f"  {'-' * 44}")
    print(f"  {'Bayesian MAP':<22s}  {hit_bayes:>9.4f}  {brier:>9.6f}")
    print(f"  {'Elo baseline':<22s}  {hit_elo:>9.4f}  {'—':>9}")
    print(f"\n  Bayesian vs Elo: {hit_bayes - hit_elo:+.4f} hit rate")
    print(f"\n  Predicted distribution: H={dist.get('H',0):,}  D={dist.get('D',0):,}  A={dist.get('A',0):,}")
    print(f"  Actual distribution:    H={actual_dist.get('H',0):,}  D={actual_dist.get('D',0):,}  A={actual_dist.get('A',0):,}")
    print("=" * 58)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    out_cols = [
        "match_date", "league", "home_team", "away_team",
        "p_home_bayes", "actual_result", "predicted_result", "correct",
    ]
    out_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "bayesian_predictions.csv")
    )
    pred_df[out_cols].to_csv(out_path, index=False)
    print(f"\nSaved {len(pred_df):,} predictions → {out_path}")


if __name__ == "__main__":
    main()
