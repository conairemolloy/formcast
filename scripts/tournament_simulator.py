#!/usr/bin/env python3
"""
Monte Carlo tournament simulator for the top 5 European soccer leagues.

Simulates remaining 2024-25 matches using Elo-based H/D/A probabilities.
Elo is updated after each simulated match (K=16, home advantage=50 pts).

Draw probability model:
    raw_p_home = 1 / (1 + 10^(-(elo_diff + 50) / 400))
    p_draw     = 1 - |2 * raw_p_home - 1| * 0.8
    p_home     = raw_p_home * (1 - p_draw)
    p_away     = (1 - raw_p_home) * (1 - p_draw)
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd

# ── Configuration ─────────────────────────────────────────────────────────────
TODAY = "2026-05-20"
N_SIMS = 100_000
K = 16          # Elo K-factor
HOME_ADV = 50   # Home advantage in Elo points
DEFAULT_ELO = 1500

LEAGUES = ["EPL", "LaLiga", "SerieA", "Bundesliga", "Ligue1"]
LEAGUE_SIZES = {
    "EPL": 20, "LaLiga": 20, "SerieA": 20, "Bundesliga": 18, "Ligue1": 18,
}
RELEGATION_SPOTS = 3
TOP_CL_SPOTS = 4
TOP_EUROPE_SPOTS = 6


# ── Elo math ──────────────────────────────────────────────────────────────────
def match_probs(
    h_elo: np.ndarray, a_elo: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (p_home, p_draw, p_away, raw_p_home) — all same shape as inputs."""
    raw_p = 1.0 / (1.0 + 10.0 ** (-(h_elo - a_elo + HOME_ADV) / 400.0))
    p_draw = 1.0 - np.abs(2.0 * raw_p - 1.0) * 0.8
    rem = 1.0 - p_draw
    return raw_p * rem, p_draw, (1.0 - raw_p) * rem, raw_p


# ── Core simulation ───────────────────────────────────────────────────────────
def simulate_season(
    current_pts: np.ndarray,
    current_gd: np.ndarray,
    current_elo: np.ndarray,
    remaining: list[tuple[int, int]],
) -> np.ndarray:
    """
    Vectorised Monte Carlo simulation of remaining matches.

    Processes matches sequentially so Elo updates propagate, but runs all
    N_SIMS trials in parallel via numpy broadcasting on each match.

    Parameters
    ----------
    current_pts, current_gd, current_elo : shape (T,)
    remaining : list of (home_team_idx, away_team_idx)

    Returns
    -------
    ranks : ndarray (N_SIMS, T), 1-based final league positions
    """
    T = len(current_pts)
    pts = np.tile(current_pts.astype(np.float32), (N_SIMS, 1))   # (N, T)
    gd  = np.tile(current_gd.astype(np.float32),  (N_SIMS, 1))   # (N, T)
    elo = np.tile(current_elo.astype(np.float32), (N_SIMS, 1))   # (N, T)

    for h_idx, a_idx in remaining:
        p_h, p_d, _p_a, raw_ph = match_probs(elo[:, h_idx], elo[:, a_idx])

        rand     = np.random.random(N_SIMS).astype(np.float32)
        home_win = rand < p_h
        away_win = rand >= (p_h + p_d)
        draw     = ~home_win & ~away_win

        pts[:, h_idx] += 3.0 * home_win + draw
        pts[:, a_idx] += 3.0 * away_win + draw

        # GD proxy: ±1.5 per decisive match
        gd[:, h_idx] += 1.5 * home_win - 1.5 * away_win
        gd[:, a_idx] += 1.5 * away_win - 1.5 * home_win

        # Elo update (K=16)
        actual = home_win.astype(np.float32) + 0.5 * draw
        delta  = K * (actual - raw_ph)
        elo[:, h_idx] += delta
        elo[:, a_idx] -= delta

    # Rank teams: higher points → lower rank number; GD as tiebreaker
    scores = pts * 1000.0 + gd                # (N, T)
    order  = np.argsort(-scores, axis=1)      # (N, T) — team index at each position
    ranks  = np.argsort(order, axis=1) + 1   # (N, T) — 1-based rank per team
    return ranks


# ── Statistics ────────────────────────────────────────────────────────────────
def compute_stats(ranks: np.ndarray, league_size: int) -> dict[str, np.ndarray]:
    """Return per-team simulation stats. Each value is an array of shape (T,)."""
    n_teams = ranks.shape[1]

    # rank_counts[t, r] = number of sims where team t finished in position r
    rank_counts = np.zeros((n_teams, league_size + 1), dtype=np.int32)
    for t in range(n_teams):
        rank_counts[t] = np.bincount(ranks[:, t], minlength=league_size + 1)

    rng = np.arange(1, league_size + 1, dtype=np.float32)
    rel_start = league_size - RELEGATION_SPOTS + 1  # first relegation position (1-based)

    return {
        "win_pct":        rank_counts[:, 1] / N_SIMS * 100.0,
        "top4_pct":       rank_counts[:, 1 : TOP_CL_SPOTS + 1].sum(1) / N_SIMS * 100.0,
        "top6_pct":       rank_counts[:, 1 : TOP_EUROPE_SPOTS + 1].sum(1) / N_SIMS * 100.0,
        "relegation_pct": rank_counts[:, rel_start : league_size + 1].sum(1) / N_SIMS * 100.0,
        "modal_position": np.argmax(rank_counts[:, 1:], axis=1) + 1,
        "mean_position":  (rank_counts[:, 1:].astype(np.float32) @ rng) / N_SIMS,
    }


