"""
Step 2: Clean and Process Data — Routes.
"""

from flask import Blueprint, request, jsonify
from backend.services.cleaning import run_step2, confirm_custom_columns, clean_ga4_organic
from backend.utils.file_helpers import clean_domain

step2_bp = Blueprint("step2", __name__, url_prefix="/api/step2")


@step2_bp.route("/run", methods=["POST"])
def run_cleaning():
    """Execute Step 2: Clean and process Screaming Frog data."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))
    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = run_step2(domain)
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step2_bp.route("/custom-columns/<domain>", methods=["GET"])
def get_custom_columns(domain):
    """Return detected custom columns for user selection."""
    from backend.session_state import get_session
    domain = clean_domain(domain)
    session = get_session(domain)
    detected = session.get("custom_columns_detected", {})

    result = {}
    for k, v in detected.items():
        result[k] = {
            "first_column": v["first_column"],
            "all_columns": v["all_columns"],
            "column_count": len(v["all_columns"]),
        }

    return jsonify({"custom_columns": result})


@step2_bp.route("/confirm-custom", methods=["POST"])
def confirm_custom_selection():
    """Confirm selected custom columns and finalize SF-200 cleaning."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))
    selected_types = data.get("selected_types", [])

    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = confirm_custom_columns(domain, selected_types)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
