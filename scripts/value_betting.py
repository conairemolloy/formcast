"""
Betting intelligence system: EV, value identification, CLV, Kelly simulation,
accumulator builder.

Inputs:
  data/processed/ensemble_v2_predictions.csv  — model probabilities (holdout)
  data/processed/results.csv                  — closing odds + actual results

Outputs:
  data/processed/value_bets.csv
  data/processed/kelly_simulation.csv
  data/processed/accumulator_bets.csv
"""
import os
from itertools import combinations

import numpy as np
import pandas as pd

EDGE_THRESHOLD   = 0.05
STARTING_BANKROLL = 1_000.0


# ---------------------------------------------------------------------------
# 1. Load & join
# ---------------------------------------------------------------------------

def load_data(base: str) -> pd.DataFrame:
    pred_path    = os.path.normpath(os.path.join(base, "..", "data", "processed",
                                                 "ensemble_v2_predictions.csv"))
    results_path = os.path.normpath(os.path.join(base, "..", "data", "processed",
                                                 "results.csv"))

    preds   = pd.read_csv(pred_path,    parse_dates=["match_date"])
    results = pd.read_csv(results_path, parse_dates=["match_date"])

    df = preds.merge(
        results[["match_date", "home_team", "away_team", "league",
                 "home_odds", "draw_odds", "away_odds"]],
        on=["match_date", "home_team", "away_team"],
        how="left",
        suffixes=("", "_r"),
    )
    # Use the league from results if it overwrote; keep original
    if "league_r" in df.columns:
        df["league"] = df["league"].fillna(df["league_r"])
        df.drop(columns=["league_r"], inplace=True)

    df = df.dropna(subset=["home_odds", "draw_odds", "away_odds"])
    df = df.sort_values("match_date").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 2. EV, overround, edge
# ---------------------------------------------------------------------------

def add_market_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["imp_h"] = 1.0 / df["home_odds"]
    df["imp_d"] = 1.0 / df["draw_odds"]
    df["imp_a"] = 1.0 / df["away_odds"]
    df["overround"] = df["imp_h"] + df["imp_d"] + df["imp_a"]

    # Margin-adjusted implied probabilities
    df["imp_adj_h"] = df["imp_h"] / df["overround"]
    df["imp_adj_d"] = df["imp_d"] / df["overround"]
    df["imp_adj_a"] = df["imp_a"] / df["overround"]

    # EV = p_model * odds - 1
    df["ev_h"] = df["p_home"] * df["home_odds"] - 1.0
    df["ev_d"] = df["p_draw"] * df["draw_odds"] - 1.0
    df["ev_a"] = df["p_away"] * df["away_odds"] - 1.0

    # Edge = model prob − margin-adjusted implied
    df["edge_h"] = df["p_home"] - df["imp_adj_h"]
    df["edge_d"] = df["p_draw"] - df["imp_adj_d"]
    df["edge_a"] = df["p_away"] - df["imp_adj_a"]

    return df


# ---------------------------------------------------------------------------
# 3. Value bet extraction (long format)
# ---------------------------------------------------------------------------