# ── Display ───────────────────────────────────────────────────────────────────
def print_table(
    league: str,
    teams: list[str],
    pts: np.ndarray,
    gd: np.ndarray,
    stats: dict[str, np.ndarray],
) -> None:
    """Print a formatted league simulation summary sorted by current standings."""
    order = np.argsort(-(pts * 1000.0 + gd))
    width = 72
    hdr_fmt = "{:<4} {:<22} {:>4}  {:>5}  {:>6}  {:>6}  {:>6}  {:>7}"
    row_fmt = "{:<4} {:<22} {:>4}  {:>+5}  {:>6}  {:>6}  {:>6}  {:>7}"

    print(f"\n{'─' * width}")
    print(f"  {league} 2024-25  |  N={N_SIMS:,} Monte Carlo simulations")
    print(f"{'─' * width}")
    print(hdr_fmt.format("Pos", "Team", "Pts", "GD", "Win%", "Top4%", "Top6%", "Rel%"))
    print(f"{'─' * width}")

    for rank, idx in enumerate(order, 1):
        print(row_fmt.format(
            rank,
            teams[idx][:22],
            int(pts[idx]),
            int(gd[idx]),
            f"{stats['win_pct'][idx]:.1f}",
            f"{stats['top4_pct'][idx]:.1f}",
            f"{stats['top6_pct'][idx]:.1f}",
            f"{stats['relegation_pct'][idx]:.1f}",
        ))
    print(f"{'─' * width}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    np.random.seed(42)

    base = Path(__file__).parent.parent
    elo_df     = pd.read_csv(base / "data/processed/elo_ratings.csv")
    results_df = pd.read_csv(base / "data/processed/results.csv")

    elo_lookup = dict(zip(elo_df["team"], elo_df["elo_rating"]))
    all_rows: list[dict] = []

    for league in LEAGUES:
        league_size = LEAGUE_SIZES[league]
        print(f"\n[{league}] Loading 2024-25 season data...", flush=True)
        t0 = time.perf_counter()

        season_df = results_df[
            (results_df["season"] == "2024-25") & (results_df["league"] == league)
        ].copy()

        # Played = result recorded AND date on or before today
        played    = season_df[
            season_df["result"].notna() & (season_df["match_date"] <= TODAY)
        ]
        remaining = season_df[
            (season_df["match_date"] > TODAY) | season_df["result"].isna()
        ]

        # Enumerate teams (stable sort for reproducibility)
        teams   = sorted(set(season_df["home_team"]) | set(season_df["away_team"]))
        team_ix = {t: i for i, t in enumerate(teams)}
        T       = len(teams)

        # Build current standings from played matches
        pts = np.zeros(T, dtype=np.float64)
        gd  = np.zeros(T, dtype=np.float64)

        for row in played.itertuples(index=False):
            h = team_ix[row.home_team]
            a = team_ix[row.away_team]
            gd_diff = float(row.home_goals) - float(row.away_goals)
            gd[h] += gd_diff
            gd[a] -= gd_diff
            if row.result == "H":
                pts[h] += 3
            elif row.result == "D":
                pts[h] += 1
                pts[a] += 1
            else:  # "A"
                pts[a] += 3

        # Elo ratings (fall back to DEFAULT_ELO for unknown teams)
        elo = np.array([elo_lookup.get(t, DEFAULT_ELO) for t in teams], dtype=np.float64)

        # Remaining matches as index pairs
        rem_list = [
            (team_ix[row.home_team], team_ix[row.away_team])
            for row in remaining.itertuples(index=False)
        ]

        n_played = len(played)
        n_rem    = len(rem_list)
        print(
            f"[{league}] {n_played} played, {n_rem} remaining — "
            f"running {N_SIMS:,} simulations...",
            flush=True,
        )

        ranks = simulate_season(pts, gd, elo, rem_list)
        stats = compute_stats(ranks, league_size)

        elapsed = time.perf_counter() - t0
        print(f"[{league}] Done in {elapsed:.1f}s", flush=True)

        print_table(league, teams, pts, gd, stats)

        for t, team in enumerate(teams):
            all_rows.append({
                "league":          league,
                "team":            team,
                "current_pts":     int(pts[t]),
                "current_gd":      int(gd[t]),
                "win_pct":         round(float(stats["win_pct"][t]), 2),
                "top4_pct":        round(float(stats["top4_pct"][t]), 2),
                "top6_pct":        round(float(stats["top6_pct"][t]), 2),
                "relegation_pct":  round(float(stats["relegation_pct"][t]), 2),
                "modal_position":  int(stats["modal_position"][t]),
                "mean_position":   round(float(stats["mean_position"][t]), 2),
            })

    out_path = base / "data/processed/tournament_simulations.csv"
    pd.DataFrame(all_rows).to_csv(out_path, index=False)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
