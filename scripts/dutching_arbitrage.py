"""
dutching_arbitrage.py

Betting utility module — four tools:

  1. dutch_stakes        — split a total stake for an equal guaranteed return
  2. find_arbitrage      — detect cross-bookmaker arb opportunities
  3. strict_value_filter — tight value-bet filter (10% edge, max 6.0 odds)
  4. Odds converters     — to_decimal / to_american / to_fractional

All functions are pure (no I/O) and can be imported from the API or run
standalone via:

    python scripts/dutching_arbitrage.py
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# 1.  Dutching calculator
# ---------------------------------------------------------------------------

def dutch_stakes(outcomes: list[dict], total_stake: float) -> dict:
    """
    Split a total stake across multiple outcomes so the return is identical
    whichever outcome lands.

    Parameters
    ----------
    outcomes    : list of {'name': str, 'odds': float, 'model_prob': float}
    total_stake : total amount to distribute

    Returns
    -------
    dict with per-outcome stakes, guaranteed_return, net_profit, ROI.

    Maths
    -----
    weight_i          = 1 / odds_i
    stake_i           = total_stake × weight_i / Σ weight_j
    guaranteed_return = total_stake / Σ weight_j   (identical for every outcome)
    net_profit        = guaranteed_return − total_stake
    roi_pct           = net_profit / total_stake × 100
    """
    if not outcomes:
        raise ValueError("outcomes must be non-empty")
    if total_stake <= 0:
        raise ValueError("total_stake must be positive")

    for o in outcomes:
        if o.get("odds", 0) <= 1.0:
            raise ValueError(
                f"odds must be > 1.0, got {o.get('odds')} for '{o.get('name')}'"
            )

    weights       = [1.0 / o["odds"] for o in outcomes]
    total_weight  = sum(weights)

    stakes            = [total_stake * w / total_weight for w in weights]
    guaranteed_return = total_stake / total_weight
    net_profit        = guaranteed_return - total_stake
    roi_pct           = net_profit / total_stake * 100.0

    return {
        "outcomes": [
            {
                "name":           o["name"],
                "odds":           o["odds"],
                "model_prob":     o.get("model_prob"),
                "stake":          round(s, 4),
                "return_if_wins": round(s * o["odds"], 4),
            }
            for o, s in zip(outcomes, stakes)
        ],
        "total_stake":        round(total_stake, 4),
        "overround":          round(total_weight, 6),
        "market_margin_pct":  round((total_weight - 1.0) * 100.0, 4),
        "guaranteed_return":  round(guaranteed_return, 4),
        "net_profit":         round(net_profit, 4),
        "roi_pct":            round(roi_pct, 4),
        "is_profitable":      net_profit > 0,
    }


# ---------------------------------------------------------------------------
# 2.  Arbitrage detector
# ---------------------------------------------------------------------------

def find_arbitrage(markets: list[dict]) -> dict:
    """
    Detect whether best-available odds across a set of bookmakers produce a
    guaranteed profit (implied sum < 1.0).

    Parameters
    ----------
    markets : list of {
        'bookmaker' : str,
        'home_odds' : float,
        'draw_odds' : float,
        'away_odds' : float,
    }

    Returns
    -------
    dict with best odds per outcome, implied sum, arb %, and (if arb exists)
    the per-outcome stakes needed to guarantee £100 profit.
    """
    if not markets:
        raise ValueError("markets must be non-empty")

    for m in markets:
        for key in ("home_odds", "draw_odds", "away_odds"):
            if m.get(key, 0) <= 1.0:
                raise ValueError(
                    f"{key} must be > 1.0, got {m.get(key)} for '{m.get('bookmaker')}'"
                )

    best_home = max(markets, key=lambda m: m["home_odds"])
    best_draw = max(markets, key=lambda m: m["draw_odds"])
    best_away = max(markets, key=lambda m: m["away_odds"])

    h_odds = float(best_home["home_odds"])
    d_odds = float(best_draw["draw_odds"])
    a_odds = float(best_away["away_odds"])

    implied_sum = 1.0 / h_odds + 1.0 / d_odds + 1.0 / a_odds
    arb_pct     = (1.0 - implied_sum) * 100.0
    is_arb      = implied_sum < 1.0

    stakes_for_100_profit: dict | None = None
    if is_arb:
        # For guaranteed profit P with stakes s_i and return R:
        #   s_i = R / odds_i  →  Σ s_i = R × implied_sum
        #   P   = R − Σ s_i   = R × (1 − implied_sum)
        #   R   = P / (1 − implied_sum)
        guaranteed_return = 100.0 / (1.0 - implied_sum)
        stakes_for_100_profit = {
            "home":               round(guaranteed_return / h_odds, 2),
            "draw":               round(guaranteed_return / d_odds, 2),
            "away":               round(guaranteed_return / a_odds, 2),
            "total_staked":       round(guaranteed_return * implied_sum, 2),
            "guaranteed_return":  round(guaranteed_return, 2),
            "guaranteed_profit":  100.0,
        }

    return {
        "best_odds": {
            "home": {"bookmaker": best_home["bookmaker"], "odds": h_odds},
            "draw": {"bookmaker": best_draw["bookmaker"], "odds": d_odds},
            "away": {"bookmaker": best_away["bookmaker"], "odds": a_odds},
        },
        "implied_sum":            round(implied_sum, 6),
        "arb_pct":                round(arb_pct, 4),
        "is_arbitrage":           is_arb,
        "stakes_for_100_profit":  stakes_for_100_profit,
        "n_bookmakers":           len(markets),
    }


# ---------------------------------------------------------------------------
# 3.  Strict value-bet filter
# ---------------------------------------------------------------------------

def strict_value_filter(
    model_prob:      float,
    bookmaker_odds:  float,
    min_edge:        float = 0.10,
    max_odds:        float = 6.0,
    min_model_prob:  float = 0.20,
) -> bool:
    """
    Tighter value-bet filter than the base 5% edge threshold used in
    value_betting.py.  Uses the raw implied probability (1/odds), not
    the margin-adjusted version, so edge must overcome the bookmaker's
    full overround before being flagged.

    Parameters
    ----------
    model_prob      : model's probability estimate for this outcome
    bookmaker_odds  : decimal odds offered by the bookmaker
    min_edge        : minimum required (model_prob − 1/odds); default 10%
    max_odds        : reject longshots above this decimal; default 6.0
    min_model_prob  : minimum model conviction required; default 20%

    Returns
    -------
    True only when all three conditions are met simultaneously.
    """
    if bookmaker_odds <= 1.0 or not (0.0 < model_prob < 1.0):
        return False

    raw_implied = 1.0 / bookmaker_odds
    edge        = model_prob - raw_implied

    return (
        edge        > min_edge
        and bookmaker_odds < max_odds
        and model_prob     > min_model_prob
    )


# ---------------------------------------------------------------------------
# 4.  Odds format converters
# ---------------------------------------------------------------------------

# Standard UK fractional odds as (numerator, denominator) pairs.
# Each entry represents fractional odds n/d (win n for every d staked).
# Decimal equivalent = 1 + n/d.
COMMON_FRACTIONS: list[tuple[int, int]] = [
    (1, 4), (1, 3), (4, 9), (1, 2), (8, 15), (4, 6), (8, 11), (4, 5), (5, 6),
    (10, 11), (1, 1), (11, 10), (6, 5), (5, 4), (11, 8), (6, 4), (13, 8), (7, 4),
    (15, 8), (2, 1), (9, 4), (5, 2), (11, 4), (3, 1), (10, 3), (4, 1), (9, 2),
    (5, 1), (6, 1), (7, 1), (8, 1), (10, 1), (12, 1), (16, 1), (20, 1), (25, 1),
    (33, 1), (50, 1), (66, 1), (100, 1),
]


def to_decimal(prob: float) -> float:
    """Convert a probability to decimal odds (e.g. 0.40 → 2.500)."""
    if not (0.0 < prob < 1.0):
        raise ValueError(f"prob must be in (0, 1), got {prob}")
    return round(1.0 / prob, 3)


def to_american(prob: float) -> str:
    """
    Convert a probability to an American moneyline string.

    Favourites (prob > 0.5) → negative  e.g. "-200"
    Underdogs  (prob ≤ 0.5) → positive  e.g. "+150"

    Maths
    -----
    favourite : american = −round(prob / (1 − prob) × 100)
    underdog  : american = +round((1 − prob) / prob × 100)
    """
    if not (0.0 < prob < 1.0):
        raise ValueError(f"prob must be in (0, 1), got {prob}")

    if prob > 0.5:
        return str(-round(prob / (1.0 - prob) * 100))
    else:
        return f"+{round((1.0 - prob) / prob * 100)}"


def to_fractional(prob: float) -> str:
    """
    Convert a probability to the nearest standard UK fractional odds string
    (e.g. 0.40 → "6/4", 0.50 → "1/1", 0.33 → "2/1").

    Finds the closest entry in COMMON_FRACTIONS by minimising
    |n/d − (1−prob)/prob|.
    """
    if not (0.0 < prob < 1.0):
        raise ValueError(f"prob must be in (0, 1), got {prob}")

    target = (1.0 - prob) / prob
    best   = min(COMMON_FRACTIONS, key=lambda f: abs(f[0] / f[1] - target))
    return f"{best[0]}/{best[1]}"


def all_formats(prob: float) -> dict:
    """Return decimal, American, and fractional representations for a probability."""
    return {
        "probability": prob,
        "decimal":     to_decimal(prob),
        "american":    to_american(prob),
        "fractional":  to_fractional(prob),
    }


# ---------------------------------------------------------------------------
# Standalone demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    sep = "=" * 60

    # ── Dutching ────────────────────────────────────────────────────
    print(f"\n{sep}\nDUTCHING CALCULATOR\n{sep}")
    outcomes = [
        {"name": "Home", "odds": 2.50, "model_prob": 0.45},
        {"name": "Draw", "odds": 3.40, "model_prob": 0.28},
        {"name": "Away", "odds": 2.80, "model_prob": 0.27},
    ]
    result = dutch_stakes(outcomes, total_stake=100.0)
    print(f"  Total stake      : £{result['total_stake']:.2f}")
    print(f"  Market overround : {result['overround']:.4f}  "
          f"({result['market_margin_pct']:+.2f}% margin)")
    print(f"  Guaranteed return: £{result['guaranteed_return']:.2f}")
    print(f"  Net profit       : £{result['net_profit']:.2f}  "
          f"(ROI: {result['roi_pct']:+.2f}%)")
    print()
    for o in result["outcomes"]:
        print(f"    {o['name']:<6}  odds={o['odds']:.2f}  "
              f"stake=£{o['stake']:.2f}  return=£{o['return_if_wins']:.2f}")

    # ── Arbitrage ───────────────────────────────────────────────────
    print(f"\n{sep}\nARBITRAGE DETECTOR\n{sep}")
    markets_no_arb = [
        {"bookmaker": "Bet365",    "home_odds": 2.50, "draw_odds": 3.20, "away_odds": 2.80},
        {"bookmaker": "Betfair",   "home_odds": 2.55, "draw_odds": 3.30, "away_odds": 2.75},
        {"bookmaker": "Ladbrokes", "home_odds": 2.45, "draw_odds": 3.25, "away_odds": 2.90},
    ]
    markets_arb = [
        {"bookmaker": "BookA", "home_odds": 2.10, "draw_odds": 3.60, "away_odds": 3.75},
        {"bookmaker": "BookB", "home_odds": 2.20, "draw_odds": 3.80, "away_odds": 3.50},
        {"bookmaker": "BookC", "home_odds": 2.05, "draw_odds": 3.50, "away_odds": 4.00},
    ]

    for label, mkts in [("No-arb example", markets_no_arb), ("Arb example", markets_arb)]:
        r = find_arbitrage(mkts)
        print(f"  {label}")
        print(f"    Implied sum : {r['implied_sum']:.6f}  |  arb%: {r['arb_pct']:+.4f}%  "
              f"|  arb: {'YES ✓' if r['is_arbitrage'] else 'no ✗'}")
        b = r["best_odds"]
        print(f"    Best odds   : H={b['home']['odds']} ({b['home']['bookmaker']})  "
              f"D={b['draw']['odds']} ({b['draw']['bookmaker']})  "
              f"A={b['away']['odds']} ({b['away']['bookmaker']})")
        if r["is_arbitrage"]:
            s = r["stakes_for_100_profit"]
            print(f"    Stakes (£100 profit)  home=£{s['home']}  draw=£{s['draw']}  "
                  f"away=£{s['away']}  total=£{s['total_staked']}")
        print()

    # ── Strict value filter ─────────────────────────────────────────
    print(f"{sep}\nSTRICT VALUE FILTER  (min_edge=10%, max_odds=6.0, min_prob=20%)\n{sep}")
    tests = [
        (0.55, 2.10, "High prob, thin edge"),
        (0.40, 3.20, "Good prob, good odds"),
        (0.30, 4.50, "Moderate prob, value odds"),
        (0.15, 7.00, "Low prob, longshot — rejected"),
        (0.25, 3.00, "Decent prob, tight edge — rejected"),
    ]
    for prob, odds, label in tests:
        implied = 1 / odds
        edge    = prob - implied
        passed  = strict_value_filter(prob, odds)
        print(f"  {label:<40}  p={prob:.2f}  odds={odds:.2f}  "
              f"edge={edge:+.3f}  → {'PASS ✓' if passed else 'FAIL ✗'}")

    # ── Odds converters ─────────────────────────────────────────────
    print(f"\n{sep}\nODDS FORMAT CONVERTERS\n{sep}")
    probs = [0.80, 0.50, 0.40, 0.25, 0.10]
    print(f"  {'Prob':>6}  {'Decimal':>8}  {'American':>10}  {'Fractional':>12}")
    print(f"  {'-'*44}")
    for p in probs:
        print(f"  {p:>6.2f}  {to_decimal(p):>8.3f}  {to_american(p):>10}  {to_fractional(p):>12}")
    print()


if __name__ == "__main__":
    _demo()
