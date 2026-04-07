"""
Flask application entry point for the Website Audit Report Builder.
Registers all route blueprints and configures CORS for local React dev server.
"""

import logging
import traceback
from flask import Flask, jsonify, request

from backend.config import DEBUG, UPLOAD_DIR, OUTPUT_DIR
from backend.routes.upload import upload_bp
from backend.routes.step2_clean import step2_bp
from backend.routes.step3_merge import step3_bp
from backend.routes.step4_categorize import step4_bp
from backend.routes.step5_actions import step5_bp
from backend.routes.step6_docs import step6_bp

# Allowed origins for CORS (React dev servers)
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("audit")


def create_app():
    """Application factory."""
    app = Flask(__name__)

    # Configuration
    app.config["DEBUG"] = DEBUG
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max upload
    app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
    app.config["OUTPUT_FOLDER"] = OUTPUT_DIR

    # Request logging (skip OPTIONS and static)
    @app.before_request
    def log_request():
        if request.method != "OPTIONS" and request.path.startswith("/api"):
            logger.info(f"{request.method} {request.path}")

    # Manual CORS — no flask-cors dependency required
    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin", "")
        if origin in CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            origin = request.headers.get("Origin", "")
            if origin in CORS_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

    # Register blueprints
    app.register_blueprint(upload_bp)
    app.register_blueprint(step2_bp)
    app.register_blueprint(step3_bp)
    app.register_blueprint(step4_bp)
    app.register_blueprint(step5_bp)
    app.register_blueprint(step6_bp)

    # Root health check
    @app.route("/")
    def index():
        return jsonify({
            "app": "Website Audit Report Builder",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "health": "GET /api/status",
                "set_domain": "POST /api/domain",
                "upload_file": "POST /api/upload",
                "list_files": "GET /api/files/<domain>",
                "session_info": "GET /api/session/<domain>",
                "reset_session": "POST /api/session/<domain>/reset",
                "step2_clean": "POST /api/step2/run",
                "step3_merge": "POST /api/step3/run",
                "step4_categorize": "POST /api/step4/run",
                "step5_actions": "POST /api/step5/run",
                "step6_docs": "POST /api/step6/generate",
            },
        })

    # Global error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File too large. Maximum size is 50MB."}), 413

    @app.errorhandler(500)
    def server_error(e):
        tb = traceback.format_exc()
        logger.error(f"500 error: {e}\n{tb}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

    return app
