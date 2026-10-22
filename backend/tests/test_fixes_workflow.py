"""
Automated workflow tests verifying FIX 1 through FIX 7:
A: Register new patient and verify persistence across backend restart.
B: Create an encounter linked to that patient.
C: Create an unidentified encounter without inventing an identity.
D: Perform a real transcription request using local faster-whisper.
E: Verify transcription response returns words, timestamps, and model-derived probabilities without fake percentages.
F: Save initial clinical record as Version 1.
G: Approve Version 1 and verify approval status.
H: Amend record with Blood Pressure (120/80 mmHg) and Heartbeat noted as normal.
I: Verify Version 2 structured extraction, immutable Version 1 preservation, separate export snapshots, and approval reset.
J: Verify Accuracy & Trust is removed from main UI navigation while telemetry/trust APIs remain intact.
"""

import pytest
import os
import io
import json
import sqlite3
from backend.app import create_app
from backend.database.db import init_db, get_db_path, get_db_connection

@pytest.fixture
def test_app_and_client(tmp_path):
    test_db = str(tmp_path / "test_workflow.db")
    os.environ["FIELD_RECORD_DB_PATH"] = test_db
    
    app = create_app()
    app.config["TESTING"] = True
    
    with app.app_context():
        init_db()
        
    client = app.test_client()
    yield app, client, test_db

