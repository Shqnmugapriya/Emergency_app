"""
Clinical Processing Routes: Text extraction, validation rules, and medicine catalogue search.
"""

from flask import Blueprint, request, jsonify
from backend.services.clinical_extractor import ClinicalExtractor
from backend.services.validation_service import ValidationService
from backend.services.medicine_service import MedicineService

clinical_bp = Blueprint("clinical", __name__)

@clinical_bp.route("/api/clinical/extract", methods=["POST"])
def extract_clinical_entities():
    """
    Extract structured clinical events from raw or edited transcript text.
    Preserves exact source phrases, character spans, and initial verification states.
    """
    body = request.get_json(silent=True) or {}
    text = body.get("text", "").strip()

    if not text:
        return jsonify({
            "success": False,
            "error": "Input text is required for clinical entity extraction."
        }), 400

    extracted = ClinicalExtractor.extract_all(text)
    warnings = ValidationService.validate_clinical_record(extracted)

    return jsonify({
        "success": True,
        "data": {
            "entities": extracted,
            "validation_warnings": warnings
        }
    }), 200

@clinical_bp.route("/api/clinical/validate", methods=["POST"])
def validate_entities():
    """Run validation rules against a structured clinical entity bundle."""
    body = request.get_json(silent=True) or {}
    clinical_data = body.get("clinical_data", {})
    warnings = ValidationService.validate_clinical_record(clinical_data)

    return jsonify({
        "success": True,
        "data": {
            "warnings": warnings,
            "has_critical": any(w.get("severity") == "CRITICAL" for w in warnings),
            "warnings_count": len(warnings)
        }
    }), 200

@clinical_bp.route("/api/medicines/search", methods=["GET"])
def search_medicines():
    """
    Search verified local medicine catalogue using exact and RapidFuzz ranking.
    Distinguishes exact match, alias match, and ambiguous candidate ranking.
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({
            "success": False,
            "error": "Query parameter 'q' is required."
        }), 400

    match_result = MedicineService.match_medicine(query)
    return jsonify({
        "success": True,
        "data": match_result
    }), 200

@clinical_bp.route("/api/medicines/catalogue", methods=["GET"])
def get_catalogue():
    """Retrieve complete local verified medicine catalogue with provenance."""
    medicines = MedicineService.get_all_medicines()
    return jsonify({
        "success": True,
        "count": len(medicines),
        "data": medicines
    }), 200
