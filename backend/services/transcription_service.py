"""
Transcription Service using faster-whisper.
Runs local, offline speech-to-text inference with medical prompt priming and audio validation.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import io
import time
import logging
import threading
from pathlib import Path
import numpy as np

logger = logging.getLogger("field_to_record.transcription")
logging.basicConfig(level=logging.INFO)

# Configurable defaults
DEFAULT_MODEL_NAME = os.environ.get("WHISPER_MODEL_NAME", "base")
DEFAULT_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
DEFAULT_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models"))
AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "audio"))

# Medical Domain Prompt for Whisper acoustic and linguistic priming
# Does NOT hardcode specific phrases; provides vocabulary priors for first responder terms.
CLINICAL_INITIAL_PROMPT = (
    "Emergency medical responder clinical field documentation. "
    "Patient vitals, blood pressure, pulse, heart rate, SpO2, respiratory rate, GCS, glucose. "
    "Medicines and dosages: paracetamol, ibuprofen, aspirin, morphine, naloxone, salbutamol, "
    "nitroglycerin, epinephrine, fentanyl, ondansetron, midazolam, oxygen. "
    "Routes: IV, IM, oral, sublingual, nebulized, mg, mcg, ml, bpm. "
    "Symptoms: chest pain, shortness of breath, trauma, laceration, denies pain."
)

class ModelStatus:
    UNINITIALIZED = "UNINITIALIZED"
    LOADING = "LOADING"
    READY = "READY"
    MISSING = "MISSING"
    ERROR = "ERROR"

class TranscriptionService:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.model = None
        self.status = ModelStatus.UNINITIALIZED
        self.status_message = "Model not yet loaded."
        self.model_name = DEFAULT_MODEL_NAME
        self.device = DEFAULT_DEVICE
        self.compute_type = DEFAULT_COMPUTE_TYPE
        self.download_progress = 0
        os.makedirs(MODELS_DIR, exist_ok=True)
        os.makedirs(AUDIO_DIR, exist_ok=True)

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def load_model(self, model_name=None, device=None, compute_type=None):
        """Load or reload the faster-whisper model."""
        from faster_whisper import WhisperModel

        if model_name:
            self.model_name = model_name
        if device:
            self.device = device
        if compute_type:
            self.compute_type = compute_type

        self.status = ModelStatus.LOADING
        self.status_message = f"Loading faster-whisper model '{self.model_name}' on {self.device} ({self.compute_type})..."
        logger.info(self.status_message)

        try:
            # download_root points to local models dir to ensure offline persistence
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=MODELS_DIR,
                cpu_threads=4
            )
            self.status = ModelStatus.READY
            self.status_message = f"Model '{self.model_name}' ready on {self.device}."
            logger.info(self.status_message)
            return True, self.status_message
        except Exception as e:
            self.status = ModelStatus.ERROR
            self.status_message = f"Failed to load Whisper model '{self.model_name}': {str(e)}"
            logger.error(self.status_message, exc_info=True)
            return False, self.status_message

    def get_status(self):
        """Return diagnostic status information about the speech engine."""
        return {
            "status": self.status,
            "message": self.status_message,
            "model_name": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "models_directory": MODELS_DIR,
            "is_ready": self.status == ModelStatus.READY,
            "offline_capable": True
        }

    def convert_and_verify_audio(self, input_filepath):
        """
        Verify that audio is valid, non-empty, and extract duration and sample info using PyAV.
        Returns: (is_valid, duration_seconds, sample_rate, error_msg)
        """
        import av
        try:
            container = av.open(input_filepath)
            audio_streams = [s for s in container.streams if s.type == 'audio']
            if not audio_streams:
                return False, 0.0, 0, "No audio stream found in file."

            stream = audio_streams[0]
            # Duration in seconds
            duration = float(stream.duration * stream.time_base) if stream.duration and stream.time_base else 0.0
            sample_rate = stream.rate or 16000

            # If duration is 0, estimate from frames
            if duration <= 0.0:
                frame_count = 0
                sample_count = 0
                for frame in container.decode(stream):
                    sample_count += frame.samples
                    frame_count += 1
                if sample_count > 0 and sample_rate > 0:
                    duration = sample_count / sample_rate

            if duration < 0.2:
                return False, duration, sample_rate, "Audio recording is too short or empty (<0.2 seconds)."

            return True, duration, sample_rate, None
        except Exception as e:
            return False, 0.0, 0, f"Corrupted or unsupported audio file: {str(e)}"

    def transcribe_audio_file(self, audio_filepath, language="en", vad_filter=True, initial_prompt=None):
        """
        Transcribe an audio file using faster-whisper.
        Applies clinical domain prompting and strict deterministic decoding.
        """
        if self.status != ModelStatus.READY or self.model is None:
            # Try to auto-load if uninitialized
            success, msg = self.load_model()
            if not success:
                raise RuntimeError(f"Transcription engine unavailable: {msg}")

        # Verify audio validity
        valid, duration, sample_rate, err = self.convert_and_verify_audio(audio_filepath)
        if not valid:
            raise ValueError(f"Audio validation failed: {err}")

        prompt = initial_prompt if initial_prompt is not None else CLINICAL_INITIAL_PROMPT

        start_time = time.time()

        # Run faster-whisper inference
        # temperature=0.0 prevents hallucination
        # beam_size=5 ensures high quality search
        # condition_on_previous_text=False prevents cascading errors on short notes
        segments_generator, info = self.model.transcribe(
            audio_filepath,
            language=language,
            task="transcribe",
            beam_size=5,
            best_of=5,
            temperature=0.0,
            condition_on_previous_text=False,
            initial_prompt=prompt,
            vad_filter=vad_filter,
            vad_parameters=dict(min_silence_duration_ms=400)
        )

        segments = []
        transcript_parts = []
        for seg in segments_generator:
            text = seg.text.strip()
            if text:
                transcript_parts.append(text)
                segments.append({
                    "id": seg.id,
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": text,
                    "avg_logprob": round(seg.avg_logprob, 3),
                    "no_speech_prob": round(seg.no_speech_prob, 3)
                })

        full_transcript = " ".join(transcript_parts).strip()
        elapsed = time.time() - start_time

        # If audio duration was unknown or zero from container header, use last segment end
        if duration <= 0.0 and segments:
            duration = segments[-1]["end"]

        return {
            "transcript": full_transcript,
            "language": info.language,
            "language_probability": round(info.language_probability, 3) if hasattr(info, "language_probability") else 1.0,
            "duration": round(duration, 2),
            "inference_duration": round(elapsed, 2),
            "segments": segments,
            "model_used": self.model_name,
            "device": self.device
        }

if __name__ == "__main__":
    import sys
    svc = TranscriptionService.get_instance()
    if "--download-model" in sys.argv:
        m_name = sys.argv[sys.argv.index("--download-model") + 1] if len(sys.argv) > sys.argv.index("--download-model") + 1 else "base"
        print(f"Downloading model '{m_name}' to {MODELS_DIR}...")
        ok, res = svc.load_model(model_name=m_name)
        print(f"Result: {ok} -> {res}")
    else:
        print("Whisper service CLI helper.")
        print("Status:", svc.get_status())