def extract_value_bets(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        for outcome, p_col, odds_col, imp_col, edge_col, ev_col in [
            ("H", "p_home", "home_odds", "imp_h", "edge_h", "ev_h"),
            ("D", "p_draw", "draw_odds", "imp_d", "edge_d", "ev_d"),
            ("A", "p_away", "away_odds", "imp_a", "edge_a", "ev_a"),
        ]:
            edge = r[edge_col]
            if edge <= EDGE_THRESHOLD:
                continue

            p_model  = r[p_col]
            odds     = r[odds_col]
            imp      = r[imp_col]
            ev       = r[ev_col]
            kelly    = (p_model * odds - 1.0) / (odds - 1.0) if odds > 1.0 else 0.0
            won      = int(r["actual_result"] == outcome)
            clv      = float(np.log(p_model / imp)) if imp > 0 and p_model > 0 else 0.0

            rows.append({
                "match_date":    r["match_date"],
                "league":        r["league"],
                "home_team":     r["home_team"],
                "away_team":     r["away_team"],
                "outcome":       outcome,
                "p_model":       round(p_model, 4),
                "odds":          round(odds, 3),
                "implied_prob":  round(imp, 4),
                "edge":          round(edge, 4),
                "EV":            round(ev, 4),
                "kelly_fraction": round(kelly, 4),
                "half_kelly":    round(kelly / 2, 4),
                "actual_result": r["actual_result"],
                "won":           won,
                "profit_flat":   round((odds - 1.0) if won else -1.0, 4),
                "profit_kelly":  round((kelly / 2) * (odds - 1.0) if won else -(kelly / 2), 4),
                "clv":           round(clv, 4),
            })

    bets = pd.DataFrame(rows)
    bets = bets.sort_values("match_date").reset_index(drop=True)
    return bets


# ---------------------------------------------------------------------------
# 4. Kelly bankroll simulation
# ---------------------------------------------------------------------------

def kelly_simulation(bets: pd.DataFrame) -> pd.DataFrame:
    bankroll  = STARTING_BANKROLL
    sim_rows  = []

    for i, r in bets.iterrows():
        hk    = float(r["half_kelly"])
        odds  = float(r["odds"])
        won   = bool(r["won"])

        if hk <= 0.0:          # skip negative-EV bets (shouldn't occur with edge > 5%)
            continue

        stake  = hk * bankroll
        profit = stake * (odds - 1.0) if won else -stake
        bankroll += profit

        sim_rows.append({
            "bet_num":        len(sim_rows) + 1,
            "match_date":     r["match_date"],
            "home_team":      r["home_team"],
            "away_team":      r["away_team"],
            "outcome":        r["outcome"],
            "odds":           odds,
            "p_model":        r["p_model"],
            "kelly_fraction": r["kelly_fraction"],
            "half_kelly":     hk,
            "stake":          round(stake, 2),
            "won":            int(won),
            "profit":         round(profit, 2),
            "bankroll_after": round(bankroll, 2),
        })

    return pd.DataFrame(sim_rows)


# ---------------------------------------------------------------------------
# 5. Accumulator builder
# ---------------------------------------------------------------------------

def build_accumulators(bets: pd.DataFrame) -> pd.DataFrame:
    """
    For each matchday find the best 2-leg and 3-leg acca built from
    positive-EV value bets on different matches.
    """
    pos_bets = bets[bets["EV"] > 0].copy()
    pos_bets["match_id"] = pos_bets["home_team"] + "_vs_" + pos_bets["away_team"]

    acca_rows = []

    for date, day in pos_bets.groupby("match_date"):
        day = day.reset_index(drop=True)

        def _best_combo(n_legs: int):
            best_ev   = -np.inf
            best_row  = None
            for combo in combinations(range(len(day)), n_legs):
                legs = [day.iloc[k] for k in combo]
                # All legs must be from different matches
                if len({lg["match_id"] for lg in legs}) < n_legs:
                    continue
                c_odds = 1.0
                c_p    = 1.0
                for lg in legs:
                    c_odds *= lg["odds"]
                    c_p    *= lg["p_model"]
                ev = c_odds * c_p - 1.0
                if ev > best_ev:
                    best_ev  = ev
                    best_row = (legs, c_odds, c_p, ev)
            return best_row

        for n_legs in (2, 3):
            result = _best_combo(n_legs)
            if result is None:
                continue
            legs, c_odds, c_p, ev = result
            won     = all(lg["won"] for lg in legs)
            row     = {
                "match_date":    date,
                "n_legs":        n_legs,
                "combined_odds": round(c_odds, 3),
                "combined_p":    round(c_p, 4),
                "acca_ev":       round(ev, 4),
                "won":           int(won),
                "profit_flat":   round(c_odds - 1.0 if won else -1.0, 4),
            }
            for k, lg in enumerate(legs, start=1):
                row[f"leg{k}_home"]    = lg["home_team"]
                row[f"leg{k}_away"]    = lg["away_team"]
                row[f"leg{k}_outcome"] = lg["outcome"]
                row[f"leg{k}_odds"]    = lg["odds"]
                row[f"leg{k}_p"]       = lg["p_model"]
            # Pad missing leg columns for 2-leg rows so CSV schema is uniform
            if n_legs == 2:
                row.update({"leg3_home": None, "leg3_away": None,
                            "leg3_outcome": None, "leg3_odds": None, "leg3_p": None})
            acca_rows.append(row)

    return pd.DataFrame(acca_rows).sort_values(["match_date", "n_legs"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 6. Max-drawdown helper
# ---------------------------------------------------------------------------

def _max_drawdown_flat(profits: np.ndarray) -> float:
    cumulative  = np.cumsum(profits)
    running_max = np.maximum.accumulate(cumulative)
    return float((running_max - cumulative).max()) if len(cumulative) else 0.0


def _max_drawdown_pct(bankrolls: np.ndarray) -> float:
    """Max peak-to-trough drawdown as percentage of peak bankroll."""
    series      = np.concatenate([[STARTING_BANKROLL], bankrolls])
    running_max = np.maximum.accumulate(series)
    dd          = (running_max - series) / running_max * 100.0
    return float(dd.max())


# ---------------------------------------------------------------------------
# 7. Print report
# ---------------------------------------------------------------------------

def print_report(bets: pd.DataFrame, sim: pd.DataFrame, accas: pd.DataFrame) -> None:
    sep = "=" * 64

    # ---- VALUE BET SUMMARY -------------------------------------------
    n_bets   = len(bets)
    win_rate = bets["won"].mean() * 100
    total_profit_flat = bets["profit_flat"].sum()
    total_stakes_flat = n_bets   # £1 per bet
    roi_flat          = total_profit_flat / total_stakes_flat * 100
    mean_clv          = bets["clv"].mean()
    returns           = bets["profit_flat"].values
    sharpe            = (returns.mean() / returns.std()) if returns.std() > 0 else 0.0
    dd_flat           = _max_drawdown_flat(returns)

    print(f"\n{sep}")
    print("VALUE BET SUMMARY")
    print(sep)
    print(f"  Total value bets identified : {n_bets:,}")
    print(f"  Win rate                    : {win_rate:.1f}%")
    print(f"  Flat stake ROI              : {roi_flat:+.2f}%  "
          f"(£{total_profit_flat:+.2f} profit on £{total_stakes_flat:,} staked)")
    print(f"  Mean CLV                    : {mean_clv:+.4f}  "
          f"({'beats closing line ✓' if mean_clv > 0 else 'below closing line ✗'})")
    print(f"  Sharpe ratio (per bet)      : {sharpe:.3f}")
    print(f"  Max drawdown (flat)         : £{dd_flat:.2f}")

    by_outcome = bets.groupby("outcome").agg(
        n=("won", "count"),
        wins=("won", "sum"),
        roi=("profit_flat", "sum"),
        mean_edge=("edge", "mean"),
    ).reindex(["H", "D", "A"])
    print(f"\n  {'Outcome':<9}  {'N':>5}  {'Wins':>5}  {'Win%':>6}  {'ROI':>8}  {'MeanEdge':>9}")
    print(f"  {'-'*55}")
    for outcome, row in by_outcome.iterrows():
        wr   = row["wins"] / row["n"] * 100 if row["n"] > 0 else 0
        roi  = row["roi"] / row["n"] * 100  if row["n"] > 0 else 0
        print(f"  {outcome:<9}  {row['n']:>5.0f}  {row['wins']:>5.0f}  {wr:>5.1f}%  {roi:>7.2f}%  {row['mean_edge']:>8.4f}")

    # ---- KELLY SIMULATION --------------------------------------------
    if len(sim) == 0:
        print(f"\n{sep}\nKELLY SIMULATION\n{sep}\n  No bets placed.\n")
    else:
        ending   = sim["bankroll_after"].iloc[-1]
        peak     = sim["bankroll_after"].max()
        dd_pct   = _max_drawdown_pct(sim["bankroll_after"].values)

        print(f"\n{sep}")
        print("KELLY SIMULATION  (half-Kelly, £1,000 starting bankroll)")
        print(sep)
        print(f"  Starting bankroll : £{STARTING_BANKROLL:,.2f}")
        print(f"  Ending bankroll   : £{ending:,.2f}  "
              f"({(ending/STARTING_BANKROLL - 1)*100:+.1f}%)")
        print(f"  Peak bankroll     : £{peak:,.2f}")
        print(f"  Max drawdown      : {dd_pct:.1f}%")
        print(f"  Total bets placed : {len(sim):,}")

    # ---- TOP 20 VALUE BETS BY EDGE -----------------------------------
    print(f"\n{sep}")
    print("TOP 20 VALUE BETS  (by edge)")
    print(sep)
    top20 = bets.nlargest(20, "edge")
    print(f"  {'Date':<12} {'Fixture':<35} {'Out':>3}  "
          f"{'p_mdl':>6}  {'Odds':>5}  {'Edge':>6}  {'EV':>6}  {'Won':>4}")
    print(f"  {'-'*88}")
    for _, r in top20.iterrows():
        fixture = f"{r['home_team'][:16]} v {r['away_team'][:14]}"
        result_str = "✓" if r["won"] else "✗"
        print(f"  {str(r['match_date'].date()):<12} {fixture:<35} {r['outcome']:>3}  "
              f"{r['p_model']:>6.3f}  {r['odds']:>5.2f}  {r['edge']:>6.4f}  "
              f"{r['EV']:>+6.4f}  {result_str:>4}")

    # ---- ACCUMULATOR EXAMPLES ----------------------------------------
    if len(accas) == 0:
        print(f"\n{sep}\nACCUMULATOR EXAMPLES\n{sep}\n  No accumulators found.\n")
        return

    two_leg = accas[accas["n_legs"] == 2].nlargest(5, "acca_ev")
    print(f"\n{sep}")
    print("ACCUMULATOR EXAMPLES  (best 5 two-leg accas by EV)")
    print(sep)
    print(f"  {'Date':<12}  {'Legs':<52}  {'Odds':>6}  {'p':>6}  {'EV':>6}  {'Won':>4}")
    print(f"  {'-'*92}")
    for _, r in two_leg.iterrows():
        leg1 = f"{r['leg1_home'][:10]}v{r['leg1_away'][:9]}({r['leg1_outcome']}@{r['leg1_odds']:.2f})"
        leg2 = f"{r['leg2_home'][:10]}v{r['leg2_away'][:9]}({r['leg2_outcome']}@{r['leg2_odds']:.2f})"
        legs = f"{leg1} + {leg2}"
        result_str = "✓" if r["won"] else "✗"
        print(f"  {str(r['match_date'].date()):<12}  {legs:<52}  "
              f"{r['combined_odds']:>6.2f}  {r['combined_p']:>6.4f}  "
              f"{r['acca_ev']:>+6.4f}  {result_str:>4}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))

    print("Loading data...")
    df = load_data(base)
    print(f"  {len(df):,} holdout matches loaded  "
          f"({df['match_date'].min().date()} → {df['match_date'].max().date()})\n")

    df = add_market_metrics(df)

    print("Identifying value bets (edge > 5%)...")
    bets = extract_value_bets(df)
    print(f"  Found {len(bets):,} value bets  "
          f"(H: {(bets['outcome']=='H').sum()}  "
          f"D: {(bets['outcome']=='D').sum()}  "
          f"A: {(bets['outcome']=='A').sum()})\n")

    print("Running Kelly bankroll simulation...")
    sim = kelly_simulation(bets)
    print(f"  {len(sim):,} bets placed\n")

    print("Building accumulators...")
    accas = build_accumulators(bets)
    n2 = (accas["n_legs"] == 2).sum() if len(accas) else 0
    n3 = (accas["n_legs"] == 3).sum() if len(accas) else 0
    print(f"  {n2} two-leg accas  |  {n3} three-leg accas found\n")

    print_report(bets, sim, accas)

    # ---- Save ---------------------------------------------------------
    out_dir = os.path.normpath(os.path.join(base, "..", "data", "processed"))

    vb_path   = os.path.join(out_dir, "value_bets.csv")
    sim_path  = os.path.join(out_dir, "kelly_simulation.csv")
    acca_path = os.path.join(out_dir, "accumulator_bets.csv")

    bets.to_csv(vb_path,   index=False)
    sim.to_csv(sim_path,   index=False)
    accas.to_csv(acca_path, index=False)

    print(f"Saved {len(bets):,} value bets        → {vb_path}")
    print(f"Saved {len(sim):,} simulation rows   → {sim_path}")
    print(f"Saved {len(accas):,} accumulator rows  → {acca_path}")


if __name__ == "__main__":
    main()
