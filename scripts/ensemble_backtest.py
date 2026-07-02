"""
ensemble_backtest.py

Walk-forward backtest of the full stacking ensemble (XGBoost + LogisticRegression
meta-learner). Features are built once via build_all_features() — the pass is
already causal (features at row i use only data from rows 0..i-1), so no future
leakage regardless of how the resulting matrix is sliced for each fold.

Fold structure (season start year extracted from the 'season' column):
  Fold 1: train < 2020, test == 2020
  Fold 2: train < 2021, test == 2021
  Fold 3: train < 2022, test == 2022
  Fold 4: train < 2023, test == 2023
  Fold 5: train < 2024, test == 2024

Per fold:
  1. 5-fold TimeSeriesSplit OOF XGBoost on train set → 3-column meta-features
  2. Full XGBoost on entire train set → 3-column meta-features for test set
  3. LogisticRegression (+ StandardScaler) meta-learner fit on OOF meta-features
  4. Meta-learner predicts test set; predictions accumulated

Output: data/processed/ensemble_backtest_predictions.csv
"""

import os
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ensemble_v2 import (  # noqa: E402
    COLD_START, FEATURE_COLS, RESULT_INV, RESULT_MAP, STACK_COLS,
    build_all_features, generate_oof_xgb,
    _build_stack, _make_xgb,
)

# ── Config ────────────────────────────────────────────────────────────────────

TEST_SEASON_YEARS = [2020, 2021, 2022, 2023, 2024]
XG_START_DATE     = "2014-08-01"
N_OOF_SPLITS      = 5


# ── Helpers ───────────────────────────────────────────────────────────────────

def _season_start_year(season) -> int:
    """Extract starting calendar year from '2020-21' or '2020'."""
    return int(str(season)[:4])


def _brier_3outcome(proba: np.ndarray, actual: pd.Series) -> float:
    """Full 3-outcome Brier score. proba columns must be [P(A), P(D), P(H)]."""
    oh = (actual.values == "H").astype(float)
    od = (actual.values == "D").astype(float)
    oa = (actual.values == "A").astype(float)
    return float(
        ((proba[:, 2] - oh) ** 2
         + (proba[:, 1] - od) ** 2
         + (proba[:, 0] - oa) ** 2).mean()
    )


def _brier_elo(home_expected: np.ndarray, actual: pd.Series) -> float:
    """Simplified 2-outcome Brier for the Elo baseline (consistent with backtest.py)."""
    ahs = actual.map({"H": 1.0, "D": 0.5, "A": 0.0}).values
    return float(((home_expected - ahs) ** 2).mean())


def _hit_nondraw(predicted: np.ndarray, actual: pd.Series) -> tuple[float, int]:
    """Hit rate restricted to matches where actual result is not a draw."""
    mask = actual.values != "D"
    n    = int(mask.sum())
    if n == 0:
        return 0.0, 0
    rate = float((predicted[mask] == actual.values[mask]).mean())
    return rate, n


