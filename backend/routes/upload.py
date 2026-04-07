"""
File upload and domain management endpoints.
Handles CSV uploads for SF, GA4 Organic, and External Links.
"""

from flask import Blueprint, request, jsonify
from backend.utils.file_helpers import (
    save_upload,
    list_domain_files,
    get_domain_upload_folder,
    clean_domain,
)
from backend.session_state import get_session, reset_session, get_session_summary, list_sessions

upload_bp = Blueprint("upload", __name__, url_prefix="/api")

# Valid upload types and their expected suffix keys
VALID_UPLOAD_TYPES = {
    "sf": "SF",
    "ga4_organic": "GA4 Organic",
    "external_links": "External Links",
}


@upload_bp.route("/domain", methods=["POST"])
def set_domain():
    """Set the active domain for the current audit session."""
    data = request.get_json()
    raw_domain = data.get("domain", "").strip()

    if not raw_domain:
        return jsonify({"error": "Domain is required"}), 400

    domain = clean_domain(raw_domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400

    # Initialize session and ensure upload folder exists
    session = get_session(domain)
    folder, _ = get_domain_upload_folder(domain)

    return jsonify({
        "domain": domain,
        "folder": folder,
        "session": get_session_summary(domain),
    })


@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    """
    Upload a CSV file for the active domain.
    Expects multipart form data with:
      - domain: the target domain
      - file_type: one of 'sf', 'ga4_organic', 'external_links'
      - file: the CSV file
    """
    domain = request.form.get("domain", "").strip()
    file_type = request.form.get("file_type", "").strip()
    file = request.files.get("file")

    # Validation
    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    if file_type not in VALID_UPLOAD_TYPES:
        return jsonify({
            "error": f"Invalid file_type. Must be one of: {list(VALID_UPLOAD_TYPES.keys())}",
        }), 400

    if not file:
        return jsonify({"error": "No file provided"}), 400

    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Only CSV files are accepted"}), 400

    
    try:
        content = file.read()
        saved_path = save_upload(domain, file_type, content)

        # --- Validate the CSV is readable immediately after save ---
        try:
            from backend.utils.file_helpers import read_csv_safe
            df_check = read_csv_safe(saved_path, nrows=3)
        except Exception as read_err:
            import os as _os
            _os.remove(saved_path)          # remove corrupt file
            return jsonify({
                "error": (
                    f"The uploaded file could not be read as a valid CSV. "
                    f"Details: {read_err}. "
                    "Re-export from Screaming Frog and try again."
                )
            }), 422

        # --- SF-specific column check ---
        if file_type == "sf":
            required_sf_cols = {"Address", "Status Code", "Content Type"}
            # Screaming Frog sometimes names it "Content-Type"
            actual_cols = set(df_check.columns)
            missing = required_sf_cols - actual_cols
            if missing:
                import os as _os
                _os.remove(saved_path)
                return jsonify({
                    "error": (
                        f"Screaming Frog file is missing required columns: {sorted(missing)}. "
                        "Make sure you exported 'All' (not 'Internal') and that the GA4 "
                        "integration was connected before crawling."
                    )
                }), 422

        return jsonify({
            "message": f"Uploaded {VALID_UPLOAD_TYPES[file_type]} file for {clean_domain(domain)}",
            "file_type": file_type,
            "file_name": f"{clean_domain(domain)} - {VALID_UPLOAD_TYPES[file_type]}.csv",
            "path": saved_path,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@upload_bp.route("/files/<domain>", methods=["GET"])
def get_files(domain):
    """List all files available for a domain."""
    domain = clean_domain(domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400

    files = list_domain_files(domain)

    file_list = []
    for key, path in files.items():
        file_list.append({
            "type": key,
            "label": VALID_UPLOAD_TYPES.get(key, key),
            "path": path,
            "exists": True,
        })

    # Also list expected files that are missing
    for key, label in VALID_UPLOAD_TYPES.items():
        if key not in files:
            file_list.append({
                "type": key,
                "label": label,
                "path": None,
                "exists": False,
            })

    return jsonify({
        "domain": domain,
        "files": file_list,
    })


@upload_bp.route("/status", methods=["GET"])
def get_status():
    """Health check and list active sessions."""
    sessions = list_sessions()
    return jsonify({
        "status": "ok",
        "active_sessions": sessions,
        "session_count": len(sessions),
    })


@upload_bp.route("/session/<domain>", methods=["GET"])
def get_session_info(domain):
    """Get session state summary for a domain."""
    domain = clean_domain(domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400

    return jsonify(get_session_summary(domain))


@upload_bp.route("/session/<domain>/reset", methods=["POST"])
def reset_session_route(domain):
    """Reset session state for a domain."""
    domain = clean_domain(domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400

    reset_session(domain)
    return jsonify({
        "message": f"Session reset for {domain}",
        "session": get_session_summary(domain),
    })
