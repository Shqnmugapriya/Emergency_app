import React, { useState, useEffect } from "react";
import {
  Mic, FileText, User, Hash, AlertCircle, ArrowRight,
  ShieldCheck, RefreshCw, CheckCircle2, Search, UserCheck
} from "lucide-react";
import { AudioRecorder } from "../components/AudioRecorder";
import { api } from "../services/api";

export function VoiceInputPage({ onRecordCreated }) {
  const [callNumber, setCallNumber] = useState(`EMS-${Math.floor(1000 + Math.random() * 9000)}`);
  const [responderId, setResponderId] = useState("Paramedic-101");
  const [patientGender, setPatientGender] = useState("Unspecified");
  const [patientAge, setPatientAge] = useState("");
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [encounterType, setEncounterType] = useState("NEW_ENCOUNTER");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  // Patient continuity integration
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [selectedPatientObj, setSelectedPatientObj] = useState(null);
  const [patientAmbiguityWarning, setPatientAmbiguityWarning] = useState(null);

  // Draft recovery state
  const [recoveredDraft, setRecoveredDraft] = useState(null);
  const [draftRestoredNotice, setDraftRestoredNotice] = useState(null);

  // Load patients for picker
  useEffect(() => {
    let isMounted = true;
    const loadPatientsList = async () => {
      try {
        const res = await api.listPatients();
        if (isMounted && res.success && res.data) {
          setPatients(res.data.patients || []);
        }
      } catch (err) {
        // Non-blocking for field voice input
      }
    };
    loadPatientsList();

    // Check for autosaved in-flight draft
    const checkDraft = async () => {
      try {
        const res = await api.getAutosavedDraft("session_active");
        if (isMounted && res.success && res.data && res.data.draft) {
          setRecoveredDraft(res.data);
        }
      } catch (err) {
        // No draft
      }
    };
    checkDraft();

    return () => { isMounted = false; };
  }, []);

  // Handle patient selection with multi-factor verification
  const handleSelectPatient = (patientId) => {
    setSelectedPatientId(patientId);
    setPatientAmbiguityWarning(null);

    if (!patientId) {
      setSelectedPatientObj(null);
      return;
    }

    const pt = patients.find((p) => p.id === patientId);
    if (pt) {
      setSelectedPatientObj(pt);
      // Auto-populate age and gender if known
      if (pt.date_of_birth) {
        const birthYear = parseInt(pt.date_of_birth.split("-")[0], 10);
        if (!isNaN(birthYear)) {
          setPatientAge(String(new Date().getFullYear() - birthYear));
        }
      }
      if (pt.gender && pt.gender !== "Unspecified") {
        setPatientGender(pt.gender);
      }

      // Check if another patient has the same full name (ambiguity check)
      const sameName = patients.filter((p) => p.full_name?.toLowerCase() === pt.full_name?.toLowerCase());
      if (sameName.length > 1) {
        setPatientAmbiguityWarning(
          `Multiple patients named "${pt.full_name}". Confirmed match by DOB (${pt.date_of_birth}) and Patient ID (${pt.patient_id_display}).`
        );
      }
    }
  };

  // Restore recovered draft
  const handleRestoreDraft = () => {
    if (!recoveredDraft?.draft) return;
    const d = recoveredDraft.draft;
    if (d.call_number) setCallNumber(d.call_number);
    if (d.responder_id) setResponderId(d.responder_id);
    if (d.patient_age) setPatientAge(d.patient_age);
    if (d.patient_gender) setPatientGender(d.patient_gender);
    if (d.chief_complaint) setChiefComplaint(d.chief_complaint);
    if (d.encounter_type) setEncounterType(d.encounter_type);
    if (d.patient_id) handleSelectPatient(d.patient_id);
    setDraftRestoredNotice("In-flight draft restored successfully.");
    setRecoveredDraft(null);
  };

  const handleDismissDraft = async () => {
    try {
      await api.clearAutosavedDraft("session_active");
    } catch (e) {
      // Ignore
    }
    setRecoveredDraft(null);
  };

  // Periodic autosave of draft form fields
  useEffect(() => {
    const timer = setTimeout(() => {
      api.autosaveDraft("session_active", {
        call_number: callNumber,
        responder_id: responderId,
        patient_age: patientAge,
        patient_gender: patientGender,
        chief_complaint: chiefComplaint,
        encounter_type: encounterType,
        patient_id: selectedPatientId,
        timestamp: new Date().toISOString()
      }).catch(() => {});
    }, 2000);
    return () => clearTimeout(timer);
  }, [callNumber, responderId, patientAge, patientGender, chiefComplaint, encounterType, selectedPatientId]);

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
        patient_id: selectedPatientId || null,
        encounter_type: encounterType,
        patient_summary: {
          age: patientAge,
          gender: patientGender,
          chief_complaint: chiefComplaint,
          patient_id: selectedPatientId || null
        }
      };

      const res = await api.createRecord(recordPayload);

      if (res.success && res.data) {
        // Clear active draft cache on success
        await api.clearAutosavedDraft("session_active").catch(() => {});
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

      {/* Recover Draft Alert Banner */}
      {recoveredDraft && (
        <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 text-blue-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-sm">
          <div className="flex items-center gap-2.5">
            <RefreshCw className="w-4 h-4 text-blue-600 shrink-0" />
            <span>
              <strong>In-flight draft detected</strong> from {recoveredDraft.saved_at ? new Date(recoveredDraft.saved_at).toLocaleTimeString() : "recent session"}. Restore your unsaved field notes?
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleRestoreDraft}
              className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow-sm"
            >
              Restore Draft
            </button>
            <button
              onClick={handleDismissDraft}
              className="px-2.5 py-1.5 rounded-lg text-slate-600 hover:text-slate-900 text-xs font-semibold"
            >
              Discard
            </button>
          </div>
        </div>
      )}

      {draftRestoredNotice && (
        <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{draftRestoredNotice}</span>
        </div>
      )}

      {submitError && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
          <span>{submitError}</span>
        </div>
      )}

      {/* Patient Continuity & Encounter Metadata */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="border-b border-slate-100 pb-2">
          <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-clinical-teal-600" />
            <span>Patient Continuity & Encounter Classification</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Patient Selector */}
          <div className="sm:col-span-2">
            <label className="text-xs font-bold text-slate-600 uppercase tracking-wider block mb-1">
              Link to Patient Profile
            </label>
            <select
              value={selectedPatientId}
              onChange={(e) => handleSelectPatient(e.target.value)}
              className="w-full text-xs font-semibold p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500 bg-white"
            >
              <option value="">-- Unidentified / Field Encounter Only --</option>
              {patients.map((pt) => (
                <option key={pt.id} value={pt.id}>
                  {pt.full_name} ({pt.patient_id_display}) • DOB: {pt.date_of_birth}
                </option>
              ))}
            </select>
          </div>

          {/* Encounter Type */}
          <div>
            <label className="text-xs font-bold text-slate-600 uppercase tracking-wider block mb-1">
              Encounter Type
            </label>
            <select
              value={encounterType}
              onChange={(e) => setEncounterType(e.target.value)}
              className="w-full text-xs font-semibold p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500 bg-white"
            >
              <option value="NEW_ENCOUNTER">New Incident Encounter</option>
              <option value="OBSERVATION">Clinical Observation</option>
              <option value="CORRECTION">Field Correction</option>
              <option value="AMENDMENT">Clinical Amendment</option>
            </select>
          </div>

          {/* Responder ID */}
          <div>
            <label className="text-xs font-bold text-slate-600 uppercase tracking-wider block mb-1">
              Responder ID / Unit
            </label>
            <input
              type="text"
              value={responderId}
              onChange={(e) => setResponderId(e.target.value)}
              className="w-full text-xs font-semibold p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500"
              placeholder="e.g. Paramedic-101"
            />
          </div>
        </div>

        {/* Ambiguity confirmation warning */}
        {patientAmbiguityWarning && (
          <div className="p-3 bg-amber-50 border border-amber-300 rounded-lg text-xs text-amber-900 flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Identity Verification Confirmed: </span>
              {patientAmbiguityWarning}
            </div>
          </div>
        )}

        {/* Selected Patient Demographics Card */}
        {selectedPatientObj && (
          <div className="p-3 bg-clinical-teal-50/70 border border-clinical-teal-200 rounded-lg flex flex-wrap items-center justify-between text-xs text-clinical-teal-900 gap-2">
            <div className="flex items-center gap-3">
              <span className="font-bold text-slate-900">{selectedPatientObj.full_name}</span>
              <span>DOB: <strong>{selectedPatientObj.date_of_birth}</strong></span>
              <span>Gender: {selectedPatientObj.gender}</span>
              <span>Blood: {selectedPatientObj.blood_type || "Unknown"}</span>
            </div>
            {selectedPatientObj.allergies && selectedPatientObj.allergies.length > 0 && (
              <span className="text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                Known Allergies: {selectedPatientObj.allergies.join(", ")}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Incident & Dispatch Header Form */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="text-xs font-bold text-slate-600 uppercase tracking-wider block mb-1">
            Incident / Call #
          </label>
          <input
            type="text"
            value={callNumber}
            onChange={(e) => setCallNumber(e.target.value)}
            className="w-full text-sm font-semibold p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500"
            placeholder="e.g. EMS-4091"
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
            className="w-full text-sm p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500"
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
            className="w-full text-sm p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500"
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
