from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app

predictions_bp = Blueprint("predictions", __name__)

def ok(data):
    return jsonify({
        "success": True,
        "data": data,
        "meta": {"count": len(data), "generated_at": datetime.now(timezone.utc).isoformat()},
    })


@predictions_bp.get("/predictions")
def get_predictions():
    df = current_app.config["DATA"]["ensemble_v2_predictions"].copy()

    league = request.args.get("league")
    date = request.args.get("date")

    if league:
        df = df[df["league"].str.lower() == league.lower()]
    if date:
        df = df[df["match_date"] == date]

    return ok(df.to_dict(orient="records"))


@predictions_bp.get("/predictions/value-bets")
def get_prediction_value_bets():
    df = current_app.config["DATA"]["value_bets"].copy()

    try:
        min_edge = float(request.args.get("min_edge", 0.05))
    except ValueError:
        return jsonify({"success": False, "error": "Invalid min_edge"}), 400

    outcome = request.args.get("outcome")

    df = df[df["edge"] >= min_edge]
    if outcome:
        df = df[df["outcome"].str.upper() == outcome.upper()]

    df = df.sort_values("edge", ascending=False)
    return ok(df.to_dict(orient="records"))


STAT_COLS = [
    "home_shots", "away_shots", "home_shots_target", "away_shots_target",
    "home_corners", "away_corners", "home_yellows", "away_yellows",
    "home_reds", "away_reds",
]

MATCH_RETURN_COLS = [
    "match_date", "league", "season", "home_team", "away_team",
    "home_goals", "away_goals", "result",
    "home_shots", "away_shots", "home_shots_target", "away_shots_target",
    "home_corners", "away_corners", "home_yellows", "away_yellows",
    "home_reds", "away_reds",
]


@predictions_bp.get("/matches")
def get_matches():
    df = current_app.config["DATA"]["results"].copy()

    league = request.args.get("league")
    team   = request.args.get("team")
    season = request.args.get("season")

    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        return jsonify({"success": False, "error": "Invalid limit"}), 400

    if season:
        df = df[df["season"] == season]
    if league:
        df = df[df["league"].str.lower() == league.lower()]
    if team:
        df = df[(df["home_team"].str.lower() == team.lower()) |
                (df["away_team"].str.lower() == team.lower())]

    df = df.sort_values("match_date", ascending=False)
    df = df.head(limit)

    return_cols = [c for c in MATCH_RETURN_COLS if c in df.columns]
    return ok(df[return_cols].to_dict(orient="records"))


@predictions_bp.get("/tournament")
def get_tournament():
    df = current_app.config["DATA"]["tournament_simulations"].copy()

    league = request.args.get("league")
    if league:
        df = df[df["league"].str.lower() == league.lower()]

    df = df.sort_values("current_pts", ascending=False)
    return ok(df.to_dict(orient="records"))
