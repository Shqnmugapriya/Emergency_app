"""
Field-to-Record Flask Application Entry Point.
Offline-first voice-to-structured clinical documentation assistant for first responders.
"""

import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, jsonify
from flask_cors import CORS
from backend.database.db import init_db
from backend.routes.health_routes import health_bp
from backend.routes.transcription_routes import transcription_bp
from backend.routes.record_routes import record_bp
from backend.routes.clinical_routes import clinical_bp
from backend.routes.audio_routes import audio_bp

def create_app(test_config=None):
    app = Flask(__name__)

    # Default configuration
    app.config.update(
        MAX_CONTENT_LENGTH=35 * 1024 * 1024,  # 35MB max upload
        JSON_SORT_KEYS=False
    )

    if test_config:
        app.config.update(test_config)

    # Configure CORS for Vite React frontend
    frontend_origins = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")

    CORS(
        app,
        resources={r"/api/*": {"origins": frontend_origins}},
        supports_credentials=True,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"]
    )

    # Initialize SQLite database schema & seeds
    with app.app_context():
        init_db()

    # Register Blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(transcription_bp)
    app.register_blueprint(record_bp)
    app.register_blueprint(clinical_bp)
    app.register_blueprint(audio_bp)

    # Consistent JSON error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "success": False,
            "error": "Bad request",
            "message": str(error.description if hasattr(error, 'description') else error)
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": "Resource not found",
            "message": str(error.description if hasattr(error, 'description') else error)
        }), 404

    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({
            "success": False,
            "error": "Payload too large",
            "message": "The uploaded audio file exceeds the maximum allowed upload size (35MB)."
        }), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected server error occurred."
        }), 500

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    print(f"Starting Field-to-Record Backend on http://127.0.0.1:{port}...")
    app.run(host="127.0.0.1", port=port, debug=debug)
