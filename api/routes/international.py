from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app
import numpy as np

international_bp = Blueprint("international", __name__)

# Bracket definition mirrored from worldcup_knockout_simulator.py.
# Tie order determines the bracket tree: adjacent pairs meet in each successive round.
_BRACKET = [
    {"id": 1,  "team1": "Canada",               "team2": "South Africa",          "date": "2026-06-28"},
    {"id": 2,  "team1": "Mexico",               "team2": "Bosnia and Herzegovina", "date": "2026-06-30"},
    {"id": 3,  "team1": "Brazil",               "team2": "Japan",                 "date": "2026-06-29"},
    {"id": 4,  "team1": "Morocco",              "team2": "Netherlands",           "date": "2026-06-29"},
    {"id": 5,  "team1": "Paraguay",             "team2": "Germany",               "date": "2026-06-29"},
    {"id": 6,  "team1": "United States",        "team2": "Ecuador",               "date": "2026-07-01"},
    {"id": 7,  "team1": "Australia",            "team2": "Ivory Coast",           "date": "2026-07-01"},
    {"id": 8,  "team1": "Switzerland",          "team2": "Sweden",                "date": "2026-07-02"},
    {"id": 9,  "team1": "Belgium",              "team2": "Cape Verde",            "date": "2026-07-02"},
    {"id": 10, "team1": "Spain",                "team2": "Egypt",                 "date": "2026-07-03"},
    {"id": 11, "team1": "France",               "team2": "Austria",               "date": "2026-07-03"},
    {"id": 12, "team1": "Argentina",            "team2": "Norway",                "date": "2026-07-04"},
    {"id": 13, "team1": "Senegal",              "team2": "Algeria",               "date": "2026-07-04"},
    {"id": 14, "team1": "England",              "team2": "Portugal",              "date": "2026-07-05"},
    {"id": 15, "team1": "Colombia",             "team2": "Croatia",               "date": "2026-07-05"},
    {"id": 16, "team1": "Ghana",                "team2": "DR Congo",              "date": "2026-07-06"},
]


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


@international_bp.get("/worldcup/bracket")
def get_worldcup_bracket():
    data = current_app.config["DATA"]
    sims_df  = data.get("worldcup_bracket_sims")
    probs_df = data.get("worldcup_match_probs")
    elo_df   = data["international_elo_ratings"]

    if sims_df is None or sims_df.empty or probs_df is None or probs_df.empty:
        return jsonify({"success": False, "error": "Bracket simulation data not yet generated"}), 503

    elo_lookup  = dict(zip(elo_df["team"], elo_df["elo_rating"].astype(float)))
    conf_lookup = dict(zip(elo_df["team"], elo_df["confederation"]))

    # Build R32 tie list
    probs_by_id = {int(r["tie_id"]): r for r in probs_df.to_dict(orient="records")}
    r32 = []
    for tie in _BRACKET:
        p = probs_by_id.get(tie["id"], {})
        winner = p.get("winner") or None
        score  = p.get("score")  or None
        # Normalise score to winner-first display ("0-1" for Canada → "1-0")
        display_score = None
        if winner and score and "pens" not in str(score):
            parts = str(score).split("-")
            if len(parts) == 2:
                h, a = int(parts[0]), int(parts[1])
                display_score = f"{a}-{h}" if winner == tie["team2"] else f"{h}-{a}"
        elif score:
            display_score = score

        r32.append({
            "tie_id":          tie["id"],
            "team1":           tie["team1"],
            "team2":           tie["team2"],
            "team1_elo":       round(elo_lookup.get(tie["team1"], 1500), 1),
            "team2_elo":       round(elo_lookup.get(tie["team2"], 1500), 1),
            "team1_conf":      conf_lookup.get(tie["team1"], ""),
            "team2_conf":      conf_lookup.get(tie["team2"], ""),
            "team1_win_pct":   float(p.get("team1_win_pct", 50.0)),
            "team2_win_pct":   float(p.get("team2_win_pct", 50.0)),
            "settled":         bool(p.get("settled", False)),
            "winner":          winner,
            "score":           display_score,
            "date":            tie["date"],
            "bracket_half":    "left" if tie["id"] <= 8 else "right",
        })

    # Team paths (sorted by champion probability)
    team_paths = sims_df.sort_values("champion_pct", ascending=False).to_dict(orient="records")

    # Draw-side analysis: remaining teams (not yet eliminated) in each half
    settled_winners = {
        r["tie_id"]: r["winner"]
        for r in probs_df.to_dict(orient="records")
        if r.get("settled") and r.get("winner")
    }
    eliminated = set()
    for tie in _BRACKET:
        w = settled_winners.get(tie["id"])
        if w:
            loser = tie["team2"] if w == tie["team1"] else tie["team1"]
            eliminated.add(loser)

    halves = {"left": [], "right": []}
    for tie in _BRACKET:
        half = "left" if tie["id"] <= 8 else "right"
        for team in (tie["team1"], tie["team2"]):
            if team not in eliminated:
                halves[half].append({
                    "team": team,
                    "elo":  round(elo_lookup.get(team, 1500), 1),
                    "confederation": conf_lookup.get(team, ""),
                })

    draw_analysis = {}
    for half, teams in halves.items():
        elos = [t["elo"] for t in teams]
        draw_analysis[half] = {
            "teams":    sorted(teams, key=lambda x: -x["elo"]),
            "avg_elo":  round(sum(elos) / len(elos), 1) if elos else 0,
            "count":    len(teams),
        }

    return jsonify({
        "success": True,
        "data": {
            "r32":          r32,
            "team_paths":   team_paths,
            "draw_analysis": draw_analysis,
        },
        "meta": {"generated_at": datetime.now(timezone.utc).isoformat()},
    })


@international_bp.get("/worldcup/team-path")
def get_worldcup_team_path():
    team = request.args.get("team", "").strip()
    if not team:
        return jsonify({"success": False, "error": "team parameter is required"}), 400

    sims_df = current_app.config["DATA"].get("worldcup_bracket_sims")
    if sims_df is None or sims_df.empty:
        return jsonify({"success": False, "error": "Bracket simulation data not yet generated"}), 503

    row = sims_df[sims_df["team"] == team]
    if row.empty:
        return jsonify({"success": False, "error": f"Team '{team}' not found in bracket"}), 404

    record = row.iloc[0].to_dict()

    # Enrich with bracket context (which R32 tie, opponent)
    bracket_tie = next(
        (t for t in _BRACKET if t["team1"] == team or t["team2"] == team), None
    )
    if bracket_tie:
        opponent = bracket_tie["team2"] if bracket_tie["team1"] == team else bracket_tie["team1"]
        record["r32_tie_id"]  = bracket_tie["id"]
        record["r32_opponent"] = opponent
        record["r32_date"]    = bracket_tie["date"]

    return jsonify({
        "success": True,
        "data":   record,
        "meta":   {"generated_at": datetime.now(timezone.utc).isoformat()},
    })
