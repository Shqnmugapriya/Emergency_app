"""
Patient Continuity Routes: Endpoints for patient management, search safeguards, and encounter linking.
"""

from flask import Blueprint, request, jsonify
from backend.services.patient_service import PatientService

patient_bp = Blueprint("patients", __name__)

@patient_bp.route("/api/patients", methods=["GET"])
def list_or_search_patients():
    """
    List or search patients.
    Supports ?q=, ?name=, ?dob=, ?phone=, ?patient_id=
    Flags ambiguous matches when name alone is searched without second identifier.
    """
    params = {
        "q": request.args.get("q"),
        "name": request.args.get("name"),
        "dob": request.args.get("dob"),
        "phone": request.args.get("phone"),
        "patient_id": request.args.get("patient_id") or request.args.get("id"),
        "patient_id_display": request.args.get("patient_id_display")
    }

    result = PatientService.search_patients(params)
    return jsonify({
        "success": True,
        "count": len(result["patients"]),
        "is_ambiguous": result["is_ambiguous"],
        "requires_confirmation": result["requires_confirmation"],
        "message": result["message"],
        "data": {
            "patients": result["patients"],
            "is_ambiguous": result["is_ambiguous"],
            "requires_confirmation": result["requires_confirmation"],
            "warning": result.get("message") if (result["is_ambiguous"] or result.get("requires_confirmation")) else None
        },
        "patients": result["patients"]
    }), 200

@patient_bp.route("/api/patients/<patient_id>", methods=["GET"])
def get_patient_profile(patient_id):
    """Retrieve full patient profile."""
    patient = PatientService.get_patient_by_id(patient_id)
    if not patient:
        return jsonify({"success": False, "error": f"Patient '{patient_id}' not found."}), 404
    return jsonify({"success": True, "data": patient}), 200

@patient_bp.route("/api/patients/<patient_id>/history", methods=["GET"])
def get_patient_encounter_history(patient_id):
    """Retrieve longitudinal encounter history for a patient."""
    history = PatientService.get_patient_history(patient_id)
    if not history:
        return jsonify({"success": False, "error": f"Patient '{patient_id}' not found."}), 404
    return jsonify({"success": True, "data": history}), 200

@patient_bp.route("/api/patients", methods=["POST"])
def register_patient():
    """Register a new patient profile."""
    body = request.get_json(silent=True) or {}
    try:
        new_pt = PatientService.register_new_patient(body)
        return jsonify({
            "success": True,
            "message": "Patient profile successfully registered.",
            "data": new_pt
        }), 201
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Internal error: {str(e)}"}), 500

@patient_bp.route("/api/patients/<patient_id>/link", methods=["POST"])
def link_patient_encounter(patient_id):
    """
    Attach an encounter record to a patient.
    Requires record_id and encounter_type (NEW_ENCOUNTER | OBSERVATION | CORRECTION | AMENDMENT).
    """
    body = request.get_json(silent=True) or {}
    record_id = body.get("record_id")
    encounter_type = body.get("encounter_type", "NEW_ENCOUNTER")
    actor = body.get("actor", "Paramedic")

    if not record_id:
        return jsonify({"success": False, "error": "'record_id' is mandatory to link encounter."}), 400

    try:
        res = PatientService.attach_encounter_to_patient(
            patient_id=patient_id,
            record_id=record_id,
            encounter_type=encounter_type,
            actor=actor
        )
        return jsonify({
            "success": True,
            "message": f"Record '{record_id}' successfully linked to patient as {encounter_type}.",
            "data": res
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Internal error: {str(e)}"}), 500