def test_workflow_fixes_a_through_j(test_app_and_client):
    app, client, test_db = test_app_and_client

    # -------------------------------------------------------------------------
    # ITEM A: Register a new patient and verify persistence across backend restart
    # -------------------------------------------------------------------------
    patient_payload = {
        "full_name": "Eleanor Vance",
        "dob": "1988-11-23",
        "gender": "Female",
        "phone": "+1-555-0199",
        "blood_type": "A+",
        "allergies": ["Penicillin", "Latex"],
        "medical_history": ["Mild Asthma"]
    }
    reg_res = client.post("/api/patients", json=patient_payload)
    assert reg_res.status_code == 201, f"Patient registration failed: {reg_res.get_data(as_text=True)}"
    reg_data = reg_res.get_json()["data"]
    patient_id = reg_data["id"]
    display_id = reg_data["patient_id_display"]
    assert patient_id.startswith("PAT-")
    assert display_id.startswith("PT-")

    # Duplicate registration prevention via multi-factor identity (Name + DOB)
    dup_res = client.post("/api/patients", json=patient_payload)
    assert dup_res.status_code == 400
    assert "already registered" in dup_res.get_json()["error"].lower()

    # Simulate backend restart: create a new app instance connecting to the same DB
    restarted_app = create_app()
    restarted_app.config["TESTING"] = True
    restarted_client = restarted_app.test_client()

    verify_pt = restarted_client.get(f"/api/patients/{patient_id}")
    assert verify_pt.status_code == 200
    persisted_patient = verify_pt.get_json()["data"]
    assert persisted_patient["full_name"] == "Eleanor Vance"
    assert persisted_patient["dob"] == "1988-11-23"
    assert "Penicillin" in persisted_patient["allergies"]

    # -------------------------------------------------------------------------
    # ITEM B: Create an encounter linked to that patient
    # -------------------------------------------------------------------------
    linked_enc_payload = {
        "call_number": "EMS-7011",
        "responder_id": "Medic-Alpha",
        "corrected_transcript": "Patient Eleanor Vance reported mild shortness of breath. Administered Salbutamol 2.5mg nebulized.",
        "patient_id": patient_id,
        "encounter_type": "NEW_ENCOUNTER",
        "patient_summary": {
            "age": "38",
            "gender": "Female",
            "chief_complaint": "Shortness of breath"
        }
    }
    enc_res = restarted_client.post("/api/records", json=linked_enc_payload)
    assert enc_res.status_code == 201
    enc_data = enc_res.get_json()["data"]
    linked_rec_id = enc_data["id"]
    assert enc_data["patient_id"] == patient_id

    # Verify link is indexed in patient history
    history_res = restarted_client.get(f"/api/patients/{patient_id}/history")
    assert history_res.status_code == 200
    encounters = history_res.get_json()["data"]["encounters"]
    assert any(e["record_id"] == linked_rec_id for e in encounters)

    # -------------------------------------------------------------------------
    # ITEM C: Create an unidentified encounter without inventing an identity
    # -------------------------------------------------------------------------
    unid_payload = {
        "call_number": "EMS-7012",
        "responder_id": "Medic-Bravo",
        "corrected_transcript": "Found unresponsive adult on sidewalk. Pulse 84, respirations 16, no identification present.",
        "patient_id": None, # Preserves unidentified status!
        "encounter_type": "NEW_ENCOUNTER"
    }
    unid_res = restarted_client.post("/api/records", json=unid_payload)
    assert unid_res.status_code == 201
    unid_rec = unid_res.get_json()["data"]
    assert unid_rec["patient_id"] is None

    # Later linking after identity is verified:
    link_later_res = restarted_client.post(f"/api/patients/{patient_id}/link", json={
        "record_id": unid_rec["id"],
        "encounter_type": "NEW_ENCOUNTER",
        "actor": "Triage Nurse"
    })
    assert link_later_res.status_code == 200

    # -------------------------------------------------------------------------
    # ITEM D: Real transcription request using local speech recognition audio fixture
    # -------------------------------------------------------------------------
    audio_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_audio", "paracetamol_phrase.wav"))
    assert os.path.exists(audio_path), f"Audio fixture missing at {audio_path}"

    with open(audio_path, "rb") as af:
        audio_bytes = af.read()

    transcribe_res = restarted_client.post(
        "/api/transcription/transcribe",
        data={"audio": (io.BytesIO(audio_bytes), "paracetamol_phrase.wav")},
        content_type="multipart/form-data"
    )
    assert transcribe_res.status_code == 200
    transcribe_data = transcribe_res.get_json()["data"]
    assert transcribe_data["transcript"] != ""
    assert "paracetamol" in transcribe_data["transcript"].lower()

    # -------------------------------------------------------------------------
    # ITEM E: Verify transcription response words, timestamps, and model probabilities
    # -------------------------------------------------------------------------
    words = transcribe_data.get("words", [])
    assert len(words) > 0, "Transcription must return word tokens"
    for w in words:
        assert "word" in w
        assert "start" in w
        assert "end" in w
        assert w["end"] >= w["start"]
        # Model-derived probability must be a float between 0 and 1, or None if unaligned
        if w["probability"] is not None:
            assert isinstance(w["probability"], (float, int))
            assert 0.0 <= w["probability"] <= 1.0
            # Must NOT be an invented 99.999% fake number
            assert w["confidence_category"] in ["HIGH", "UNCERTAIN", "LOW", "NOT_AVAILABLE"]

    # Check medical catalogue verification attached to word tokens
    paracetamol_word = next((w for w in words if "paracetamol" in w["word"].lower()), None)
    if paracetamol_word:
        assert paracetamol_word["medical_match"]["status"] in ["EXACT_MATCH", "ALIAS_MATCH"]
        assert paracetamol_word["medical_match"]["matched_entity"] == "Paracetamol"

    # -------------------------------------------------------------------------
    # ITEM F: Save initial clinical record as Version 1
    # -------------------------------------------------------------------------
    v1_payload = {
        "call_number": "EMS-7015",
        "responder_id": "Medic-101",
        "machine_transcript": "Patient has fever and took paracetamol 500mg.",
        "corrected_transcript": "Patient has fever and took paracetamol 500mg."
    }
    v1_res = restarted_client.post("/api/records", json=v1_payload)
    assert v1_res.status_code == 201
    v1_rec = v1_res.get_json()["data"]
    test_rec_id = v1_rec["id"]
    assert v1_rec["version"] == 1
    assert v1_rec["status"] in ["Draft", "Needs Review"]

    # Verify structured clinical data in Version 1
    v1_clinical = v1_rec["clinical_data"]
    assert any(m["canonical_name"] == "Paracetamol" for m in v1_clinical["medications"])
    assert any("fever" in s["symptom"].lower() for s in v1_clinical["symptoms"])

    # -------------------------------------------------------------------------
    # ITEM G: Approve Version 1 and verify approval status
    # -------------------------------------------------------------------------
    approve_res = restarted_client.post(f"/api/records/{test_rec_id}/approve", json={
        "reviewer_id": "Dr. House",
        "override_notes": "Reviewed and verified initial run."
    })
    assert approve_res.status_code == 200
    approved_v1 = approve_res.get_json()["data"]
    assert approved_v1["status"] == "Approved"
    assert approved_v1["approved_at"] is not None
    assert approved_v1["version"] == 1

    # -------------------------------------------------------------------------
    # ITEM H: Amend the record with Blood Pressure 120/80 mmHg & Heartbeat noted as normal
    # -------------------------------------------------------------------------
    amended_transcript = (
        "Patient has fever and took paracetamol 500mg. "
        "Blood Pressure: 120/80 mmHg. Heartbeat noted as normal."
    )
    amend_res = restarted_client.post(f"/api/records/{test_rec_id}/amend", json={
        "reason": "Secondary triage assessment: recorded blood pressure and cardiac rhythm examination.",
        "corrected_transcript": amended_transcript
    })
    assert amend_res.status_code == 200
    v2_rec = amend_res.get_json()["data"]

    # -------------------------------------------------------------------------
    # ITEM I: Verify Version 2 structured extraction, V1 snapshot preservation,
    #         separate export snapshots, and approval reset
    # -------------------------------------------------------------------------
    # 1. Version 2 created
    assert v2_rec["version"] == 2

    # 2. Approval is cleared for Version 2 so it can be reviewed independently
    assert v2_rec["status"] in ["Needs Review", "Amended"]
    assert v2_rec["approved_at"] is None

    # 3. Amended clinical facts are mapped into structured fields
    v2_clinical = v2_rec["clinical_data"]
    vitals = v2_clinical.get("vital_signs", [])
    bp_vital = next((v for v in vitals if "blood pressure" in v["name"].lower()), None)
    assert bp_vital is not None, "Blood Pressure must be mapped into structured vital_signs"
    assert bp_vital["value"] == "120/80"
    assert bp_vital["unit"] == "mmHg"

    examinations = v2_clinical.get("examinations", [])
    heartbeat_exam = next((e for e in examinations if "heartbeat" in e["finding"].lower() or "cardiovascular" in e["system"].lower()), None)
    assert heartbeat_exam is not None, "Heartbeat observation must be mapped into structured examinations"
    assert heartbeat_exam["value"] == "normal"

    # 4. Version 1 snapshot remains intact and immutable
    versions_res = restarted_client.get(f"/api/records/{test_rec_id}/versions")
    assert versions_res.status_code == 200
    res_data = versions_res.get_json()
    history_versions = res_data.get("versions") if "versions" in res_data else res_data["data"]
    v1_snapshot_meta = next((v for v in history_versions if v["version_number"] == 1), None)
    assert v1_snapshot_meta is not None, "Version 1 snapshot must exist in version history"

    v1_snap_res = restarted_client.get(f"/api/records/{test_rec_id}/versions/1")
    assert v1_snap_res.status_code == 200
    v1_snap_data = v1_snap_res.get_json()["data"]["snapshot_data"]
    # V1 snapshot narrative must NOT contain Blood Pressure or Heartbeat
    assert "120/80" not in v1_snap_data["corrected_transcript"]
    # V1 snapshot structured vitals must NOT contain Blood Pressure
    assert not any("blood pressure" in v["name"].lower() for v in v1_snap_data["clinical_data"].get("vital_signs", []))

    # 5. Version 1 export reflects only Version 1 data
    v1_export_res = restarted_client.get(f"/api/records/{test_rec_id}/export/json?version=1")
    assert v1_export_res.status_code == 200
    v1_export_json = v1_export_res.get_json()
    assert v1_export_json["export_metadata"]["version"] == 1
    assert "120/80" not in v1_export_json["record"]["corrected_transcript"]
    assert not any("blood pressure" in v["name"].lower() for v in v1_export_json["record"]["clinical_data"].get("vital_signs", []))

    # 6. Version 2 export reflects the updated clinical data
    v2_export_res = restarted_client.get(f"/api/records/{test_rec_id}/export/json?version=2")
    assert v2_export_res.status_code == 200
    v2_export_json = v2_export_res.get_json()
    assert v2_export_json["export_metadata"]["version"] == 2
    assert "120/80" in v2_export_json["record"]["corrected_transcript"]
    assert any("blood pressure" in v["name"].lower() for v in v2_export_json["record"]["clinical_data"].get("vital_signs", []))
    assert any("heartbeat" in e["finding"].lower() for e in v2_export_json["record"]["clinical_data"].get("examinations", []))

    # PDF exports for V1 and V2
    v1_pdf_res = restarted_client.get(f"/api/records/{test_rec_id}/export/pdf?version=1")
    assert v1_pdf_res.status_code == 200
    assert v1_pdf_res.mimetype == "application/pdf"
    assert len(v1_pdf_res.data) > 1000

    v2_pdf_res = restarted_client.get(f"/api/records/{test_rec_id}/export/pdf?version=2")
    assert v2_pdf_res.status_code == 200
    assert v2_pdf_res.mimetype == "application/pdf"
    assert len(v2_pdf_res.data) > 1000

    # -------------------------------------------------------------------------
    # ITEM J: Verify Accuracy & Trust is removed from main UI navigation while
    #         underlying trust/accuracy checks remain accessible for maintenance/audit
    # -------------------------------------------------------------------------
    frontend_nav_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "components", "Navbar.jsx"))
    with open(frontend_nav_path, "r", encoding="utf-8") as f:
        navbar_src = f.read()

    # Accuracy & Trust must NOT appear as a user navigation item
    assert "Accuracy & Trust" not in navbar_src
    assert "nav-trust" not in navbar_src

    # Backend trust telemetry endpoint remains accessible for audit/maintenance
    trust_status_res = restarted_client.get("/api/trust/status")
    assert trust_status_res.status_code == 200
    trust_data = trust_status_res.get_json()["data"]
    assert "database" in trust_data
    assert "speech_model" in trust_data
    assert "audio_pipeline" in trust_data
