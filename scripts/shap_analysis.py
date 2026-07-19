"""
SHAP feature importance analysis for the XGBoost ensemble.

Loads xgb_ensemble.pkl and rebuilds the full 85-feature training matrix via
build_all_features (same pipeline as ensemble_v2.main), then computes SHAP
values on the 10,000 most recent training rows.

Usage:
    python scripts/shap_analysis.py

Output:
    data/processed/shap_importance.csv  — full 85-feature ranking
    stdout                              — ranked table, bottom 15, Batch 2-4 spotlight
"""
import os
import sys

import joblib
import numpy as np
import pandas as pd
import shap

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)

from ensemble_v2 import (
    COLD_START,
    FEATURE_COLS,
    build_all_features,
)

SAMPLE_N   = 10_000
MODELS_DIR = os.path.join(_ROOT, "models")
DATA_DIR   = os.path.join(_ROOT, "data", "processed")
OUTPUT_CSV = os.path.join(DATA_DIR, "shap_importance.csv")

# Batch 2-4 additions to spotlight explicitly
RECENT_ADDITIONS = [
    # Batch 2 Tier 1
    "late_season_form_diff",
    "home_shot_conversion", "away_shot_conversion",
    "h2h_all_time_dominance",
    "is_derby",
    # Batch 3 — Glicko-2 venue split
    "home_g2_home", "away_g2_away", "g2_venue_diff", "away_g2_uncertainty",
    # Batch 3 — interaction terms
    "elo_x_form", "fatigue_x_congestion", "derby_x_h2h",
    # Batch 4 — stadium geography
    "away_travel_km", "altitude_diff", "home_capacity_log",
]


def _build_feature_matrix() -> pd.DataFrame:
    results_path = os.path.join(DATA_DIR, "results.csv")
    xg_path      = os.path.join(DATA_DIR, "results_with_xg.csv")

    df = pd.read_csv(results_path, parse_dates=["match_date"], dtype={"referee": str})
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])
    print(f"Loaded {len(df):,} matches from results.csv")

    xg_lookup: dict = {}
    if os.path.exists(xg_path):
        xg_df = pd.read_csv(xg_path, parse_dates=["match_date"])
        xg_df = xg_df.dropna(subset=["home_xg", "away_xg", "xg_diff"])
        for _, r in xg_df.iterrows():
            key = (r["match_date"].date(), r["home_team"], r["away_team"], r["league"])
            xg_lookup[key] = (float(r["home_xg"]), float(r["away_xg"]), float(r["xg_diff"]))
        print(f"Loaded {len(xg_lookup):,} xG records")

    print("Building 85-feature matrix via build_all_features (2-3 min)...")
    feat_df, _ = build_all_features(df, xg_lookup)

    feat_df = feat_df[feat_df["match_date"] >= "2014-08-01"].reset_index(drop=True)
    feat_df = feat_df.iloc[COLD_START:].reset_index(drop=True)
    print(f"Feature matrix ready: {len(feat_df):,} rows after 2014 filter + cold-start drop")
    return feat_df


def main() -> None:
    pkl_path = os.path.join(MODELS_DIR, "xgb_ensemble.pkl")
    if not os.path.exists(pkl_path):
        sys.exit(f"ERROR: {pkl_path} not found — run ensemble_v2.py first to generate pickles")

    print(f"Loading model: {pkl_path}")
    model = joblib.load(pkl_path)

    feat_df = _build_feature_matrix()

    # 10,000 most recent rows — representative of current model conditions
    sample = feat_df.tail(SAMPLE_N).reset_index(drop=True)
    X = sample[FEATURE_COLS].fillna(0.0).values
    print(f"\nSample: {len(X):,} rows  "
          f"({sample['match_date'].min().date()} → {sample['match_date'].max().date()})")

    print("Computing SHAP values via TreeExplainer...")
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    # shap_values is either a list of 3 arrays (one per class, each shape
    # [n_samples, n_features]) or a single 3-D array [n_samples, n_features, n_classes].
    if isinstance(shap_values, list):
        mean_abs_shap = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
    else:
        mean_abs_shap = np.abs(shap_values).mean(axis=(0, 2)) if shap_values.ndim == 3 \
            else np.abs(shap_values).mean(axis=0)

    n_features = len(FEATURE_COLS)
    importance = (
        pd.DataFrame({"feature": FEATURE_COLS, "mean_abs_shap": mean_abs_shap})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    importance.index += 1
    importance.index.name = "rank"
    importance.to_csv(OUTPUT_CSV)
    print(f"Saved to {OUTPUT_CSV}\n")

    # ------------------------------------------------------------------ #
    # Full ranking
    # ------------------------------------------------------------------ #
    bottom15_start = n_features - 14  # ranks 71-85
    print("=" * 65)
    print(f"FULL FEATURE RANKING  (sample={len(X):,} rows, mean |SHAP|)")
    print("=" * 65)
    for rank, row in importance.iterrows():
        flag = "  ◀ BOTTOM 15" if rank >= bottom15_start else ""
        print(f"  {rank:3d}.  {row['feature']:<38s}  {row['mean_abs_shap']:.6f}{flag}")

    # ------------------------------------------------------------------ #
    # Bottom 15
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 65)
    print("BOTTOM 15 — candidates for culling (review before removing)")
    print("=" * 65)
    for rank, row in importance[importance.index >= bottom15_start].iterrows():
        print(f"  {rank:3d}.  {row['feature']:<38s}  {row['mean_abs_shap']:.6f}")

    # ------------------------------------------------------------------ #
    # Batch 2-4 spotlight
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 65)
    print("BATCH 2-4 RECENT ADDITIONS — rank and signal strength")
    print("=" * 65)
    feat_to_rank = {row["feature"]: rank for rank, row in importance.iterrows()}
    feat_to_val  = {row["feature"]: row["mean_abs_shap"] for _, row in importance.iterrows()}
    for feat in RECENT_ADDITIONS:
        if feat in feat_to_rank:
            rank = feat_to_rank[feat]
            val  = feat_to_val[feat]
            tier = "TOP THIRD" if rank <= n_features // 3 else (
                   "MID THIRD" if rank <= 2 * n_features // 3 else "BOTTOM THIRD")
            print(f"  {rank:3d}/{n_features}  {tier:<12s}  {feat:<38s}  {val:.6f}")
        else:
            print(f"  ???  NOT IN FEATURE_COLS: {feat}")


if __name__ == "__main__":
    main()
