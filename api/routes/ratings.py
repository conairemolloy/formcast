from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app
import pandas as pd

ratings_bp = Blueprint("ratings", __name__)

def ok(data):
    return jsonify({
        "success": True,
        "data": data,
        "meta": {"count": len(data), "generated_at": datetime.now(timezone.utc).isoformat()},
    })


@ratings_bp.get("/ratings")
def get_ratings():
    df = current_app.config["DATA"]["elo_ratings"].copy()
    league = request.args.get("league")
    if league and "league" in df.columns:
        df = df[df["league"].str.lower() == league.lower()]
    df = df.sort_values("elo_rating", ascending=False)
    return ok(df.to_dict(orient="records"))


@ratings_bp.get("/ratings/glicko2")
def get_glicko2():
    df = current_app.config["DATA"]["glicko2_ratings"]
    return ok(df.to_dict(orient="records"))


@ratings_bp.get("/ratings/btl")
def get_btl():
    df = current_app.config["DATA"]["btl_ratings"]
    return ok(df.to_dict(orient="records"))


@ratings_bp.get("/ratings/history")
def get_ratings_history():
    team = request.args.get("team", "").strip()
    if not team:
        return jsonify({"success": False, "error": "team parameter required"}), 400

    df = current_app.config["DATA"]["elo_predictions"]
    team_lower = team.lower()
    mask = (df["home_team"].str.lower() == team_lower) | (df["away_team"].str.lower() == team_lower)
    team_df = df[mask].copy()

    if team_df.empty:
        return jsonify({"success": False, "error": f"Team '{team}' not found"}), 404

    team_df["elo"] = team_df.apply(
        lambda r: r["home_elo_before"] if r["home_team"].lower() == team_lower else r["away_elo_before"],
        axis=1,
    )

    team_df = team_df.dropna(subset=["match_date", "season"]).sort_values("match_date")

    history = (
        team_df.groupby("season", sort=False)["elo"]
        .last()
        .reset_index()
        .rename(columns={"elo": "elo_rating"})
        .sort_values("season")
    )
    history["elo_rating"] = history["elo_rating"].round(1)

    return ok(history.to_dict(orient="records"))


@ratings_bp.get("/ratings/<team>")
def get_team_ratings(team):
    elo = current_app.config["DATA"]["elo_ratings"]
    glicko = current_app.config["DATA"]["glicko2_ratings"]
    btl = current_app.config["DATA"]["btl_ratings"]

    elo_row = elo[elo["team"].str.lower() == team.lower()]
    glicko_row = glicko[glicko["team"].str.lower() == team.lower()]
    btl_row = btl[btl["team"].str.lower() == team.lower()]

    if elo_row.empty and glicko_row.empty and btl_row.empty:
        return jsonify({"success": False, "error": f"Team '{team}' not found"}), 404

    result = {"team": team}
    if not elo_row.empty:
        result["elo"] = elo_row.iloc[0].to_dict()
    if not glicko_row.empty:
        result["glicko2"] = glicko_row.iloc[0].to_dict()
    if not btl_row.empty:
        result["btl"] = btl_row.iloc[0].to_dict()

    return jsonify({
        "success": True,
        "data": result,
        "meta": {"generated_at": datetime.now(timezone.utc).isoformat()},
    })
