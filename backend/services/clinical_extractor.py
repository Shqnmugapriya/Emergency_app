"""
Clinical Extractor Service: Deterministic rule-based extraction of first responder clinical entities.
Extracts: Vital signs, Medicines, Dosages, Routes, Symptoms, Procedures, Negation, and Timestamps.
Preserves exact text spans, character offsets, source phrases, and verification states.
Purely a documentation assistant: NEVER diagnoses or recommends treatment.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import re
import uuid
from backend.services.medicine_service import MedicineService

# Common clinical symptom keywords
SYMPTOMS_LIST = [
    "chest pain", "shortness of breath", "dyspnea", "wheezing", "stridor", "cough",
    "nausea", "vomiting", "dizziness", "lightheadedness", "headache", "confusion",
    "syncope", "loss of consciousness", "altered mental status", "diaphoresis",
    "palpitations", "abdominal pain", "flank pain", "back pain", "trauma", "laceration",
    "contusion", "hematoma", "bleeding", "hemorrhage", "deformity", "fracture",
    "burn", "rash", "fever", "chills", "numbness", "weakness", "facial droop", "slurred speech"
]

# Common prehospital procedures
PROCEDURES_LIST = [
    "bag-valve-mask", "bvm", "high-flow oxygen", "oxygen therapy", "nasal cannula",
    "non-rebreather mask", "nrb mask", "iv cannulation", "iv access", "cpr",
    "chest compressions", "defibrillation", "shock advised", "shock delivered",
    "wound dressing", "pressure dressing", "tourniquet applied", "splint application",
    "cervical collar", "c-collar", "spinal immobilization", "suctioning",
    "endotracheal intubation", "et tube", "supraglottic airway", "12-lead ecg", "cardiac monitor"
]

# Negation triggers
NEGATION_TRIGGERS = [
    r"\bno\b", r"\bnot\b", r"\bdenies\b", r"\bdenied\b", r"\bwithout\b",
    r"\bdid not\b", r"\bdidn't\b", r"\bnegative for\b", r"\bno signs of\b",
    r"\bfree of\b", r"\bno report of\b"
]

class ClinicalExtractor:

    @classmethod
    def extract_all(cls, transcript_text):
        """
        Extract all clinical entities from a transcript string.
        Returns a dictionary of structured clinical findings.
        """
        if not transcript_text:
            return {
                "vital_signs": [],
                "medications": [],
                "symptoms": [],
                "procedures": [],
                "examinations": [],
                "timestamps": [],
                "raw_text": ""
            }

        text = transcript_text.strip()

        vitals = cls.extract_vitals(text)
        meds = cls.extract_medications(text)
        symptoms = cls.extract_symptoms(text)
        procedures = cls.extract_procedures(text)
        examinations = cls.extract_examinations(text)
        timestamps = cls.extract_timestamps(text)

        return {
            "vital_signs": vitals,
            "medications": meds,
            "symptoms": symptoms,
            "procedures": procedures,
            "examinations": examinations,
            "timestamps": timestamps,
            "raw_text": text
        }

    @classmethod
    def check_negation(cls, text, match_start, window=45):
        """
        Check if an entity is preceded by a negation trigger within a character window.
        Returns (is_negated: bool, trigger_phrase: str or None)
        """
        window_start = max(0, match_start - window)
        preceding_text = text[window_start:match_start].lower()

        # Check for sentence boundaries between trigger and entity
        last_period = preceding_text.rfind(".")
        if last_period != -1:
            preceding_text = preceding_text[last_period + 1:]

        for pattern in NEGATION_TRIGGERS:
            m = re.search(pattern, preceding_text, re.IGNORECASE)
            if m:
                return True, m.group(0).strip()
        return False, None

    @classmethod
    def extract_vitals(cls, text):
        """Extract physiological vital signs."""
        vitals = []

        # 1. Blood Pressure: e.g. "BP 120/80", "blood pressure 130 over 85"
        bp_patterns = [
            r"(?i)\b(?:bp|blood pressure|pressure)\s*(?:is|was|of|measured)?\s*([0-9]{2,3})\s*(?:/|over)\s*([0-9]{2,3})\b",
            r"\b([0-9]{2,3})\s*/\s*([0-9]{2,3})\s*(?:mm\s*hg)?\b"
        ]
        bp_spans = []
        for pat in bp_patterns:
            for m in re.finditer(pat, text):
                start, end = m.start(), m.end()
                # Deduplicate overlapping spans (e.g. prevents "130/85" duplicating "blood pressure 130/85")
                if any(max(start, s) < min(end, e) for s, e in bp_spans):
                    continue
                sys_val = int(m.group(1))
                dia_val = int(m.group(2))
                # Sanity filter: realistic blood pressure ranges
                if 40 <= sys_val <= 300 and 20 <= dia_val <= 200:
                    bp_spans.append((start, end))
                    vitals.append({
                        "id": f"vit-{uuid.uuid4().hex[:6]}",
                        "type": "Blood Pressure",
                        "name": "Blood Pressure",
                        "systolic": sys_val,
                        "diastolic": dia_val,
                        "value": f"{sys_val}/{dia_val}",
                        "unit": "mmHg",
                        "source_phrase": m.group(0),
                        "char_start": start,
                        "char_end": end,
                        "verification_state": "Extracted"
                    })

        # 2. Heart Rate / Pulse: e.g. "pulse 78", "heart rate 88 bpm", "pulse of 92"
        hr_pattern = r"(?i)\b(?:pulse|heart rate|hr)\s*(?:is|was|of|at)?\s*([0-9]{2,3})\s*(?:bpm|beats per min(?:ute)?)?\b"
        for m in re.finditer(hr_pattern, text):
            val = int(m.group(1))
            if 30 <= val <= 260:
                vitals.append({
                    "id": f"vit-{uuid.uuid4().hex[:6]}",
                    "type": "Heart Rate",
                    "name": "Heart Rate / Pulse",
                    "value": str(val),
                    "unit": "bpm",
                    "source_phrase": m.group(0),
                    "char_start": m.start(),
                    "char_end": m.end(),
                    "verification_state": "Extracted"
                })

        # 3. Respiratory Rate: e.g. "respiratory rate 16", "RR 18", "breathing 20"
        rr_pattern = r"(?i)\b(?:respiratory rate|rr|breathing rate|respirations)\s*(?:is|was|at|of)?\s*([0-9]{1,2})\s*(?:bpm|breaths per min(?:ute)?)?\b"
        for m in re.finditer(rr_pattern, text):
            val = int(m.group(1))
            if 4 <= val <= 60:
                vitals.append({
                    "id": f"vit-{uuid.uuid4().hex[:6]}",
                    "type": "Respiratory Rate",
                    "name": "Respiratory Rate",
                    "value": str(val),
                    "unit": "breaths/min",
                    "source_phrase": m.group(0),
                    "char_start": m.start(),
                    "char_end": m.end(),
                    "verification_state": "Extracted"
                })

        # 4. SpO2 / Oxygen Saturation: e.g. "SpO2 98%", "sats 95%"
        spo2_pattern = r"(?i)\b(?:spo2|sats|o2 sat(?:uration)?|oxygen sat(?:uration)?)\s*(?:is|was|at|of)?\s*([0-9]{2,3})\s*%"
        for m in re.finditer(spo2_pattern, text):
            val = int(m.group(1))
            vitals.append({
                "id": f"vit-{uuid.uuid4().hex[:6]}",
                "type": "Oxygen Saturation",
                "name": "SpO2",
                "value": str(val),
                "unit": "%",
                "source_phrase": m.group(0),
                "char_start": m.start(),
                "char_end": m.end(),
                "verification_state": "Extracted"
            })

        # 5. Temperature: e.g. "temperature 37.2", "temp 38.5 C", "temp is 98.6 F"
        temp_pattern = r"(?i)\b(?:temp|temperature)\s*(?:is|was|of|at)?\s*([0-9]{2}(?:\.[0-9])?)\s*(?:degrees\s*)?(c|celsius|f|fahrenheit)?\b"
        for m in re.finditer(temp_pattern, text):
            val = float(m.group(1))
            raw_unit = (m.group(2) or "C").upper()
            unit = "°F" if "F" in raw_unit else "°C"
            vitals.append({
                "id": f"vit-{uuid.uuid4().hex[:6]}",
                "type": "Temperature",
                "name": "Body Temperature",
                "value": str(val),
                "unit": unit,
                "source_phrase": m.group(0),
                "char_start": m.start(),
                "char_end": m.end(),
                "verification_state": "Extracted"
            })

        # 6. Glasgow Coma Scale (GCS): e.g. "GCS 15", "GCS of 14"
        gcs_pattern = r"(?i)\b(?:gcs|glasgow coma scale)\s*(?:is|was|of)?\s*([3-9]|1[0-5])\b"
        for m in re.finditer(gcs_pattern, text):
            val = int(m.group(1))
            vitals.append({
                "id": f"vit-{uuid.uuid4().hex[:6]}",
                "type": "GCS",
                "name": "Glasgow Coma Scale",
                "value": str(val),
                "unit": "/15",
                "source_phrase": m.group(0),
                "char_start": m.start(),
                "char_end": m.end(),
                "verification_state": "Extracted"
            })

        # 7. Blood Glucose: e.g. "glucose 5.4", "blood sugar 110 mg/dl"
        bgl_pattern = r"(?i)\b(?:blood glucose|glucose|blood sugar|bgl)\s*(?:is|was|of|at)?\s*([0-9]{1,3}(?:\.[0-9])?)\s*(mmol/l|mg/dl)?\b"
        for m in re.finditer(bgl_pattern, text):
            val = float(m.group(1))
            unit = m.group(2) or ("mmol/L" if val < 35.0 else "mg/dL")
            vitals.append({
                "id": f"vit-{uuid.uuid4().hex[:6]}",
                "type": "Blood Glucose",
                "name": "Blood Glucose Level",
                "value": str(val),
                "unit": unit,
                "source_phrase": m.group(0),
                "char_start": m.start(),
                "char_end": m.end(),
                "verification_state": "Extracted"
            })

        return vitals

    @classmethod
    def extract_medications(cls, text):
        """Extract medications, dosages, routes, and link with medicine catalogue."""
        medications = []
        all_known_meds = MedicineService.get_all_medicines()

        # Build search patterns for all canonical names and aliases
        candidates_to_search = []
        for med in all_known_meds:
            candidates_to_search.append((med["canonical_name"], med))
            for alias in med["aliases"]:
                candidates_to_search.append((alias, med))

        # Sort longer names first so "Morphine Sulfate" matches before "Morphine"
        candidates_to_search.sort(key=lambda x: len(x[0]), reverse=True)

        found_spans = []

        for name, med_meta in candidates_to_search:
            pattern = rf"(?i)\b{re.escape(name)}\b"
            for m in re.finditer(pattern, text):
                start, end = m.start(), m.end()

                # Avoid duplicate overlapping span
                if any(start >= s and end <= e for s, e in found_spans):
                    continue
                found_spans.append((start, end))

                # Check negation (e.g., "no paracetamol given", "did not administer morphine")
                is_neg, neg_trigger = cls.check_negation(text, start)

                # Search surrounding window (+- 60 chars) for dosage and route
                window_start = max(0, start - 30)
                window_end = min(len(text), end + 60)
                surrounding = text[window_start:window_end]

                # Dosage regex
                dose_pattern = r"(?i)\b([0-9]+(?:\.[0-9]+)?)\s*(mg|mcg|micrograms?|milligrams?|g|grams?|ml|milliliters?|puffs?|sprays?|tablets?|tabs?|l/min|units?)\b"
                dose_match = re.search(dose_pattern, surrounding)
                dosage = None
                dose_unit = None
                if dose_match:
                    dosage = dose_match.group(1)
                    raw_u = dose_match.group(2).lower()
                    # Normalize unit
                    if "mcg" in raw_u or "micro" in raw_u:
                        dose_unit = "mcg"
                    elif "mg" in raw_u or "milli" in raw_u:
                        dose_unit = "mg"
                    elif "g" in raw_u or "gram" in raw_u:
                        dose_unit = "g"
                    elif "ml" in raw_u:
                        dose_unit = "ml"
                    elif "puff" in raw_u:
                        dose_unit = "puffs"
                    elif "spray" in raw_u:
                        dose_unit = "sprays"
                    elif "tab" in raw_u:
                        dose_unit = "tablets"
                    else:
                        dose_unit = raw_u

                # Route regex
                route_pattern = r"(?i)\b(iv|intravenous|im|intramuscular|oral|orally|po|sublingual|sl|in|intranasal|nebulized|inhaled|io|intraosseous|topical|pr|per\s+rectum)\b"
                route_match = re.search(route_pattern, surrounding)
                route = None
                if route_match:
                    raw_r = route_match.group(1).upper()
                    if raw_r in ["IV", "INTRAVENOUS"]:
                        route = "IV"
                    elif raw_r in ["IM", "INTRAMUSCULAR"]:
                        route = "IM"
                    elif raw_r in ["ORAL", "ORALLY", "PO"]:
                        route = "Oral"
                    elif raw_r in ["SUBLINGUAL", "SL"]:
                        route = "Sublingual"
                    elif raw_r in ["IN", "INTRANASAL"]:
                        route = "Intranasal"
                    elif raw_r in ["NEBULIZED", "INHALED"]:
                        route = "Inhaled/Nebulized"
                    elif raw_r in ["IO", "INTRAOSSEOUS"]:
                        route = "IO"
                    else:
                        route = raw_r

                # Match details from catalogue
                match_result = MedicineService.match_medicine(name)

                # Verification state
                state = "Extracted"
                if match_result["status"] == "AMBIGUOUS":
                    state = "Uncertain"
                if is_neg:
                    state = "Extracted"  # Noted as withheld/not given

                medications.append({
                    "id": f"med-{uuid.uuid4().hex[:6]}",
                    "raw_mention": name,
                    "canonical_name": med_meta["canonical_name"],
                    "category": med_meta["category"],
                    "dosage": dosage,
                    "unit": dose_unit,
                    "route": route,
                    "is_negated": is_neg,
                    "negation_trigger": neg_trigger,
                    "pediatric_warning": bool(med_meta["pediatric_warning"]),
                    "contraindications_notes": med_meta["contraindications_notes"],
                    "provenance": med_meta["provenance"],
                    "match_status": match_result["status"],
                    "candidates": match_result["candidates"],
                    "source_phrase": text[window_start:window_end].strip(),
                    "char_start": start,
                    "char_end": end,
                    "verification_state": state
                })

        return medications

    @classmethod
    def get_clean_source_phrase(cls, text, start, end, neg_trigger=None):
        """Extract a clean clause or sentence span without cutting mid-word."""
        if neg_trigger:
            return f"{neg_trigger} {text[start:end]}".strip()
        clause_start = max(text.rfind(".", 0, start), text.rfind(",", 0, start), text.rfind(";", 0, start))
        clause_start = 0 if clause_start == -1 else clause_start + 1
        clause_end = len(text)
        for p in [".", ",", ";"]:
            idx = text.find(p, end)
            if idx != -1 and idx < clause_end:
                clause_end = idx
        phrase = text[clause_start:clause_end].strip()
        return phrase if phrase else text[start:end]

    @classmethod
    def extract_symptoms(cls, text):
        """Extract clinical symptoms and patient complaints with negation status."""
        symptoms = []
        found_spans = []

        for sym in sorted(SYMPTOMS_LIST, key=len, reverse=True):
            pattern = rf"(?i)\b{re.escape(sym)}\b"
            for m in re.finditer(pattern, text):
                start, end = m.start(), m.end()
                if any(start >= s and end <= e for s, e in found_spans):
                    continue
                found_spans.append((start, end))

                is_neg, neg_trigger = cls.check_negation(text, start)

                symptoms.append({
                    "id": f"sym-{uuid.uuid4().hex[:6]}",
                    "symptom": sym.title(),
                    "is_negated": is_neg,
                    "negation_trigger": neg_trigger,
                    "source_phrase": cls.get_clean_source_phrase(text, start, end, neg_trigger),
                    "char_start": start,
                    "char_end": end,
                    "verification_state": "Extracted"
                })

        return symptoms

    @classmethod
    def extract_procedures(cls, text):
        """Extract first responder interventions and procedures."""
        procedures = []
        found_spans = []

        for proc in sorted(PROCEDURES_LIST, key=len, reverse=True):
            pattern = rf"(?i)\b{re.escape(proc)}\b"
            for m in re.finditer(pattern, text):
                start, end = m.start(), m.end()
                if any(start >= s and end <= e for s, e in found_spans):
                    continue
                found_spans.append((start, end))

                is_neg, neg_trigger = cls.check_negation(text, start)

                procedures.append({
                    "id": f"proc-{uuid.uuid4().hex[:6]}",
                    "procedure": proc.title(),
                    "is_negated": is_neg,
                    "negation_trigger": neg_trigger,
                    "source_phrase": cls.get_clean_source_phrase(text, start, end, neg_trigger),
                    "char_start": start,
                    "char_end": end,
                    "verification_state": "Extracted"
                })

        return procedures

    @classmethod
    def extract_examinations(cls, text):
        """
        Extract physical examination and clinical observation findings.
        Maps observations (e.g. cardiac rhythm, breath sounds, pupils, abdomen)
        into structured examination fields while marking them for explicit clinician verification.
        Never infers that a measurement is clinically normal merely because the transcript says so.
        """
        examinations = []
        exam_patterns = [
            (
                "Cardiovascular",
                "Heart Rhythm / Cardiac Examination",
                r"(?i)\b(?:heartbeat|heart rate|heart sounds|cardiac rhythm|pulse rhythm|heart rhythm)\s*(?:is|was|noted as|documented as|appears|found to be)?\s*(normal|regular|irregular|abnormal|rapid|slow|arrhythmic|weak|bounding|thready|palpable|absent)\b"
            ),
            (
                "Cardiovascular",
                "Cardiac Rhythm",
                r"(?i)\b(normal sinus rhythm|regular rate and rhythm|sinus tachycardia|sinus bradycardia|atrial fibrillation|asystole)\b"
            ),
            (
                "Respiratory",
                "Breath / Lung Sounds",
                r"(?i)\b(?:breath sounds|lung sounds|auscultation|lungs)\s*(?:are|were|noted as|documented as)?\s*(clear|clear bilaterally|wheezing|wheezes|crackles|rales|rhonchi|diminished|absent|stridor)\b"
            ),
            (
                "Neurological",
                "Pupillary Assessment",
                r"(?i)\b(?:pupils|pupillary response)\s*(?:are|were|noted as)?\s*(equal round and reactive|perrl|sluggish|fixed and dilated|pinpoint|constricted|dilated|reactive)\b"
            ),
            (
                "Abdomen",
                "Abdominal Examination",
                r"(?i)\b(?:abdomen|abdominal examination|belly)\s*(?:is|was|noted as)?\s*(soft non-tender|soft and non-tender|rigid|distended|tender|guarding|rebound)\b"
            ),
            (
                "Integumentary",
                "Skin Assessment",
                r"(?i)\b(?:skin)\s*(?:is|was|noted as)?\s*(warm and dry|pale and clammy|cool and diaphoretic|cyanotic|flushed|jaundiced|turgor normal)\b"
            )
        ]

        found_spans = []
        for system, exam_name, pat in exam_patterns:
            for m in re.finditer(pat, text):
                start, end = m.start(), m.end()
                if any(max(start, s) < min(end, e) for s, e in found_spans):
                    continue
                found_spans.append((start, end))

                finding_text = m.group(0).strip()
                val_text = m.group(1).strip() if m.groups() else finding_text

                examinations.append({
                    "id": f"exam-{uuid.uuid4().hex[:6]}",
                    "system": system,
                    "exam": exam_name,
                    "finding": finding_text,
                    "value": val_text,
                    "documented_value": val_text,
                    "source_phrase": finding_text,
                    "char_start": start,
                    "char_end": end,
                    "verification_state": "Extracted"  # Flagged for clinician verification; not assumed medically approved
                })

        return examinations

    @classmethod
    def extract_timestamps(cls, text):
        """Extract time indicators from speech (clock times and relative durations)."""
        timestamps = []

        # Clock times: e.g. "at 14:30", "14:15 hrs", "2:30 pm"
        clock_pattern = r"(?i)\b(?:at\s+)?([01]?[0-9]|2[0-3]):([0-5][0-9])\s*(?:am|pm|hrs|hours)?\b"
        for m in re.finditer(clock_pattern, text):
            timestamps.append({
                "id": f"time-{uuid.uuid4().hex[:6]}",
                "type": "Clock Time",
                "expression": m.group(0).strip(),
                "hours": m.group(1),
                "minutes": m.group(2),
                "source_phrase": m.group(0),
                "char_start": m.start(),
                "char_end": m.end(),
                "verification_state": "Extracted"
            })

        # Relative elapsed time: e.g. "10 minutes ago", "onset 30 mins ago"
        rel_pattern = r"(?i)\b([0-9]{1,3})\s*(?:minutes?|mins|hours?|hrs)\s*ago\b"
        for m in re.finditer(rel_pattern, text):
            timestamps.append({
                "id": f"time-{uuid.uuid4().hex[:6]}",
                "type": "Relative Elapsed Time",
                "expression": m.group(0).strip(),
                "value": m.group(1),
                "source_phrase": m.group(0),
                "char_start": m.start(),
                "char_end": m.end(),
                "verification_state": "Extracted"
            })

        return timestamps
