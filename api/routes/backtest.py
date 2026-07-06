from datetime import datetime, timezone
import json
import os
import joblib
import pandas as pd
from flask import Blueprint, jsonify, request, current_app
from scipy.stats import chi2, norm

backtest_bp = Blueprint("backtest", __name__)


@backtest_bp.get("/backtest")
def get_backtest():
    df = current_app.config["DATA"]["backtest_predictions"].copy()

    league = request.args.get("league")
    if league:
        df = df[df["league"].str.lower() == league.lower()]

    if df.empty:
        return jsonify({"success": False, "error": "No data found"}), 404

    overall_hit_rate = round(df["correct"].mean(), 4)
    overall_brier = round(df["brier_contribution"].mean(), 4)

    by_league = (
        df.groupby("league")
        .agg(hit_rate=("correct", "mean"), brier=("brier_contribution", "mean"), matches=("correct", "count"))
        .round(4)
        .reset_index()
        .to_dict(orient="records")
    )

    by_season = (
        df.groupby("season")
        .agg(hit_rate=("correct", "mean"), matches=("correct", "count"))
        .round(4)
        .reset_index()
        .to_dict(orient="records")
    )

    result = {
        "overall": {
            "hit_rate": overall_hit_rate,
            "brier_score": overall_brier,
            "total_matches": len(df),
        },
        "by_league": by_league,
        "by_season": by_season,
    }

    return jsonify({
        "success": True,
        "data": result,
        "meta": {"generated_at": datetime.now(timezone.utc).isoformat()},
    })


@backtest_bp.get("/backtest/calibration")
def get_calibration():
    df = current_app.config["DATA"]["ensemble_v2_predictions"].copy()

    df["actual_home"] = (df["actual_result"] == "H").astype(int)

    bin_edges = [i / 10 for i in range(11)]
    bin_labels = [f"{i * 10}–{(i + 1) * 10}%" for i in range(10)]

    df["bin"] = pd.cut(
        df["p_home"],
        bins=bin_edges,
        labels=bin_labels,
        include_lowest=True,
    )

    calibration = (
        df.groupby("bin", observed=True)
        .agg(
            mean_predicted=("p_home", "mean"),
            actual_rate=("actual_home", "mean"),
            count=("actual_home", "count"),
        )
        .round(4)
        .reset_index()
        .rename(columns={"bin": "bin_label"})
    )

    # Hosmer-Lemeshow chi-squared test
    hl_bins = calibration[calibration["count"] > 0].copy()
    obs   = hl_bins["actual_rate"] * hl_bins["count"]
    exp   = hl_bins["mean_predicted"] * hl_bins["count"]
    n_i   = hl_bins["count"]
    denom = (exp * (1 - exp / n_i)).clip(lower=1e-10)
    hl_stat = float(((obs - exp) ** 2 / denom).sum())
    hl_df   = max(1, len(hl_bins) - 2)
    hl_pval = float(1 - chi2.cdf(hl_stat, hl_df))
    hl_interp = "Well calibrated (p>0.05)" if hl_pval > 0.05 else "Poorly calibrated (p≤0.05)"

    return jsonify({
        "success": True,
        "data": {
            "bins":           calibration.to_dict(orient="records"),
            "hl_statistic":   round(hl_stat, 4),
            "hl_pvalue":      round(hl_pval, 4),
            "hl_interpretation": hl_interp,
        },
    })


@backtest_bp.get("/backtest/pnl")
def get_pnl():
    df = current_app.config["DATA"]["value_bets"].copy()
    df = df.sort_values("match_date").reset_index(drop=True)

    if df.empty:
        return jsonify({"success": False, "error": "No value bets data available"}), 404

    df["cumulative_pnl"] = df["profit_flat"].cumsum()
    df["match_number"] = range(1, len(df) + 1)

    total_bets = len(df)
    final_pnl  = round(float(df["cumulative_pnl"].iloc[-1]), 2)
    roi        = round(final_pnl / total_bets * 100, 2) if total_bets else 0.0
    win_rate   = round(float(df["won"].mean() * 100), 2)

    indices = list(range(0, total_bets, 10))
    if (total_bets - 1) not in indices:
        indices.append(total_bets - 1)

    sampled = df.iloc[indices][["match_number", "cumulative_pnl", "match_date"]].copy()
    sampled["cumulative_pnl"] = sampled["cumulative_pnl"].round(2)
    chart = sampled.rename(columns={"match_date": "date"}).to_dict(orient="records")

    return jsonify({
        "success": True,
        "data": {
            "chart":      chart,
            "total_bets": total_bets,
            "final_pnl":  final_pnl,
            "roi":        roi,
            "win_rate":   win_rate,
        },
    })


