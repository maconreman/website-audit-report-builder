"""
File upload and domain management endpoints.
Handles CSV uploads for SF, GA4 Organic, and External Links.

Chunked upload flow (for files over ~4 MB):
  1. POST /api/upload-chunk  — send chunk N of M
  2. POST /api/upload-chunk  — send chunk N+1 of M  (repeat)
  3. POST /api/upload-finalize — assemble all chunks into final file
"""

import os
import json
from flask import Blueprint, request, jsonify
from backend.utils.file_helpers import (
    save_upload,
    list_domain_files,
    get_domain_upload_folder,
    clean_domain,
    read_csv_safe,
)
from backend.session_state import get_session, reset_session, get_session_summary, list_sessions

upload_bp = Blueprint("upload", __name__, url_prefix="/api")

VALID_UPLOAD_TYPES = {
    "sf": "SF",
    "ga4_organic": "GA4 Organic",
    "external_links": "External Links",
}

# Vercel hard limit is 4.5 MB. We target 3.5 MB chunks to stay comfortably under.
CHUNK_SIZE_BYTES = 3_500_000  # 3.5 MB


def _get_chunk_dir(domain, file_type):
    """Temporary directory where incoming chunks are stored."""
    folder, _ = get_domain_upload_folder(domain)
    chunk_dir = os.path.join(folder, f".chunks_{file_type}")
    os.makedirs(chunk_dir, exist_ok=True)
    return chunk_dir


def _validate_csv(saved_path, file_type):
    """
    Read the assembled file and validate structure.
    Returns (ok: bool, error_message: str | None).
    """
    try:
        df = read_csv_safe(saved_path, nrows=3)
    except Exception as e:
        return False, (
            f"The file could not be read as a valid CSV. Details: {e}. "
            "Re-export from the source and try again."
        )

    if file_type == "sf":
        required = {"Address", "Status Code", "Content Type"}
        missing = required - set(df.columns)
        if missing:
            return False, (
                f"Screaming Frog file is missing required columns: {sorted(missing)}. "
                "Make sure you exported 'All' (not 'Internal') and that the GA4 "
                "integration was connected before crawling."
            )

    return True, None


# ── Domain management ────────────────────────────────────────────────────────

