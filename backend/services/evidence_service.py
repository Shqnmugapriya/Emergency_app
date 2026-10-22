"""
Evidence Passport Service: Binds every extracted clinical data point to its underlying evidence.
Tracks:
- Source type ('audio_transcript', 'manual_entry', 'reviewer_correction')
- Verbatim supporting phrase & character offset
- Audio timestamp interval (start/end in seconds) matched against Whisper segments
- Extracted vs corrected values
- Verification status & reviewer decision history
- Highlights unsupported clinical assertions without fabricating evidence
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import uuid
from datetime import datetime, timezone
from backend.database.db import get_db_connection

class EvidencePassportService:

    @classmethod
    def compile_evidence_passport(cls, record_id, clinical_data, transcript_text, transcription_meta=None, reviewer_decisions=None):
        """
        Compile complete Evidence Passport bundle for all clinical items in an encounter.
        Matches extracted items against transcript and Whisper segment timestamps.
        """
        evidence_items = []
        segments = (transcription_meta or {}).get("segments", [])
        decisions = reviewer_decisions or {}

        # 1. Process Vital Signs
        for v in clinical_data.get("vital_signs", []):
            item = cls._build_item_passport(
                record_id=record_id,
                field_id=v.get("id"),
                field_category="VITAL_SIGN",
                field_name=v.get("name", "Vital Sign"),
                extracted_val=f"{v.get('value')} {v.get('unit', '')}".strip(),
                corrected_val=v.get("corrected_value"),
                source_phrase=v.get("source_phrase"),
                char_start=v.get("char_start"),
                char_end=v.get("char_end"),
                current_state=v.get("verification_state", "Extracted"),
                transcript_text=transcript_text,
                segments=segments,
                reviewer_decisions=decisions
            )
            evidence_items.append(item)

        # 2. Process Medications
        for m in clinical_data.get("medications", []):
            val_str = f"{m.get('canonical_name', m.get('raw_mention'))} {m.get('dosage') or ''} {m.get('unit') or ''}".strip()
            item = cls._build_item_passport(
                record_id=record_id,
                field_id=m.get("id"),
                field_category="MEDICATION",
                field_name=m.get("canonical_name", "Medication"),
                extracted_val=val_str,
                corrected_val=m.get("corrected_value"),
                source_phrase=m.get("source_phrase") or m.get("raw_mention"),
                char_start=m.get("char_start"),
                char_end=m.get("char_end"),
                current_state=m.get("verification_state", "Extracted"),
                transcript_text=transcript_text,
                segments=segments,
                reviewer_decisions=decisions,
                extra_notes=f"Route: {m.get('route') or 'Unspecified'} • Provenance: {m.get('provenance', 'Local Catalogue')}"
            )
            evidence_items.append(item)

        # 3. Process Symptoms
        for s in clinical_data.get("symptoms", []):
            neg_prefix = "DENIED: " if s.get("is_negated") else "REPORTED: "
            item = cls._build_item_passport(
                record_id=record_id,
                field_id=s.get("id"),
                field_category="SYMPTOM",
                field_name=s.get("symptom"),
                extracted_val=f"{neg_prefix}{s.get('symptom')}",
                corrected_val=None,
                source_phrase=s.get("source_phrase"),
                char_start=s.get("char_start"),
                char_end=s.get("char_end"),
                current_state=s.get("verification_state", "Extracted"),
                transcript_text=transcript_text,
                segments=segments,
                reviewer_decisions=decisions
            )
            evidence_items.append(item)

        # 4. Process Procedures
        for p in clinical_data.get("procedures", []):
            item = cls._build_item_passport(
                record_id=record_id,
                field_id=p.get("id"),
                field_category="PROCEDURE",
                field_name=p.get("procedure"),
                extracted_val=p.get("procedure"),
                corrected_val=None,
                source_phrase=p.get("source_phrase"),
                char_start=p.get("char_start"),
                char_end=p.get("char_end"),
                current_state=p.get("verification_state", "Extracted"),
                transcript_text=transcript_text,
                segments=segments,
                reviewer_decisions=decisions
            )
            evidence_items.append(item)

        unsupported = sum(1 for e in evidence_items if not e.get("has_supporting_evidence"))
        return {
            "entries": evidence_items,
            "unsupported_claims_count": unsupported,
            "total_count": len(evidence_items)
        }

    @classmethod
    def _build_item_passport(cls, record_id, field_id, field_category, field_name,
                             extracted_val, corrected_val, source_phrase, char_start,
                             char_end, current_state, transcript_text, segments,
                             reviewer_decisions, extra_notes=None):
        """Construct individual evidence token with audio segment alignment."""
        has_phrase = bool(source_phrase and source_phrase.strip())
        source_type = "audio_transcript" if has_phrase else "manual_entry"

        audio_start = None
        audio_end = None

        # Search Whisper segments for timestamp alignment
        if has_phrase and segments:
            search_term = source_phrase.lower()
            for seg in segments:
                seg_text = seg.get("text", "").lower()
                if search_term in seg_text or any(token in seg_text for token in search_term.split() if len(token) > 4):
                    audio_start = seg.get("start")
                    audio_end = seg.get("end")
                    break

        # Verification status check
        v_status = current_state
        if not has_phrase and source_type != "manual_entry":
            v_status = "Unsupported"

        item_decision = reviewer_decisions.get(field_id, {})

        passport_item = {
            "id": f"EVD-{field_id or uuid.uuid4().hex[:6]}",
            "record_id": record_id,
            "field_id": field_id,
            "field_category": field_category,
            "field_name": field_name,
            "source_type": source_type,
            "source_location": source_phrase or "Direct Clinician Entry",
            "char_start": char_start,
            "char_end": char_end,
            "audio_timestamp_start": audio_start,
            "audio_timestamp_end": audio_end,
            "audio_interval_formatted": f"{audio_start}s - {audio_end}s" if audio_start is not None else "No audio timestamp alignment",
            "extracted_value": extracted_val,
            "field_value": extracted_val,
            "corrected_value": corrected_val,
            "verification_status": v_status,
            "has_supporting_evidence": has_phrase,
            "is_supported": has_phrase,
            "supporting_phrase": source_phrase,
            "reviewer_decision": item_decision.get("decision", "Pending Review"),
            "decision_timestamp": item_decision.get("timestamp"),
            "reviewer_id": item_decision.get("reviewer_id", "Reviewer"),
            "notes": extra_notes,
            "compiled_at": datetime.now(timezone.utc).isoformat()
        }

        return passport_item

    @classmethod
    def persist_evidence_passport(cls, record_id, evidence_items):
        """Save evidence items to evidence_passports table."""
        items = evidence_items.get("entries", []) if isinstance(evidence_items, dict) else (evidence_items or [])
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            for ev in items:
                cursor.execute("""
                    INSERT OR REPLACE INTO evidence_passports (
                        id, record_id, field_id, field_category, field_name, source_type,
                        source_location, char_start, char_end, audio_timestamp_start,
                        audio_timestamp_end, extracted_value, corrected_value,
                        verification_status, reviewer_decision, decision_timestamp,
                        reviewer_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    ev["id"],
                    record_id,
                    ev.get("field_id", ""),
                    ev.get("field_category", "GENERAL"),
                    ev.get("field_name", ""),
                    ev.get("source_type", "audio_transcript"),
                    ev.get("source_location", ""),
                    ev.get("char_start"),
                    ev.get("char_end"),
                    ev.get("audio_timestamp_start"),
                    ev.get("audio_timestamp_end"),
                    ev.get("extracted_value", ""),
                    ev.get("corrected_value"),
                    ev.get("verification_status", "Extracted"),
                    ev.get("reviewer_decision"),
                    ev.get("decision_timestamp"),
                    ev.get("reviewer_id"),
                    datetime.now(timezone.utc).isoformat()
                ))
            conn.commit()
        finally:
            conn.close()
