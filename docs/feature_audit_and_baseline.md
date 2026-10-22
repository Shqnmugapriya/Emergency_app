# Field-to-Record: Feature Inventory, Audit, and Baseline Report

## 1. Executive Summary & Verification Checkpoint
- **Git Baseline Commit**: `c5460b6` ("Baseline: Working Field-to-Record system before additive enhancements")
- **Database Backup**: `data/db/field_to_record_baseline.db`
- **Baseline Test Suite**: 13/13 passing in `backend/tests/test_backend_full.py` (2.85s)
- **Speech Benchmark**: 100% medicine accuracy, 2.8% primed average WER on real SAPI audio (`backend/tests/wer_benchmark.py`)

---

## 2. Existing Feature Inventory & Operational Status

| Component / Subsystem | Status | Relevant Existing Files | Notes & Behavior |
| :--- | :--- | :--- | :--- |
| **Local Speech-to-Text** | Working | `backend/services/transcription_service.py`, `backend/routes/transcription_routes.py` | Faster-Whisper `base` model running CPU int8 offline. Clinical prompt vocabulary priming active. VAD filtering enabled. |
| **Clinical Entity Extraction** | Working | `backend/services/clinical_extractor.py`, `backend/routes/clinical_routes.py` | Regex & lexical NLP parser extracts Vitals (BP, HR, RR, SpO2, Temp, GCS, BGL), Medications, Symptoms, Procedures, Negation (`is_negated: True`), and Timestamps. Overlapping BP spans deduplicated. |
| **Verified Medicine Catalogue** | Working | `backend/services/medicine_service.py`, `backend/database/db.py` | 12 essential pre-hospital medicines (Paracetamol, Ibuprofen, Aspirin, Morphine, Naloxone, Salbutamol, Nitroglycerin, Epinephrine, Fentanyl, Ondansetron, Midazolam, Oxygen). Exact match, alias match, RapidFuzz ranking. |
| **Validation Rules Engine** | Working | `backend/services/validation_service.py` | Critical warnings for physiological contradictions (SBP <= DBP, SpO2 > 100%), missing dosages/routes, ambiguous medicines, and pediatric warnings. |
| **Record Lifecycle & SQLite** | Working | `backend/database/db.py`, `backend/routes/record_routes.py` | States: `Draft` -> `Needs Review` -> `Reviewed` -> `Approved` -> `Amended`. Immutable audit trail in `audit_logs` table. Version incrementing on amendment. |
| **Reports (JSON & PDF)** | Working | `backend/services/report_service.py` | Structured JSON export. ReportLab PDF generation with single-page density, non-overlapping two-line footers, and clean UTC timestamps. |
| **React Frontend** | Working | `frontend/src/App.jsx`, `frontend/src/pages/*`, `frontend/src/components/*` | Dashboard, Voice Input (MediaRecorder), Clinical Review, Timeline, Records table, Record Details, Settings & System Status. |

---

## 3. Architecture Preservation & Additive Strategy Plan

All enhancements are designed as **additive extensions** around the existing architecture without removing, renaming, or breaking existing database tables, API routes, or React pages:

```
Existing Tables (Preserved):
  records (id, call_number, responder_id, status, created_at, updated_at, ...)
  audit_logs (id, record_id, action, actor, timestamp, details)
  medicine_catalogue (id, canonical_name, aliases, category, standard_routes, ...)

New Additive Tables (Compatible Extensions):
  patients (id PRIMARY KEY, patient_id_display, full_name, dob, gender, blood_type, allergies, conditions, emergency_contact, created_at, updated_at)
  patient_encounters (id PRIMARY KEY, patient_id REFERENCES patients(id), record_id REFERENCES records(id), encounter_type, created_at)
  evidence_passports (id PRIMARY KEY, record_id REFERENCES records(id), field_id, field_name, source_type, source_text, char_start, char_end, audio_start, audio_end, extracted_value, corrected_value, verification_state, decision_timestamp, reviewer_id)
  record_versions (id PRIMARY KEY, record_id REFERENCES records(id), version_number, snapshot_json, approved_at, approved_by, amendment_reason)
  accuracy_eval_logs (id PRIMARY KEY, test_suite_name, model_version, exact_match_accuracy, wer_score, precision_score, recall_score, f1_score, sample_count, evaluated_at, details_json)
```

### Existing Columns on `records` Table Extension
To maintain backward compatibility:
- Add nullable foreign key: `patient_id TEXT` (defaults to NULL / Unassigned for legacy encounters).
- Add nullable timestamps: `event_at TEXT`, `exported_at TEXT` (without modifying existing `created_at` or `updated_at`).
- Add JSON column: `evidence_passport TEXT DEFAULT '[]'`.
- Add JSON column: `uncertainty_ledger TEXT DEFAULT '[]'`.
- Add JSON column: `change_impact_radar TEXT DEFAULT '{}'`.
