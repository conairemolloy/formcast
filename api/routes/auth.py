import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint("auth", __name__)

_supabase = None
_admin_sb = None


def _get_clients():
    global _supabase, _admin_sb
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        svc = os.environ.get("SUPABASE_SERVICE_KEY", key)
        _supabase = create_client(url, key)
        _admin_sb = create_client(url, svc)
    return _supabase, _admin_sb


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token() -> str | None:
    h = request.headers.get("Authorization", "")
    tok = h.removeprefix("Bearer ").strip()
    return tok or None


def _get_user(token: str):
    sb, _ = _get_clients()
    try:
        return sb.auth.get_user(token).user
    except Exception:
        return None


def _profile_row(user_id: str) -> dict:
    _, admin = _get_clients()
    rows = admin.table("profiles").select("*").eq("id", user_id).execute()
    return rows.data[0] if rows.data else {}


def _shape_profile(row: dict) -> dict:
    return {
        "id":           row.get("id"),
        "email":        row.get("email"),
        "name":         row.get("name"),
        "tier":         row.get("tier", "free"),
        "watchlist":    row.get("watchlist") or [],
        "email_alerts": row.get("email_alerts", True),
        "odds_format":  row.get("odds_format", "decimal"),
    }


@auth_bp.post("/auth/signup")
def signup():
    body     = request.get_json(silent=True) or {}
    email    = body.get("email", "").strip()
    password = body.get("password", "")
    name     = body.get("name", "").strip()

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400

    sb, admin = _get_clients()
    try:
        resp = sb.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    user    = resp.user
    session = resp.session

    if not user:
        return jsonify({"error": "Signup failed — check your email for a confirmation link"}), 400

    try:
        admin.table("profiles").insert({
            "id":    user.id,
            "email": email,
            "name":  name,
        }).execute()
    except Exception as e:
        return jsonify({"error": f"Profile creation failed: {e}"}), 500

    profile = {
        "id":           user.id,
        "email":        email,
        "name":         name,
        "tier":         "free",
        "watchlist":    [],
        "email_alerts": True,
    }
    return jsonify({
        "access_token": session.access_token if session else None,
        "profile":      profile,
    }), 201


@auth_bp.post("/auth/login")
def login():
    body     = request.get_json(silent=True) or {}
    email    = body.get("email", "").strip()
    password = body.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400

    sb, _ = _get_clients()
    try:
        resp = sb.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        return jsonify({"error": "Invalid email or password"}), 401

    session = resp.session
    user    = resp.user

    row     = _profile_row(user.id)
    profile = _shape_profile({**row, "id": user.id, "email": user.email})

    return jsonify({
        "access_token": session.access_token,
        "profile":      profile,
    })


@auth_bp.post("/auth/logout")
def logout():
    return jsonify({"success": True})


@auth_bp.get("/auth/profile")
def get_profile():
    token = _token()
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    user = _get_user(token)
    if not user:
        return jsonify({"error": "Invalid token"}), 401

    row = _profile_row(user.id)
    if not row:
        return jsonify({"error": "Profile not found"}), 404

    return jsonify({"profile": _shape_profile(row)})


@auth_bp.put("/auth/profile")
def update_profile():
    token = _token()
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    user = _get_user(token)
    if not user:
        return jsonify({"error": "Invalid token"}), 401

    body    = request.get_json(silent=True) or {}
    updates = {"updated_at": _now()}
    if "name" in body:
        updates["name"] = body["name"]
    if "email_alerts" in body:
        updates["email_alerts"] = bool(body["email_alerts"])
    if body.get("odds_format") in ("decimal", "fractional", "american"):
        updates["odds_format"] = body["odds_format"]

    _, admin = _get_clients()
    admin.table("profiles").update(updates).eq("id", user.id).execute()

    row = _profile_row(user.id)
    return jsonify({"profile": _shape_profile(row)})


@auth_bp.post("/auth/watchlist/add")
def watchlist_add():
    token = _token()
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    user = _get_user(token)
    if not user:
        return jsonify({"error": "Invalid token"}), 401

    team_name = (request.get_json(silent=True) or {}).get("team_name", "").strip()
    if not team_name:
        return jsonify({"error": "team_name required"}), 400

    row     = _profile_row(user.id)
    current = list(row.get("watchlist") or [])
    if team_name not in current:
        current.append(team_name)
        _, admin = _get_clients()
        admin.table("profiles").update({
            "watchlist":  current,
            "updated_at": _now(),
        }).eq("id", user.id).execute()

    return jsonify({"watchlist": current})


@auth_bp.post("/auth/watchlist/remove")
def watchlist_remove():
    token = _token()
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    user = _get_user(token)
    if not user:
        return jsonify({"error": "Invalid token"}), 401

    team_name = (request.get_json(silent=True) or {}).get("team_name", "").strip()
    if not team_name:
        return jsonify({"error": "team_name required"}), 400

    row     = _profile_row(user.id)
    current = [t for t in (row.get("watchlist") or []) if t != team_name]
    _, admin = _get_clients()
    admin.table("profiles").update({
        "watchlist":  current,
        "updated_at": _now(),
    }).eq("id", user.id).execute()

    return jsonify({"watchlist": current})
