# Local Whisper Models Directory

Field-to-Record uses `faster-whisper` for offline speech-to-text inference.

## Model Caching
By default, models are downloaded on first use or pre-downloaded and cached locally in:
- This directory (`models/`) or standard Hugging Face cache (`~/.cache/huggingface/hub`)
- Configuration option `WHISPER_MODEL_DIR` can point directly to local model weights for fully air-gapped / offline deployments.

## Supported Model Sizes
- `tiny` (~75 MB): Fastest, lowest memory (~390 MB RAM), ideal for quick smoke tests and low-power hardware.
- `base` (~145 MB): Recommended default for Windows laptops. Good balance between latency (~0.5s - 1.5s per utterance) and medical vocabulary recognition.
- `small` (~480 MB): Higher accuracy for accented speech.

## Offline Setup
To prepare for 100% offline operation:
Run the download script:
```powershell
.\backend\venv\Scripts\python.exe backend/services/transcription_service.py --download-model base
```
Once downloaded, the model will run locally without internet connectivity.
