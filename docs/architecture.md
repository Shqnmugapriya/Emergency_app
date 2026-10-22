# Field-to-Record: Architecture Documentation

## 1. System Overview

Field-to-Record is an offline-first pre-hospital clinical documentation assistant designed for emergency medical responders (paramedics, EMTs, disaster response personnel).

### Core Principle
**Documentation Assistant, Not a Diagnostic or Treatment Engine.**
The application accelerates the capture of structured encounter data from verbal notes while keeping the clinician firmly in the loop with strict human-in-the-loop review before finalizing records.

```
+-------------------------------------------------------------------------+
|                              FRONTEND                                   |
|   React (Vite) + Tailwind CSS + Lucide Icons                            |
|   - Microphone Recording (MediaRecorder API) / File Upload              |
|   - Human-in-the-loop Review & Ambiguity Resolution UI                  |
|   - Chronological Visual Timeline & Status Dashboard                    |
+------------------------------------+------------------------------------+
                                     | HTTP REST (VITE_API_BASE_URL)
                                     v
+------------------------------------+------------------------------------+
|                               BACKEND                                   |
|   Python 3.10 + Flask + Flask-CORS                                      |
|                                                                         |
|   +-----------------------+     +----------------------------------+    |
|   |  Speech-to-Text       |     |  Clinical Entity Extraction      |    |
|   |  - faster-whisper     |     |  - Regex & Lexical NLP Parser    |    |
|   |  - CPU int8 inference |     |  - Vitals, Meds, Routes, Units   |    |
|   |  - Clinical Priming   |     |  - Negation Detection Triggers   |    |
|   +-----------------------+     +----------------------------------+    |
|                                                                         |
|   +-----------------------+     +----------------------------------+    |
|   |  Medicine Catalogue   |     |  Safety & Consistency Validation |    |
|   |  - WHO Model List     |     |  - Physiological contradictions  |    |
|   |  - RapidFuzz ranking  |     |  - Critical warning gates        |    |
|   |  - Ambiguity alerts   |     |  - Missing dosage / unit alerts  |    |
|   +-----------------------+     +----------------------------------+    |
|                                                                         |
|   +-----------------------+     +----------------------------------+    |
|   |  Report Compilation   |     |  Local Persistence & Audit       |    |
|   |  - Structured JSON    |     |  - SQLite (WAL mode)             |    |
|   |  - ReportLab PDF Run  |     |  - Immutable Audit Log Table     |    |
|   +-----------------------+     +----------------------------------+    |
+------------------------------------+------------------------------------+
                                     |
                                     v
                       +---------------------------+
                       | Local File System Storage |
                       | data/db/ (field_to_record)|
                       | data/audio/ (Recordings)  |
                       | data/reports/ (PDFs)      |
                       | models/ (Whisper weights) |
                       +---------------------------+
```

## 2. Key Modules

### A. Speech Recognition Engine (`backend/services/transcription_service.py`)
- Powered by `faster-whisper` (CTranslate2).
- Zero external cloud transmission.
- Runs on standard laptop CPUs via `int8` quantization.
- Implements clinical domain vocabulary priors via `initial_prompt`.
- Built-in Voice Activity Detection (`vad_filter=True`) to strip silence artifacts.

### B. Verified Medicine Catalogue (`backend/services/medicine_service.py`)
- Verified against the **WHO Model List of Essential Medicines (23rd Ed. 2023)** and **JRCALC Pre-Hospital Clinical Practice Guidelines**.
- Exact canonical matching and verified aliases take precedence.
- RapidFuzz ranks candidate medicines when typos occur, but **never silently assigns medicine identity**.
- Ambiguity threshold: When multiple medicines score closely (score delta < 12%), an `AMBIGUOUS` flag is raised, requiring human clinician confirmation in the UI.

### C. Clinical NLP Extractor (`backend/services/clinical_extractor.py`)
- Extracts physiological vitals: Blood Pressure, Pulse/Heart Rate, Respiratory Rate, SpO2, Temperature, GCS, Blood Glucose.
- Preserves verbatim source spans, character offsets, and verification states (`Extracted`, `Verified`, `Uncertain`, `Unknown`, `Missing`, `Conflicting`, `Rejected`).
- Negation detection: Identifies explicit negations ("patient denies chest pain", "did not give morphine") and marks `is_negated: True`.

### D. Validation & Safety Rules (`backend/services/validation_service.py`)
- Physiological contradictions (e.g., Systolic BP <= Diastolic BP, SpO2 > 100%).
- Missing required fields (e.g., medication administered without dosage or route).
- Critical warning gate blocks record approval unless explicitly resolved or overridden with clinician justification.

### E. Traceability & Immutability (`backend/database/db.py`)
- Status progression: `Draft` -> `Needs Review` -> `Reviewed` -> `Approved` -> `Amended`.
- Approved records are immutable to standard PUT requests.
- Amendments increment version numbers (`v1` -> `v2`) and require an explicit justification note.
- Immutable `audit_logs` table logs every user and system event with timestamp and payload diff.
