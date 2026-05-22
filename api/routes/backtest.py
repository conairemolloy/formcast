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
    bp = current_app.config["DATA"]["backtest_predictions"].copy()
    results = current_app.config["DATA"]["results"]

    bp = bp.merge(
        results[["match_date", "home_team", "away_team", "league",
                 "home_odds", "draw_odds", "away_odds"]],
        on=["match_date", "home_team", "away_team", "league"],
        how="left",
    )

    has_odds = bp[["home_odds", "draw_odds", "away_odds"]].notna().any(axis=1)
    bp = bp[has_odds].copy()

    if bp.empty:
        return jsonify({"success": False, "error": "No odds data available"}), 404

    bp = bp.sort_values("match_date").reset_index(drop=True)

    def _predicted_odds(row):
        if row["predicted_result"] == "H":
            return row["home_odds"]
        elif row["predicted_result"] == "D":
            return row["draw_odds"]
        return row["away_odds"]

    bp["predicted_odds"] = bp.apply(_predicted_odds, axis=1)
    bp = bp[bp["predicted_odds"].notna()].copy().reset_index(drop=True)

    bp["profit"] = bp.apply(
        lambda r: float(r["predicted_odds"]) - 1.0 if r["correct"] == 1.0 else -1.0,
        axis=1,
    )
    bp["cumulative_pnl"] = bp["profit"].cumsum()
    bp["match_number"] = range(1, len(bp) + 1)

    total_bets = len(bp)
    final_pnl  = round(float(bp["cumulative_pnl"].iloc[-1]), 2)
    roi        = round(final_pnl / total_bets * 100, 2) if total_bets else 0.0
    win_rate   = round(float(bp["correct"].mean() * 100), 2)

    step = max(50, total_bets // 500)
    indices = list(range(0, total_bets, step))
    if (total_bets - 1) not in indices:
        indices.append(total_bets - 1)

    sampled = bp.iloc[indices][["match_number", "cumulative_pnl", "match_date"]].copy()
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
