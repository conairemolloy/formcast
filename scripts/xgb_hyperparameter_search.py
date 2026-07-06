"""
Random search over XGBoost hyperparameters using OOF evaluation.

Features are built live via build_all_features from ensemble_v2, so
the search is always in sync with the current 63-feature set. Samples
30 random combinations from PARAM_GRID, evaluates each with 5-fold
TimeSeriesSplit OOF, and reports 3-outcome Brier score and hit rate.
"""
import os
import random
import sys
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ensemble_v2 import COLD_START, FEATURE_COLS, RESULT_MAP, build_all_features

N_TRIALS = 30
N_SPLITS = 5
RANDOM_SEED = 42

PARAM_GRID = {
    "n_estimators":     [300, 500, 700],
    "max_depth":        [3, 4, 5, 6],
    "learning_rate":    [0.01, 0.03, 0.05],
    "subsample":        [0.7, 0.8, 0.9],
    "colsample_bytree": [0.6, 0.7, 0.8],
    "min_child_weight": [1, 3, 5],
}

# Current hardcoded params in ensemble_v2 — used for delta comparison
CURRENT_PARAMS = {
    "n_estimators": 500, "max_depth": 5, "learning_rate": 0.03,
    "subsample": 0.8, "colsample_bytree": 0.7, "min_child_weight": 3,
}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _brier_multiclass(proba: np.ndarray, y: np.ndarray) -> float:
    """Mean sum-of-squared-errors across all three outcome classes."""
    one_hot = np.eye(proba.shape[1])[y]
    return float(np.mean(np.sum((proba - one_hot) ** 2, axis=1)))


