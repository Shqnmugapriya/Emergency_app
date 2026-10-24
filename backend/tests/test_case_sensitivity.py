"""
Regression tests for case-sensitive medication matching and clinical route phrase matching.
Verifies:
- All case variations of medications (canonical and aliases) match correctly
- Punctuation-tolerant exact matching
- Standard clinical route phrase matching (e.g. 'by mouth', 'PO', 'chewed', 'SL', 'via nebulizer')
- Route equivalence mapping against formulary standard routes
- Preservation of raw_mention casing with normalized canonical output
"""

import pytest
from backend.app import create_app
from backend.services.medicine_service import MedicineService, check_route_match, ROUTE_EQUIVALENCE
from backend.services.clinical_extractor import ClinicalExtractor

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    with app.test_client() as test_client:
        yield test_client

# ==========================================================
# 1. Medication Case Variations & Punctuation
# ==========================================================
def test_medication_case_variations():
    test_cases = [
        # Query, Expected Canonical, Expected Status
        ("paracetamol", "Paracetamol", "EXACT"),
        ("PARACETAMOL", "Paracetamol", "EXACT"),
        ("Paracetamol", "Paracetamol", "EXACT"),
        ("PaRaCeTaMoL", "Paracetamol", "EXACT"),
        ("paracetamol.", "Paracetamol", "EXACT"),
        ("aspirin", "Aspirin", "EXACT"),
        ("ASPIRIN", "Aspirin", "EXACT"),
        ("Aspirin", "Aspirin", "EXACT"),
        ("morphine", "Morphine", "EXACT"),
        ("MORPHINE", "Morphine", "EXACT"),
        ("fentanyl", "Fentanyl", "EXACT"),
        ("FENTANYL", "Fentanyl", "EXACT"),
        ("salbutamol", "Salbutamol", "EXACT"),
        ("SALBUTAMOL", "Salbutamol", "EXACT"),
        ("nitroglycerin", "Nitroglycerin", "EXACT"),
        ("NITROGLYCERIN", "Nitroglycerin", "EXACT"),
        ("naloxone", "Naloxone", "EXACT"),
        ("NALOXONE", "Naloxone", "EXACT"),
        ("epinephrine", "Epinephrine", "EXACT"),
        ("EPINEPHRINE", "Epinephrine", "EXACT"),
        ("midazolam", "Midazolam", "EXACT"),
        ("MIDAZOLAM", "Midazolam", "EXACT"),
        ("ondansetron", "Ondansetron", "EXACT"),
        ("ONDANSETRON", "Ondansetron", "EXACT"),
        ("ibuprofen", "Ibuprofen", "EXACT"),
        ("IBUPROFEN", "Ibuprofen", "EXACT"),
    ]

    for query, expected_canonical, expected_status in test_cases:
        res = MedicineService.match_medicine(query)
        assert res["matched_canonical"] == expected_canonical, f"Failed canonical for {query}"
        assert res["status"] == expected_status, f"Failed status for {query}"
        assert res["confidence_score"] == 100.0
        assert res["requires_confirmation"] is False

def test_alias_case_variations():
    test_cases = [
        ("panadol", "Paracetamol", "ALIAS"),
        ("PANADOL", "Paracetamol", "ALIAS"),
        ("Panadol", "Paracetamol", "ALIAS"),
        ("tylenol", "Paracetamol", "ALIAS"),
        ("TYLENOL", "Paracetamol", "ALIAS"),
        ("calpol", "Paracetamol", "ALIAS"),
        ("CALPOL", "Paracetamol", "ALIAS"),
        ("albuterol", "Salbutamol", "ALIAS"),
        ("ALBUTEROL", "Salbutamol", "ALIAS"),
        ("narcan", "Naloxone", "ALIAS"),
        ("NARCAN", "Naloxone", "ALIAS"),
        ("adrenaline", "Epinephrine", "ALIAS"),
        ("ADRENALINE", "Epinephrine", "ALIAS"),
        ("zofran", "Ondansetron", "ALIAS"),
        ("ZOFRAN", "Ondansetron", "ALIAS"),
        ("advil", "Ibuprofen", "ALIAS"),
        ("ADVIL", "Ibuprofen", "ALIAS"),
    ]

    for query, expected_canonical, expected_status in test_cases:
        res = MedicineService.match_medicine(query)
        assert res["matched_canonical"] == expected_canonical, f"Failed alias canonical for {query}"
        assert res["status"] == expected_status, f"Failed alias status for {query}"
        assert res["requires_confirmation"] is False

