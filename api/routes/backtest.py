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
