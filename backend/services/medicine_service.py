"""
Medicine Service: Verified local medicine catalogue search and ambiguity verification.
Provenance: WHO Model List 2023 / EMS Formulary v1.2.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import json
from rapidfuzz import process, fuzz
from backend.database.db import get_db_connection

class MedicineService:
    @classmethod
    def get_all_medicines(cls):
        """Fetch all verified medicines from SQLite."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM medicine_catalogue ORDER BY canonical_name ASC;")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["aliases"] = json.loads(item["aliases"])
                item["standard_routes"] = json.loads(item["standard_routes"])
                item["standard_units"] = json.loads(item["standard_units"])
                item["typical_doses"] = json.loads(item["typical_doses"])
                results.append(item)
            return results
        finally:
            conn.close()

    @classmethod
    def match_medicine(cls, query_text):
        """
        Match a query text against verified medicines.
        Returns:
            {
                "status": "EXACT" | "ALIAS" | "AMBIGUOUS" | "UNRESOLVED",
                "matched_canonical": str or None,
                "confidence_score": float (0-100),
                "candidates": list of { "canonical_name", "score", "provenance" },
                "pediatric_warning": bool,
                "requires_confirmation": bool,
                "provenance": str
            }
        """
        if not query_text or not query_text.strip():
            return {
                "status": "UNRESOLVED",
                "matched_canonical": None,
                "confidence_score": 0.0,
                "candidates": [],
                "pediatric_warning": False,
                "requires_confirmation": True,
                "provenance": "None"
            }

        q = query_text.strip().lower()
        medicines = cls.get_all_medicines()

        # Step 1: Check Exact Canonical Match
        for med in medicines:
            if med["canonical_name"].lower() == q:
                return {
                    "status": "EXACT",
                    "matched_canonical": med["canonical_name"],
                    "confidence_score": 100.0,
                    "candidates": [{
                        "canonical_name": med["canonical_name"],
                        "score": 100.0,
                        "category": med["category"],
                        "provenance": med["provenance"]
                    }],
                    "pediatric_warning": bool(med["pediatric_warning"]),
                    "requires_confirmation": False,
                    "provenance": med["provenance"]
                }

        # Step 2: Check Exact Verified Alias Match
        for med in medicines:
            for alias in med["aliases"]:
                if alias.lower() == q:
                    return {
                        "status": "ALIAS",
                        "matched_canonical": med["canonical_name"],
                        "alias_matched": alias,
                        "confidence_score": 98.0,
                        "candidates": [{
                            "canonical_name": med["canonical_name"],
                            "matched_alias": alias,
                            "score": 98.0,
                            "category": med["category"],
                            "provenance": med["provenance"]
                        }],
                        "pediatric_warning": bool(med["pediatric_warning"]),
                        "requires_confirmation": False,
                        "provenance": med["provenance"]
                    }

        # Step 3: RapidFuzz candidate ranking (NEVER silently commits fuzzy match!)
        candidate_pool = {}
        for med in medicines:
            # Score canonical
            canonical_ratio = fuzz.ratio(q, med["canonical_name"].lower())
            token_ratio = fuzz.token_sort_ratio(q, med["canonical_name"].lower())
            best_med_score = max(canonical_ratio, token_ratio)

            # Score aliases
            for alias in med["aliases"]:
                ar = fuzz.ratio(q, alias.lower())
                tr = fuzz.token_sort_ratio(q, alias.lower())
                best_med_score = max(best_med_score, ar, tr)

            if best_med_score >= 60.0:
                candidate_pool[med["canonical_name"]] = {
                    "canonical_name": med["canonical_name"],
                    "score": round(best_med_score, 1),
                    "category": med["category"],
                    "pediatric_warning": bool(med["pediatric_warning"]),
                    "provenance": med["provenance"]
                }

        ranked_candidates = sorted(candidate_pool.values(), key=lambda x: x["score"], reverse=True)

        if not ranked_candidates:
            return {
                "status": "UNRESOLVED",
                "matched_canonical": None,
                "confidence_score": 0.0,
                "candidates": [],
                "pediatric_warning": False,
                "requires_confirmation": True,
                "provenance": "Local Catalogue v1.2.0"
            }

        top_candidate = ranked_candidates[0]
        # Ambiguity check: if multiple candidates are close in score
        if len(ranked_candidates) > 1:
            diff = top_candidate["score"] - ranked_candidates[1]["score"]
            if diff < 12.0 or top_candidate["score"] < 90.0:
                # Ambiguous! RapidFuzz must NOT determine identity by itself
                return {
                    "status": "AMBIGUOUS",
                    "matched_canonical": top_candidate["canonical_name"],
                    "confidence_score": top_candidate["score"],
                    "candidates": ranked_candidates[:4],
                    "pediatric_warning": top_candidate["pediatric_warning"],
                    "requires_confirmation": True,
                    "ambiguity_reason": f"Multiple plausible matches (e.g., {top_candidate['canonical_name']} vs {ranked_candidates[1]['canonical_name']})",
                    "provenance": top_candidate["provenance"]
                }

        # Single high-scoring candidate but not exact: requires confirmation
        return {
            "status": "FUZZY_SUGGESTION",
            "matched_canonical": top_candidate["canonical_name"],
            "confidence_score": top_candidate["score"],
            "candidates": ranked_candidates[:3],
            "pediatric_warning": top_candidate["pediatric_warning"],
            "requires_confirmation": True,
            "provenance": top_candidate["provenance"]
        }
