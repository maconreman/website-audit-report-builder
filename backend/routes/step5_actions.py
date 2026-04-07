"""
Step 5: Assign Actions — Routes.
"""

from flask import Blueprint, request, jsonify
from backend.services.actions import (
    run_step5, configure_old_content, get_threshold_stats,
    apply_threshold, skip_threshold, preview_threshold,
    recent_content_keep, recent_content_skip,
)
from backend.utils.file_helpers import clean_domain

step5_bp = Blueprint("step5", __name__, url_prefix="/api/step5")


@step5_bp.route("/run", methods=["POST"])
def run_actions():
    """Execute Step 5: Start action assignment workflow."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))
    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = run_step5(domain)
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step5_bp.route("/old-content-config", methods=["POST"])
def config_old_content():
    """Configure old content check settings."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))
    enabled = data.get("enabled", False)
    cutoff_year = data.get("cutoff_year")
    date_field = data.get("date_field")

    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = configure_old_content(domain, enabled, cutoff_year, date_field)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step5_bp.route("/threshold-stats/<domain>", methods=["GET"])
def threshold_stats(domain):
    """Return statistics for current threshold metric."""
    domain = clean_domain(domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400

    try:
        result = get_threshold_stats(domain)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step5_bp.route("/preview-threshold", methods=["POST"])
def preview_thresh():
    """Preview how many pages would be kept at a given threshold (without applying)."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))
    threshold_type = data.get("threshold_type", "percentage")
    value = data.get("value", 10)

    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = preview_threshold(domain, threshold_type, value)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step5_bp.route("/apply-threshold", methods=["POST"])
def apply_thresh():
    """Apply a threshold for the current metric."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))
    threshold_type = data.get("threshold_type", "percentage")
    value = data.get("value", 10)

    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = apply_threshold(domain, threshold_type, value)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step5_bp.route("/skip-threshold", methods=["POST"])
def skip_thresh():
    """Skip current threshold metric."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))

    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = skip_threshold(domain)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step5_bp.route("/recent-content-keep", methods=["POST"])
def keep_recent():
    """Override recent content to Keep."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))

    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = recent_content_keep(domain)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step5_bp.route("/recent-content-skip", methods=["POST"])
def skip_recent():
    """Skip recent content override."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))

    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = recent_content_skip(domain)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
