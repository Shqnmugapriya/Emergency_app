"""
Uncertainty Ledger & Change Impact Radar Service.
Maintains explicit categorization of clinical uncertainties:
- 'Not Mentioned'
- 'Unknown'
- 'Unclear'
- 'Conflicting'

Change Impact Radar evaluates the ripple effects of clinician edits on dependent vitals,
warnings, timelines, and report sections, marking affected areas for re-verification.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import uuid
from datetime import datetime, timezone
from backend.services.validation_service import ValidationService

class UncertaintyType:
    NOT_MENTIONED = "Not Mentioned"
    UNKNOWN = "Unknown"
    UNCLEAR = "Unclear"
    CONFLICTING = "Conflicting"

class UncertaintyService:

    @classmethod
    def compile_uncertainty_ledger(cls, clinical_data, warnings):
        """
        Synthesize all clinical ambiguities, missing values, and contradictions
        into a traceable Uncertainty Ledger.
        """
        ledger = []

        # 1. Evaluate Vitals
        vitals = clinical_data.get("vital_signs", [])
        recorded_vital_types = {v.get("type") for v in vitals}
        core_vital_types = [
            ("Blood Pressure", "Core hemodynamic parameter"),
            ("Heart Rate", "Core hemodynamic parameter"),
            ("Respiratory Rate", "Ventilation status"),
            ("Oxygen Saturation", "Oxygenation status")
        ]

        for vt, desc in core_vital_types:
            if vt not in recorded_vital_types:
                ledger.append({
                    "id": f"unc-{uuid.uuid4().hex[:6]}",
                    "category": "Vital Sign",
                    "field": vt,
                    "uncertainty_type": UncertaintyType.NOT_MENTIONED,
                    "description": f"{vt} was not mentioned in the field narrative.",
                    "clinical_impact": f"{desc} unrecorded in pre-hospital documentation.",
                    "requires_action": False
                })

        # 2. Evaluate Medications
        for m in clinical_data.get("medications", []):
            cname = m.get("canonical_name", m.get("raw_mention", "Medication"))
            # Dosage check
            if not m.get("dosage"):
                ledger.append({
                    "id": f"unc-{uuid.uuid4().hex[:6]}",
                    "category": "Medication Dosage",
                    "field": f"{cname} Dosage",
                    "uncertainty_type": UncertaintyType.UNKNOWN,
                    "description": f"Medication '{cname}' was mentioned without numeric dose.",
                    "clinical_impact": "Dose quantification absent. Overdose/underdose cannot be assessed.",
                    "requires_action": True
                })

            # Route check
            if not m.get("route"):
                ledger.append({
                    "id": f"unc-{uuid.uuid4().hex[:6]}",
                    "category": "Medication Route",
                    "field": f"{cname} Route",
                    "uncertainty_type": UncertaintyType.UNKNOWN,
                    "description": f"Administration route for '{cname}' was not documented.",
                    "clinical_impact": "Pharmacokinetics (onset speed) unverified.",
                    "requires_action": True
                })

            # Ambiguity check
            if m.get("match_status") == "AMBIGUOUS":
                ledger.append({
                    "id": f"unc-{uuid.uuid4().hex[:6]}",
                    "category": "Medicine Identity",
                    "field": cname,
                    "uncertainty_type": UncertaintyType.UNCLEAR,
                    "description": f"Auditory mention '{m.get('raw_mention')}' is ambiguous across multiple formulary medicines.",
                    "clinical_impact": "Medication identity unverified. Risk of adverse drug event.",
                    "requires_action": True
                })

        # 3. Evaluate Warnings for Contradictions
        for w in warnings:
            if "Contradiction" in w.get("category", "") or "Physiological" in w.get("category", ""):
                ledger.append({
                    "id": f"unc-{uuid.uuid4().hex[:6]}",
                    "category": "Physiological Contradiction",
                    "field": w.get("field", "Vitals"),
                    "uncertainty_type": UncertaintyType.CONFLICTING,
                    "description": w.get("message", "Physiological contradiction"),
                    "clinical_impact": "Severe data inconsistency blocking official sign-off.",
                    "requires_action": True
                })

        # 4. Timeline Timing Check
        timestamps = clinical_data.get("timestamps", [])
        if not timestamps:
            ledger.append({
                "id": f"unc-{uuid.uuid4().hex[:6]}",
                "category": "Temporal Precision",
                "field": "Encounter Milestones",
                "uncertainty_type": UncertaintyType.UNKNOWN,
                "description": "No explicit clinical clock times or relative elapsed intervals were stated.",
                "clinical_impact": "Event chronology relies solely on audio capture timestamp.",
                "requires_action": False
            })

        counts = {
            "not_mentioned": sum(1 for item in ledger if item.get("uncertainty_type") == UncertaintyType.NOT_MENTIONED),
            "unknown": sum(1 for item in ledger if item.get("uncertainty_type") == UncertaintyType.UNKNOWN),
            "unclear": sum(1 for item in ledger if item.get("uncertainty_type") == UncertaintyType.UNCLEAR),
            "conflicting": sum(1 for item in ledger if item.get("uncertainty_type") == UncertaintyType.CONFLICTING)
        }
        return {
            "items": ledger,
            "counts": counts,
            "total_count": len(ledger)
        }

    @classmethod
    def analyze_change_impact(cls, old_record, new_clinical_data, new_transcript):
        """
        Change Impact Radar:
        Compares old record state with new updates and detects downstream dependencies
        that require clinician re-verification.
        """
        old_clinical = old_record.get("clinical_data", {})
        old_vitals = {v.get("type"): v for v in old_clinical.get("vital_signs", [])}
        new_vitals = {v.get("type"): v for v in new_clinical_data.get("vital_signs", [])}

        old_meds = {m.get("canonical_name", m.get("raw_mention")): m for m in old_clinical.get("medications", [])}
        new_meds = {m.get("canonical_name", m.get("raw_mention")): m for m in new_clinical_data.get("medications", [])}

        impact_items = []
        affected_sections = set()

        # Check Vitals differences
        for v_type, new_v in new_vitals.items():
            if v_type not in old_vitals:
                impact_items.append({
                    "type": "VITAL_ADDED",
                    "field": v_type,
                    "detail": f"New vital sign '{v_type}' added ({new_v.get('value')} {new_v.get('unit', '')}).",
                    "reverification_needed": True
                })
                affected_sections.add("Vitals Table")
            elif old_vitals[v_type].get("value") != new_v.get("value"):
                impact_items.append({
                    "type": "VITAL_MODIFIED",
                    "field": v_type,
                    "detail": f"Vital sign '{v_type}' value changed from '{old_vitals[v_type].get('value')}' to '{new_v.get('value')}'.",
                    "reverification_needed": True
                })
                affected_sections.add("Vitals Table")
                affected_sections.add("Safety Warnings")

        for v_type in old_vitals:
            if v_type not in new_vitals:
                impact_items.append({
                    "type": "VITAL_REMOVED",
                    "field": v_type,
                    "detail": f"Vital sign '{v_type}' removed from clinical record.",
                    "reverification_needed": True
                })
                affected_sections.add("Vitals Table")

        # Check Medication differences
        for m_name, new_m in new_meds.items():
            if m_name not in old_meds:
                impact_items.append({
                    "type": "MEDICATION_ADDED",
                    "field": m_name,
                    "detail": f"New medication '{m_name}' documented ({new_m.get('dosage')} {new_m.get('unit', '')} via {new_m.get('route', 'N/A')}).",
                    "reverification_needed": True
                })
                affected_sections.add("Medications Table")
                affected_sections.add("Safety Warnings")
            elif (old_meds[m_name].get("dosage") != new_m.get("dosage") or
                  old_meds[m_name].get("route") != new_m.get("route")):
                impact_items.append({
                    "type": "MEDICATION_DOSAGE_CHANGED",
                    "field": m_name,
                    "detail": f"Medication '{m_name}' dose/route changed from '{old_meds[m_name].get('dosage')} {old_meds[m_name].get('route')}' to '{new_m.get('dosage')} {new_m.get('route')}'.",
                    "reverification_needed": True
                })
                affected_sections.add("Medications Table")
                affected_sections.add("Safety Warnings")

        # Recalculate warnings on updated dataset
        new_warnings = ValidationService.validate_clinical_record(new_clinical_data)

        return {
            "has_changes": len(impact_items) > 0,
            "impact_count": len(impact_items),
            "affected_sections": list(affected_sections),
            "impact_items": impact_items,
            "changes_detected": [item["detail"] for item in impact_items],
            "summary": f"{len(impact_items)} field(s) modified affecting {len(affected_sections)} section(s)." if impact_items else "No critical changes detected.",
            "recalculated_warnings_count": len(new_warnings),
            "recalculated_warnings": new_warnings,
            "evaluated_at": datetime.now(timezone.utc).isoformat()
        }