def _make_meta() -> Pipeline:
    """Meta-learner: LogisticRegression in a StandardScaler pipeline.
    Identical to ensemble_v2.py main()."""
    return Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(C=1.0, max_iter=1000, random_state=42)),
    ])


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    base         = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "results.csv")
    )

    # ── Load raw match data ───────────────────────────────────────────────
    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(
        subset=["home_team", "away_team", "home_goals", "away_goals", "result"]
    )
    print(f"Loaded {len(df):,} matches across {df['league'].nunique()} leagues\n")

    # ── xG lookup (optional — xG features fall back to defaults if absent) ─
    xg_lookup: dict = {}
    xg_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed", "results_with_xg.csv")
    )
    if os.path.exists(xg_path):
        xg_df = pd.read_csv(xg_path, parse_dates=["match_date"])
        xg_df = xg_df.dropna(subset=["home_xg", "away_xg", "xg_diff"])
        for _, r in xg_df.iterrows():
            key = (r["match_date"].date(), r["home_team"], r["away_team"], r["league"])
            xg_lookup[key] = (
                float(r["home_xg"]), float(r["away_xg"]), float(r["xg_diff"])
            )
        print(f"Loaded {len(xg_lookup):,} xG records\n")
    else:
        print("Warning: results_with_xg.csv not found — xG features will use defaults\n")

    # ── Build all 48 features in one causal pass ──────────────────────────
    print(f"Building {len(FEATURE_COLS)}-feature matrix for {len(df):,} matches"
          f" (single causal pass)...")
    feat_df = build_all_features(df, xg_lookup)
    print()

    # ── Filter to xG era + drop cold start ───────────────────────────────
    feat_df = feat_df[feat_df["match_date"] >= XG_START_DATE].reset_index(drop=True)
    feat_df = feat_df.iloc[COLD_START:].reset_index(drop=True)
    feat_df["target"]      = feat_df["result"].map(RESULT_MAP)
    feat_df["season_year"] = feat_df["season"].apply(_season_start_year)

    print(
        f"Modelling set: {len(feat_df):,} matches  "
        f"({feat_df['match_date'].min().date()} → "
        f"{feat_df['match_date'].max().date()})"
    )
    print(
        f"Meta-learner inputs ({len(STACK_COLS)} features): "
        f"{', '.join(STACK_COLS)}\n"
    )

    # ── Walk-forward folds ────────────────────────────────────────────────
    all_preds: list[pd.DataFrame] = []

    for test_year in TEST_SEASON_YEARS:
        train_df = feat_df[feat_df["season_year"] <  test_year].reset_index(drop=True)
        test_df  = feat_df[feat_df["season_year"] == test_year].reset_index(drop=True)

        if len(train_df) == 0 or len(test_df) == 0:
            print(f"Fold {test_year}: insufficient data — skipping\n")
            continue

        print(f"{'='*60}")
        print(
            f"Fold: test {test_year}  "
            f"(train={len(train_df):,}  test={len(test_df):,})"
        )
        print(
            f"  Train: {train_df['match_date'].min().date()} → "
            f"{train_df['match_date'].max().date()}"
        )
        print(
            f"  Test:  {test_df['match_date'].min().date()} → "
            f"{test_df['match_date'].max().date()}"
        )

        X_train = train_df[FEATURE_COLS].values
        y_train = train_df["target"].values
        X_test  = test_df[FEATURE_COLS].values

        # Step 1: OOF XGBoost on train → 3-column meta-features for meta-learner
        print(f"  OOF XGBoost ({N_OOF_SPLITS}-fold TimeSeriesSplit)...")
        oof_proba   = generate_oof_xgb(X_train, y_train, n_splits=N_OOF_SPLITS)
        train_stack = _build_stack(train_df, oof_proba)

        # Step 2: Full XGBoost on all train → 3-column meta-features for test
        print(f"  Full XGBoost on train set...")
        xgb_full       = _make_xgb()
        xgb_full.fit(X_train, y_train)
        test_xgb_proba = xgb_full.predict_proba(X_test)
        test_stack     = _build_stack(test_df, test_xgb_proba)

        # Step 3: Meta-learner fit on OOF stack, predict test stack
        print(f"  Meta-learner (LogisticRegression + StandardScaler)...")
        meta       = _make_meta()
        meta.fit(train_stack, y_train)
        # meta_proba columns follow sklearn class order: [P(A)=0, P(D)=1, P(H)=2]
        meta_proba = meta.predict_proba(test_stack)
        meta_pred  = np.array(
            [RESULT_INV[int(i)] for i in np.argmax(meta_proba, axis=1)]
        )

        # Elo baseline on the same test window
        elo_pred = np.where(test_df["home_expected"].values > 0.5, "H", "A")

        fold_ens_hit,  n_nd = _hit_nondraw(meta_pred, test_df["result"])
        fold_elo_hit,  _    = _hit_nondraw(elo_pred,  test_df["result"])
        fold_ens_brier      = _brier_3outcome(meta_proba, test_df["result"])
        fold_elo_brier      = _brier_elo(test_df["home_expected"].values, test_df["result"])

        print(
            f"  Ensemble : hit={fold_ens_hit:.4f} ({fold_ens_hit*100:.1f}%)  "
            f"brier3={fold_ens_brier:.6f}  n_nondraw={n_nd:,}"
        )
        print(
            f"  Elo base : hit={fold_elo_hit:.4f} ({fold_elo_hit*100:.1f}%)  "
            f"brier2={fold_elo_brier:.6f}\n"
        )

        # Accumulate fold
        fold_df = test_df[
            ["match_date", "season", "league",
             "home_team", "away_team", "home_expected", "result"]
        ].copy().rename(columns={"result": "actual_result"})

        fold_df["season_year"]        = test_year
        fold_df["p_home_ensemble"]    = meta_proba[:, 2]
        fold_df["p_draw_ensemble"]    = meta_proba[:, 1]
        fold_df["p_away_ensemble"]    = meta_proba[:, 0]
        fold_df["predicted_ensemble"] = meta_pred
        fold_df["predicted_elo"]      = elo_pred
        fold_df["correct_ensemble"]   = (
            meta_pred == fold_df["actual_result"].values
        ).astype(int)
        fold_df["correct_elo"] = (
            elo_pred == fold_df["actual_result"].values
        ).astype(int)

        all_preds.append(fold_df)

    if not all_preds:
        print("No predictions accumulated — check that season data covers TEST_SEASON_YEARS.")
        return

    out_df = pd.concat(all_preds, ignore_index=True)

    # ── Aggregate metrics across all folds ────────────────────────────────
    actual       = out_df["actual_result"]
    # Reconstruct [P(A), P(D), P(H)] matrix for 3-outcome Brier
    proba_all    = out_df[["p_away_ensemble", "p_draw_ensemble", "p_home_ensemble"]].values
    pred_ens_all = out_df["predicted_ensemble"].values
    pred_elo_all = out_df["predicted_elo"].values

    total_ens_hit,  n_nd_total = _hit_nondraw(pred_ens_all, actual)
    total_elo_hit,  _          = _hit_nondraw(pred_elo_all, actual)
    total_ens_brier            = _brier_3outcome(proba_all, actual)
    total_elo_brier            = _brier_elo(out_df["home_expected"].values, actual)

    # ── Summary report ────────────────────────────────────────────────────
    print("=" * 60)
    print("ENSEMBLE WALK-FORWARD BACKTEST REPORT")
    print("=" * 60)
    print(f"Total matches predicted : {len(out_df):,}")
    print(f"Non-draw matches        : {n_nd_total:,}")
    print(f"Test seasons            : {TEST_SEASON_YEARS}\n")

    print(f"  {'Model':<22}  {'Hit Rate':>10}  {'Brier':>12}  Note")
    print(f"  {'-'*62}")
    print(
        f"  {'Ensemble (stacked)':<22}  {total_ens_hit:>10.4f}  "
        f"{total_ens_brier:>12.6f}  3-outcome"
    )
    print(
        f"  {'Elo baseline':<22}  {total_elo_hit:>10.4f}  "
        f"{total_elo_brier:>12.6f}  2-outcome (home_expected)"
    )
    d_hit   = total_ens_hit  - total_elo_hit
    d_brier = total_ens_brier - total_elo_brier
    print(f"\n  Ensemble vs Elo:  hit {d_hit:+.4f}  brier {d_brier:+.6f}")

    print(f"\n--- Hit rate by test season (non-draw) ---")
    for yr, grp in out_df.groupby("season_year"):
        act    = grp["actual_result"]
        e_hit, n = _hit_nondraw(grp["predicted_ensemble"].values, act)
        o_hit, _ = _hit_nondraw(grp["predicted_elo"].values,      act)
        print(
            f"  {yr}  ensemble={e_hit:.4f} ({e_hit*100:.1f}%)  "
            f"elo={o_hit:.4f} ({o_hit*100:.1f}%)  n={n:,}"
        )

    print(f"\n--- Hit rate by league (non-draw, all folds) ---")
    for league, grp in out_df.groupby("league"):
        act    = grp["actual_result"]
        e_hit, n = _hit_nondraw(grp["predicted_ensemble"].values, act)
        o_hit, _ = _hit_nondraw(grp["predicted_elo"].values,      act)
        print(
            f"  {league:<14}  ensemble={e_hit:.4f} ({e_hit*100:.1f}%)  "
            f"elo={o_hit:.4f} ({o_hit*100:.1f}%)  n={n:,}"
        )

    print("=" * 60)

    # ── Save accumulated predictions ──────────────────────────────────────
    out_path = os.path.normpath(
        os.path.join(base, "..", "data", "processed",
                     "ensemble_backtest_predictions.csv")
    )
    out_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(out_df):,} predictions to {out_path}")


if __name__ == "__main__":
    main()
