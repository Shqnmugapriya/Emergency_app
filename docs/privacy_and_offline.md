# Privacy, Security, and Offline Operation Guide

## 1. Zero Cloud Data Transmission
Field-to-Record is architected from the ground up for strict offline execution:
- Speech recognition runs locally using `faster-whisper` compiled with `CTranslate2`.
- Audio blobs never leave `localhost`.
- Clinical entity extraction, RapidFuzz fuzzy matching, and SQLite persistence execute entirely in-process within the local Python runtime.
- No third-party analytics, external fonts, or cloud AI services are called.

## 2. Audio Retention and De-identification
- Uploaded audio is stored in `data/audio/` under non-sequential UUID identifiers (e.g. `rec_a9f1b2c4...webm`).
- Path traversal protections (`werkzeug.utils.secure_filename`) prevent arbitrary filesystem access.
- Original audio is preserved for clinical and legal audit purposes and can be securely scrubbed according to jurisdictional data retention policies.

## 3. Immutability and Traceability
- Encounters transition through a formal clinical status flow: `Draft` -> `Needs Review` -> `Reviewed` -> `Approved` -> `Amended`.
- Approved records are write-protected; any subsequent clinical modification requires a formal amendment request with an explicit clinical justification (`amendment_reason`), incrementing the document version number.
- All actions are logged to the `audit_logs` SQLite table with actor ID, timestamp, and modification payload.

## 4. Local Deployment Security Checklist
- Run backend behind a local reverse proxy or restricted loopback binding (`127.0.0.1`).
- Enable full-disk encryption (e.g., BitLocker) on laptops deploying the Field-to-Record local database.
