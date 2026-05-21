import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app
import pandas as pd

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


RESULTS_CSV = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "results.csv")
)

MATCH_COLS = [
    "match_date", "league", "season", "home_team", "away_team",
    "home_goals", "away_goals", "result",
    "home_shots", "away_shots", "home_shots_target", "away_shots_target",
    "home_corners", "away_corners", "home_yellows", "away_yellows",
    "home_reds", "away_reds",
]


@predictions_bp.get("/matches")
def get_matches():
    league = request.args.get("league")
    team   = request.args.get("team")
    season = request.args.get("season")

    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        return jsonify({"success": False, "error": "Invalid limit"}), 400

    all_cols = pd.read_csv(RESULTS_CSV, nrows=0).columns.tolist()
    usecols = [c for c in MATCH_COLS if c in all_cols]
    df = pd.read_csv(RESULTS_CSV, usecols=usecols)

    if season:
        df = df[df["season"] == season]
    if league:
        df = df[df["league"].str.lower() == league.lower()]
    if team:
        df = df[(df["home_team"].str.lower() == team.lower()) |
                (df["away_team"].str.lower() == team.lower())]

    df = df.sort_values("match_date", ascending=False).head(limit)

    import math
    records = []
    for row in df[usecols].to_dict(orient="records"):
        records.append({k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()})

    return ok(records)


@predictions_bp.get("/tournament")
def get_tournament():
    df = current_app.config["DATA"]["tournament_simulations"].copy()

    league = request.args.get("league")
    if league:
        df = df[df["league"].str.lower() == league.lower()]

    df = df.sort_values("current_pts", ascending=False)
    return ok(df.to_dict(orient="records"))
