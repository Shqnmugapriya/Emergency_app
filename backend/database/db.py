"""
Database management for Field-to-Record.
Offline SQLite storage for clinical documentation, audit history, and medicine catalogue.
"""

import sqlite3
import json
import os
import uuid
from datetime import datetime, timezone

DATABASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "db"))
DATABASE_PATH = os.path.join(DATABASE_DIR, "field_to_record.db")

def get_db_path():
    return os.environ.get("FIELD_RECORD_DB_PATH", DATABASE_PATH)

def get_db_connection():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initialize database tables and seed medicine catalogue if empty."""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Records table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id TEXT PRIMARY KEY,
            call_number TEXT,
            responder_id TEXT DEFAULT 'Paramedic-101',
            status TEXT NOT NULL DEFAULT 'Draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            recording_time TEXT,
            transcription_time TEXT,
            reviewed_at TEXT,
            approved_at TEXT,
            audio_filename TEXT,
            audio_mimetype TEXT,
            audio_duration_seconds REAL DEFAULT 0.0,
            machine_transcript TEXT DEFAULT '',
            corrected_transcript TEXT DEFAULT '',
            transcription_metadata TEXT DEFAULT '{}',
            clinical_data TEXT DEFAULT '{}',
            validation_warnings TEXT DEFAULT '[]',
            review_decisions TEXT DEFAULT '{}',
            patient_summary TEXT DEFAULT '{}',
            version INTEGER DEFAULT 1
        );
    """)

    # Audit logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            details TEXT DEFAULT '{}',
            FOREIGN KEY (record_id) REFERENCES records (id) ON DELETE CASCADE
        );
    """)

    # Medicine catalogue table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicine_catalogue (
            id TEXT PRIMARY KEY,
            canonical_name TEXT NOT NULL UNIQUE,
            aliases TEXT NOT NULL,
            category TEXT NOT NULL,
            standard_routes TEXT NOT NULL,
            standard_units TEXT NOT NULL,
            typical_doses TEXT NOT NULL,
            pediatric_warning INTEGER DEFAULT 0,
            contraindications_notes TEXT,
            provenance TEXT NOT NULL,
            version TEXT NOT NULL
        );
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_status ON records(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_created ON records(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_record_id ON audit_logs(record_id);")

    conn.commit()
    seed_medicine_catalogue(conn)
    conn.close()

def seed_medicine_catalogue(conn):
    """Seed verified local medicine catalogue with provenance."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM medicine_catalogue;")
    if cursor.fetchone()[0] > 0:
        return

    # Verified EMS & First Responder Essential Medicines Catalogue (WHO Model List 2023 / EMS Formulary v1.2)
    catalog = [
        {
            "id": "MED-001",
            "canonical_name": "Paracetamol",
            "aliases": ["Acetaminophen", "Tylenol", "Panadol", "Calpol", "APAP", "Paramol"],
            "category": "Analgesic / Antipyretic",
            "standard_routes": ["Oral", "IV", "PR"],
            "standard_units": ["mg", "g"],
            "typical_doses": ["500mg", "1000mg", "1g", "15mg/kg"],
            "pediatric_warning": 0,
            "contraindications_notes": "Severe hepatic impairment or active liver disease.",
            "provenance": "WHO Model List of Essential Medicines (23rd list, 2023) / Resuscitation Guidelines v1.2",
            "version": "1.2.0"
        },
        {
            "id": "MED-002",
            "canonical_name": "Ibuprofen",
            "aliases": ["Advil", "Motrin", "Nurofen", "Brufen"],
            "category": "NSAID",
            "standard_routes": ["Oral"],
            "standard_units": ["mg"],
            "typical_doses": ["200mg", "400mg", "600mg"],
            "pediatric_warning": 0,
            "contraindications_notes": "Active GI bleeding, third-trimester pregnancy, severe renal failure.",
            "provenance": "WHO Model List of Essential Medicines (2023) / JRCALC EMS Guidelines",
            "version": "1.2.0"
        },
        {
            "id": "MED-003",
            "canonical_name": "Aspirin",
            "aliases": ["Acetylsalicylic Acid", "ASA", "Disprin", "Bayer"],
            "category": "Antiplatelet / Analgesic",
            "standard_routes": ["Oral", "Chewable"],
            "standard_units": ["mg"],
            "typical_doses": ["75mg", "150mg", "300mg", "324mg"],
            "pediatric_warning": 1,
            "contraindications_notes": "Reye's syndrome risk in pediatric patients under 16; active gastrointestinal ulcer.",
            "provenance": "American Heart Association ACLS / WHO EML 2023",
            "version": "1.2.0"
        },
        {
            "id": "MED-004",
            "canonical_name": "Morphine",
            "aliases": ["Morphine Sulfate", "MS Contin", "Duramorph"],
            "category": "Opioid Analgesic",
            "standard_routes": ["IV", "IM", "SC", "Oral"],
            "standard_units": ["mg"],
            "typical_doses": ["2mg", "2.5mg", "5mg", "10mg"],
            "pediatric_warning": 1,
            "contraindications_notes": "Severe respiratory depression, hypotension (systolic < 90), altered consciousness.",
            "provenance": "JRCALC Clinical Practice Guidelines / WHO EML 2023",
            "version": "1.2.0"
        },
        {
            "id": "MED-005",
            "canonical_name": "Naloxone",
            "aliases": ["Narcan", "Evzio"],
            "category": "Opioid Antagonist",
            "standard_routes": ["IN", "IM", "IV", "SC"],
            "standard_units": ["mg", "mcg"],
            "typical_doses": ["0.4mg", "0.8mg", "2mg", "4mg"],
            "pediatric_warning": 0,
            "contraindications_notes": "Known hypersensitivity; may precipitate acute opioid withdrawal.",
            "provenance": "WHO Guidelines on Community Management of Opioid Overdose / ACLS 2023",
            "version": "1.2.0"
        },
        {
            "id": "MED-006",
            "canonical_name": "Salbutamol",
            "aliases": ["Albuterol", "Ventolin", "Proventil", "Accuneb"],
            "category": "Short-acting Beta-2 Agonist (Bronchodilator)",
            "standard_routes": ["Inhaled", "Nebulized"],
            "standard_units": ["mg", "mcg", "puffs"],
            "typical_doses": ["2.5mg", "5mg", "2 puffs", "4 puffs", "100mcg"],
            "pediatric_warning": 0,
            "contraindications_notes": "Severe tachycardia, caution in severe cardiac disease.",
            "provenance": "British National Formulary / WHO EML 2023",
            "version": "1.2.0"
        },
        {
            "id": "MED-007",
            "canonical_name": "Nitroglycerin",
            "aliases": ["Glyceryl Trinitrate", "GTN", "Nitrostat", "Nitrolingual"],
            "category": "Vasodilator / Nitrate",
            "standard_routes": ["Sublingual", "Transdermal", "IV"],
            "standard_units": ["mcg", "mg", "tablets", "sprays"],
            "typical_doses": ["400mcg", "0.4mg", "1 spray", "1 tablet"],
            "pediatric_warning": 1,
            "contraindications_notes": "Hypotension (SBP < 90 mmHg), phosphodiesterase-5 inhibitor use within 24-48h.",
            "provenance": "American Heart Association ACS Guidelines / WHO EML 2023",
            "version": "1.2.0"
        },
        {
            "id": "MED-008",
            "canonical_name": "Epinephrine",
            "aliases": ["Adrenaline", "EpiPen", "Auvi-Q"],
            "category": "Sympathomimetic / Vasopressor / Anaphylaxis Agent",
            "standard_routes": ["IM", "IV", "IO", "SC", "Nebulized"],
            "standard_units": ["mg", "mcg", "ml"],
            "typical_doses": ["0.15mg", "0.3mg", "0.5mg", "1mg", "1:1000", "1:10000"],
            "pediatric_warning": 0,
            "contraindications_notes": "No absolute contraindications in life-threatening anaphylaxis or cardiac arrest.",
            "provenance": "ILCOR Resuscitation Guidelines / WHO EML 2023",
            "version": "1.2.0"
        },
        {
            "id": "MED-009",
            "canonical_name": "Fentanyl",
            "aliases": ["Sublimaze", "Actiq", "Duragesic"],
            "category": "Synthetic Opioid Analgesic",
            "standard_routes": ["IV", "IN", "IM", "IO"],
            "standard_units": ["mcg"],
            "typical_doses": ["25mcg", "50mcg", "100mcg"],
            "pediatric_warning": 1,
            "contraindications_notes": "Severe respiratory depression, MAO inhibitor use.",
            "provenance": "Prehospital Trauma Life Support (PHTLS) / JRCALC 2023",
            "version": "1.2.0"
        },
        {
            "id": "MED-010",
            "canonical_name": "Ondansetron",
            "aliases": ["Zofran", "Zuplenz"],
            "category": "Antiemetic (5-HT3 Antagonist)",
            "standard_routes": ["IV", "Oral", "IM", "ODT"],
            "standard_units": ["mg"],
            "typical_doses": ["4mg", "8mg"],
            "pediatric_warning": 0,
            "contraindications_notes": "Prolonged QT interval, concurrent apomorphine use.",
            "provenance": "WHO EML 2023 / EMS Antiemetic Protocols",
            "version": "1.2.0"
        },
        {
            "id": "MED-011",
            "canonical_name": "Midazolam",
            "aliases": ["Versed", "Hypnovel"],
            "category": "Benzodiazepine / Anticonvulsant / Sedative",
            "standard_routes": ["IN", "IV", "IM", "Buccal"],
            "standard_units": ["mg"],
            "typical_doses": ["2.5mg", "5mg", "10mg"],
            "pediatric_warning": 1,
            "contraindications_notes": "Severe respiratory depression, acute narrow-angle glaucoma.",
            "provenance": "American Epilepsy Society / JRCALC 2023",
            "version": "1.2.0"
        },
        {
            "id": "MED-012",
            "canonical_name": "Oxygen",
            "aliases": ["O2", "Supplemental Oxygen"],
            "category": "Medical Gas",
            "standard_routes": ["Inhaled", "Nasal Cannula", "Non-rebreather Mask", "BVM"],
            "standard_units": ["L/min", "%"],
            "typical_doses": ["2 L/min", "4 L/min", "10 L/min", "15 L/min"],
            "pediatric_warning": 0,
            "contraindications_notes": "Target 94-98% SpO2 in most acute conditions; 88-92% in patients at risk of hypercapnic respiratory failure (COPD).",
            "provenance": "British Thoracic Society Emergency Oxygen Guidelines / WHO EML 2023",
            "version": "1.2.0"
        }
    ]

    for item in catalog:
        cursor.execute("""
            INSERT OR REPLACE INTO medicine_catalogue (
                id, canonical_name, aliases, category, standard_routes, standard_units,
                typical_doses, pediatric_warning, contraindications_notes, provenance, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            item["id"],
            item["canonical_name"],
            json.dumps(item["aliases"]),
            item["category"],
            json.dumps(item["standard_routes"]),
            json.dumps(item["standard_units"]),
            json.dumps(item["typical_doses"]),
            item["pediatric_warning"],
            item["contraindications_notes"],
            item["provenance"],
            item["version"]
        ))
    conn.commit()

def log_audit_event(record_id, action, actor, details=None):
    """Log an immutable audit trail entry."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (record_id, action, actor, timestamp, details)
            VALUES (?, ?, ?, ?, ?);
        """, (
            record_id,
            action,
            actor,
            datetime.now(timezone.utc).isoformat(),
            json.dumps(details or {})
        ))
        conn.commit()
    finally:
        conn.close()

def get_record(record_id):
    """Retrieve a single record with parsed JSON structures."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM records WHERE id = ?;", (record_id,))
        row = cursor.fetchone()
        if not row:
            return None
        rec = dict(row)
        rec["transcription_metadata"] = json.loads(rec["transcription_metadata"] or "{}")
        rec["clinical_data"] = json.loads(rec["clinical_data"] or "{}")
        rec["validation_warnings"] = json.loads(rec["validation_warnings"] or "[]")
        rec["review_decisions"] = json.loads(rec["review_decisions"] or "{}")
        rec["patient_summary"] = json.loads(rec["patient_summary"] or "{}")
        return rec
    finally:
        conn.close()

def list_records(limit=100, offset=0, status_filter=None):
    """List records with summary information."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if status_filter:
            cursor.execute("""
                SELECT id, call_number, responder_id, status, created_at, updated_at,
                       audio_duration_seconds, machine_transcript, corrected_transcript,
                       patient_summary, version
                FROM records WHERE status = ?
                ORDER BY created_at DESC LIMIT ? OFFSET ?;
            """, (status_filter, limit, offset))
        else:
            cursor.execute("""
                SELECT id, call_number, responder_id, status, created_at, updated_at,
                       audio_duration_seconds, machine_transcript, corrected_transcript,
                       patient_summary, version
                FROM records
                ORDER BY created_at DESC LIMIT ? OFFSET ?;
            """, (limit, offset))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["patient_summary"] = json.loads(d["patient_summary"] or "{}")
            result.append(d)
        return result
    finally:
        conn.close()

def get_record_audit_logs(record_id):
    """Retrieve full audit log history for a record."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, record_id, action, actor, timestamp, details
            FROM audit_logs
            WHERE record_id = ?
            ORDER BY timestamp ASC;
        """, (record_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["details"] = json.loads(d["details"] or "{}")
            result.append(d)
        return result
    finally:
        conn.close()
