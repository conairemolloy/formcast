import math
import os

import numpy as np
import pandas as pd

# --- Glicko-2 parameters ---
TAU = 0.5            # system volatility constraint
EPSILON = 1e-6       # Illinois algorithm convergence tolerance
INITIAL_RATING = 1500
INITIAL_RD = 200
INITIAL_SIGMA = 0.06
SCALE = 173.7178     # converts between Elo scale and Glicko-2 internal scale

INITIAL_MU = 0.0
INITIAL_PHI = INITIAL_RD / SCALE

HOME_ADV_G2 = 50.0 / SCALE  # home advantage in Glicko-2 scale (same 50 pts as Elo)

COLD_START = 50
INACTIVITY_DAYS = 30

# --- Elo comparison parameters (optimised via hyperparameter_search.py) ---
ELO_K = 16
ELO_HOME_ADV = 50
ELO_STARTING = 1500.0

# Output column order
PRED_COLS = [
    "match_date", "league", "home_team", "away_team",
    "home_rating", "away_rating", "home_RD", "away_RD",
    "home_expected", "actual_result", "predicted_result", "correct",
]


# ---------------------------------------------------------------------------
# Glicko-2 maths
# ---------------------------------------------------------------------------

def _g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / (math.pi * math.pi))


def _E(mu: float, mu_j: float, phi_j: float) -> float:
    """Expected score for a player with rating mu against opponent (mu_j, phi_j)."""
    return 1.0 / (1.0 + math.exp(-_g(phi_j) * (mu - mu_j)))


def _f_illinois(x: float, delta: float, phi: float, v: float, a: float) -> float:
    """Objective function for the Illinois sigma update (Glickman 2012, eq. 11)."""
    ex = math.exp(x)
    return (
        ex * (delta * delta - phi * phi - v - ex) / (2.0 * (phi * phi + v + ex) ** 2)
        - (x - a) / (TAU * TAU)
    )


def _update_sigma(sigma: float, phi: float, v: float, delta: float) -> float:
    """Illinois algorithm: find new volatility sigma' such that f(ln sigma'^2) = 0."""
    a = math.log(sigma * sigma)

    A = a
    if delta * delta > phi * phi + v:
        B = math.log(delta * delta - phi * phi - v)
    else:
        k = 1
        while _f_illinois(a - k * TAU, delta, phi, v, a) < 0.0:
            k += 1
        B = a - k * TAU

    f_A = _f_illinois(A, delta, phi, v, a)
    f_B = _f_illinois(B, delta, phi, v, a)

    while abs(B - A) > EPSILON:
        C = A + (A - B) * f_A / (f_B - f_A)
        f_C = _f_illinois(C, delta, phi, v, a)
        if f_C * f_B < 0.0:
            A, f_A = B, f_B
        else:
            f_A /= 2.0
        B, f_B = C, f_C

    return math.exp(A / 2.0)


def _glicko2_step(
    mu: float, phi: float, sigma: float,
    opp_phi: float, E_j: float, score: float,
) -> tuple[float, float, float]:
    """One Glicko-2 update for a single match (one opponent, one result).

    E_j must be pre-computed (including any home advantage adjustment).
    """
    E_safe = max(1e-7, min(1.0 - 1e-7, E_j))
    g_j = _g(opp_phi)

    v = 1.0 / (g_j * g_j * E_safe * (1.0 - E_safe))
    delta = v * g_j * (score - E_safe)

    sigma_new = _update_sigma(sigma, phi, v, delta)
    phi_star = math.sqrt(phi * phi + sigma_new * sigma_new)
    phi_new = 1.0 / math.sqrt(1.0 / (phi_star * phi_star) + 1.0 / v)
    mu_new = mu + phi_new * phi_new * g_j * (score - E_safe)

    return mu_new, phi_new, sigma_new


# ---------------------------------------------------------------------------
# Walk-forward processing
# ---------------------------------------------------------------------------