# ==========================================================
# 2. Clinical Route Phrase Matching & Equivalence
# ==========================================================
def test_route_phrase_matching():
    test_cases = [
        # (Medicine, Route phrase, Expected match boolean)
        ("Paracetamol", "oral", True),
        ("Paracetamol", "ORAL", True),
        ("Paracetamol", "orally", True),
        ("Paracetamol", "by mouth", True),
        ("Paracetamol", "BY MOUTH", True),
        ("Paracetamol", "PO", True),
        ("Paracetamol", "po", True),
        ("Paracetamol", "p.o.", True),
        ("Paracetamol", "IV", True),
        ("Paracetamol", "via iv", True),
        ("Paracetamol", "rectally", True),
        ("Paracetamol", "PR", True),
        ("Paracetamol", "sublingual", False),  # Not standard for Paracetamol
        ("Aspirin", "chewable", True),
        ("Aspirin", "chewed", True),
        ("Aspirin", "CHEWED", True),
        ("Aspirin", "oral", True),
        ("Aspirin", "by mouth", True),
        ("Salbutamol", "nebulized", True),
        ("Salbutamol", "via nebulizer", True),
        ("Salbutamol", "inhaled", True),
        ("Salbutamol", "inhaler", True),
        ("Salbutamol", "Inhaled/Nebulized", True),
        ("Nitroglycerin", "SL", True),
        ("Nitroglycerin", "sl", True),
        ("Nitroglycerin", "sublingual", True),
        ("Nitroglycerin", "sublingually", True),
        ("Nitroglycerin", "patch", True),
        ("Nitroglycerin", "transdermal", True),
        ("Morphine", "IV", True),
        ("Morphine", "iv push", True),
        ("Morphine", "IM", True),
        ("Morphine", "intramuscularly", True),
        ("Morphine", "subcutaneous", True),
        ("Morphine", "subcutaneously", True),
        ("Morphine", "sub-q", True),
        ("Naloxone", "IN", True),
        ("Naloxone", "in", True),
        ("Naloxone", "intranasal", True),
        ("Naloxone", "intranasally", True),
        ("Naloxone", "nasal spray", True),
        ("Epinephrine", "IM", True),
        ("Epinephrine", "intramuscularly", True),
        ("Epinephrine", "IO", True),
        ("Midazolam", "buccal", True),
        ("Midazolam", "buccally", True),
        ("Ondansetron", "ODT", True),
        ("Ondansetron", "orally disintegrating", True),
    ]

    for med, route, expected in test_cases:
        res = MedicineService.compare_strength_and_route(med, route=route)
        assert res["route_match"] == expected, f"Failed route check: med={med}, route={route}, got={res['route_match']}, expected={expected}"

# ==========================================================
# 3. Clinical Entity Extractor with Case Variations and Route Phrases
# ==========================================================
def test_clinical_extractor_medication_variations():
    # Narrative with mixed casing and common field route phrases
    text = (
        "Administered 500mg PARACETAMOL by mouth. "
        "Also gave 2.5mg SALBUTAMOL via nebulizer and 400mcg NITROGLYCERIN SL. "
        "Patient chewed 300mg ASPIRIN. Patient denies any chest pain and NO MORPHINE WAS GIVEN."
    )
    entities = ClinicalExtractor.extract_all(text)
    meds = entities["medications"]

    # Paracetamol check
    paracetamol = next((m for m in meds if m["canonical_name"] == "Paracetamol"), None)
    assert paracetamol is not None
    assert paracetamol["raw_mention"] == "PARACETAMOL"
    assert paracetamol["dosage"] == "500"
    assert paracetamol["unit"] == "mg"
    assert paracetamol["route"] == "Oral"
    assert paracetamol["match_status"] == "EXACT"
    assert paracetamol["is_negated"] is False

    # Salbutamol check
    salbutamol = next((m for m in meds if m["canonical_name"] == "Salbutamol"), None)
    assert salbutamol is not None
    assert salbutamol["raw_mention"] == "SALBUTAMOL"
    assert salbutamol["dosage"] == "2.5"
    assert salbutamol["unit"] == "mg"
    assert salbutamol["route"] == "Inhaled/Nebulized"
    assert salbutamol["match_status"] == "EXACT"

    # Nitroglycerin check
    nitro = next((m for m in meds if m["canonical_name"] == "Nitroglycerin"), None)
    assert nitro is not None
    assert nitro["raw_mention"] == "NITROGLYCERIN"
    assert nitro["dosage"] == "400"
    assert nitro["unit"] == "mcg"
    assert nitro["route"] == "Sublingual"
    assert nitro["match_status"] == "EXACT"

    # Aspirin check
    aspirin = next((m for m in meds if m["canonical_name"] == "Aspirin"), None)
    assert aspirin is not None
    assert aspirin["raw_mention"] == "ASPIRIN"
    assert aspirin["dosage"] == "300"
    assert aspirin["unit"] == "mg"
    assert aspirin["route"] == "Chewable"
    assert aspirin["match_status"] == "EXACT"

    # Negated Morphine check
    morphine = next((m for m in meds if m["canonical_name"] == "Morphine"), None)
    assert morphine is not None
    assert morphine["raw_mention"] == "MORPHINE"
    assert morphine["is_negated"] is True
    assert morphine["negation_trigger"] is not None

def test_api_medicine_search_case_variations(client):
    # Test through the Flask API endpoint
    for query in ["paracetamol", "PARACETAMOL", "Paracetamol", "PaRaCeTaMoL"]:
        res = client.get(f"/api/medicines/search?q={query}")
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["status"] == "EXACT"
        assert data["matched_canonical"] == "Paracetamol"
        assert data["requires_confirmation"] is False

    for query in ["panadol", "PANADOL", "Panadol"]:
        res = client.get(f"/api/medicines/search?q={query}")
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["status"] == "ALIAS"
        assert data["matched_canonical"] == "Paracetamol"
        assert data["requires_confirmation"] is False
