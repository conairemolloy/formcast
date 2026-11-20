import math
import os
import sys
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app
import pandas as pd

# The API runs with api/ on sys.path; add the repo root so scripts/ is importable.
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
from scripts.league_coverage import is_covered_league  # noqa: E402

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


PREDICTION_LOG_CSV = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "prediction_log.csv")
)


def _multiclass_brier(df: pd.DataFrame) -> tuple[float | None, int]:
    """Multiclass Brier over settled log rows: mean of sum_k (p_k - 1{actual=k})^2
    for k in H/D/A. Range 0 (perfect) to 2; uniform 1/3 guessing scores 0.667.
    Rows without a H/D/A result or with unparseable probabilities are skipped."""
    probs = df[["p_home", "p_draw", "p_away"]].apply(pd.to_numeric, errors="coerce")
    rows  = df["actual_result"].isin(["H", "D", "A"]) & probs.notna().all(axis=1)
    if not rows.any():
        return None, 0
    actual = df.loc[rows, "actual_result"]
    p      = probs[rows]
    score  = ((p["p_home"] - (actual == "H")) ** 2
              + (p["p_draw"] - (actual == "D")) ** 2
              + (p["p_away"] - (actual == "A")) ** 2)
    return round(float(score.mean()), 4), int(rows.sum())


def load_prediction_log():
    """Read prediction_log.csv as strings. Returns None if the file is absent."""
    if not os.path.exists(PREDICTION_LOG_CSV):
        return None
    return pd.read_csv(PREDICTION_LOG_CSV, dtype=str).fillna("")


def derive_status(df):
    """Add a derived `status` column (settled > not_tracked > pending).
    Never written back to the CSV — the file and every row hash stay untouched.
    Leagues results.csv doesn't cover can never settle, so they're "not tracked"
    rather than "pending" and are kept out of the tracked totals."""
    is_settled = df["correct"].isin(["0", "1"])
    covered    = df["league"].map(is_covered_league)
    df["status"] = "pending"
    df.loc[~covered, "status"] = "not_tracked"
    df.loc[is_settled, "status"] = "settled"
    return df


def summarize_log(df):
    """Counts for the log/summary endpoints. `total` means tracked rows
    (not-tracked excluded), matching the existing /log contract.
    Adds the `status` column to `df` in place (via derive_status)."""
    if df is None or df.empty:
        return {"total": 0, "tracked": 0, "pending": 0, "not_tracked": 0,
                "correct": 0, "settled": 0, "hit_rate": None,
                "leagues": [], "date_from": None, "date_to": None,
                "brier_live": None, "brier_live_n": 0}
    df = derive_status(df)
    is_settled  = df["correct"].isin(["0", "1"])
    tracked     = df[df["status"] != "not_tracked"]
    settled     = df[is_settled]
    total       = len(tracked)
    n_pending   = int((df["status"] == "pending").sum())
    not_tracked = int((df["status"] == "not_tracked").sum())
    correct     = int((settled["correct"] == "1").sum())
    n_settled   = len(settled)
    hit_rate    = round(correct / n_settled, 4) if n_settled > 0 else None
    leagues     = sorted(tracked["league"].replace("", pd.NA).dropna().unique().tolist())
    dates       = tracked["match_date"].replace("", pd.NA).dropna()
    date_from   = str(dates.min()) if len(dates) else None
    date_to     = str(dates.max()) if len(dates) else None
    brier_live, brier_live_n = _multiclass_brier(df)
    return {"total": total, "tracked": total, "pending": n_pending,
            "not_tracked": not_tracked, "correct": correct, "settled": n_settled,
            "hit_rate": hit_rate, "leagues": leagues, "date_from": date_from,
            "date_to": date_to, "brier_live": brier_live, "brier_live_n": brier_live_n}


@predictions_bp.get("/predictions/log")
def get_prediction_log():
    df = load_prediction_log()
    if df is None:
        return jsonify({
            "success": True,
            "data": [],
            "summary": summarize_log(None),
            "meta": {"count": 0, "generated_at": datetime.now(timezone.utc).isoformat()},
        })

    df = df.sort_values("match_date", ascending=False)
    summary = summarize_log(df)  # also adds the derived `status` column to df

    records = []
    for row in df.to_dict(orient="records"):
        records.append({k: (None if v == "" else v) for k, v in row.items()})

    return jsonify({
        "success": True,
        "data": records,
        "summary": summary,
        "meta": {"count": len(records), "generated_at": datetime.now(timezone.utc).isoformat()},
    })


@predictions_bp.get("/predictions/summary")
def get_prediction_summary():
    """Lightweight counts for landing/dashboard/proof pages. Same status
    logic as /predictions/log, so the numbers always agree. No row data."""
    df = load_prediction_log()
    return jsonify({
        "success": True,
        "data": summarize_log(df),
        "meta": {"generated_at": datetime.now(timezone.utc).isoformat()},
    })


@predictions_bp.get("/tournament")
def get_tournament():
    df = current_app.config["DATA"]["tournament_simulations"].copy()

    league = request.args.get("league")
    if league:
        df = df[df["league"].str.lower() == league.lower()]

    df = df.sort_values("current_pts", ascending=False)
    return ok(df.to_dict(orient="records"))
