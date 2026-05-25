import math
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app

accumulator_bp = Blueprint("accumulator", __name__)


def _clean(records):
    """Replace float NaN with None so jsonify serialises as null, not NaN."""
    return [
        {k: None if isinstance(v, float) and math.isnan(v) else v for k, v in row.items()}
        for row in records
    ]


def ok(data):
    return jsonify({
        "success": True,
        "data": data,
        "meta": {"count": len(data), "generated_at": datetime.now(timezone.utc).isoformat()},
    })


@accumulator_bp.get("/accumulator")
def get_accumulators():
    df = current_app.config["DATA"]["accumulator_bets"].copy()

    try:
        n_legs = int(request.args.get("n_legs", 2))
        limit = int(request.args.get("limit", 20))
    except ValueError:
        return jsonify({"success": False, "error": "Invalid query parameter"}), 400

    if n_legs not in (2, 3):
        return jsonify({"success": False, "error": "n_legs must be 2 or 3"}), 400

    df = df[df["n_legs"] == n_legs]
    df = df.sort_values("acca_ev", ascending=False).head(limit)
    return ok(_clean(df.to_dict(orient="records")))


@accumulator_bp.get("/accumulator/best")
def get_best_accumulators():
    df = current_app.config["DATA"]["accumulator_bets"].copy()
    df = df.sort_values("acca_ev", ascending=False).head(10)
    return ok(_clean(df.to_dict(orient="records")))
