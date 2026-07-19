"""
fetch_weather.py

Fetches 5-day weather forecasts for upcoming fixtures from OpenWeatherMap.
Uses the home team's stadium coordinates from data/reference/stadiums.csv.

Output: data/processed/upcoming_weather.csv
  Columns: match_date, home_team, away_team, temp_c, wind_kph, rain_mm, condition

Run BEFORE predict_upcoming.py so the weather CSV is ready for merging.
Requires OPENWEATHER_API_KEY env var.  Gracefully writes an empty CSV and
emits a warning if the key is absent — never blocks the prediction pipeline.
"""

import os
import sys
import csv
import math
import time
from datetime import datetime, timezone

import httpx
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OWM_KEY      = os.environ.get("OPENWEATHER_API_KEY", "")
OWM_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"
UPCOMING_URL = os.environ.get(
    "FORMCAST_API_URL",
    "https://web-production-eb371.up.railway.app/api/live/upcoming"
)

BASE_DIR  = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR  = os.path.join(BASE_DIR, "data", "processed")
REF_DIR   = os.path.join(BASE_DIR, "data", "reference")
OUT_PATH  = os.path.join(DATA_DIR, "upcoming_weather.csv")

EMPTY_COLS = ["match_date", "home_team", "away_team", "temp_c", "wind_kph", "rain_mm", "condition"]

# ---------------------------------------------------------------------------
# Stadium lookup
# ---------------------------------------------------------------------------

def _load_stadiums() -> dict[str, dict]:
    path = os.path.join(REF_DIR, "stadiums.csv")
    lookup: dict[str, dict] = {}
    if not os.path.exists(path):
        return lookup
    df = pd.read_csv(path, keep_default_na=False)
    for _, row in df.iterrows():
        raw = str(row["team"])
        try:
            entry = {
                "lat": float(row["latitude"])  if row["latitude"]  != "" else None,
                "lng": float(row["longitude"]) if row["longitude"] != "" else None,
            }
        except (ValueError, KeyError):
            entry = {"lat": None, "lng": None}
        lookup[raw] = entry
        stripped = raw.strip()
        if stripped != raw:
            lookup.setdefault(stripped, entry)
    return lookup


def _resolve_stadium(name: str, lookup: dict) -> dict:
    return lookup.get(name) or lookup.get(name.strip(), {})


# ---------------------------------------------------------------------------
# OWM helpers
# ---------------------------------------------------------------------------

def _match_kickoff_utc(match_date: str, match_time: str | None) -> datetime:
    """Best estimate of kickoff as a UTC-aware datetime."""
    try:
        d = datetime.strptime(match_date, "%Y-%m-%d")
    except ValueError:
        d = datetime.now(timezone.utc).replace(tzinfo=None)
    hour, minute = (15, 0)
    if match_time:
        try:
            t = datetime.strptime(match_time, "%H:%M")
            hour, minute = t.hour, t.minute
        except ValueError:
            pass
    return d.replace(hour=hour, minute=minute, tzinfo=timezone.utc)


def _fetch_forecast(lat: float, lng: float) -> list[dict]:
    resp = httpx.get(
        OWM_FORECAST,
        params={"lat": lat, "lon": lng, "appid": OWM_KEY, "units": "metric", "cnt": 40},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("list", [])


def _pick_slot(slots: list[dict], kickoff: datetime) -> dict | None:
    """Return the forecast slot whose dt is closest to kickoff."""
    if not slots:
        return None
    kickoff_ts = kickoff.timestamp()
    return min(slots, key=lambda s: abs(s.get("dt", 0) - kickoff_ts))


def _parse_slot(slot: dict) -> dict:
    main   = slot.get("main", {})
    wind   = slot.get("wind", {})
    rain   = slot.get("rain", {})
    clouds = slot.get("weather", [{}])[0]
    return {
        "temp_c":    round(float(main.get("temp", 15.0)), 1),
        "wind_kph":  round(float(wind.get("speed", 0.0)) * 3.6, 1),
        "rain_mm":   round(float(rain.get("3h", 0.0)), 1),
        "condition": str(clouds.get("main", "Unknown")),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not OWM_KEY:
        print("WARNING: OPENWEATHER_API_KEY not set — skipping weather fetch, writing empty file.",
              file=sys.stderr)
        pd.DataFrame(columns=EMPTY_COLS).to_csv(OUT_PATH, index=False)
        return

    # Load stadiums
    stadiums = _load_stadiums()
    print(f"Stadium lookup loaded: {len(stadiums)} entries")

    # Fetch upcoming fixtures
    print(f"Fetching fixtures from {UPCOMING_URL}...")
    try:
        resp = httpx.get(UPCOMING_URL, timeout=30)
        resp.raise_for_status()
        fixtures = resp.json().get("data", [])
    except Exception as exc:
        print(f"WARNING: could not fetch fixtures: {exc}", file=sys.stderr)
        pd.DataFrame(columns=EMPTY_COLS).to_csv(OUT_PATH, index=False)
        return

    print(f"  {len(fixtures)} fixtures returned")

    # Filter to next 7 days (OWM free tier covers 5 days; keep all returned)
    rows = []
    seen_locations: dict[tuple, list] = {}  # (lat, lng) → forecast slots cache

    for fix in fixtures:
        home       = fix.get("home_team", "")
        away       = fix.get("away_team", "")
        match_date = fix.get("match_date", "")
        match_time = fix.get("match_time", "")

        if not home or not match_date:
            continue

        stad = _resolve_stadium(home, stadiums)
        lat, lng = stad.get("lat"), stad.get("lng")
        if lat is None:
            continue  # no coordinates for this home team — skip silently

        # Cache OWM calls per location (rounded to 2dp ≈ 1km grid)
        loc_key = (round(lat, 2), round(lng, 2))
        if loc_key not in seen_locations:
            try:
                seen_locations[loc_key] = _fetch_forecast(lat, lng)
                time.sleep(0.25)  # OWM free tier: 60 calls/min
            except Exception as exc:
                print(f"  WARNING: OWM fetch failed for {home} ({lat},{lng}): {exc}",
                      file=sys.stderr)
                seen_locations[loc_key] = []

        slots   = seen_locations[loc_key]
        kickoff = _match_kickoff_utc(match_date, match_time)
        slot    = _pick_slot(slots, kickoff)

        if slot is None:
            continue

        wx = _parse_slot(slot)
        rows.append({
            "match_date": match_date,
            "home_team":  home,
            "away_team":  away,
            **wx,
        })

    out_df = pd.DataFrame(rows, columns=EMPTY_COLS) if rows else pd.DataFrame(columns=EMPTY_COLS)
    out_df.to_csv(OUT_PATH, index=False)
    print(f"Saved weather for {len(out_df)} fixtures → {OUT_PATH}")


if __name__ == "__main__":
    main()
