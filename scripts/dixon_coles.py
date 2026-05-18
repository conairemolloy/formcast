import os
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln

XI = 0.005       # temporal decay rate
MAX_GOALS = 10   # max goals per team in score matrix


def tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    """Dixon-Coles low-score correction factor (scalar)."""
    if x == 0 and y == 0:
        return 1 - lam * mu * rho
    if x == 0 and y == 1:
        return 1 + lam * rho
    if x == 1 and y == 0:
        return 1 + mu * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0


def _poisson_logpmf(k: np.ndarray, lam: np.ndarray) -> np.ndarray:
    return k * np.log(np.maximum(lam, 1e-10)) - lam - gammaln(k + 1)


def build_neg_log_likelihood(home_idx, away_idx, hg, ag, weights, n_teams):
    m00 = (hg == 0) & (ag == 0)
    m01 = (hg == 0) & (ag == 1)
    m10 = (hg == 1) & (ag == 0)
    m11 = (hg == 1) & (ag == 1)

    def neg_ll(params):
        # Reparameterise: attacks[0] = -sum(attacks[1:]) enforces mean(attacks) = 0
        free_atk = params[:n_teams - 1]
        atk = np.concatenate([[-np.sum(free_atk)], free_atk])
        dfc = params[n_teams - 1: 2 * n_teams - 1]
        home_adv = params[2 * n_teams - 1]
        rho = params[2 * n_teams]

        lam = np.exp(atk[home_idx] + dfc[away_idx] + home_adv)
        mu = np.exp(atk[away_idx] + dfc[home_idx])

        ll = _poisson_logpmf(hg, lam) + _poisson_logpmf(ag, mu)

        tau_vals = np.ones(len(hg))
        tau_vals[m00] = 1 - lam[m00] * mu[m00] * rho
        tau_vals[m01] = 1 + lam[m01] * rho
        tau_vals[m10] = 1 + mu[m10] * rho
        tau_vals[m11] = 1 - rho

        if np.any(tau_vals <= 0):
            return 1e10

        ll += np.log(tau_vals)
        return -np.sum(weights * ll)

    return neg_ll


