# Field-to-Record REST API Specification

Base URL: `http://127.0.0.1:5000/api`

## Endpoints Summary

### System Diagnostics
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check verifying Flask and SQLite accessibility |
| `GET` | `/api/transcription/status` | Reports whether Whisper is ready, missing, loading, or in error |
| `POST` | `/api/transcription/load` | Dynamically loads or switches model (`tiny`, `base`, `small`) |

### Speech Recognition
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/transcription/transcribe` | Multipart FormData audio upload (`audio` or `file`). Returns transcript, language info, segment timestamps, audio file reference. |

### Clinical Processing & Medicines
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/clinical/extract` | Extract vitals, medications, symptoms, procedures, negation, and timestamps from text |
| `POST` | `/api/clinical/validate` | Evaluates consistency rules and returns structured validation warnings |
| `GET` | `/api/medicines/search?q={query}` | Search verified medicine catalogue with RapidFuzz ranking & ambiguity detection |
| `GET` | `/api/medicines/catalogue` | Returns all 12 verified essential medicines with provenance and routes |

### Record Lifecycle & Auditing
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/records` | Create new clinical record (Draft / Needs Review) |
| `GET` | `/api/records` | List records with pagination and status filters |
| `GET` | `/api/records/<record_id>` | Retrieve full structured record with clinical findings |
| `PUT` | `/api/records/<record_id>` | Update draft transcript, clinical entities, or review decisions |
| `POST` | `/api/records/<record_id>/approve` | Finalize and approve record. Blocks if unresolved critical warnings exist without override notes. |
| `POST` | `/api/records/<record_id>/amend` | Amend an approved record. Requires justification reason and increments version. |
| `GET` | `/api/records/<record_id>/export/json` | Download structured clinical JSON export |
| `GET` | `/api/records/<record_id>/export/pdf` | Download official formatted clinical run PDF |
| `GET` | `/api/records/<record_id>/audit` | Retrieve complete immutable audit trail |

### Audio Streaming
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/audio/<filename>` | Securely stream stored field recording to browser audio player |
