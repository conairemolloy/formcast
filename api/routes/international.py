from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app

international_bp = Blueprint("international", __name__)


def ok(data):
    return jsonify({
        "success": True,
        "data": data,
        "meta": {"count": len(data), "generated_at": datetime.now(timezone.utc).isoformat()},
    })


@international_bp.get("/ratings")
def get_international_ratings():
    df = current_app.config["DATA"]["international_elo_ratings"].copy()

    confederation = request.args.get("confederation")
    if confederation:
        df = df[df["confederation"].str.lower() == confederation.lower()]

    min_matches = request.args.get("min_matches")
    if min_matches is not None:
        try:
            min_matches = int(min_matches)
        except ValueError:
            return jsonify({"success": False, "error": "min_matches must be an integer"}), 400
        df = df[df["matches_played"] >= min_matches]

    df = df.sort_values("elo_rating", ascending=False)
    return ok(df.to_dict(orient="records"))


@international_bp.get("/confederations")
def get_confederations():
    df = current_app.config["DATA"]["international_elo_ratings"]
    counts = (
        df.groupby("confederation", sort=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    return ok(counts.to_dict(orient="records"))
