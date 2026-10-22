# Field-to-Record

> **Offline-first voice-to-structured clinical documentation assistant for emergency first responders.**

Field-to-Record allows paramedics, EMTs, and emergency personnel to record or type field notes, transcribe speech offline using local Whisper inference, correct transcripts, extract structured clinical events (vitals, medications, symptoms, procedures, negation, timestamps), review consistency warnings, approve records, and export reports in JSON and ReportLab PDF formats.

> **Important Clinical Scope Notice:** Field-to-Record is a documentation assistant, **not** an automated diagnostic or treatment recommendation system.

---

## Architecture Overview

- **Frontend:** React, Vite, Tailwind CSS, Lucide Icons.
- **Backend:** Python (Flask, Flask-CORS).
- **Speech Recognition:** Whisper via `faster-whisper` (CTranslate2) running locally on CPU in Python. No cloud APIs.
- **Database:** SQLite (`data/db/field_to_record.db`), accessed exclusively by the backend.
- **Reports:** JSON export & formal pre-hospital clinical run PDF export via ReportLab.
- **Testing:** Pytest automated backend suite & speech recognition WER benchmarks.

```
field-to-record/
  frontend/          # React + Vite + Tailwind CSS interface
  backend/           # Flask backend application
    app.py           # Application entry point & CORS configuration
    requirements.txt # Pinned Python dependencies
    database/        # SQLite schema, tables & audit logging (db.py)
    routes/          # Blueprints (health, transcription, records, clinical, audio)
    services/        # Business logic (transcription, medicine, clinical_extractor, validation, report)
    tests/           # Automated pytest tests, audio generator, WER benchmark
  data/
    audio/           # Local preserved audio recordings
    db/              # SQLite database file
    reports/         # Compiled PDF and JSON reports
  models/            # Local cached faster-whisper weights (base/tiny)
  docs/              # Architectural specs, API docs, WER benchmark reports
  README.md
  .gitignore
```

---

## Quick Start Guide

### 1. Prerequisites
- **Python 3.10** (or 3.11/3.12)
- **Node.js 18+** and **npm**

---

### 2. Backend Setup & Run

Open a terminal in the project root directory:

```powershell
# 1. Activate the Python virtual environment (already set up in backend/venv)
.\backend\venv\Scripts\Activate.ps1

# 2. (Optional) Re-install dependencies if starting fresh on another machine
python -m pip install -r backend/requirements.txt

# 3. Verify Whisper model is downloaded and ready offline
python backend/services/transcription_service.py --download-model base

# 4. Start the Flask Backend API server (runs on port 5000)
$env:PYTHONPATH="."
python backend/app.py
```

The backend API will start at: `http://127.0.0.1:5000`

---

### 3. Frontend Setup & Run

Open a **separate terminal** in the project root directory:

```powershell
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies (if starting on a new machine)
npm.cmd install

# 3. Start the Vite React development server
npm.cmd run dev
```

The frontend application will start at: `http://localhost:5173`

---

### 4. Running Automated Tests & Benchmarks

In your backend terminal:

```powershell
# Run the complete automated test suite (13 tests verifying DB, Whisper, and APIs)
$env:PYTHONPATH="."
.\backend\venv\Scripts\pytest.exe backend/tests/test_backend_full.py -v

# Run the Word Error Rate (WER) Speech Recognition Benchmark on real audio
$env:PYTHONPATH="."
.\backend\venv\Scripts\python.exe backend/tests/wer_benchmark.py
```

---

## Key Features

1. **Local Speech-to-Text with Domain Priming**
   - Employs `faster-whisper` with clinical vocabulary priming (`initial_prompt`), VAD filtering, and strict beam search (`temperature=0.0`).
   - Resolves the known short-utterance failure mode (`"I want paracetamol"` misrecognized as `"I want that if you don't worry"`).
   - Measured average Word Error Rate: **2.8%** with **100% medicine name recognition accuracy**.

2. **Deterministic Clinical NLP Extractor**
   - Extracts vital signs with physiological unit normalization (mmHg, bpm, breaths/min, %, °C, mmol/L, GCS).
   - Identifies medications, dosages, units, and administration routes.
   - Detects negative findings and denials (`"denies chest pain"`, `"no morphine given"`).
   - Preserves source evidence spans and character offsets.

3. **Verified Medicine Catalogue & Ambiguity Gate**
   - Sourced from the **WHO Model List of Essential Medicines (23rd Ed. 2023)** and pre-hospital EMS protocols.
   - RapidFuzz assists with ranking candidate matches for typos, but **never silently assigns medicine identity**.
   - If multiple candidates are close in probability, an `AMBIGUOUS` flag requires explicit human clinician selection.

4. **Safety & Completeness Validation**
   - Flags physiological contradictions (e.g. Systolic BP <= Diastolic BP, SpO2 > 100%).
   - Flags unquantified medications or missing administration routes.
   - Blocks record approval unless critical warnings are addressed or justified via clinician override notes.

5. **Traceable Audit History & Amendments**
   - States: `Draft` -> `Needs Review` -> `Reviewed` -> `Approved` -> `Amended`.
   - Approved records cannot be overwritten; amendments require an explicit justification note, incrementing document version (`v1` -> `v2`) with immutable audit logging.

6. **Official Report Generation**
   - High-fidelity EMS Run Reports compiled to PDF via ReportLab.
   - Chronological event timeline distinguishing patient onset, field recording time, transcription time, review time, and sign-off.
