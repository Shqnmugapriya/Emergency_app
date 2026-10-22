import React, { useState, useRef, useEffect } from "react";
import { Mic, Square, Play, Pause, RotateCcw, Upload, Volume2, AlertTriangle, Clock, Sparkles } from "lucide-react";
import { api } from "../services/api";

export function AudioRecorder({ onTranscriptionComplete, onSaveDraft }) {
  const [mode, setMode] = useState("record"); // "record" | "upload"
  const [recordingState, setRecordingState] = useState("idle"); // "idle" | "recording" | "paused" | "stopped"
  const [duration, setDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcriptionError, setTranscriptionError] = useState(null);
  const [machineTranscript, setMachineTranscript] = useState("");
  const [editableTranscript, setEditableTranscript] = useState("");
  const [transcriptionMeta, setTranscriptionMeta] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [transcribeElapsed, setTranscribeElapsed] = useState(0);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const audioElementRef = useRef(null);
  const transcribeTimerRef = useRef(null);

  // Timer for active recording
  useEffect(() => {
    if (recordingState === "recording") {
      timerRef.current = setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [recordingState]);

  // Elapsed timer while backend transcribes
  useEffect(() => {
    if (isTranscribing) {
      setTranscribeElapsed(0);
      transcribeTimerRef.current = setInterval(() => {
        setTranscribeElapsed((prev) => +(prev + 0.1).toFixed(1));
      }, 100);
    } else {
      clearInterval(transcribeTimerRef.current);
    }
    return () => clearInterval(transcribeTimerRef.current);
  }, [isTranscribing]);

  // Clean up object URLs
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  const formatTime = (secs) => {
    const mins = Math.floor(secs / 60);
    const remaining = secs % 60;
    return `${mins.toString().padStart(2, "0")}:${remaining.toString().padStart(2, "0")}`;
  };

  const startRecording = async () => {
    setTranscriptionError(null);
    audioChunksRef.current = [];
    setAudioBlob(null);
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(null);
    setDuration(0);

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Audio recording is not supported in this browser environment.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true
        }
      });

      // Preferred supported MIME types
      let mimeType = "audio/webm;codecs=opus";
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        if (MediaRecorder.isTypeSupported("audio/webm")) {
          mimeType = "audio/webm";
        } else if (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")) {
          mimeType = "audio/ogg;codecs=opus";
        } else {
          mimeType = ""; // Browser default
        }
      }

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const actualMime = recorder.mimeType || "audio/webm";
        const finalBlob = new Blob(audioChunksRef.current, { type: actualMime });

        if (finalBlob.size === 0) {
          setTranscriptionError("Recording failed: Collected audio is empty (0 bytes). Check microphone permissions.");
          setRecordingState("idle");
          return;
        }

        setAudioBlob(finalBlob);
        const url = URL.createObjectURL(finalBlob);
        setAudioUrl(url);
        setRecordingState("stopped");

        // Stop all audio tracks to release microphone hardware
        stream.getTracks().forEach((track) => track.stop());
      };

      recorder.start(250); // Collect chunk every 250ms
      setRecordingState("recording");
    } catch (err) {
      setTranscriptionError(`Microphone access error: ${err.message || err.name}. Please grant microphone permissions in browser.`);
      setRecordingState("idle");
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && recordingState === "recording") {
      mediaRecorderRef.current.pause();
      setRecordingState("paused");
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && recordingState === "paused") {
      mediaRecorderRef.current.resume();
      setRecordingState("recording");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && (recordingState === "recording" || recordingState === "paused")) {
      mediaRecorderRef.current.stop();
    }
  };

  const resetRecording = () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setDuration(0);
    setRecordingState("idle");
    setMachineTranscript("");
    setEditableTranscript("");
    setTranscriptionMeta(null);
    setTranscriptionError(null);
  };

  const togglePlayback = () => {
    if (!audioElementRef.current) return;
    if (isPlaying) {
      audioElementRef.current.pause();
      setIsPlaying(false);
    } else {
      audioElementRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size === 0) {
      setTranscriptionError("Selected file is empty (0 bytes).");
      return;
    }

    if (file.size > 30 * 1024 * 1024) {
      setTranscriptionError("Audio file exceeds maximum 30MB limit.");
      return;
    }

    setSelectedFile(file);
    setAudioBlob(file);
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    const url = URL.createObjectURL(file);
    setAudioUrl(url);
    setRecordingState("stopped");
    setTranscriptionError(null);
  };

  const handleTranscribe = async () => {
    if (!audioBlob) {
      setTranscriptionError("No audio available. Please record or upload an audio file first.");
      return;
    }

    setIsTranscribing(true);
    setTranscriptionError(null);

    try {
      const formData = new FormData();
      const ext = audioBlob.type?.includes("ogg") ? "ogg" : audioBlob.type?.includes("wav") ? "wav" : "webm";
      const filename = selectedFile?.name || `field_recording_${Date.now()}.${ext}`;

      formData.append("audio", audioBlob, filename);

      const res = await api.transcribeAudio(formData);

      if (res.success && res.data) {
        setMachineTranscript(res.data.transcript);
        setEditableTranscript(res.data.transcript);
        setTranscriptionMeta(res.data);

        if (onTranscriptionComplete) {
          onTranscriptionComplete(res.data);
        }
      } else {
        throw new Error(res.error || "Transcription returned no text.");
      }
    } catch (err) {
      setTranscriptionError(err.message || "Failed to transcribe audio. Verify backend is running and Whisper is ready.");
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleSaveDraft = () => {
    if (!editableTranscript.trim()) {
      setTranscriptionError("Please record and transcribe audio or type field notes before saving.");
      return;
    }

    if (onSaveDraft) {
      onSaveDraft({
        machine_transcript: machineTranscript,
        corrected_transcript: editableTranscript,
        audio_filename: transcriptionMeta?.audio_filename || null,
        audio_mimetype: audioBlob?.type || "audio/webm",
        audio_duration_seconds: duration || transcriptionMeta?.duration_seconds || 0,
        transcription_metadata: transcriptionMeta || {}
      });
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Header Tabs */}
      <div className="flex border-b border-slate-200 bg-slate-50/70 px-6 pt-4">
        <button
          onClick={() => setMode("record")}
          className={`flex items-center gap-2 pb-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
            mode === "record"
              ? "border-clinical-teal-600 text-clinical-teal-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Mic className="w-4 h-4" />
          <span>Microphone Recording</span>
        </button>
        <button
          onClick={() => setMode("upload")}
          className={`flex items-center gap-2 pb-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
            mode === "upload"
              ? "border-clinical-teal-600 text-clinical-teal-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Upload className="w-4 h-4" />
          <span>Upload Audio File</span>
        </button>
      </div>

      <div className="p-6 space-y-6">
        {/* Error Alert */}
        {transcriptionError && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 flex items-start gap-3 text-sm">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold">Transcription / Audio Notice: </span>
              {transcriptionError}
            </div>
          </div>
        )}

        {/* Recording Controls */}
        {mode === "record" ? (
          <div className="flex flex-col items-center justify-center p-8 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200 text-center space-y-4">
            {/* Status indicator */}
            <div className="flex items-center gap-2 text-sm font-semibold">
              {recordingState === "recording" && (
                <span className="flex items-center gap-1.5 text-red-600">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-record-pulse"></span>
                  RECORDING IN PROGRESS
                </span>
              )}
              {recordingState === "paused" && (
                <span className="text-amber-600">RECORDING PAUSED</span>
              )}
              {recordingState === "stopped" && (
                <span className="text-emerald-700">AUDIO READY FOR TRANSCRIPTION</span>
              )}
              {recordingState === "idle" && (
                <span className="text-slate-500">READY TO CAPTURE CLINICAL FIELD NOTES</span>
              )}
            </div>

            {/* Timer */}
            <div className="text-4xl font-mono font-bold text-slate-800 tracking-wider">
              {formatTime(duration)}
            </div>

            {/* Control Buttons */}
            <div className="flex items-center gap-3 pt-2">
              {recordingState === "idle" && (
                <button
                  onClick={startRecording}
                  className="flex items-center gap-2 px-6 py-3 rounded-full bg-clinical-teal-600 hover:bg-clinical-teal-700 text-white font-semibold shadow-md transition-all active:scale-95"
                >
                  <Mic className="w-5 h-5" />
                  <span>Start Recording</span>
                </button>
              )}

              {recordingState === "recording" && (
                <>
                  <button
                    onClick={pauseRecording}
                    className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold shadow-sm"
                  >
                    <Pause className="w-4 h-4" />
                    <span>Pause</span>
                  </button>
                  <button
                    onClick={stopRecording}
                    className="flex items-center gap-1.5 px-6 py-2.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-semibold shadow-md active:scale-95"
                  >
                    <Square className="w-4 h-4" />
                    <span>Stop Recording</span>
                  </button>
                </>
              )}

              {recordingState === "paused" && (
                <>
                  <button
                    onClick={resumeRecording}
                    className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold shadow-sm"
                  >
                    <Play className="w-4 h-4" />
                    <span>Resume</span>
                  </button>
                  <button
                    onClick={stopRecording}
                    className="flex items-center gap-1.5 px-6 py-2.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-semibold shadow-md"
                  >
                    <Square className="w-4 h-4" />
                    <span>Stop</span>
                  </button>
                </>
              )}

              {recordingState === "stopped" && (
                <button
                  onClick={resetRecording}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 text-sm font-semibold"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Record Again</span>
                </button>
              )}
            </div>

            <p className="text-xs text-slate-400 max-w-md">
              Speak clearly. State patient symptoms, vital signs (e.g. BP 120/80, pulse 75), and administered medications with doses and routes.
            </p>
          </div>
        ) : (
          /* File Upload Box */
          <div className="p-8 bg-slate-50 rounded-xl border-2 border-dashed border-slate-300 text-center space-y-4">
            <Upload className="w-10 h-10 text-slate-400 mx-auto" />
            <div>
              <label
                htmlFor="audio-upload"
                className="cursor-pointer inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-clinical-teal-600 hover:bg-clinical-teal-700 text-white text-sm font-semibold shadow-sm"
              >
                <span>Select Audio File</span>
                <input
                  id="audio-upload"
                  type="file"
                  accept="audio/*,.webm,.wav,.mp3,.ogg,.m4a"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>
              <p className="text-xs text-slate-500 mt-2">
                Supported formats: WebM, WAV, MP3, OGG, M4A (Max 30MB)
              </p>
            </div>
            {selectedFile && (
              <div className="text-sm font-medium text-slate-700 bg-white p-2.5 rounded border border-slate-200 inline-block">
                Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
              </div>
            )}
          </div>
        )}

        {/* Audio Player for Review */}
        {audioUrl && (
          <div className="bg-slate-100 p-4 rounded-xl flex items-center justify-between border border-slate-200">
            <div className="flex items-center gap-3">
              <button
                onClick={togglePlayback}
                className="w-10 h-10 rounded-full bg-clinical-teal-700 text-white flex items-center justify-center hover:bg-clinical-teal-800 shadow-sm"
              >
                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
              </button>
              <div>
                <span className="text-sm font-semibold text-slate-800">Recorded Field Audio</span>
                <p className="text-xs text-slate-500">
                  {audioBlob ? `${(audioBlob.size / 1024).toFixed(1)} KB • ${audioBlob.type || "audio/webm"}` : ""}
                </p>
              </div>
              <audio
                ref={audioElementRef}
                src={audioUrl}
                onEnded={() => setIsPlaying(false)}
                className="hidden"
              />
            </div>

            {/* Transcribe Trigger Button */}
            <button
              onClick={handleTranscribe}
              disabled={isTranscribing}
              className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-clinical-teal-600 hover:bg-clinical-teal-700 disabled:bg-slate-300 text-white text-sm font-semibold shadow-md transition-all"
            >
              <Sparkles className="w-4 h-4" />
              <span>{isTranscribing ? `Transcribing (${transcribeElapsed}s)...` : "Transcribe with Whisper"}</span>
            </button>
          </div>
        )}

        {/* Transcribe Spinner Indicator */}
        {isTranscribing && (
          <div className="p-4 bg-teal-50 border border-teal-200 rounded-lg flex items-center gap-3 text-teal-800 text-sm">
            <div className="w-5 h-5 border-2 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
            <div>
              <span className="font-semibold">Local Faster-Whisper Inference Running: </span>
              Decoding speech offline with clinical vocabulary priors... ({transcribeElapsed}s elapsed)
            </div>
          </div>
        )}

        {/* Editable Transcript Text Area */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-bold text-slate-800">
              Clinical Narrative / Field Notes Transcript
            </label>
            <span className="text-xs text-slate-500">
              {editableTranscript.trim() ? `${editableTranscript.trim().split(/\s+/).length} words` : "0 words"}
            </span>
          </div>

          <textarea
            rows={5}
            value={editableTranscript}
            onChange={(e) => setEditableTranscript(e.target.value)}
            placeholder="Whisper transcript will appear here automatically. You can also type or correct transcripts manually before extracting structured clinical data..."
            className="w-full p-3.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500 focus:border-clinical-teal-500 text-sm text-slate-800 placeholder-slate-400 bg-white shadow-inner resize-y"
          />
        </div>

        {/* Original Machine Transcript Diff / Display */}
        {machineTranscript && machineTranscript !== editableTranscript && (
          <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-xs space-y-1">
            <div className="font-semibold text-amber-800 flex items-center gap-1.5">
              <span>Original Machine Transcript (Unmodified Audit Reference):</span>
            </div>
            <p className="text-amber-900 italic font-mono bg-white/70 p-2 rounded border border-amber-100">
              "{machineTranscript}"
            </p>
          </div>
        )}

        {/* Bottom Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-200">
          <div className="text-xs text-slate-500">
            {transcriptionMeta && (
              <span>
                Language: <b className="uppercase">{transcriptionMeta.language}</b> • Audio Duration:{" "}
                <b>{transcriptionMeta.duration_seconds}s</b> • Model: <b>{transcriptionMeta.model_used}</b>
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSaveDraft}
              disabled={!editableTranscript.trim()}
              className="px-6 py-2.5 rounded-lg bg-clinical-navy-800 hover:bg-clinical-navy-900 disabled:bg-slate-300 text-white text-sm font-semibold shadow-md transition-all"
            >
              Extract Clinical Events & Save Draft
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
