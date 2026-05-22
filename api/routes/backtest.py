from datetime import datetime, timezone
import pandas as pd
from flask import Blueprint, jsonify, request, current_app

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

    return jsonify({
        "success": True,
        "data": calibration.to_dict(orient="records"),
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
