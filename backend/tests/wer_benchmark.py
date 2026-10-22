"""
Word Error Rate (WER) and Clinical Entity Recognition Accuracy Benchmark.
Directly investigates and evaluates the known speech-recognition issue:
'I want paracetamol' misrecognized as 'I want that if you don't worry'.

Measures:
1. Exact Word Error Rate (WER) using Levenshtein distance on normalized tokens.
2. Medicine Name Recognition Accuracy (whether intended medical term was recognized).
3. Compares Default Unprimed Whisper vs Field-to-Record Clinically Primed Whisper.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import re
import string
from backend.services.transcription_service import TranscriptionService, CLINICAL_INITIAL_PROMPT
from backend.services.clinical_extractor import ClinicalExtractor

def normalize_text(text):
    """Normalize text for WER calculation (lowercase, remove punctuation)."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", text).strip().split()

def compute_wer(reference, hypothesis):
    """
    Standard Levenshtein distance based Word Error Rate (WER).
    WER = (Substitutions + Insertions + Deletions) / Number of Reference Words
    """
    ref_words = normalize_text(reference)
    hyp_words = normalize_text(hypothesis)

    if not ref_words:
        return 1.0 if hyp_words else 0.0

    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]

    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                cost = 0
            else:
                cost = 1
            d[i][j] = min(
                d[i - 1][j] + 1,       # deletion
                d[i][j - 1] + 1,       # insertion
                d[i - 1][j - 1] + cost # substitution
            )

    return d[len(ref_words)][len(hyp_words)] / len(ref_words)

def run_wer_benchmark():
    test_audio_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_audio"))
    service = TranscriptionService.get_instance()
    service.load_model("base")

    test_cases = [
        {
            "category": "Known Failure Phrase ('I want paracetamol')",
            "file": "paracetamol_phrase.wav",
            "reference": "I want paracetamol",
            "target_medicine": "paracetamol"
        },
        {
            "category": "Noisy Speech (Background Noise)",
            "file": "paracetamol_noisy.wav",
            "reference": "I want paracetamol",
            "target_medicine": "paracetamol"
        },
        {
            "category": "Complete Clinical Note (Chest pain, BP, Paracetamol)",
            "file": "clinical_note_1.wav",
            "reference": "Patient has severe chest pain blood pressure 130 over 85 administered 500 mg paracetamol orally",
            "target_medicine": "paracetamol"
        },
        {
            "category": "Numerical Vital Signs (BP, Pulse, SpO2, RR)",
            "file": "vitals_numbers.wav",
            "reference": "Blood pressure 140 over 90 pulse 88 oxygen saturation 96 percent respiratory rate 18",
            "target_medicine": None
        },
        {
            "category": "Fast-Paced / Indian English Simulation",
            "file": "fast_speech.wav",
            "reference": "Patient conscious and oriented denies shortness of breath blood glucose 5.4 administered 1000 mg paracetamol",
            "target_medicine": "paracetamol"
        },
        {
            "category": "Asthma Intervention (Wheezing, Salbutamol)",
            "file": "asthma_note.wav",
            "reference": "Severe wheezing observed oxygen saturation 91 percent gave 5 mg salbutamol nebulized",
            "target_medicine": "salbutamol"
        }
    ]

    print("=" * 80)
    print("FIELD-TO-RECORD SPEECH RECOGNITION BENCHMARK REPORT")
    print("Model: faster-whisper base | Device: CPU (int8)")
    print("=" * 80)

    results = []

    for tc in test_cases:
        filepath = os.path.join(test_audio_dir, tc["file"])
        if not os.path.exists(filepath):
            print(f"Skipping {tc['file']}, file not found.")
            continue

        # Test A: Unprimed (No clinical prompt, default temperature)
        res_unprimed = service.transcribe_audio_file(
            filepath,
            language="en",
            initial_prompt=""  # No prompt priming
        )
        wer_unprimed = compute_wer(tc["reference"], res_unprimed["transcript"])

        # Test B: Field-to-Record Primed (Clinical Prompt + VAD + Strict Beam Search)
        res_primed = service.transcribe_audio_file(
            filepath,
            language="en",
            initial_prompt=CLINICAL_INITIAL_PROMPT
        )
        wer_primed = compute_wer(tc["reference"], res_primed["transcript"])

        # Check medicine recognition
        med_recognized = False
        if tc["target_medicine"]:
            med_recognized = tc["target_medicine"].lower() in res_primed["transcript"].lower()

        results.append({
            "category": tc["category"],
            "reference": tc["reference"],
            "transcript_unprimed": res_unprimed["transcript"],
            "wer_unprimed": round(wer_unprimed * 100, 1),
            "transcript_primed": res_primed["transcript"],
            "wer_primed": round(wer_primed * 100, 1),
            "target_medicine": tc["target_medicine"],
            "medicine_recognized": med_recognized
        })

    for r in results:
        print(f"\n--- {r['category']} ---")
        print(f"  Reference:           \"{r['reference']}\"")
        print(f"  Unprimed Output:     \"{r['transcript_unprimed']}\" (WER: {r['wer_unprimed']}%)")
        print(f"  Field-to-Record:     \"{r['transcript_primed']}\" (WER: {r['wer_primed']}%)")
        if r["target_medicine"]:
            print(f"  Medicine Correct:    {'YES [OK]' if r['medicine_recognized'] else 'NO [MISSED]'}")

    avg_wer_unprimed = sum(r["wer_unprimed"] for r in results) / len(results)
    avg_wer_primed = sum(r["wer_primed"] for r in results) / len(results)
    med_trials = [r for r in results if r["target_medicine"]]
    med_acc = (sum(1 for r in med_trials if r["medicine_recognized"]) / len(med_trials)) * 100 if med_trials else 100

    print("\n" + "=" * 80)
    print("SUMMARY METRICS:")
    print(f"  Average WER (Unprimed default):         {avg_wer_unprimed:.1f}%")
    print(f"  Average WER (Field-to-Record Primed):   {avg_wer_primed:.1f}%")
    print(f"  Medicine Name Recognition Accuracy:     {med_acc:.1f}%")
    print("=" * 80)

    return results

if __name__ == "__main__":
    run_wer_benchmark()
