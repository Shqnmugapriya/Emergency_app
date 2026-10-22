"""
Clinical Accuracy Routes: Endpoints for internal benchmark metrics and on-demand model validation.
"""

from flask import Blueprint, jsonify, request
from backend.services.accuracy_eval_service import AccuracyEvaluationService

accuracy_bp = Blueprint("accuracy", __name__)

@accuracy_bp.route("/api/accuracy/metrics", methods=["GET"])
def get_accuracy_metrics():
    """Retrieve measured system performance metrics from ground-truth evaluation."""
    metrics_data = AccuracyEvaluationService.get_latest_metrics()
    return jsonify({
        "success": True,
        "data": metrics_data
    }), 200

@accuracy_bp.route("/api/accuracy/evaluate", methods=["POST"])
def trigger_evaluation():
    """Trigger an on-demand evaluation run against verified reference dataset."""
    body = request.get_json(silent=True) or {}
    model_name = body.get("model_name")
    res = AccuracyEvaluationService.run_full_evaluation(model_name=model_name)
    return jsonify({
        "success": True,
        "message": "Clinical accuracy evaluation run completed successfully.",
        "data": res
    }), 200
