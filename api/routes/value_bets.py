from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app
import numpy as np

value_bets_bp = Blueprint("value_bets", __name__)

def ok(data):
    return jsonify({
        "success": True,
        "data": data,
        "meta": {"count": len(data), "generated_at": datetime.now(timezone.utc).isoformat()},
    })


@value_bets_bp.get("/value-bets")
def get_value_bets():
    df = current_app.config["DATA"]["value_bets"].copy()

    try:
        min_edge = float(request.args.get("min_edge", 0.05))
        limit = int(request.args.get("limit", 50))
    except ValueError:
        return jsonify({"success": False, "error": "Invalid query parameter"}), 400

    league = request.args.get("league")
    outcome = request.args.get("outcome")

    df = df[df["edge"] >= min_edge]
    if league:
        df = df[df["league"].str.lower() == league.lower()]
    if outcome:
        df = df[df["outcome"].str.upper() == outcome.upper()]

    df = df.sort_values("edge", ascending=False).head(limit)
    return ok(df.to_dict(orient="records"))


@value_bets_bp.get("/value-bets/summary")
def get_summary():
    df = current_app.config["DATA"]["value_bets"].copy()

    total_bets = len(df)
    win_rate = round(df["won"].mean(), 4) if "won" in df.columns else None

    if "profit_flat" in df.columns:
        roi = round(df["profit_flat"].sum() / total_bets, 4) if total_bets else 0
    else:
        roi = None

    mean_clv = round(df["clv"].mean(), 4) if "clv" in df.columns else None

    if "profit_flat" in df.columns and total_bets > 1:
        returns = df["profit_flat"]
        sharpe = round(returns.mean() / returns.std(), 4) if returns.std() > 0 else None
        cumulative = np.cumsum(returns.values)
        running_max = np.maximum.accumulate(cumulative)
        max_drawdown = round(float((running_max - cumulative).max()), 4)
    else:
        sharpe = None
        max_drawdown = None

    result = {
        "total_bets": total_bets,
        "win_rate": win_rate,
        "roi": roi,
        "mean_clv": mean_clv,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
    }

    return jsonify({
        "success": True,
        "data": result,
        "meta": {"generated_at": datetime.now(timezone.utc).isoformat()},
    })


@value_bets_bp.get("/value-bets/kelly")
def get_kelly():
    df = current_app.config["DATA"]["kelly_simulation"]
    return ok(df.to_dict(orient="records"))
