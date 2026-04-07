"""
Step 3: Merge Data Sources — Routes.
"""

from flask import Blueprint, request, jsonify
from backend.services.merging import run_step3
from backend.utils.file_helpers import clean_domain

step3_bp = Blueprint("step3", __name__, url_prefix="/api/step3")


@step3_bp.route("/run", methods=["POST"])
def run_merge():
    """Execute Step 3: Merge GA4 Organic and External Links into audit."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))
    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = run_step3(domain)
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
