from datetime import datetime, timezone
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
