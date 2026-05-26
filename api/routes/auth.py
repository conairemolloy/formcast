import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

_URL = os.getenv("SUPABASE_URL", "")
_KEY = os.getenv("SUPABASE_KEY", "")
_SVC = os.getenv("SUPABASE_SERVICE_KEY", _KEY)

supabase = create_client(_URL, _KEY)
admin_sb = create_client(_URL, _SVC)

auth_bp = Blueprint("auth", __name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token() -> str | None:
    h = request.headers.get("Authorization", "")
    tok = h.removeprefix("Bearer ").strip()
    return tok or None


def _get_user(token: str):
    try:
        return supabase.auth.get_user(token).user
    except Exception:
        return None


def _profile_row(user_id: str) -> dict:
    rows = admin_sb.table("profiles").select("*").eq("id", user_id).execute()
    return rows.data[0] if rows.data else {}


def _shape_profile(row: dict) -> dict:
    return {
        "id":           row.get("id"),
        "email":        row.get("email"),
        "name":         row.get("name"),
        "tier":         row.get("tier", "free"),
        "watchlist":    row.get("watchlist") or [],
        "email_alerts": row.get("email_alerts", True),
    }


@auth_bp.post("/auth/signup")
def signup():
    body     = request.get_json(silent=True) or {}
    email    = body.get("email", "").strip()
    password = body.get("password", "")
    name     = body.get("name", "").strip()

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400

    try:
        resp = supabase.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    user    = resp.user
    session = resp.session

    if not user:
        return jsonify({"error": "Signup failed — check your email for a confirmation link"}), 400

    try:
        admin_sb.table("profiles").insert({
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

    try:
        resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
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

    admin_sb.table("profiles").update(updates).eq("id", user.id).execute()

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
        admin_sb.table("profiles").update({
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
    admin_sb.table("profiles").update({
        "watchlist":  current,
        "updated_at": _now(),
    }).eq("id", user.id).execute()

    return jsonify({"watchlist": current})