@upload_bp.route("/domain", methods=["POST"])
def set_domain():
    data = request.get_json()
    raw_domain = data.get("domain", "").strip()
    if not raw_domain:
        return jsonify({"error": "Domain is required"}), 400
    domain = clean_domain(raw_domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400
    get_session(domain)
    folder, _ = get_domain_upload_folder(domain)
    return jsonify({
        "domain": domain,
        "folder": folder,
        "session": get_session_summary(domain),
    })


# ── Single-request upload (kept for backward compat & small files) ───────────

@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    """
    Upload a CSV file in a single request.
    Works for files under ~4 MB (Vercel's body limit).
    For larger files, use /api/upload-chunk + /api/upload-finalize instead.
    """
    domain = request.form.get("domain", "").strip()
    file_type = request.form.get("file_type", "").strip()
    file = request.files.get("file")

    if not domain:
        return jsonify({"error": "Domain is required"}), 400
    if file_type not in VALID_UPLOAD_TYPES:
        return jsonify({"error": f"Invalid file_type. Must be one of: {list(VALID_UPLOAD_TYPES.keys())}"}), 400
    if not file:
        return jsonify({"error": "No file provided"}), 400
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Only CSV files are accepted"}), 400

    try:
        content = file.read()
        saved_path = save_upload(domain, file_type, content)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    ok, err = _validate_csv(saved_path, file_type)
    if not ok:
        try:
            os.remove(saved_path)
        except OSError:
            pass
        return jsonify({"error": err}), 422

    return jsonify({
        "message": f"Uploaded {VALID_UPLOAD_TYPES[file_type]} file for {clean_domain(domain)}",
        "file_type": file_type,
        "file_name": f"{clean_domain(domain)} - {VALID_UPLOAD_TYPES[file_type]}.csv",
        "path": saved_path,
    })


# ── Chunked upload ────────────────────────────────────────────────────────────

@upload_bp.route("/upload-chunk", methods=["POST"])
def upload_chunk():
    """
    Receive one chunk of a multi-part file upload.

    Form fields:
      domain      — client domain string
      file_type   — one of sf / ga4_organic / external_links
      chunk_index — 0-based index of this chunk
      total_chunks — total number of chunks
      file        — binary chunk data
    """
    domain = request.form.get("domain", "").strip()
    file_type = request.form.get("file_type", "").strip()
    chunk_index = request.form.get("chunk_index", "")
    total_chunks = request.form.get("total_chunks", "")
    chunk_file = request.files.get("file")

    # Validate
    if not domain:
        return jsonify({"error": "Domain is required"}), 400
    if file_type not in VALID_UPLOAD_TYPES:
        return jsonify({"error": f"Invalid file_type"}), 400
    if not chunk_file:
        return jsonify({"error": "No chunk data provided"}), 400
    try:
        chunk_index = int(chunk_index)
        total_chunks = int(total_chunks)
    except (ValueError, TypeError):
        return jsonify({"error": "chunk_index and total_chunks must be integers"}), 400

    try:
        chunk_dir = _get_chunk_dir(clean_domain(domain), file_type)
        chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index:05d}")
        with open(chunk_path, "wb") as f:
            f.write(chunk_file.read())

        return jsonify({
            "received": chunk_index,
            "total": total_chunks,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@upload_bp.route("/upload-finalize", methods=["POST"])
def upload_finalize():
    """
    Assemble all chunks into the final CSV file, validate it, and clean up.

    JSON body:
      domain       — client domain string
      file_type    — one of sf / ga4_organic / external_links
      total_chunks — expected number of chunks
      filename     — original filename (for logging only)
    """
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", "").strip())
    file_type = data.get("file_type", "").strip()
    total_chunks = data.get("total_chunks", 0)
    filename = data.get("filename", "upload.csv")

    if not domain:
        return jsonify({"error": "Domain is required"}), 400
    if file_type not in VALID_UPLOAD_TYPES:
        return jsonify({"error": f"Invalid file_type"}), 400

    chunk_dir = _get_chunk_dir(domain, file_type)

    # Verify all chunks are present
    missing = []
    for i in range(total_chunks):
        cp = os.path.join(chunk_dir, f"chunk_{i:05d}")
        if not os.path.exists(cp):
            missing.append(i)
    if missing:
        return jsonify({"error": f"Missing chunks: {missing}. Please retry the upload."}), 400

    # Assemble
    try:
        assembled_path = get_domain_upload_folder(domain)[0]
        label = VALID_UPLOAD_TYPES[file_type]
        final_path = os.path.join(assembled_path, f"{domain} - {label}.csv")

        with open(final_path, "wb") as out_file:
            for i in range(total_chunks):
                chunk_path = os.path.join(chunk_dir, f"chunk_{i:05d}")
                with open(chunk_path, "rb") as chunk_file:
                    out_file.write(chunk_file.read())

        # Clean up chunk directory
        for i in range(total_chunks):
            try:
                os.remove(os.path.join(chunk_dir, f"chunk_{i:05d}"))
            except OSError:
                pass
        try:
            os.rmdir(chunk_dir)
        except OSError:
            pass

    except Exception as e:
        return jsonify({"error": f"Failed to assemble file: {e}"}), 500

    # Validate assembled file
    ok, err = _validate_csv(final_path, file_type)
    if not ok:
        try:
            os.remove(final_path)
        except OSError:
            pass
        return jsonify({"error": err}), 422

    return jsonify({
        "message": f"Uploaded {label} file for {domain}",
        "file_type": file_type,
        "file_name": f"{domain} - {label}.csv",
        "path": final_path,
    })


# ── File listing & session management ────────────────────────────────────────

@upload_bp.route("/files/<domain>", methods=["GET"])
def get_files(domain):
    domain = clean_domain(domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400
    files = list_domain_files(domain)
    file_list = []
    for key, path in files.items():
        file_list.append({"type": key, "label": VALID_UPLOAD_TYPES.get(key, key), "path": path, "exists": True})
    for key, label in VALID_UPLOAD_TYPES.items():
        if key not in files:
            file_list.append({"type": key, "label": label, "path": None, "exists": False})
    return jsonify({"domain": domain, "files": file_list})


@upload_bp.route("/status", methods=["GET"])
def get_status():
    sessions = list_sessions()
    return jsonify({"status": "ok", "active_sessions": sessions, "session_count": len(sessions)})


@upload_bp.route("/session/<domain>", methods=["GET"])
def get_session_info(domain):
    domain = clean_domain(domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400
    return jsonify(get_session_summary(domain))


@upload_bp.route("/session/<domain>/reset", methods=["POST"])
def reset_session_route(domain):
    domain = clean_domain(domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400
    reset_session(domain)
    return jsonify({"message": f"Session reset for {domain}", "session": get_session_summary(domain)})