@backtest_bp.get("/backtest/dm-test")
def get_dm_test():
    data_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
    )
    path = os.path.join(data_dir, "ensemble_backtest_predictions.csv")

    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        return jsonify({"success": False, "error": "ensemble_backtest_predictions.csv not found"}), 404

    required = {"correct_ensemble", "correct_elo"}
    if not required.issubset(df.columns):
        return jsonify({"success": False, "error": f"Missing columns: {required - set(df.columns)}"}), 422

    # DM test: d_t = L(ensemble_t) - L(elo_t), L = binary squared error (1 - correct)
    d = (1 - df["correct_ensemble"]) - (1 - df["correct_elo"])
    n = len(d)
    mean_d = float(d.mean())
    var_d  = float(d.var(ddof=1))

    if var_d == 0:
        return jsonify({"success": False, "error": "Zero variance in loss differential — models are identical"}), 422

    dm_stat = mean_d / (var_d / n) ** 0.5
    p_value = float(2 * (1 - norm.cdf(abs(dm_stat))))  # two-tailed

    ensemble_better = mean_d < 0  # lower loss = better

    if p_value < 0.05:
        sig = "significantly" if p_value < 0.01 else "marginally"
        winner = "Ensemble" if ensemble_better else "Elo"
        loser  = "Elo" if ensemble_better else "Ensemble"
        interp = f"{winner} {sig} outperforms {loser} (p={p_value:.4f})"
    else:
        interp = f"No significant difference between Ensemble and Elo (p={p_value:.4f})"

    return jsonify({
        "success": True,
        "data": {
            "dm_statistic":      round(dm_stat, 4),
            "p_value":           round(p_value, 4),
            "interpretation":    interp,
            "ensemble_better":   bool(ensemble_better),
            "n_matches":         n,
            "ensemble_hit_rate": round(float(df["correct_ensemble"].mean() * 100), 2),
            "elo_hit_rate":      round(float(df["correct_elo"].mean() * 100), 2),
        },
    })


@backtest_bp.get("/backtest/feature-importance")
def get_feature_importance():
    models_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "models")
    )
    model_path   = os.path.join(models_dir, "xgb_ensemble.pkl")
    feature_path = os.path.join(models_dir, "feature_cols.json")

    if not os.path.exists(model_path):
        return jsonify({"success": False, "error": "xgb_ensemble.pkl not found"}), 404
    if not os.path.exists(feature_path):
        return jsonify({"success": False, "error": "feature_cols.json not found"}), 404

    if "xgb_ensemble" not in current_app.config:
        current_app.config["xgb_ensemble"]      = joblib.load(model_path)
        with open(feature_path) as f:
            current_app.config["xgb_feature_cols"] = json.load(f)

    model        = current_app.config["xgb_ensemble"]
    feature_cols = current_app.config["xgb_feature_cols"]

    # Model trained on numpy arrays → XGBoost internal names are f0, f1, …
    raw_scores = model.get_booster().get_score(importance_type="gain")

    scores = {
        name: float(raw_scores.get(f"f{i}", 0.0))
        for i, name in enumerate(feature_cols)
    }
    total      = sum(scores.values()) or 1.0
    normalized = {k: v / total for k, v in scores.items()}

    sorted_features = sorted(normalized.items(), key=lambda x: x[1], reverse=True)
    top30 = [
        {"feature": name, "importance": round(imp, 6), "rank": rank + 1}
        for rank, (name, imp) in enumerate(sorted_features[:30])
    ]

    return jsonify({
        "success": True,
        "data": {
            "features":   top30,
            "method":     "XGBoost gain",
            "n_features": len(feature_cols),
        },
    })


@backtest_bp.get("/backtest/clv")
def get_clv():
    df = current_app.config["DATA"]["value_bets"].copy()
    df = df.sort_values("match_date").reset_index(drop=True)

    if df.empty:
        return jsonify({"success": False, "error": "No value bets data available"}), 404

    df["cumulative_clv"] = df["clv"].cumsum()
    df["match_number"]   = range(1, len(df) + 1)

    clv_pos = df[df["clv"] > 0]
    positive_clv_bets = len(clv_pos)
    mean_clv  = round(float(df["clv"].mean()), 4)
    clv_win_rate = round(float(clv_pos["won"].mean() * 100), 2) if positive_clv_bets else 0.0
    clv_profit   = float(clv_pos["profit_flat"].sum())
    clv_roi      = round(clv_profit / positive_clv_bets * 100, 2) if positive_clv_bets else 0.0

    total = len(df)
    indices = list(range(0, total, 10))
    if (total - 1) not in indices:
        indices.append(total - 1)

    sampled = df.iloc[indices][["match_number", "cumulative_clv", "match_date"]].copy()
    sampled["cumulative_clv"] = sampled["cumulative_clv"].round(4)
    clv_chart = sampled.rename(columns={"match_date": "date"}).to_dict(orient="records")

    return jsonify({
        "success": True,
        "data": {
            "clv_chart":        clv_chart,
            "positive_clv_bets": positive_clv_bets,
            "mean_clv":         mean_clv,
            "clv_win_rate":     clv_win_rate,
            "clv_roi":          clv_roi,
        },
    })
