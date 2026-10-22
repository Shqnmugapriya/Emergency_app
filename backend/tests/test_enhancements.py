import pytest
import json
from backend.app import create_app
from backend.database.db import init_db

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

def test_patient_registry_and_continuity(client):
    """Test patient registration, multi-factor search, and longitudinal encounter linking."""
    import uuid
    uniq = uuid.uuid4().hex[:4]
    name = f"Sarah-{uniq}"
    dob = "1984-05-12"

    # 1. Register a test patient
    new_pt = {
        "first_name": name,
        "last_name": "Connor",
        "date_of_birth": dob,
        "gender": "Female",
        "phone": f"555-{uniq}",
        "blood_type": "O-",
        "allergies": ["Sulfa"],
        "medical_history": ["Asthma"],
        "emergency_contacts": [{"name": "John Connor", "phone": "555-0100", "relationship": "Son"}]
    }
    res = client.post("/api/patients", json=new_pt)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    patient_id = data["data"]["id"]
    display_id = data["data"]["patient_id_display"]
    assert display_id.startswith("PT-")

    # 2. Multi-factor search with DOB
    res = client.get(f"/api/patients?name={name}&dob={dob}")
    assert res.status_code == 200
    search_data = res.get_json()["data"]
    assert len(search_data["patients"]) >= 1
    assert any(p["id"] == patient_id for p in search_data["patients"])
    assert search_data["is_ambiguous"] is False

    # 3. Create a record linked to this patient
    rec_payload = {
        "call_number": "EMS-9901",
        "responder_id": "Unit-1",
        "corrected_transcript": "Patient Sarah Connor, blood pressure 130 over 80, pulse 76, administered Albuterol 2.5mg nebulized.",
        "patient_id": patient_id,
        "encounter_type": "NEW_ENCOUNTER"
    }
    rec_res = client.post("/api/records", json=rec_payload)
    assert rec_res.status_code == 201
    record_id = rec_res.get_json()["data"]["id"]

    # 4. Check patient history reflects linked encounter
    hist_res = client.get(f"/api/patients/{patient_id}/history")
    assert hist_res.status_code == 200
    encounters = hist_res.get_json()["data"]["encounters"]
    assert len(encounters) >= 1
    assert any(e["record_id"] == record_id for e in encounters)

def test_evidence_passport_and_uncertainty_ledger(client):
    """Test Evidence Passport source extraction and Uncertainty Ledger categorization."""
    rec_payload = {
        "call_number": "EMS-9902",
        "responder_id": "Unit-2",
        "corrected_transcript": "Pulse 88, SpO2 98 percent on room air, administered Aspirin 324 mg orally.",
    }
    rec_res = client.post("/api/records", json=rec_payload)
    assert rec_res.status_code == 201
    rec_data = rec_res.get_json()["data"]

    # Evidence Passport verification
    passport = rec_data.get("evidence_passport")
    assert passport is not None
    assert "entries" in passport
    entries = passport["entries"]
    assert len(entries) >= 2
    # Verify at least one entry has supporting phrase
    supported_entries = [e for e in entries if e.get("is_supported")]
    assert len(supported_entries) > 0
    assert any("Aspirin" in e.get("field_value", "") or "Pulse" in e.get("field_name", "") for e in supported_entries)

    # Uncertainty Ledger verification
    ledger = rec_data.get("uncertainty_ledger")
    assert ledger is not None
    assert "items" in ledger
    assert "counts" in ledger
    assert isinstance(ledger["counts"]["not_mentioned"], int)

def test_medicine_ambiguity_candidate_ranking(client):
    """Test phonetic Soundex and spelling candidate ranking on ambiguous terms."""
    res = client.get("/api/medicines/search?q=epinefrin")
    assert res.status_code == 200
    data = res.get_json()["data"]
    candidates = data.get("candidates", [])
    assert len(candidates) > 0
    top_cand = candidates[0]
    assert "Epinephrine" in top_cand["canonical_name"]
    assert top_cand["score"] > 60

def test_change_impact_radar(client):
    """Test Change Impact Radar detects downstream consequences on edit."""
    # Create record
    rec_res = client.post("/api/records", json={
        "call_number": "EMS-9903",
        "responder_id": "Unit-3",
        "corrected_transcript": "Blood pressure 240 over 130, pulse 120."
    })
    record_id = rec_res.get_json()["data"]["id"]

    # Update BP to normal and verify Change Impact Radar
    put_res = client.put(f"/api/records/{record_id}", json={
        "corrected_transcript": "Blood pressure 120 over 80, pulse 72.",
        "clinical_data": {
            "vital_signs": [
                {"id": "v1", "name": "Blood Pressure", "value": "120/80", "unit": "mmHg", "source_phrase": "120 over 80"},
                {"id": "v2", "name": "Heart Rate", "value": "72", "unit": "bpm", "source_phrase": "pulse 72"}
            ],
            "medications": [],
            "symptoms": [],
            "procedures": [],
            "timestamps": []
        }
    })
    assert put_res.status_code == 200
    radar = put_res.get_json()["data"].get("change_impact_radar")
    assert radar is not None
    assert radar["has_changes"] is True
    assert len(radar["changes_detected"]) > 0

def test_standards_compatible_fhir_export_and_metric_scrubbing(client):
    """Test FHIR R4 Bundle export and ensure clinical accuracy metrics are stripped from patient reports."""
    rec_res = client.post("/api/records", json={
        "call_number": "EMS-9904",
        "responder_id": "Unit-4",
        "corrected_transcript": "Patient with allergic reaction, administered Epinephrine 0.3 mg IM."
    })
    record_id = rec_res.get_json()["data"]["id"]

    # FHIR Bundle Export
    fhir_res = client.get(f"/api/records/{record_id}/export/fhir")
    assert fhir_res.status_code == 200
    fhir_data = fhir_res.get_json()
    assert fhir_data["resourceType"] == "Bundle"
    assert fhir_data["type"] == "document"
    assert len(fhir_data["entry"]) >= 2  # Composition + Observation/MedicationAdministration

    # JSON Export should strictly scrub accuracy metrics
    json_res = client.get(f"/api/records/{record_id}/export/json")
    assert json_res.status_code == 200
    patient_report = json_res.get_json()
    assert "accuracy_metrics" not in patient_report
    assert "model_eval_summary" not in patient_report
    assert "internal_wer" not in patient_report

def test_in_flight_draft_autosave_and_recovery(client):
    """Test autosaving and retrieving in-flight drafts via telemetry endpoint."""
    session_id = "test_first_responder_unit"
    draft_payload = {
        "call_number": "EMS-DRAFT-01",
        "patient_age": "45",
        "chief_complaint": "Syncope episode",
        "transcript": "Found patient conscious on floor..."
    }

    # Save draft
    save_res = client.post("/api/trust/drafts/save", json={
        "session_id": session_id,
        "draft": draft_payload
    })
    assert save_res.status_code == 200

    # Retrieve draft
    get_res = client.get(f"/api/trust/drafts/{session_id}")
    assert get_res.status_code == 200
    recovered = get_res.get_json()["data"]["draft"]
    assert recovered["call_number"] == "EMS-DRAFT-01"
    assert recovered["chief_complaint"] == "Syncope episode"

    # Delete draft
    del_res = client.delete(f"/api/trust/drafts/{session_id}")
    assert del_res.status_code == 200
    get_after = client.get(f"/api/trust/drafts/{session_id}")
    assert get_after.get_json()["data"]["draft"] is None
