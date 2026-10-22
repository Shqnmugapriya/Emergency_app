"""
Utility script to generate real audio test cases for speech recognition and WER evaluation.
Uses Windows SAPI for zero-cloud, 100% offline speech audio synthesis.
"""

import os
import subprocess
import numpy as np
import scipy.io.wavfile as wavfile

TEST_AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_audio"))
os.makedirs(TEST_AUDIO_DIR, exist_ok=True)

def generate_speech_file(filename, text, rate=0):
    """Generate a clean speech wav file using Windows SAPI."""
    out_path = os.path.join(TEST_AUDIO_DIR, filename)
    ps_script = f"""
    Add-Type -AssemblyName System.Speech
    $speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $speaker.Rate = {rate}
    $speaker.SetOutputToWaveFile('{out_path}')
    $speaker.Speak('{text}')
    $speaker.Dispose()
    """
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)
    return out_path

def generate_noisy_audio(filename, base_wav_path, noise_level=0.08):
    """Mix Gaussian background noise into a base audio file."""
    out_path = os.path.join(TEST_AUDIO_DIR, filename)
    sr, data = wavfile.read(base_wav_path)
    data = data.astype(np.float32)

    noise = np.random.normal(0, np.max(np.abs(data)) * noise_level, data.shape)
    noisy_data = np.clip(data + noise, -32767, 32767).astype(np.int16)

    wavfile.write(out_path, sr, noisy_data)
    return out_path

def generate_empty_and_corrupt_files():
    """Create empty (0 bytes) and corrupted header files."""
    empty_path = os.path.join(TEST_AUDIO_DIR, "empty.wav")
    with open(empty_path, "wb") as f:
        pass

    corrupt_path = os.path.join(TEST_AUDIO_DIR, "corrupt.wav")
    with open(corrupt_path, "wb") as f:
        f.write(b"RIFF\x00\x00\x00\x00NOT_A_VALID_WAV_HEADER_DATA_GARBAGE")

    return empty_path, corrupt_path

def create_all_test_audios():
    test_cases = [
        # The key failure case from Section 9
        ("paracetamol_phrase.wav", "I want paracetamol", 0),
        # Medical field note with vitals and meds
        ("clinical_note_1.wav", "Patient has severe chest pain, blood pressure 130 over 85, administered 500 mg paracetamol orally.", 0),
        # Numerical values and vitals
        ("vitals_numbers.wav", "Blood pressure 140 over 90, pulse 88, oxygen saturation 96 percent, respiratory rate 18.", 0),
        # Indian-accented / faster paced English simulation (higher speech rate)
        ("fast_speech.wav", "Patient conscious and oriented, denies shortness of breath, blood glucose 5.4, administered 1000 mg paracetamol.", 2),
        # Asthma case with salbutamol
        ("asthma_note.wav", "Severe wheezing observed, oxygen saturation 91 percent, gave 5 mg salbutamol nebulized.", 0)
    ]

    generated = {}
    for fname, text, rate in test_cases:
        p = generate_speech_file(fname, text, rate)
        generated[fname] = {"path": p, "expected_text": text}

    # Add noisy version of the paracetamol test case
    noisy_path = generate_noisy_audio("paracetamol_noisy.wav", generated["paracetamol_phrase.wav"]["path"], 0.05)
    generated["paracetamol_noisy.wav"] = {"path": noisy_path, "expected_text": "I want paracetamol"}

    empty_p, corrupt_p = generate_empty_and_corrupt_files()
    generated["empty.wav"] = {"path": empty_p, "expected_text": None}
    generated["corrupt.wav"] = {"path": corrupt_p, "expected_text": None}

    print(f"Successfully generated {len(generated)} test audio files in {TEST_AUDIO_DIR}")
    return generated

if __name__ == "__main__":
    create_all_test_audios()
