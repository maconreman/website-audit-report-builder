"""
Step 4: Assign Page Categories — Routes.
"""

from flask import Blueprint, request, jsonify
from backend.services.categorization import (
    run_step4, approve_category, reject_category,
    approve_all_remaining, finalize_categories,
)
from backend.utils.file_helpers import clean_domain

step4_bp = Blueprint("step4", __name__, url_prefix="/api/step4")


@step4_bp.route("/run", methods=["POST"])
def run_categorize():
    """Execute Step 4: Analyze URL patterns and start category workflow."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))
    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = run_step4(domain)
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step4_bp.route("/approve", methods=["POST"])
def approve_cat():
    """Approve a single category recommendation."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))
    pattern_key = data.get("pattern_key", "")

    if not domain or not pattern_key:
        return jsonify({"error": "Domain and pattern_key are required"}), 400

    try:
        result = approve_category(domain, pattern_key)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step4_bp.route("/reject", methods=["POST"])
def reject_cat():
    """Reject (flag for manual check) a category recommendation."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))
    pattern_key = data.get("pattern_key", "")

    if not domain or not pattern_key:
        return jsonify({"error": "Domain and pattern_key are required"}), 400

    try:
        result = reject_category(domain, pattern_key)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step4_bp.route("/approve-all", methods=["POST"])
def approve_all():
    """Approve all remaining category recommendations and finalize."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))

    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = approve_all_remaining(domain)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step4_bp.route("/finalize", methods=["POST"])
def finalize():
    """Finalize page categories after all approvals/rejections."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))

    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = finalize_categories(domain)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
