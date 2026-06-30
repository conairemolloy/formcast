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


@international_bp.get("/team/profile")
def get_international_team_profile():
    team = request.args.get("team", "").strip()
    if not team:
        return jsonify({"success": False, "error": "team parameter is required"}), 400

    df = current_app.config["DATA"]["international_results"]

    matches = df[(df["home_team"] == team) | (df["away_team"] == team)].copy()

    if matches.empty:
        return jsonify({"success": False, "error": "Team not found"}), 404

    matches_played   = len(matches)
    first_match_date = str(matches["date"].min())
    last_match_date  = str(matches["date"].max())

    # Build team-perspective columns vectorised
    home_mask = matches["home_team"] == team

    matches["opponent"]       = matches["away_team"].where(home_mask, matches["home_team"])
    matches["venue"]          = "N"
    matches.loc[ home_mask & ~matches["neutral"], "venue"] = "H"
    matches.loc[~home_mask & ~matches["neutral"], "venue"] = "A"
    matches["team_score"]     = matches["home_score"].where(home_mask, matches["away_score"])
    matches["opponent_score"] = matches["away_score"].where(home_mask, matches["home_score"])

    raw  = matches["result"]
    won  = ((raw == "H") &  home_mask) | ((raw == "A") & ~home_mask)
    lost = ((raw == "A") &  home_mask) | ((raw == "H") & ~home_mask)
    matches["team_result"] = "D"
    matches.loc[won,  "team_result"] = "W"
    matches.loc[lost, "team_result"] = "L"

    recent = (
        matches.sort_values("date", ascending=False)
        .head(10)[["date", "opponent", "venue", "team_score", "opponent_score", "team_result", "tournament"]]
        .rename(columns={"team_result": "result"})
        .to_dict(orient="records")
    )

    return jsonify({
        "success": True,
        "data": {
            "team":             team,
            "matches_played":   matches_played,
            "first_match_date": first_match_date,
            "last_match_date":  last_match_date,
            "recent_results":   recent,
        },
        "meta": {"generated_at": datetime.now(timezone.utc).isoformat()},
    })
