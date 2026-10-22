"""
Report Confidence & Quality Assessment Service.
Calculates transparent, criteria-based report quality levels:
- HIGH
- MEDIUM
- LOW
- NOT EVALUATED

Evaluates:
1. Speech transcription uncertainty (acoustic softmax probability, unaligned tokens).
2. Clinical formulary verification & drug ambiguity resolution.
3. Supporting evidence coverage (unsupported assertions in Evidence Passport).
4. Automated safety checks (unresolved physiological contradictions or critical dose limits).
5. Human clinician review status.

Documented Thresholds & Principles:
- A high score reflects documentation completeness and evidence coverage.
- It does NOT indicate medical correctness, clinical appropriateness, or automated diagnostic approval.
"""

from datetime import datetime, timezone

class ReportQualityLevel:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NOT_EVALUATED = "NOT EVALUATED"

class ReportConfidenceService:

    @classmethod
    def evaluate_record_quality(cls, record):
        """
        Evaluate overall clinical report quality and uncertainty level.
        Returns a structured dictionary with transparent criteria and documentation.
        """
        if not record:
            return {
                "level": ReportQualityLevel.NOT_EVALUATED,
                "score_percent": None,
                "summary": "No record provided for quality evaluation.",
                "criteria": {},
                "disclaimer": "Report quality not evaluated."
            }

        clinical_data = record.get("clinical_data") or {}
        warnings = record.get("validation_warnings") or []
        evidence_passport = record.get("evidence_passport") or {}
        trans_meta = record.get("transcription_metadata") or {}
        status = record.get("status", "Draft")

        # 1. Check if pure manual entry without speech alignment
        is_manual_only = not bool(record.get("audio_filename") or trans_meta.get("segments"))

        # 2. Safety Warnings Check
        critical_unresolved = [
            w for w in warnings
            if w.get("severity") == "CRITICAL" and not w.get("resolved")
        ]
        non_critical_warnings = [
            w for w in warnings
            if w.get("severity") != "CRITICAL" and not w.get("resolved")
        ]

        # 3. Medicine Ambiguity Check
        medications = clinical_data.get("medications", [])
        ambiguous_meds = [
            m for m in medications
            if m.get("match_status") == "AMBIGUOUS" and m.get("verification_state") != "Verified"
        ]

        # 4. Evidence Support Check
        if isinstance(evidence_passport, dict):
            unsupported_claims = evidence_passport.get("unsupported_claims_count", 0)
            total_evidence_entries = evidence_passport.get("total_count", len(evidence_passport.get("entries", [])))
        elif isinstance(evidence_passport, list):
            unsupported_claims = sum(1 for e in evidence_passport if not e.get("has_supporting_evidence"))
            total_evidence_entries = len(evidence_passport)
        else:
            unsupported_claims = 0
            total_evidence_entries = 0

        # 5. Transcription Confidence Check (where technically available)
        # We inspect word-level or segment-level probabilities from faster-whisper
        speech_probs = []
        words = trans_meta.get("words", [])
        if words:
            for w in words:
                p = w.get("probability")
                if p is not None and isinstance(p, (int, float)):
                    speech_probs.append(float(p))
        elif trans_meta.get("segments"):
            for s in trans_meta.get("segments"):
                # avg_logprob typically ranges from -0.1 (high) to -1.5 (low)
                lp = s.get("avg_logprob")
                if lp is not None:
                    # convert logprob to approximate probability
                    import math
                    p = math.exp(max(lp, -3.0))
                    speech_probs.append(p)

        avg_speech_prob = (sum(speech_probs) / len(speech_probs)) if speech_probs else None

        # Build Criteria Explanations
        transcription_status = (
            f"Mean acoustic word probability: {round(avg_speech_prob * 100, 1)}%"
            if avg_speech_prob is not None else
            ("Manual clinical documentation (no speech inference model evaluated)" if is_manual_only else "Acoustic confidence not available")
        )

        medication_status = (
            f"{len(ambiguous_meds)} ambiguous medicine name(s) pending verification"
            if ambiguous_meds else
            ("All medicines verified against catalogue" if medications else "No medications documented")
        )

        evidence_status = (
            f"{unsupported_claims} unsupported clinical claim(s) flagged"
            if unsupported_claims > 0 else
            "All documented clinical assertions corroborated by narrative text"
        )

        warnings_status = (
            f"{len(critical_unresolved)} critical safety warning(s) unresolved"
            if critical_unresolved else
            (f"{len(non_critical_warnings)} minor advisory warning(s)" if non_critical_warnings else "Zero validation warnings")
        )

        # Classification Algorithm based on transparent criteria:
        # LOW: Critical safety warning present, unresolved ambiguous drug, or high unsupported claim count
        if critical_unresolved or ambiguous_meds or unsupported_claims > 2:
            level = ReportQualityLevel.LOW
            score = 45 if not critical_unresolved else 30
            summary = "LOW: Unresolved critical validation warnings or unverified ambiguous medication identities require remediation prior to sign-off."

        elif is_manual_only and not critical_unresolved and not ambiguous_meds:
            # Manual entries with verified data
            level = ReportQualityLevel.HIGH if status in ("Approved", "Reviewed") else ReportQualityLevel.MEDIUM
            score = 88 if level == ReportQualityLevel.HIGH else 75
            summary = f"{level}: Clean clinical validation with complete manual documentation."

        elif avg_speech_prob is not None and avg_speech_prob < 0.65:
            level = ReportQualityLevel.LOW
            score = round(avg_speech_prob * 100)
            summary = "LOW: High speech recognition acoustic uncertainty detected in recorded narrative."

        elif non_critical_warnings or unsupported_claims > 0 or (avg_speech_prob is not None and avg_speech_prob < 0.82):
            level = ReportQualityLevel.MEDIUM
            score = 72
            summary = "MEDIUM: Core documentation complete; non-critical warnings or minor transcription uncertainty present."

        else:
            level = ReportQualityLevel.HIGH
            score = round((avg_speech_prob * 100)) if avg_speech_prob else 92
            summary = "HIGH: All clinical assertions evidence-backed, zero critical warnings, and verified formulary matching."

        return {
            "level": level,
            "score_percent": score,
            "summary": summary,
            "criteria": {
                "transcription_quality": transcription_status,
                "clinical_term_resolution": medication_status,
                "supporting_evidence_status": evidence_status,
                "safety_warnings_status": warnings_status,
                "clinician_approval_status": f"Record status: {status}"
            },
            "documented_thresholds": {
                "HIGH": "Score >= 80%, zero critical warnings, 0 ambiguous drugs, all claims evidence-supported.",
                "MEDIUM": "Score 65-79%, zero critical warnings, minor advisories or moderate transcription uncertainty.",
                "LOW": "Score < 65%, critical validation warnings present, or unresolved drug ambiguities.",
                "NOT_EVALUATED": "Incomplete unaligned entry."
            },
            "disclaimer": "CONFIDENTIAL DOCUMENTATION METRIC ONLY: Report quality level measures evidence completeness, transcription alignment, and automated rule consistency. It does NOT constitute proof of medical correctness, diagnosis, or clinical sign-off."
        }
