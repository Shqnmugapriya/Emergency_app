import React, { useState } from "react";
import { Mic, FileText, User, Hash, AlertCircle, ArrowRight } from "lucide-react";
import { AudioRecorder } from "../components/AudioRecorder";
import { api } from "../services/api";

export function VoiceInputPage({ onRecordCreated }) {
  const [callNumber, setCallNumber] = useState(`EMS-${Math.floor(1000 + Math.random() * 9000)}`);
  const [responderId, setResponderId] = useState("Paramedic-101");
  const [patientGender, setPatientGender] = useState("Unspecified");
  const [patientAge, setPatientAge] = useState("");
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const handleSaveDraft = async (transcriptionData) => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const recordPayload = {
        call_number: callNumber,
        responder_id: responderId,
        machine_transcript: transcriptionData.machine_transcript || "",
        corrected_transcript: transcriptionData.corrected_transcript || "",
        audio_filename: transcriptionData.audio_filename,
        audio_mimetype: transcriptionData.audio_mimetype,
        audio_duration_seconds: transcriptionData.audio_duration_seconds,
        transcription_metadata: transcriptionData.transcription_metadata,
        patient_summary: {
          age: patientAge,
          gender: patientGender,
          chief_complaint: chiefComplaint
        }
      };

      const res = await api.createRecord(recordPayload);

      if (res.success && res.data) {
        if (onRecordCreated) {
          onRecordCreated(res.data.id);
        }
      } else {
        throw new Error(res.error || "Failed to create record in database.");
      }
    } catch (err) {
      setSubmitError(err.message || "Failed to save draft.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Title Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          New Clinical Field Encounter
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Capture voice narrative or type field notes. Local Whisper runs speech inference without internet access.
        </p>
      </div>

      {submitError && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
          <span>{submitError}</span>
        </div>
      )}

      {/* Incident & Dispatch Header Form */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label className="text-xs font-bold text-slate-600 uppercase tracking-wider block mb-1">
            Incident / Call #
          </label>
          <div className="relative">
            <input
              type="text"
              value={callNumber}
              onChange={(e) => setCallNumber(e.target.value)}
              className="w-full text-sm font-semibold p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500 focus:border-clinical-teal-500"
              placeholder="e.g. EMS-4091"
            />
          </div>
        </div>

        <div>
          <label className="text-xs font-bold text-slate-600 uppercase tracking-wider block mb-1">
            Responder ID / Unit
          </label>
          <input
            type="text"
            value={responderId}
            onChange={(e) => setResponderId(e.target.value)}
            className="w-full text-sm font-semibold p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500 focus:border-clinical-teal-500"
            placeholder="e.g. Paramedic-101"
          />
        </div>

        <div>
          <label className="text-xs font-bold text-slate-600 uppercase tracking-wider block mb-1">
            Estimated Patient Age
          </label>
          <input
            type="text"
            value={patientAge}
            onChange={(e) => setPatientAge(e.target.value)}
            className="w-full text-sm p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500 focus:border-clinical-teal-500"
            placeholder="e.g. 54"
          />
        </div>

        <div>
          <label className="text-xs font-bold text-slate-600 uppercase tracking-wider block mb-1">
            Reported Chief Complaint
          </label>
          <input
            type="text"
            value={chiefComplaint}
            onChange={(e) => setChiefComplaint(e.target.value)}
            className="w-full text-sm p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500 focus:border-clinical-teal-500"
            placeholder="e.g. Acute chest discomfort"
          />
        </div>
      </div>

      {/* Main Recording & Transcription Area */}
      <AudioRecorder
        onTranscriptionComplete={() => {}}
        onSaveDraft={handleSaveDraft}
      />
    </div>
  );
}
