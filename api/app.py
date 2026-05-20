import os
import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS

from routes.ratings import ratings_bp
from routes.predictions import predictions_bp
from routes.backtest import backtest_bp
from routes.value_bets import value_bets_bp
from routes.accumulator import accumulator_bp

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    return pd.read_csv(path)

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
        "kelly_simulation":       load_csv("kelly_simulation.csv"),
        "accumulator_bets":       load_csv("accumulator_bets.csv"),
        "tournament_simulations": load_csv("tournament_simulations.csv"),
    }

    app.register_blueprint(ratings_bp,     url_prefix="/api")
    app.register_blueprint(predictions_bp, url_prefix="/api")
    app.register_blueprint(backtest_bp,    url_prefix="/api")
    app.register_blueprint(value_bets_bp,  url_prefix="/api")
    app.register_blueprint(accumulator_bp, url_prefix="/api")

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
