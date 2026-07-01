#!/usr/bin/env python3
"""
Monte Carlo simulator for FIFA World Cup 2026 knockout stage.

Bracket: 16 R32 ties (32 teams) in fixed bracket order.
Settled ties use real results; unsettled ties simulate forward using
Elo-based win probabilities (no draws — knockout goes to ET/pens).

Outputs:
  data/processed/worldcup_bracket_sims_v2.csv  — per-team advancement %
  data/processed/worldcup_match_probs_v2.csv   — per-tie win probabilities
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd

N_SIMS = 100_000
DEFAULT_ELO = 1500

# ── Bracket definition ────────────────────────────────────────────────────────
# 16 ties in bracket order: pairs (0,1), (2,3) ... (30,31) are R32 ties.
# Tie winners advance: tie i winner → slot i for the next round.
# Left half  (ties  1-8, slots  0-15): semifinal 1 side.
# Right half (ties 9-16, slots 16-31): semifinal 2 side.

BRACKET = [
    # ── Left half — SF1 side (matches 73-80) ──
    # Adjacent pairs meet in R16: (1,2)→M89, (3,4)→M90, then QF M97, then SF M101
    {"id": 1,  "team1": "Germany",              "team2": "Paraguay",               "date": "2026-06-29"},
    {"id": 2,  "team1": "France",               "team2": "Sweden",                 "date": "2026-07-01"},
    {"id": 3,  "team1": "South Africa",         "team2": "Canada",                 "date": "2026-06-28"},
    {"id": 4,  "team1": "Netherlands",          "team2": "Morocco",                "date": "2026-06-29"},
    {"id": 5,  "team1": "Portugal",             "team2": "Croatia",                "date": "2026-07-02"},
    {"id": 6,  "team1": "Spain",                "team2": "Austria",                "date": "2026-07-02"},
    {"id": 7,  "team1": "United States",        "team2": "Bosnia and Herzegovina", "date": "2026-07-01"},
    {"id": 8,  "team1": "Belgium",              "team2": "Senegal",                "date": "2026-07-01"},
    # ── Right half — SF2 side (matches 81-88) ──
    # Adjacent pairs meet in R16: (9,10)→M91, (11,12)→M92, (13,14)→M96, (15,16)→M95, then QF M99/M100, then SF M102
    {"id": 9,  "team1": "Brazil",               "team2": "Japan",                  "date": "2026-06-29"},
    {"id": 10, "team1": "Ivory Coast",          "team2": "Norway",                 "date": "2026-06-30"},
    {"id": 11, "team1": "Mexico",               "team2": "Ecuador",                "date": "2026-06-30"},
    {"id": 12, "team1": "England",              "team2": "DR Congo",               "date": "2026-07-01"},
    {"id": 13, "team1": "Argentina",            "team2": "Cape Verde",             "date": "2026-07-03"},
    {"id": 14, "team1": "Switzerland",          "team2": "Algeria",                "date": "2026-07-02"},
    {"id": 15, "team1": "Australia",            "team2": "Egypt",                  "date": "2026-07-03"},
    {"id": 16, "team1": "Colombia",             "team2": "Ghana",                  "date": "2026-07-03"},
]

# Round labels in progression order
ROUND_LABELS = ["r32", "r16", "qf", "sf", "final", "champion"]


# ── Settle ties from results data ─────────────────────────────────────────────

def resolve_settled_ties(bracket, results_df, shootouts_df):
    """
    For each bracket tie, check results_df for a completed FIFA World Cup match
    between the two teams on or after the tournament start date. Determine the
    winner (checking shootouts_df when the match ended level in regular time).

    Returns a dict mapping tie_id → {"winner": team_name, "score": "X-Y[*]"}.
    """
    ko_start = pd.Timestamp("2026-06-28")
    wc_mask = (
        (results_df["tournament"] == "FIFA World Cup") &
        (pd.to_datetime(results_df["date"]) >= ko_start)
    )
    ko_matches = results_df[wc_mask].copy()

    # Build a lookup: frozenset({home, away}) → row
    match_lookup = {}
    for _, row in ko_matches.iterrows():
        key = frozenset([row["home_team"], row["away_team"]])
        match_lookup[key] = row

    # Build shootout lookup: frozenset({home, away}) → winner
    shootout_lookup = {}
    if not shootouts_df.empty:
        so_2026 = shootouts_df[
            pd.to_datetime(shootouts_df["date"]) >= ko_start
        ]
        for _, row in so_2026.iterrows():
            key = frozenset([row["home_team"], row["away_team"]])
            shootout_lookup[key] = row["winner"]

    settled = {}
    for tie in bracket:
        key = frozenset([tie["team1"], tie["team2"]])
        if key not in match_lookup:
            continue
        row = match_lookup[key]
        result = row["result"]
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])

        if result == "H":
            winner = row["home_team"]
            score = f"{home_score}-{away_score}"
        elif result == "A":
            winner = row["away_team"]
            score = f"{home_score}-{away_score}"
        else:  # Draw in regular time — go to shootouts
            winner = shootout_lookup.get(key)
            score = f"{home_score}-{away_score} (pens)"

        if winner:
            settled[tie["id"]] = {"winner": winner, "score": score}

    return settled


# ── Monte Carlo simulation ────────────────────────────────────────────────────

def simulate(bracket, elo_lookup, settled, n_sims=N_SIMS):
    """
    Vectorised single-elimination Monte Carlo simulation.

    bracket  — list of 16 tie dicts in bracket order
    elo_lookup — {team_name: elo_float}
    settled  — {tie_id: {"winner": str, "score": str}}

    Returns:
        adv_counts  ndarray (32, 6) — sims reaching each of 6 rounds
        team_names  list[str]       — index → team name
    """
    team_names = []
    for tie in bracket:
        for t in (tie["team1"], tie["team2"]):
            if t not in team_names:
                team_names.append(t)

    n_teams = len(team_names)  # 32
    team_idx = {t: i for i, t in enumerate(team_names)}

    elo_arr = np.array(
        [elo_lookup.get(t, DEFAULT_ELO) for t in team_names], dtype=np.float32
    )
    # prob_matrix[i, j] = P(team i beats team j) in a knockout match (no draws)
    prob_matrix = 1.0 / (1.0 + 10.0 ** (-(elo_arr[:, None] - elo_arr[None, :]) / 400.0))

    # Initial field: (n_sims, 32) — each cell = team index at that bracket slot
    init_slots = np.array(
        [team_idx[t] for tie in bracket for t in (tie["team1"], tie["team2"])],
        dtype=np.int32,
    )
    field = np.tile(init_slots, (n_sims, 1))  # (N, 32)

    adv_counts = np.zeros((n_teams, 6), dtype=np.int64)
    adv_counts[:, 0] = n_sims  # all 32 teams start in R32

    for round_idx in range(5):  # R32→R16, R16→QF, QF→SF, SF→Final, Final→Champion
        n_matches = field.shape[1] // 2
        t1 = field[:, 0::2]  # (N, n_matches)
        t2 = field[:, 1::2]  # (N, n_matches)

        win_p = prob_matrix[t1, t2]  # (N, n_matches) via advanced indexing
        rand = np.random.random((n_sims, n_matches)).astype(np.float32)
        t1_wins = rand < win_p  # bool (N, n_matches)

        # Override R32 settled ties (round_idx == 0)
        if round_idx == 0:
            for tie in bracket:
                if tie["id"] in settled:
                    match_slot = tie["id"] - 1  # 0-indexed match position
                    winner_id = team_idx[settled[tie["id"]]["winner"]]
                    t1_wins[:, match_slot] = (winner_id == t1[0, match_slot])

        field = np.where(t1_wins, t1, t2)  # (N, n_matches)

        counts = np.bincount(field.flatten(), minlength=n_teams)
        adv_counts[:, round_idx + 1] = counts

    return adv_counts, team_names


# ── Elo-based R32 win probabilities ──────────────────────────────────────────

def compute_r32_probs(bracket, elo_lookup, settled):
    """Return per-tie Elo win probabilities and metadata for output CSV."""
    rows = []
    for tie in bracket:
        e1 = elo_lookup.get(tie["team1"], DEFAULT_ELO)
        e2 = elo_lookup.get(tie["team2"], DEFAULT_ELO)
        t1_win_p = 1.0 / (1.0 + 10.0 ** (-(e1 - e2) / 400.0))

        info = settled.get(tie["id"], {})
        rows.append({
            "round":         "r32",
            "tie_id":        tie["id"],
            "team1":         tie["team1"],
            "team2":         tie["team2"],
            "team1_elo":     round(e1, 2),
            "team2_elo":     round(e2, 2),
            "team1_win_pct": round(t1_win_p * 100, 2),
            "team2_win_pct": round((1 - t1_win_p) * 100, 2),
            "settled":       tie["id"] in settled,
            "winner":        info.get("winner", ""),
            "score":         info.get("score", ""),
            "date":          tie["date"],
            "bracket_half":  "left" if tie["id"] <= 8 else "right",
        })
    return rows


# ── Draw-side analysis ────────────────────────────────────────────────────────

def draw_side_analysis(bracket, elo_lookup, settled):
    """Compute aggregate Elo for each half, only counting surviving teams."""
    eliminated = set()
    for tie in bracket:
        info = settled.get(tie["id"])
        if info:
            loser = (
                tie["team2"] if info["winner"] == tie["team1"] else tie["team1"]
            )
            eliminated.add(loser)

    halves = {"left": [], "right": []}
    for tie in bracket:
        half = "left" if tie["id"] <= 8 else "right"
        for team in (tie["team1"], tie["team2"]):
            if team not in eliminated:
                halves[half].append({
                    "team": team,
                    "elo": round(elo_lookup.get(team, DEFAULT_ELO), 2),
                })

    results = {}
    for half, teams in halves.items():
        elos = [t["elo"] for t in teams]
        results[half] = {
            "teams": sorted(teams, key=lambda x: -x["elo"]),
            "avg_elo": round(sum(elos) / len(elos), 2) if elos else 0,
            "count": len(teams),
        }
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    np.random.seed(42)
    t0 = time.perf_counter()

    base = Path(__file__).parent.parent
    elo_df       = pd.read_csv(base / "data/processed/international_elo_ratings.csv")
    results_df   = pd.read_csv(base / "data/processed/international_results.csv")
    shootouts_df = pd.read_csv(base / "data/processed/international_shootouts.csv")

    elo_lookup  = dict(zip(elo_df["team"], elo_df["elo_rating"].astype(float)))
    conf_lookup = dict(zip(elo_df["team"], elo_df["confederation"]))

    # Auto-detect settled ties from results data
    settled = resolve_settled_ties(BRACKET, results_df, shootouts_df)
    print(f"Settled ties detected: {len(settled)}/16")
    for tid, info in sorted(settled.items()):
        print(f"  Tie {tid}: {info['winner']} ({info['score']})")

    # Per-tie R32 win probabilities
    match_rows = compute_r32_probs(BRACKET, elo_lookup, settled)
    match_df = pd.DataFrame(match_rows)
    match_path = base / "data/processed/worldcup_match_probs_v2.csv"
    match_df.to_csv(match_path, index=False)
    print(f"Match probabilities saved → {match_path}")

    # Monte Carlo simulation
    print(f"Running {N_SIMS:,} simulations...", flush=True)
    adv_counts, team_names = simulate(BRACKET, elo_lookup, settled, N_SIMS)

    # Assemble output dataframe
    sim_rows = []
    for i, team in enumerate(team_names):
        counts = adv_counts[i]
        sim_rows.append({
            "team":           team,
            "elo":            round(elo_lookup.get(team, DEFAULT_ELO), 2),
            "confederation":  conf_lookup.get(team, ""),
            "r32_pct":        round(counts[0] / N_SIMS * 100, 2),
            "r16_pct":        round(counts[1] / N_SIMS * 100, 2),
            "qf_pct":         round(counts[2] / N_SIMS * 100, 2),
            "sf_pct":         round(counts[3] / N_SIMS * 100, 2),
            "final_pct":      round(counts[4] / N_SIMS * 100, 2),
            "champion_pct":   round(counts[5] / N_SIMS * 100, 2),
        })

    sim_df = pd.DataFrame(sim_rows).sort_values("champion_pct", ascending=False)
    sim_path = base / "data/processed/worldcup_bracket_sims_v2.csv"
    sim_df.to_csv(sim_path, index=False)
    print(f"Bracket simulations saved → {sim_path}")

    # Print leaderboard
    elapsed = time.perf_counter() - t0
    print(f"\n{'─' * 72}")
    print(f"  WC 2026 Title Odds  |  {N_SIMS:,} Monte Carlo sims  |  {elapsed:.1f}s")
    print(f"{'─' * 72}")
    hdr = f"{'Team':<28} {'Elo':>6}  {'R16':>6}  {'QF':>6}  {'SF':>6}  {'Final':>6}  {'Win':>6}"
    print(hdr)
    print(f"{'─' * 72}")
    for row in sim_rows[:16]:
        print(
            f"{row['team']:<28} {row['elo']:>6.0f}  "
            f"{row['r16_pct']:>6.1f}  {row['qf_pct']:>6.1f}  "
            f"{row['sf_pct']:>6.1f}  {row['final_pct']:>6.1f}  "
            f"{row['champion_pct']:>6.1f}"
        )
    print(f"{'─' * 72}")


if __name__ == "__main__":
    main()