def predict_outcome_probs(
    home_idx: np.ndarray,
    away_idx: np.ndarray,
    attacks: np.ndarray,
    defences: np.ndarray,
    home_adv: float,
    rho: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lam = np.exp(attacks[home_idx] + defences[away_idx] + home_adv)
    mu = np.exp(attacks[away_idx] + defences[home_idx])

    goals = np.arange(MAX_GOALS + 1)
    home_pmf = np.exp(_poisson_logpmf(goals[None, :], lam[:, None]))  # (n, 11)
    away_pmf = np.exp(_poisson_logpmf(goals[None, :], mu[:, None]))   # (n, 11)

    score_matrix = home_pmf[:, :, None] * away_pmf[:, None, :]  # (n, 11, 11)

    # Apply tau correction to low-score cells
    score_matrix[:, 0, 0] *= (1 - lam * mu * rho)
    score_matrix[:, 0, 1] *= (1 + lam * rho)
    score_matrix[:, 1, 0] *= (1 + mu * rho)
    score_matrix[:, 1, 1] *= (1 - rho)

    i_idx = goals[:, None]  # rows = home goals
    j_idx = goals[None, :]  # cols = away goals

    p_home = np.sum(score_matrix * (i_idx > j_idx), axis=(1, 2))
    p_draw = np.sum(score_matrix * (i_idx == j_idx), axis=(1, 2))
    p_away = np.sum(score_matrix * (i_idx < j_idx), axis=(1, 2))

    return p_home, p_draw, p_away


def main() -> None:
    base = os.path.dirname(__file__)
    results_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "results.csv"))

    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])
    df["home_goals"] = df["home_goals"].astype(int)
    df["away_goals"] = df["away_goals"].astype(int)

    ref_date = df["match_date"].max()
    df["days_since"] = (ref_date - df["match_date"]).dt.days.astype(int)

    teams = sorted(set(df["home_team"]).union(set(df["away_team"])))
    team_idx = {t: i for i, t in enumerate(teams)}
    n_teams = len(teams)

    print(f"Loaded {len(df):,} matches | {n_teams} teams across {df['league'].nunique()} leagues")
    print(f"Date range: {df['match_date'].min().date()} → {df['match_date'].max().date()}\n")

    home_idx = np.array([team_idx[t] for t in df["home_team"]])
    away_idx = np.array([team_idx[t] for t in df["away_team"]])
    hg = df["home_goals"].values
    ag = df["away_goals"].values
    weights = np.exp(-XI * df["days_since"].values)

    neg_ll = build_neg_log_likelihood(home_idx, away_idx, hg, ag, weights, n_teams)

    # Parameter layout: [free_attacks (n_teams-1), defences (n_teams), home_adv, rho]
    x0 = np.zeros(2 * n_teams + 1)
    x0[2 * n_teams - 1] = 0.1   # home_adv
    x0[2 * n_teams] = -0.1      # rho

    iteration = [0]

    def callback(params):
        iteration[0] += 1
        if iteration[0] % 50 == 0:
            print(f"  iter {iteration[0]:4d} | neg log-likelihood: {neg_ll(params):.4f}", flush=True)

    print("Optimising (L-BFGS-B)...")
    result = minimize(
        neg_ll,
        x0,
        method="L-BFGS-B",
        callback=callback,
        options={"maxiter": 5000, "ftol": 1e-10, "gtol": 1e-6, "disp": True},
    )

    status = "converged" if result.success else "did not converge"
    print(f"\nOptimisation {status}: {result.message}")
    print(f"Final neg log-likelihood: {result.fun:.4f}")

    params = result.x
    free_atk = params[:n_teams - 1]
    attacks = np.concatenate([[-np.sum(free_atk)], free_atk])
    defences = params[n_teams - 1: 2 * n_teams - 1]
    home_adv = params[2 * n_teams - 1]
    rho = params[2 * n_teams]

    print(f"\nHome advantage : {home_adv:.4f}")
    print(f"Rho            : {rho:.4f}")

    attack_df = (
        pd.DataFrame({"team": teams, "attack": attacks})
        .sort_values("attack", ascending=False)
        .reset_index(drop=True)
    )
    defence_df = (
        pd.DataFrame({"team": teams, "defence": defences})
        .sort_values("defence")
        .reset_index(drop=True)
    )

    print("\nTop 10 attack ratings:")
    print(attack_df.head(10).round(4).to_string(index=False))
    print("\nTop 10 defence ratings (most negative = best):")
    print(defence_df.head(10).round(4).to_string(index=False))

    p_home, p_draw, p_away = predict_outcome_probs(
        home_idx, away_idx, attacks, defences, home_adv, rho
    )

    predicted = np.where(
        (p_home >= p_draw) & (p_home >= p_away), "H",
        np.where(p_draw >= p_away, "D", "A"),
    )
    actual = df["result"].values
    correct = (predicted == actual).astype(int)

    actual_home_score = np.where(actual == "H", 1.0, np.where(actual == "D", 0.5, 0.0))
    hit_rate = correct.mean()
    brier = np.mean((p_home - actual_home_score) ** 2)

    print(f"\nHit rate   : {hit_rate:.4f}  ({hit_rate * 100:.1f}%)")
    print(f"Brier score: {brier:.6f}")

    pred_df = pd.DataFrame({
        "match_date": df["match_date"],
        "league": df["league"],
        "home_team": df["home_team"],
        "away_team": df["away_team"],
        "p_home": np.round(p_home, 4),
        "p_draw": np.round(p_draw, 4),
        "p_away": np.round(p_away, 4),
        "predicted_result": predicted,
        "actual_result": actual,
        "correct": correct,
    })

    out_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "dc_predictions.csv"))
    pred_df.to_csv(out_path, index=False)
    print(f"\nSaved predictions to {out_path}")


if __name__ == "__main__":
    main()
