"""
api.py
──────
REST API blueprint.
Register in app.py with:  app.register_blueprint(api_bp, url_prefix="/api")
"""

from flask import Blueprint, jsonify
import random, time

api_bp = Blueprint("api", __name__)


@api_bp.route("/chart-data")
def chart_data():
    """Return the latest sensor level readings as JSON."""
    return jsonify({
        "l1":        random.randint(0, 5),
        "l2":        random.randint(0, 8),
        "l3":        random.randint(0, 3),
        "timestamp": time.strftime("%H:%M:%S"),
    })


@api_bp.route("/status")
def status():
    """Return current fall-detection status."""
    states  = ["NORMAL", "UNBALANCED", "FALLING", "CRITICAL"]
    weights = [0.70, 0.15, 0.10, 0.05]
    state   = random.choices(states, weights=weights)[0]
    risk    = {"NORMAL": 0, "UNBALANCED": 25, "FALLING": 75, "CRITICAL": 99}[state]
    return jsonify({
        "state":     state,
        "risk":      risk,
        "timestamp": time.strftime("%H:%M:%S"),
    })