def _hit_rate(proba: np.ndarray, y: np.ndarray) -> float:
    return float((np.argmax(proba, axis=1) == y).mean())


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def _sample_grid(grid: dict, n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    keys = list(grid.keys())
    seen: set[tuple] = set()
    samples: list[dict] = []
    attempts = 0
    while len(samples) < n and attempts < n * 50:
        combo = tuple(rng.choice(grid[k]) for k in keys)
        if combo not in seen:
            seen.add(combo)
            samples.append(dict(zip(keys, combo)))
        attempts += 1
    return samples


# ---------------------------------------------------------------------------
# OOF evaluation
# ---------------------------------------------------------------------------

def _oof_eval(X: np.ndarray, y: np.ndarray, params: dict) -> tuple[float, float]:
    tss = TimeSeriesSplit(n_splits=N_SPLITS)
    # Uniform prior for the initial training rows that are never in a val fold
    oof = np.full((len(X), 3), 1.0 / 3)
    for tr_idx, val_idx in tss.split(X):
        model = XGBClassifier(
            **params,
            eval_metric="mlogloss",
            random_state=RANDOM_SEED,
            n_jobs=-1,
        )
        model.fit(X[tr_idx], y[tr_idx])
        oof[val_idx] = model.predict_proba(X[val_idx])
    return _brier_multiclass(oof, y), _hit_rate(oof, y)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "results.csv")
    )

    print("Loading results.csv...")
    df = pd.read_csv(results_path, parse_dates=["match_date"], dtype={"referee": str})
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])
    print(f"  {len(df):,} matches across {df['league'].nunique()} leagues")

    xg_lookup: dict = {}
    xg_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "results_with_xg.csv")
    )
    if os.path.exists(xg_path):
        xg_df = pd.read_csv(xg_path, parse_dates=["match_date"])
        xg_df = xg_df.dropna(subset=["home_xg", "away_xg", "xg_diff"])
        for _, r in xg_df.iterrows():
            key = (r["match_date"].date(), r["home_team"], r["away_team"], r["league"])
            xg_lookup[key] = (float(r["home_xg"]), float(r["away_xg"]), float(r["xg_diff"]))
        print(f"  Loaded {len(xg_lookup):,} xG records")

    print("\nBuilding features (63-feature set + rolling DC)...")
    feat_df, _ = build_all_features(df, xg_lookup)
    feat_df = feat_df[feat_df["match_date"] >= "2014-08-01"].reset_index(drop=True)
    print(f"  Filtered to xG era: {len(feat_df):,} matches")

    model_df = feat_df.iloc[COLD_START:].reset_index(drop=True)
    model_df["target"] = model_df["result"].map(RESULT_MAP)

    holdout_split = int(len(model_df) * 0.80)
    train_df = model_df.iloc[:holdout_split].reset_index(drop=True)
    print(
        f"  Training set: {len(train_df):,} matches "
        f"({train_df['match_date'].min().date()} → {train_df['match_date'].max().date()})\n"
    )

    X = train_df[FEATURE_COLS].values
    y = train_df["target"].values

    combos = _sample_grid(PARAM_GRID, N_TRIALS, RANDOM_SEED)
    print(f"Running {len(combos)} random trials ({N_SPLITS}-fold TimeSeriesSplit OOF)...\n")

    records: list[dict] = []
    t0 = time.time()

    for idx, params in enumerate(combos):
        t_trial = time.time()
        brier, hit = _oof_eval(X, y, params)
        trial_elapsed = time.time() - t_trial

        records.append({**params, "brier": brier, "hit_rate": hit})

        if (idx + 1) % 5 == 0 or (idx + 1) == len(combos):
            total_elapsed = time.time() - t0
            param_str = "  ".join(f"{k}={v}" for k, v in params.items())
            print(
                f"  [{idx + 1:>2}/{len(combos)}]  "
                f"brier={brier:.6f}  hit={hit:.4f}  "
                f"trial={trial_elapsed:.1f}s  total={total_elapsed:.0f}s  "
                f"{param_str}"
            )

    results_df = pd.DataFrame(records).sort_values("brier").reset_index(drop=True)

    # ------------------------------------------------------------------
    # Results table
    # ------------------------------------------------------------------
    print("\n" + "=" * 82)
    print(
        f"TOP 10 BY 3-OUTCOME BRIER (lower is better)  "
        f"—  {len(combos)} trials, {N_SPLITS}-fold OOF"
    )
    print("=" * 82)
    print(
        f"  {'#':<3}  {'n_est':>5}  {'depth':>5}  {'lr':>5}  "
        f"{'sub':>4}  {'col':>4}  {'mcw':>3}  {'brier':>10}  {'hit':>7}"
    )
    print("  " + "-" * 58)
    for i, row in results_df.head(10).iterrows():
        marker = "  ◀ best" if i == 0 else ""
        print(
            f"  {i + 1:<3}  {int(row.n_estimators):>5}  {int(row.max_depth):>5}  "
            f"{row.learning_rate:>5.2f}  {row.subsample:>4.1f}  "
            f"{row.colsample_bytree:>4.1f}  {int(row.min_child_weight):>3}  "
            f"{row.brier:>10.6f}  {row.hit_rate:>7.4f}{marker}"
        )

    # ------------------------------------------------------------------
    # Best vs. current ensemble_v2 params
    # ------------------------------------------------------------------
    best = results_df.iloc[0]

    print("\n" + "=" * 82)
    print("BEST COMBINATION")
    print("=" * 82)
    for k in PARAM_GRID:
        changed = "  ◀ changed" if best[k] != CURRENT_PARAMS[k] else ""
        print(f"  {k:<20s} : {best[k]}{changed}")
    print(f"  {'brier':<20s} : {best.brier:.6f}")
    print(f"  {'hit_rate':<20s} : {best.hit_rate:.4f}")

    current_row = results_df[
        (results_df["n_estimators"]    == CURRENT_PARAMS["n_estimators"])    &
        (results_df["max_depth"]       == CURRENT_PARAMS["max_depth"])       &
        (results_df["learning_rate"]   == CURRENT_PARAMS["learning_rate"])   &
        (results_df["subsample"]       == CURRENT_PARAMS["subsample"])       &
        (results_df["colsample_bytree"]== CURRENT_PARAMS["colsample_bytree"])&
        (results_df["min_child_weight"]== CURRENT_PARAMS["min_child_weight"])
    ]
    if not current_row.empty:
        cur = current_row.iloc[0]
        print(f"\n  vs. current ensemble_v2 params (n_est=500, depth=5, lr=0.03, "
              f"sub=0.8, col=0.7, mcw=3):")
        print(f"    Brier improvement : {cur.brier - best.brier:+.6f}  "
              f"({'✓ better' if best.brier < cur.brier else '✗ no gain'})")
        print(f"    Hit rate change   : {best.hit_rate - cur.hit_rate:+.4f}")
    else:
        print(
            "\n  Current ensemble_v2 params were not sampled in this run. "
            "Re-run with a different seed or add them manually to PARAM_GRID."
        )
    print("=" * 82)

    out_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "hyperparam_results.csv")
    )
    results_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(results_df)} trial results to {out_path}")
    print(f"Total elapsed: {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
