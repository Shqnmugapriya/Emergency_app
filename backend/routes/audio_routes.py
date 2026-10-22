"""
Audio Streaming Routes: Safely serve preserved audio recordings to the frontend.
"""

import os
from flask import Blueprint, send_from_directory, abort, jsonify
from werkzeug.utils import secure_filename
from backend.services.transcription_service import AUDIO_DIR

audio_bp = Blueprint("audio", __name__)

@audio_bp.route("/api/audio/<filename>", methods=["GET"])
def stream_audio(filename):
    """Serve preserved audio file securely without directory traversal."""
    safe_name = secure_filename(filename)
    file_path = os.path.join(AUDIO_DIR, safe_name)

    if not os.path.exists(file_path):
        return jsonify({
            "success": False,
            "error": f"Audio file '{safe_name}' not found."
        }), 404

    # Determine mimetype
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else "webm"
    mimetypes = {
        "webm": "audio/webm",
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
        "flac": "audio/flac"
    }
    mimetype = mimetypes.get(ext, "application/octet-stream")

    return send_from_directory(AUDIO_DIR, safe_name, mimetype=mimetype)
