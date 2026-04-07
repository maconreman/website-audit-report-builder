"""
Step 6: Save Documentation — Routes.
"""

from flask import Blueprint, request, jsonify, send_file
from backend.services.documentation import (
    generate_docs, get_audit_download_path, get_docs_download_path,
)
from backend.utils.file_helpers import clean_domain

step6_bp = Blueprint("step6", __name__, url_prefix="/api/step6")


@step6_bp.route("/generate", methods=["POST"])
def gen_docs():
    """Generate and save audit documentation."""
    data = request.get_json() or {}
    domain = clean_domain(data.get("domain", ""))
    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    try:
        result = generate_docs(domain)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@step6_bp.route("/download/<domain>", methods=["GET"])
def download_docs(domain):
    """Download the generated documentation file."""
    domain = clean_domain(domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400

    path = get_docs_download_path(domain)
    if not path:
        return jsonify({"error": "Documentation file not found. Generate it first."}), 404

    return send_file(path, as_attachment=True)


@step6_bp.route("/download-audit/<domain>", methods=["GET"])
def download_audit(domain):
    """Download the final Website Audit CSV."""
    domain = clean_domain(domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400
    path = get_audit_download_path(domain)
    if not path:
        return jsonify({"error": "Audit file not found."}), 404
    return send_file(path, as_attachment=True)


@step6_bp.route("/download-xlsx/<domain>", methods=["GET"])
def download_xlsx(domain):
    """Download the Excel audit file."""
    import os
    domain = clean_domain(domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400
    from backend.utils.file_helpers import get_domain_output_folder
    folder, cd = get_domain_output_folder(domain)
    if not folder:
        return jsonify({"error": "Not found"}), 404
    # Find most recent xlsx
    xlsx_files = [f for f in os.listdir(folder) if f.endswith('.xlsx')] if os.path.exists(folder) else []
    if not xlsx_files:
        return jsonify({"error": "Excel file not found. Generate documentation first."}), 404
    xlsx_files.sort(reverse=True)
    return send_file(os.path.join(folder, xlsx_files[0]), as_attachment=True)


@step6_bp.route("/preview/<domain>", methods=["GET"])
def preview_audit(domain):
    """Return first N rows of the audit CSV + doc summary for preview."""
    import pandas as pd
    domain = clean_domain(domain)
    if not domain:
        return jsonify({"error": "Invalid domain"}), 400

    path = get_audit_download_path(domain)
    if not path:
        return jsonify({"error": "Audit file not found."}), 404

    try:
        df = pd.read_csv(path)
        rows = int(request.args.get("rows", 20))
        preview = df.head(rows).fillna("").to_dict(orient="records")
        columns = df.columns.tolist()

        # Summary stats
        summary = {"total_rows": len(df), "total_columns": len(columns)}
        if "Action" in df.columns:
            summary["action_counts"] = df["Action"].value_counts().to_dict()
        if "Page Category" in df.columns:
            summary["category_counts"] = df["Page Category"].value_counts().to_dict()

        # Metric summaries
        for col in ["Landing Page Traffic", "Organic Traffic", "Clicks", "Impressions"]:
            if col in df.columns:
                vals = pd.to_numeric(df[col], errors="coerce").fillna(0)
                summary[col] = {"total": float(vals.sum()), "mean": float(vals.mean()), "max": float(vals.max())}

        # Doc content
        from backend.services.documentation import get_docs_download_path
        doc_path = get_docs_download_path(domain)
        doc_content = ""
        if doc_path:
            import os
            if os.path.exists(doc_path):
                with open(doc_path, "r") as f:
                    doc_content = f.read()

        return jsonify({
            "preview": preview,
            "columns": columns,
            "summary": summary,
            "documentation": doc_content,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
