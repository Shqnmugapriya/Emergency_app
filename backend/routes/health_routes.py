"""
Health and System Diagnostic Routes.
Verifies Flask runtime, SQLite database connection, and local Whisper model state.
"""

from flask import Blueprint, jsonify, request
from backend.database.db import get_db_connection
from backend.services.transcription_service import TranscriptionService

health_bp = Blueprint("health", __name__)

@health_bp.route("/api/health", methods=["GET"])
def health_check():
    """Verify backend and database accessibility."""
    db_status = "error"
    db_details = ""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM records;")
        record_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM medicine_catalogue;")
        med_count = cursor.fetchone()[0]
        conn.close()
        db_status = "healthy"
        db_details = f"Accessible ({record_count} records, {med_count} verified medicines)"
    except Exception as e:
        db_details = str(e)

    overall_healthy = (db_status == "healthy")
    status_code = 200 if overall_healthy else 503

    return jsonify({
        "status": "healthy" if overall_healthy else "unhealthy",
        "service": "Field-to-Record Backend API",
        "version": "1.0.0",
        "database": {
            "status": db_status,
            "details": db_details
        }
    }), status_code

@health_bp.route("/api/transcription/status", methods=["GET"])
def transcription_status():
    """Report whether Whisper is ready, missing, loading, or in an error state."""
    svc = TranscriptionService.get_instance()
    info = svc.get_status()
    return jsonify({
        "success": True,
        "data": info
    }), 200

@health_bp.route("/api/transcription/load", methods=["POST"])
def load_transcription_model():
    """Load or switch the Whisper model (e.g. tiny, base, small)."""
    payload = request.get_json(silent=True) or {}
    model_name = payload.get("model_name", "base")
    device = payload.get("device", "cpu")
    compute_type = payload.get("compute_type", "int8")

    valid_models = ["tiny", "base", "small", "medium"]
    if model_name not in valid_models:
        return jsonify({
            "success": False,
            "error": f"Invalid model name '{model_name}'. Supported: {valid_models}"
        }), 400

    svc = TranscriptionService.get_instance()
    ok, msg = svc.load_model(model_name=model_name, device=device, compute_type=compute_type)
    status_code = 200 if ok else 500

    return jsonify({
        "success": ok,
        "message": msg,
        "status": svc.get_status()
    }), status_code
