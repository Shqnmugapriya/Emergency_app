"""
Patient Continuity Engine Service.
Manages persistent patient identities, multi-factor search, ambiguity safeguards,
and encounter link provenance without modifying existing record workflows.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from datetime import datetime, timezone
from backend.database.db import (
    get_patient, list_patients, search_patients_multifield,
    create_patient, link_encounter, get_patient_encounters, log_audit_event
)

class PatientService:

    @classmethod
    def get_patient_by_id(cls, patient_id):
        """Retrieve patient profile with verified details."""
        return get_patient(patient_id)

    @classmethod
    def search_patients(cls, query_params):
        """
        Multi-factor patient identification.
        Rule: NEVER identify a patient by name alone.
        Returns: {
            "patients": list,
            "is_ambiguous": bool,
            "requires_confirmation": bool,
            "message": str
        }
        """
        name = query_params.get("name")
        dob = query_params.get("dob")
        phone = query_params.get("phone")
        patient_id_display = query_params.get("patient_id_display") or query_params.get("patient_id")
        search_term = query_params.get("q")

        if patient_id_display:
            matches, _ = search_patients_multifield(patient_id_display=patient_id_display)
            return {
                "patients": matches,
                "is_ambiguous": False,
                "requires_confirmation": False,
                "message": f"Exact ID match found ({len(matches)} patient)." if matches else "No patient matching ID."
            }

        if name and dob:
            matches, is_ambig = search_patients_multifield(name=name, dob=dob)
            return {
                "patients": matches,
                "is_ambiguous": is_ambig or len(matches) > 1,
                "requires_confirmation": len(matches) > 1,
                "message": "Dual-factor match (Name + DOB)." if len(matches) == 1 else "Multiple or zero matches."
            }

        # If name alone is queried:
        if name and not dob and not phone:
            matches, _ = search_patients_multifield(name=name)
            if len(matches) > 1:
                return {
                    "patients": matches,
                    "is_ambiguous": True,
                    "requires_confirmation": True,
                    "message": f"Ambiguous name match: {len(matches)} patients share the name '{name}'. Explicit date of birth or ID verification is required."
                }
            elif len(matches) == 1:
                return {
                    "patients": matches,
                    "is_ambiguous": False,
                    "requires_confirmation": True,  # Name alone requires confirmation
                    "message": f"Single name candidate found. Confirmation of date of birth required before linking."
                }

        # General text query
        if search_term:
            matches = list_patients(search_term=search_term)
            return {
                "patients": matches,
                "is_ambiguous": len(matches) > 1,
                "requires_confirmation": True,
                "message": f"Found {len(matches)} matching candidates."
            }

        all_pts = list_patients(limit=50)
        return {
            "patients": all_pts,
            "is_ambiguous": False,
            "requires_confirmation": False,
            "message": f"Listing {len(all_pts)} registered patients."
        }

    @classmethod
    def register_new_patient(cls, patient_data):
        """Create new persistent patient profile."""
        if not patient_data.get("full_name") or not patient_data.get("dob"):
            raise ValueError("Full name and Date of Birth (DOB) are mandatory to register a patient.")

        # Check if identical patient already exists
        existing, _ = search_patients_multifield(name=patient_data["full_name"], dob=patient_data["dob"])
        if existing:
            raise ValueError(f"Patient with name '{patient_data['full_name']}' and DOB '{patient_data['dob']}' is already registered (ID: {existing[0]['patient_id_display']}).")

        created = create_patient(patient_data)
        return created

    @classmethod
    def attach_encounter_to_patient(cls, patient_id, record_id, encounter_type="NEW_ENCOUNTER", actor="Paramedic"):
        """
        Link an encounter record to a patient.
        Distinguishes:
        - NEW_ENCOUNTER: brand new emergency run
        - OBSERVATION: supplemental field observation added to ongoing encounter
        - CORRECTION: unapproved draft correction
        - AMENDMENT: post-approval clinical amendment
        """
        patient = get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient with ID '{patient_id}' not found.")

        valid_types = ["NEW_ENCOUNTER", "OBSERVATION", "CORRECTION", "AMENDMENT"]
        if encounter_type not in valid_types:
            raise ValueError(f"Invalid encounter type '{encounter_type}'. Supported: {valid_types}")

        link_id = link_encounter(patient["id"], record_id, encounter_type=encounter_type)

        log_audit_event(
            record_id=record_id,
            action="LINK_PATIENT",
            actor=actor,
            details={
                "patient_id": patient["id"],
                "patient_display_id": patient["patient_id_display"],
                "patient_name": patient["full_name"],
                "encounter_type": encounter_type,
                "link_id": link_id
            }
        )

        return {
            "link_id": link_id,
            "patient": patient,
            "encounter_type": encounter_type
        }

    @classmethod
    def get_patient_history(cls, patient_id):
        """Get full longitudinal encounter timeline and medical history for a patient."""
        patient = get_patient(patient_id)
        if not patient:
            return None

        encounters = get_patient_encounters(patient["id"])
        return {
            "patient": patient,
            "encounter_count": len(encounters),
            "encounters": encounters
        }
