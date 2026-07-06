"""
portfolio_analytics.py

Portfolio-level performance metrics for the value betting system.

Primary data sources
--------------------
  data/processed/value_bets.csv         — holdout backtest value bets (value_betting.py output)
  data/processed/prediction_log.csv     — live model predictions; settled rows joined with
  data/processed/results.csv              results.csv to get odds and compute Kelly fractions

Outputs
-------
  data/processed/portfolio_pnl.csv
  data/processed/portfolio_analytics.json
"""

import json
import os

import numpy as np
import pandas as pd

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

STARTING_BANKROLL = 1_000.0
EDGE_THRESHOLD    = 0.05
KELLY_MULTIPLIERS = [0.10, 0.25, 0.50, 1.00]   # fractions of full Kelly to simulate


# ---------------------------------------------------------------------------
# 1.  Data loading
# ---------------------------------------------------------------------------

def _load_value_bets() -> pd.DataFrame:
    """Load settled value bets produced by value_betting.py."""
    path = os.path.join(DATA_DIR, "value_bets.csv")
    if not os.path.exists(path):
        print("  value_bets.csv not found — skipping backtest source.")
        return pd.DataFrame()

    df = pd.read_csv(path, parse_dates=["match_date"])
    df["source"] = "backtest"
    return df


def _load_prediction_log_bets() -> pd.DataFrame:
    """
    Load settled rows from prediction_log.csv, enrich with odds from results.csv,
    then identify value bets (edge > EDGE_THRESHOLD) across all three outcomes.
    Returns empty DataFrame when no settled rows exist (e.g. early in the season).
    """
    log_path     = os.path.join(DATA_DIR, "prediction_log.csv")
    results_path = os.path.join(DATA_DIR, "results.csv")

    if not os.path.exists(log_path) or not os.path.exists(results_path):
        return pd.DataFrame()

    log     = pd.read_csv(log_path, dtype=str).fillna("")
    settled = log[log["actual_result"].str.strip() != ""].copy()
    if settled.empty:
        return pd.DataFrame()

    results = pd.read_csv(results_path, parse_dates=["match_date"], low_memory=False)
    odds_cols = ["home_odds", "draw_odds", "away_odds"]
    results   = results[["match_date", "home_team", "away_team"] + odds_cols].dropna(
        subset=odds_cols
    )

    settled["match_date"] = pd.to_datetime(settled["match_date"])
    for col in ["p_home", "p_draw", "p_away"]:
        settled[col] = pd.to_numeric(settled[col], errors="coerce")

    merged = settled.merge(results, on=["match_date", "home_team", "away_team"], how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged["imp_h"]     = 1.0 / merged["home_odds"]
    merged["imp_d"]     = 1.0 / merged["draw_odds"]
    merged["imp_a"]     = 1.0 / merged["away_odds"]
    merged["overround"] = merged["imp_h"] + merged["imp_d"] + merged["imp_a"]
    merged["imp_adj_h"] = merged["imp_h"] / merged["overround"]
    merged["imp_adj_d"] = merged["imp_d"] / merged["overround"]
    merged["imp_adj_a"] = merged["imp_a"] / merged["overround"]

    rows = []
    for _, r in merged.iterrows():
        for outcome, p_col, odds_col, imp_col, imp_adj_col in [
            ("H", "p_home", "home_odds", "imp_h", "imp_adj_h"),
            ("D", "p_draw", "draw_odds", "imp_d", "imp_adj_d"),
            ("A", "p_away", "away_odds", "imp_a", "imp_adj_a"),
        ]:
            p_model = float(r[p_col])
            edge    = p_model - float(r[imp_adj_col])
            if edge <= EDGE_THRESHOLD:
                continue

            odds  = float(r[odds_col])
            imp   = float(r[imp_col])
            kelly = (p_model * odds - 1.0) / (odds - 1.0) if odds > 1.0 else 0.0
            won   = int(str(r["actual_result"]).strip() == outcome)
            clv   = float(np.log(p_model / imp)) if imp > 0 and p_model > 0 else 0.0

            rows.append({
                "match_date":     r["match_date"],
                "league":         r["league"],
                "home_team":      r["home_team"],
                "away_team":      r["away_team"],
                "outcome":        outcome,
                "p_model":        round(p_model, 4),
                "odds":           round(odds, 3),
                "implied_prob":   round(imp, 4),
                "edge":           round(edge, 4),
                "EV":             round(p_model * odds - 1.0, 4),
                "kelly_fraction": round(kelly, 4),
                "half_kelly":     round(kelly / 2, 4),
                "actual_result":  str(r["actual_result"]).strip(),
                "won":            won,
                "profit_flat":    round((odds - 1.0) if won else -1.0, 4),
                "profit_kelly":   round((kelly / 2) * (odds - 1.0) if won else -(kelly / 2), 4),
                "clv":            round(clv, 4),
                "source":         "prediction_log",
            })

    return pd.DataFrame(rows)


def load_all_bets() -> pd.DataFrame:
    """Combine backtest and live-log value bets, deduplicated by (date, match, outcome)."""
    backtest = _load_value_bets()
    live     = _load_prediction_log_bets()

    if backtest.empty and live.empty:
        raise RuntimeError(
            "No settled value bets found. "
            "Run value_betting.py first (backtest) or wait for live predictions to settle."
        )

    parts    = [df for df in [backtest, live] if not df.empty]
    combined = pd.concat(parts, ignore_index=True)

    # Keep backtest record when both sources have the same (date, fixture, outcome)
    combined = (
        combined
        .sort_values(["match_date", "source"])       # "backtest" < "prediction_log" alphabetically
        .drop_duplicates(
            subset=["match_date", "home_team", "away_team", "outcome"], keep="first"
        )
        .sort_values("match_date")
        .reset_index(drop=True)
    )

    return combined


# ---------------------------------------------------------------------------
# 2.  P&L tracking
# ---------------------------------------------------------------------------

def build_pnl(bets: pd.DataFrame, kelly_mult: float = 0.5) -> pd.DataFrame:
    """
    Sequential bankroll-proportional P&L.  stake = kelly_fraction × kelly_mult × bankroll.
    Returns one row per bet placed (bets with non-positive Kelly are skipped).
    """
    bankroll = STARTING_BANKROLL
    rows: list[dict] = []

    for _, r in bets.iterrows():
        kf = float(r["kelly_fraction"]) * kelly_mult
        if kf <= 0.0:
            continue

        odds  = float(r["odds"])
        won   = bool(r["won"])
        stake = kf * bankroll
        pnl   = stake * (odds - 1.0) if won else -stake
        bankroll += pnl

        rows.append({
            "date":           r["match_date"].date(),
            "match":          f"{r['home_team']} vs {r['away_team']}",
            "league":         r["league"],
            "outcome":        r["outcome"],
            "odds":           round(odds, 3),
            "stake":          round(stake, 4),
            "won":            int(won),
            "pnl":            round(pnl, 4),
            "cumulative_pnl": round(bankroll - STARTING_BANKROLL, 4),
            "bankroll":       round(bankroll, 4),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3.  Metric helpers
# ---------------------------------------------------------------------------

def _max_drawdown_pct(bankrolls: np.ndarray) -> float:
    series      = np.concatenate([[STARTING_BANKROLL], bankrolls])
    running_max = np.maximum.accumulate(series)
    dd          = (running_max - series) / running_max * 100.0
    return float(dd.max())


def _sharpe(pnl_df: pd.DataFrame) -> float:
    """
    Annualised Sharpe: aggregate daily P&L as a fraction of starting bankroll,
    then mean / std × sqrt(252).
    """
    if pnl_df.empty:
        return 0.0
    daily     = pnl_df.groupby("date")["pnl"].sum() / STARTING_BANKROLL
    if len(daily) < 2 or daily.std() == 0:
        return 0.0
    return float(daily.mean() / daily.std() * np.sqrt(252))


def _segment_metrics(bets_seg: pd.DataFrame) -> dict:
    """Flat-stake metrics for a sub-segment of bets (used for breakdowns)."""
    n = len(bets_seg)
    if n == 0:
        return {}
    wins           = int(bets_seg["won"].sum())
    total_profit_f = float(bets_seg["profit_flat"].sum())
    roi_flat       = total_profit_f / n * 100
    flat_returns   = bets_seg["profit_flat"].values
    sharpe_flat    = (float(flat_returns.mean() / flat_returns.std())
                      if flat_returns.std() > 0 else 0.0)
    dd_flat        = float((np.maximum.accumulate(np.cumsum(flat_returns))
                            - np.cumsum(flat_returns)).max()) if n > 0 else 0.0

    return {
        "n_bets":         n,
        "win_rate_pct":   round(wins / n * 100, 2),
        "roi_flat_pct":   round(roi_flat, 2),
        "sharpe_flat":    round(sharpe_flat, 3),
        "max_drawdown_flat_units": round(dd_flat, 2),
        "avg_odds":       round(float(bets_seg["odds"].mean()), 3),
        "avg_edge_pct":   round(float(bets_seg["edge"].mean()) * 100, 2),
        "mean_clv":       round(float(bets_seg["clv"].mean()), 4) if "clv" in bets_seg.columns else None,
        "total_profit_flat": round(total_profit_f, 2),
    }


def compute_overall_metrics(bets: pd.DataFrame, pnl: pd.DataFrame) -> dict:
    total_staked  = float(pnl["stake"].sum())
    total_profit  = float(pnl["pnl"].sum())
    ending_br     = float(pnl["bankroll"].iloc[-1]) if len(pnl) else STARTING_BANKROLL
    roi_kelly     = total_profit / total_staked * 100 if total_staked > 0 else 0.0

    flat_profit   = float(bets["profit_flat"].sum())
    roi_flat      = flat_profit / len(bets) * 100 if len(bets) else 0.0

    return {
        "n_bets":              len(bets),
        "date_range_start":    str(bets["match_date"].min().date()),
        "date_range_end":      str(bets["match_date"].max().date()),
        "roi_kelly_pct":       round(roi_kelly, 2),
        "roi_flat_pct":        round(roi_flat, 2),
        "sharpe_annualised":   round(_sharpe(pnl), 3),
        "max_drawdown_pct":    round(_max_drawdown_pct(pnl["bankroll"].values), 2) if len(pnl) else 0.0,
        "win_rate_pct":        round(float(bets["won"].mean()) * 100, 2),
        "avg_odds":            round(float(bets["odds"].mean()), 3),
        "avg_edge_pct":        round(float(bets["edge"].mean()) * 100, 2),
        "mean_clv":            round(float(bets["clv"].mean()), 4) if "clv" in bets.columns else None,
        "total_staked":        round(total_staked, 2),
        "total_profit_kelly":  round(total_profit, 2),
        "total_profit_flat":   round(flat_profit, 2),
        "starting_bankroll":   STARTING_BANKROLL,
        "ending_bankroll":     round(ending_br, 2),
        "bankroll_growth_pct": round((ending_br / STARTING_BANKROLL - 1) * 100, 2),
    }


# ---------------------------------------------------------------------------
# 4.  Market breakdowns
# ---------------------------------------------------------------------------

def compute_breakdowns(bets: pd.DataFrame) -> dict:
    out = {}

    # --- by predicted outcome (H / D / A) ---
    by_outcome = {}
    for outcome in ["H", "D", "A"]:
        seg = bets[bets["outcome"] == outcome]
        by_outcome[outcome] = _segment_metrics(seg)
    out["by_outcome"] = by_outcome

    # --- by league (top 10 by volume, rest grouped as "Other") ---
    top_leagues = bets["league"].value_counts().head(10).index.tolist()
    by_league   = {}
    for league in top_leagues:
        seg = bets[bets["league"] == league]
        by_league[league] = _segment_metrics(seg)
    other_seg = bets[~bets["league"].isin(top_leagues)]
    if len(other_seg):
        by_league["Other"] = _segment_metrics(other_seg)
    out["by_league"] = by_league

    # --- by edge bucket ---
    def _edge_label(e: float) -> str:
        if e < 0.10:
            return "5-10%"
        if e < 0.15:
            return "10-15%"
        return "15%+"

    bets_copy = bets.copy()
    bets_copy["edge_bucket"] = bets_copy["edge"].apply(_edge_label)
    by_edge = {}
    for bucket in ["5-10%", "10-15%", "15%+"]:
        seg = bets_copy[bets_copy["edge_bucket"] == bucket]
        by_edge[bucket] = _segment_metrics(seg)
    out["by_edge_bucket"] = by_edge

    return out


# ---------------------------------------------------------------------------
# 5.  Kelly sensitivity simulation
# ---------------------------------------------------------------------------

def kelly_sensitivity(bets: pd.DataFrame) -> dict:
    """
    Simulate the same historical bet sequence at four Kelly multipliers.
    Returns a dict keyed by multiplier label with risk/return metrics.
    """
    results = {}
    for mult in KELLY_MULTIPLIERS:
        pnl = build_pnl(bets, kelly_mult=mult)
        if pnl.empty:
            continue

        ending_br = float(pnl["bankroll"].iloc[-1])
        max_dd    = _max_drawdown_pct(pnl["bankroll"].values)
        sharpe    = _sharpe(pnl)
        total_p   = float(pnl["pnl"].sum())
        total_s   = float(pnl["stake"].sum())
        roi       = total_p / total_s * 100 if total_s > 0 else 0.0

        label = f"{mult:.2f}x Kelly"
        results[label] = {
            "kelly_multiplier":    mult,
            "ending_bankroll":     round(ending_br, 2),
            "bankroll_growth_pct": round((ending_br / STARTING_BANKROLL - 1) * 100, 2),
            "roi_pct":             round(roi, 2),
            "max_drawdown_pct":    round(max_dd, 2),
            "sharpe_annualised":   round(sharpe, 3),
            "n_bets_placed":       len(pnl),
        }

    return results


# ---------------------------------------------------------------------------
# 6.  Print report
# ---------------------------------------------------------------------------

def print_report(
    overall:   dict,
    breakdown: dict,
    kelly_sim: dict,
) -> None:
    sep  = "=" * 66
    sep2 = "-" * 66

    print(f"\n{sep}")
    print("PORTFOLIO ANALYTICS  (half-Kelly staking, £1,000 starting bankroll)")
    print(sep)

    o = overall
    print(f"  Date range          : {o['date_range_start']}  →  {o['date_range_end']}")
    print(f"  Value bets analysed : {o['n_bets']:,}")
    print(f"  Win rate            : {o['win_rate_pct']:.1f}%")
    print(f"  Avg odds            : {o['avg_odds']:.3f}")
    print(f"  Avg edge            : {o['avg_edge_pct']:+.2f}%")
    if o["mean_clv"] is not None:
        print(f"  Mean CLV            : {o['mean_clv']:+.4f}  "
              f"({'beats market ✓' if o['mean_clv'] > 0 else 'below market ✗'})")
    print()
    print(f"  ROI (Kelly stake)   : {o['roi_kelly_pct']:+.2f}%")
    print(f"  ROI (flat stake)    : {o['roi_flat_pct']:+.2f}%")
    print(f"  Sharpe (annualised) : {o['sharpe_annualised']:.3f}")
    print(f"  Max drawdown        : {o['max_drawdown_pct']:.1f}%")
    print(f"  Starting bankroll   : £{o['starting_bankroll']:,.2f}")
    print(f"  Ending bankroll     : £{o['ending_bankroll']:,.2f}  "
          f"({o['bankroll_growth_pct']:+.1f}%)")
    print(f"  Total Kelly profit  : £{o['total_profit_kelly']:+,.2f}")
    print(f"  Total flat profit   : £{o['total_profit_flat']:+,.2f}")

    # --- Outcome breakdown ---
    print(f"\n{sep}")
    print("BY PREDICTED OUTCOME")
    print(sep)
    outcome_map = {"H": "Home", "D": "Draw", "A": "Away"}
    print(f"  {'Outcome':<8}  {'N':>5}  {'Win%':>6}  {'ROI%':>7}  "
          f"{'AvgOdds':>8}  {'AvgEdge%':>9}  {'Sharpe':>7}")
    print(f"  {sep2}")
    for k, label in outcome_map.items():
        m = breakdown["by_outcome"].get(k, {})
        if not m:
            continue
        print(f"  {label:<8}  {m['n_bets']:>5,}  {m['win_rate_pct']:>5.1f}%  "
              f"{m['roi_flat_pct']:>+6.2f}%  {m['avg_odds']:>8.3f}  "
              f"{m['avg_edge_pct']:>+8.2f}%  {m['sharpe_flat']:>7.3f}")

    # --- Edge bucket breakdown ---
    print(f"\n{sep}")
    print("BY EDGE BUCKET")
    print(sep)
    print(f"  {'Edge':>8}  {'N':>5}  {'Win%':>6}  {'ROI%':>7}  "
          f"{'AvgOdds':>8}  {'MeanCLV':>8}")
    print(f"  {sep2}")
    for bucket in ["5-10%", "10-15%", "15%+"]:
        m = breakdown["by_edge_bucket"].get(bucket, {})
        if not m:
            continue
        clv_str = f"{m['mean_clv']:+.4f}" if m.get("mean_clv") is not None else "   N/A"
        print(f"  {bucket:>8}  {m['n_bets']:>5,}  {m['win_rate_pct']:>5.1f}%  "
              f"{m['roi_flat_pct']:>+6.2f}%  {m['avg_odds']:>8.3f}  {clv_str:>8}")

    # --- League breakdown ---
    print(f"\n{sep}")
    print("BY LEAGUE  (top 10 by volume)")
    print(sep)
    print(f"  {'League':<22}  {'N':>5}  {'Win%':>6}  {'ROI%':>7}  {'AvgEdge%':>9}")
    print(f"  {sep2}")
    for league, m in breakdown["by_league"].items():
        if not m:
            continue
        print(f"  {league[:22]:<22}  {m['n_bets']:>5,}  {m['win_rate_pct']:>5.1f}%  "
              f"{m['roi_flat_pct']:>+6.2f}%  {m['avg_edge_pct']:>+8.2f}%")

    # --- Kelly sensitivity ---
    print(f"\n{sep}")
    print("KELLY SENSITIVITY  (same historical bets, different stake sizes)")
    print(sep)
    print(f"  {'Fraction':<14}  {'Ending £':>10}  {'Growth%':>8}  "
          f"{'ROI%':>7}  {'MaxDD%':>7}  {'Sharpe':>7}")
    print(f"  {sep2}")
    for label, m in kelly_sim.items():
        print(f"  {label:<14}  {m['ending_bankroll']:>10,.2f}  "
              f"{m['bankroll_growth_pct']:>+7.1f}%  "
              f"{m['roi_pct']:>+6.2f}%  {m['max_drawdown_pct']:>6.1f}%  "
              f"{m['sharpe_annualised']:>7.3f}")

    print()


# ---------------------------------------------------------------------------
# 7.  Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Loading value bets...")
    bets = load_all_bets()

    n_bt   = (bets["source"] == "backtest").sum()
    n_live = (bets["source"] == "prediction_log").sum()
    print(f"  {len(bets):,} bets loaded  "
          f"(backtest: {n_bt:,}  |  prediction_log: {n_live:,})")
    print(f"  Range: {bets['match_date'].min().date()} → {bets['match_date'].max().date()}\n")

    print("Building P&L track (half-Kelly)...")
    pnl = build_pnl(bets, kelly_mult=0.5)
    print(f"  {len(pnl):,} bets placed\n")

    print("Computing portfolio metrics...")
    overall   = compute_overall_metrics(bets, pnl)
    breakdown = compute_breakdowns(bets)

    print("Running Kelly sensitivity simulation...")
    kelly_sim = kelly_sensitivity(bets)

    print_report(overall, breakdown, kelly_sim)

    # ---- Serialise --------------------------------------------------------
    out_json = {
        "summary":           overall,
        "by_outcome":        breakdown["by_outcome"],
        "by_league":         breakdown["by_league"],
        "by_edge_bucket":    breakdown["by_edge_bucket"],
        "kelly_sensitivity": kelly_sim,
    }

    pnl_path  = os.path.join(DATA_DIR, "portfolio_pnl.csv")
    json_path = os.path.join(DATA_DIR, "portfolio_analytics.json")

    pnl.to_csv(pnl_path, index=False)
    with open(json_path, "w") as fh:
        json.dump(out_json, fh, indent=2)

    print(f"Saved P&L track ({len(pnl):,} rows)  → {pnl_path}")
    print(f"Saved analytics JSON             → {json_path}")


if __name__ == "__main__":
    main()
