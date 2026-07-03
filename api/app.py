import os
import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

try:
    sentry_sdk.init(
        dsn="https://09ddb43847d98e33846d7f9ddb865f09@o4511077614223360.ingest.de.sentry.io/4511611061141584",
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
except Exception as e:
    print(f"Sentry init failed, continuing without error monitoring: {e}")

from routes.ratings import ratings_bp
from routes.predictions import predictions_bp
from routes.backtest import backtest_bp
from routes.value_bets import value_bets_bp
from routes.accumulator import accumulator_bp
from routes.live import live_bp
from routes.auth import auth_bp
from routes.international import international_bp
from routes.markets import markets_bp

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    return pd.read_csv(path)

def _load_team_tendencies():
    path = os.path.join(DATA_DIR, "team_tendencies.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def _load_live_value_bets():
    path = os.path.join(DATA_DIR, "live_value_bets.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)

def _load_optional_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)

def _load_elo_predictions():
    df = pd.read_csv(
        os.path.join(DATA_DIR, "elo_predictions.csv"),
        low_memory=False,
        parse_dates=["match_date"],
    )
    def _season(d):
        if pd.isna(d):
            return None
        y, m = d.year, d.month
        return f"{y}-{str(y + 1)[-2:]}" if m >= 7 else f"{y - 1}-{str(y)[-2:]}"
    df["season"] = df["match_date"].apply(_season)
    return df

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config["DATA"] = {
        "elo_ratings":            load_csv("elo_ratings.csv"),
        "glicko2_ratings":        load_csv("glicko2_ratings.csv"),
        "btl_ratings":            load_csv("btl_ratings.csv"),
        "ensemble_v2_predictions": load_csv("ensemble_v2_predictions.csv"),
        "value_bets":             load_csv("value_bets.csv"),
        "backtest_predictions":   load_csv("backtest_predictions.csv"),
        "results":                load_csv("results.csv"),
        "kelly_simulation":       load_csv("kelly_simulation.csv"),
        "accumulator_bets":       load_csv("accumulator_bets.csv"),
        "tournament_simulations": load_csv("tournament_simulations.csv"),
        "elo_predictions":        _load_elo_predictions(),
        "live_value_bets":        _load_live_value_bets(),
        "team_tendencies":        _load_team_tendencies(),
        "international_elo_ratings": load_csv("international_elo_ratings.csv"),
        "international_results":     load_csv("international_results.csv"),
        "worldcup_bracket_sims":     _load_optional_csv("worldcup_bracket_sims_v2.csv"),
        "worldcup_match_probs":      _load_optional_csv("worldcup_match_probs_v2.csv"),
    }

    app.register_blueprint(ratings_bp,     url_prefix="/api")
    app.register_blueprint(predictions_bp, url_prefix="/api")
    app.register_blueprint(backtest_bp,    url_prefix="/api")
    app.register_blueprint(value_bets_bp,  url_prefix="/api")
    app.register_blueprint(accumulator_bp, url_prefix="/api")
    app.register_blueprint(live_bp,        url_prefix="/api")
    app.register_blueprint(auth_bp,        url_prefix="/api")
    app.register_blueprint(international_bp, url_prefix="/api/international")
    app.register_blueprint(markets_bp,      url_prefix="/api/markets")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "version": "1.0.0"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "error": "Internal server error"}), 500

    return app


if __name__ == "__main__":
    import os
    app = create_app()
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