def run(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process all matches chronologically.

    Returns:
        pred_df   — per-match prediction records (from match COLD_START onward)
        ratings_df — final team ratings
    """
    # Glicko-2 state: team -> (mu, phi, sigma)
    g2: dict[str, tuple[float, float, float]] = {}
    last_played: dict[str, pd.Timestamp] = {}

    # Elo state (parallel, for comparison)
    elo: dict[str, float] = {}

    pred_records: list[dict] = []

    for i, row in enumerate(df.itertuples(index=False)):
        home, away = row.home_team, row.away_team
        date: pd.Timestamp = row.match_date
        result: str = row.result

        # Initialise unseen teams
        if home not in g2:
            g2[home] = (INITIAL_MU, INITIAL_PHI, INITIAL_SIGMA)
        if away not in g2:
            g2[away] = (INITIAL_MU, INITIAL_PHI, INITIAL_SIGMA)

        mu_h, phi_h, sigma_h = g2[home]
        mu_a, phi_a, sigma_a = g2[away]

        # --- Inactivity RD increase (applied before computing probabilities) ---
        if home in last_played:
            days = (date - last_played[home]).days
            if days > INACTIVITY_DAYS:
                phi_h = math.sqrt(phi_h * phi_h + sigma_h * sigma_h * days / 30.0)
        if away in last_played:
            days = (date - last_played[away]).days
            if days > INACTIVITY_DAYS:
                phi_a = math.sqrt(phi_a * phi_a + sigma_a * sigma_a * days / 30.0)

        # --- Expected scores (home advantage added to home team's mu) ---
        # E_h: probability home team "wins" (used for prediction and home update)
        # E_a: from away team's perspective (used for away update)
        E_h = _E(mu_h + HOME_ADV_G2, mu_a, phi_a)
        E_a = _E(mu_a, mu_h + HOME_ADV_G2, phi_h)

        # --- Outcome ---
        if result == "H":
            s_h, s_a = 1.0, 0.0
        elif result == "D":
            s_h, s_a = 0.5, 0.5
        else:
            s_h, s_a = 0.0, 1.0

        # --- Glicko-2 updates (both teams use pre-match values) ---
        mu_h_new, phi_h_new, sigma_h_new = _glicko2_step(mu_h, phi_h, sigma_h, phi_a, E_h, s_h)
        mu_a_new, phi_a_new, sigma_a_new = _glicko2_step(mu_a, phi_a, sigma_a, phi_h, E_a, s_a)

        g2[home] = (mu_h_new, phi_h_new, sigma_h_new)
        g2[away] = (mu_a_new, phi_a_new, sigma_a_new)
        last_played[home] = date
        last_played[away] = date

        # --- Parallel Elo update ---
        home_r = elo.get(home, ELO_STARTING)
        away_r = elo.get(away, ELO_STARTING)
        elo_exp = 1.0 / (1.0 + 10.0 ** ((away_r - home_r - ELO_HOME_ADV) / 400.0))
        gd = int(row.home_goals) - int(row.away_goals)
        mov = min(2.0, 1.0 + math.log(1.0 + abs(gd)) / math.log(10.0))
        elo[home] = home_r + ELO_K * mov * (s_h - elo_exp)
        elo[away] = away_r + ELO_K * mov * (s_a - (1.0 - elo_exp))

        if i < COLD_START:
            continue

        pred_records.append({
            "match_date": date,
            "league": row.league,
            "home_team": home,
            "away_team": away,
            "home_rating": round(mu_h * SCALE + INITIAL_RATING, 2),
            "away_rating": round(mu_a * SCALE + INITIAL_RATING, 2),
            "home_RD": round(phi_h * SCALE, 2),
            "away_RD": round(phi_a * SCALE, 2),
            "home_expected": round(E_h, 6),
            "actual_result": result,
            "predicted_result": "H" if E_h > 0.5 else "A",
            "correct": (int(("H" if E_h > 0.5 else "A") == result) if result != "D" else None),
            "_elo_exp": elo_exp,
            "_elo_pred": "H" if elo_exp > 0.5 else "A",
        })

    # Build final ratings table
    rating_records = [
        {
            "team": team,
            "rating": round(mu * SCALE + INITIAL_RATING, 2),
            "RD": round(phi * SCALE, 2),
            "sigma": round(sigma, 6),
            "mu": round(mu, 6),
            "phi": round(phi, 6),
        }
        for team, (mu, phi, sigma) in g2.items()
    ]

    return pd.DataFrame(pred_records), pd.DataFrame(rating_records)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(__file__)
    results_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "results.csv"))

    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])

    print(f"Loaded {len(df):,} matches across {df['league'].nunique()} leagues")
    print(f"Date range: {df['match_date'].min().date()} → {df['match_date'].max().date()}")
    print(f"Skipping first {COLD_START} matches (cold start)\n")

    pred_df, ratings_df = run(df)

    # --- Top 15 by rating ---
    top_rated = ratings_df.nlargest(15, "rating").reset_index(drop=True)
    print("=" * 52)
    print("TOP 15 TEAMS BY GLICKO-2 RATING")
    print("=" * 52)
    print(f"  {'#':<3}  {'Team':<25}  {'Rating':>7}  {'RD':>6}  {'σ':>7}")
    print("  " + "-" * 46)
    for i, row in top_rated.iterrows():
        print(f"  {i + 1:<3}  {row['team']:<25}  {row['rating']:>7.1f}  "
              f"{row['RD']:>6.1f}  {row['sigma']:>7.5f}")

    # --- Top 15 by certainty (lowest RD) ---
    most_certain = ratings_df.nsmallest(15, "RD").reset_index(drop=True)
    print("\n" + "=" * 52)
    print("TOP 15 TEAMS BY CERTAINTY (lowest RD)")
    print("=" * 52)
    print(f"  {'#':<3}  {'Team':<25}  {'Rating':>7}  {'RD':>6}  {'σ':>7}")
    print("  " + "-" * 46)
    for i, row in most_certain.iterrows():
        print(f"  {i + 1:<3}  {row['team']:<25}  {row['rating']:>7.1f}  "
              f"{row['RD']:>6.1f}  {row['sigma']:>7.5f}")

    # --- Metrics ---
    actual_hs = pred_df["actual_result"].map({"H": 1.0, "D": 0.5, "A": 0.0})

    non_draw = pred_df[pred_df["correct"].notna()]
    g2_hit = non_draw["correct"].mean()
    g2_brier = ((pred_df["home_expected"] - actual_hs) ** 2).mean()

    elo_non_draw = pred_df[pred_df["actual_result"] != "D"]
    elo_hit = (elo_non_draw["_elo_pred"] == elo_non_draw["actual_result"]).mean()
    elo_brier = ((pred_df["_elo_exp"] - actual_hs) ** 2).mean()

    print("\n" + "=" * 52)
    print("PREDICTION ACCURACY")
    print("=" * 52)
    print(f"  Matches predicted  : {len(pred_df):,}")
    print(f"  Non-draw matches   : {len(non_draw):,}")
    print(f"\n  {'Model':<12}  {'Hit Rate':>10}  {'Brier':>10}")
    print(f"  {'-' * 36}")
    print(f"  {'Glicko-2':<12}  {g2_hit:>10.4f}  {g2_brier:>10.6f}")
    print(f"  {'Elo':<12}  {elo_hit:>10.4f}  {elo_brier:>10.6f}")
    print(f"\n  G2 vs Elo hit rate : {g2_hit - elo_hit:+.4f}")
    print(f"  G2 vs Elo Brier    : {g2_brier - elo_brier:+.6f}")

    print(f"\n  RD range  : {ratings_df['RD'].min():.1f} – {ratings_df['RD'].max():.1f}")
    print(f"  σ  range  : {ratings_df['sigma'].min():.5f} – {ratings_df['sigma'].max():.5f}")
    print("=" * 52)

    # --- Save ---
    out_dir = os.path.normpath(os.path.join(base, "..", "data", "processed"))

    ratings_out = os.path.join(out_dir, "glicko2_ratings.csv")
    ratings_df.sort_values("rating", ascending=False).to_csv(ratings_out, index=False)
    print(f"\nSaved ratings to {ratings_out}")

    pred_out = os.path.join(out_dir, "glicko2_predictions.csv")
    pred_df[PRED_COLS].to_csv(pred_out, index=False)
    print(f"Saved predictions to {pred_out}")


if __name__ == "__main__":
    main()
