"""
Backend API Unit and Integration Tests.
Tests health, transcription status, records CRUD, approval gating, amendments,
clinical entity extraction, medicine ambiguity, and report exports.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import io
import json
import pytest
from backend.app import create_app
from backend.database.db import init_db, get_db_connection
from backend.services.medicine_service import MedicineService
from backend.services.clinical_extractor import ClinicalExtractor
from backend.services.validation_service import ValidationService, ValidationSeverity

@pytest.fixture
def client(tmp_path):
    test_db = os.path.join(tmp_path, "test_field_to_record.db")
    os.environ["FIELD_RECORD_DB_PATH"] = test_db
    init_db()

    app = create_app({"TESTING": True})
    with app.test_client() as test_client:
        yield test_client

# ==========================================================
# 1. Health & Diagnostic Endpoints
# ==========================================================
def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["database"]["status"] == "healthy"

def test_transcription_status_endpoint(client):
    res = client.get("/api/transcription/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "status" in data["data"]
    assert "model_name" in data["data"]

# ==========================================================
# 2. Medicine Catalogue & RapidFuzz Ambiguity
# ==========================================================
def test_medicine_exact_match(client):
    match = MedicineService.match_medicine("Paracetamol")
    assert match["status"] == "EXACT"
    assert match["matched_canonical"] == "Paracetamol"
    assert match["confidence_score"] == 100.0
    assert match["requires_confirmation"] is False

def test_medicine_alias_match(client):
    match = MedicineService.match_medicine("Panadol")
    assert match["status"] == "ALIAS"
    assert match["matched_canonical"] == "Paracetamol"
    assert match["confidence_score"] >= 95.0

def test_medicine_ambiguity_flagging(client):
    # Typo query close to multiple medicines or candidate ranking
    match = MedicineService.match_medicine("par")
    # For ambiguous or unresolved matches, RapidFuzz must flag requires_confirmation
    assert match["requires_confirmation"] is True

# ==========================================================
# 3. Clinical Entity Extractor & Negation
# ==========================================================
def test_vitals_extraction():
    text = "Patient BP is 130/85, pulse 82 bpm, respiratory rate 16, SpO2 98%, temp 37.2 C, GCS 15, glucose 5.2."
    entities = ClinicalExtractor.extract_all(text)
    vitals = {v["type"]: v for v in entities["vital_signs"]}

    assert "Blood Pressure" in vitals
    assert vitals["Blood Pressure"]["systolic"] == 130
    assert vitals["Blood Pressure"]["diastolic"] == 85
    assert vitals["Blood Pressure"]["verification_state"] == "Extracted"

    assert "Heart Rate" in vitals
    assert vitals["Heart Rate"]["value"] == "82"

    assert "Oxygen Saturation" in vitals
    assert vitals["Oxygen Saturation"]["value"] == "98"

def test_medication_and_negation_extraction():
    text = "Administered 1000 mg paracetamol orally. Patient denies chest pain and no morphine was given."
    entities = ClinicalExtractor.extract_all(text)

    meds = entities["medications"]
    paracetamol = next((m for m in meds if m["canonical_name"] == "Paracetamol"), None)
    assert paracetamol is not None
    assert paracetamol["dosage"] == "1000"
    assert paracetamol["unit"] == "mg"
    assert paracetamol["route"] == "Oral"
    assert paracetamol["is_negated"] is False

    morphine = next((m for m in meds if m["canonical_name"] == "Morphine"), None)
    assert morphine is not None
    assert morphine["is_negated"] is True
    assert morphine["negation_trigger"] is not None

    symptoms = entities["symptoms"]
    chest_pain = next((s for s in symptoms if s["symptom"] == "Chest Pain"), None)
    assert chest_pain is not None
    assert chest_pain["is_negated"] is True

# ==========================================================
# 4. Validation Rules & Safety Warnings
# ==========================================================
def test_contradictory_vitals_warning():
    # Systolic <= Diastolic
    contradictory_data = {
        "vital_signs": [{
            "id": "v-1",
            "type": "Blood Pressure",
            "systolic": 80,
            "diastolic": 120,
            "source_phrase": "80/120"
        }],
        "medications": []
    }
    warnings = ValidationService.validate_clinical_record(contradictory_data)
    crit = [w for w in warnings if w["severity"] == ValidationSeverity.CRITICAL]
    assert len(crit) > 0
    assert "Systolic pressure" in crit[0]["message"]

def test_missing_medication_dosage_warning():
    med_data = {
        "vital_signs": [],
        "medications": [{
            "id": "m-1",
            "canonical_name": "Morphine",
            "dosage": None,
            "unit": None,
            "route": "IV",
            "is_negated": False
        }]
    }
    warnings = ValidationService.validate_clinical_record(med_data)
    dosage_warn = [w for w in warnings if w["field"] == "Dosage"]
    assert len(dosage_warn) > 0

# ==========================================================
# 5. Record CRUD & Lifecycle Flow
# ==========================================================
def test_record_lifecycle_flow(client):
    # 1. Create Draft
    create_res = client.post("/api/records", json={
        "call_number": "EMS-9910",
        "responder_id": "Medic-42",
        "machine_transcript": "Patient BP 120/80, pulse 75, gave 500 mg paracetamol orally.",
        "corrected_transcript": "Patient BP 120/80, pulse 75, gave 500 mg paracetamol orally."
    })
    assert create_res.status_code == 201
    record = create_res.get_json()["data"]
    rec_id = record["id"]
    assert record["status"] in ["Draft", "Needs Review"]
    assert len(record["clinical_data"]["vital_signs"]) >= 2
    assert len(record["clinical_data"]["medications"]) >= 1

    # 2. Retrieve
    get_res = client.get(f"/api/records/{rec_id}")
    assert get_res.status_code == 200
    assert get_res.get_json()["data"]["id"] == rec_id

    # 3. Update Draft
    update_res = client.put(f"/api/records/{rec_id}", json={
        "status": "Reviewed",
        "review_decisions": {"clinician_notes": "All vitals verified on scene."}
    })
    assert update_res.status_code == 200
    assert update_res.get_json()["data"]["status"] == "Reviewed"

    # 4. Approve Record
    approve_res = client.post(f"/api/records/{rec_id}/approve", json={
        "reviewer_id": "Supervisor-Dr-Smith",
        "override_notes": "Reviewed and verified."
    })
    assert approve_res.status_code == 200
    approved_rec = approve_res.get_json()["data"]
    assert approved_rec["status"] == "Approved"
    assert approved_rec["approved_at"] is not None

    # 5. Direct PUT on Approved record is blocked (Immutability rule)
    blocked_put = client.put(f"/api/records/{rec_id}", json={"corrected_transcript": "tampered"})
    assert blocked_put.status_code == 409

    # 6. Amend Record
    amend_res = client.post(f"/api/records/{rec_id}/amend", json={
        "reason": "Late entry: hospital handover time added.",
        "responder_id": "Medic-42"
    })
    assert amend_res.status_code == 200
    amended_rec = amend_res.get_json()["data"]
    assert amended_rec["status"] in ["Needs Review", "Amended"]
    assert amended_rec["approved_at"] is None
    assert amended_rec["version"] == 2

    # 7. Check Audit Trail
    audit_res = client.get(f"/api/records/{rec_id}/audit")
    assert audit_res.status_code == 200
    actions = [log["action"] for log in audit_res.get_json()["data"]]
    assert "CREATE" in actions
    assert "APPROVE" in actions
    assert "AMEND" in actions

    # 8. Export JSON
    json_res = client.get(f"/api/records/{rec_id}/export/json")
    assert json_res.status_code == 200
    json_data = json_res.get_json()
    assert "export_metadata" in json_data
    assert json_data["record"]["id"] == rec_id

    # 9. Export PDF
    pdf_res = client.get(f"/api/records/{rec_id}/export/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["Content-Type"] == "application/pdf"
    assert len(pdf_res.data) > 1000

# ==========================================================
# 6. Transcription API Handling
# ==========================================================
def test_transcribe_empty_file_rejected(client):
    data = {"audio": (io.BytesIO(b""), "empty.webm")}
    res = client.post("/api/transcription/transcribe", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    assert "empty" in res.get_json()["error"].lower()

def test_transcribe_corrupt_file_rejected(client):
    data = {"audio": (io.BytesIO(b"RIFF_FAKE_CORRUPTED_HEADER_BYTES_12345"), "corrupt.wav")}
    res = client.post("/api/transcription/transcribe", data=data, content_type="multipart/form-data")
    assert res.status_code in [422, 500]

def test_transcribe_real_audio(client):
    test_audio_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_audio", "paracetamol_phrase.wav"))
    if not os.path.exists(test_audio_path):
        pytest.skip("Test audio file not generated.")

    with open(test_audio_path, "rb") as f:
        audio_bytes = f.read()

    data = {"audio": (io.BytesIO(audio_bytes), "paracetamol_phrase.wav")}
    res = client.post("/api/transcription/transcribe", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    resp_json = res.get_json()
    assert resp_json["success"] is True
    transcript = resp_json["data"]["transcript"].lower()
    assert "paracetamol" in transcript
