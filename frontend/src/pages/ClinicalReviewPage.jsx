import React, { useState, useEffect } from "react";
import {
  CheckCircle2, AlertTriangle, ShieldCheck, FileText, ArrowLeft,
  Clock, Download, RefreshCw, XCircle, HelpCircle, Save, Edit2
} from "lucide-react";
import { api } from "../services/api";
import { StatusBadge, SeverityBadge, VerificationBadge } from "../components/StatusBadge";

export function ClinicalReviewPage({ recordId, onBack, onNavigateTimeline }) {
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Editable fields
  const [correctedTranscript, setCorrectedTranscript] = useState("");
  const [clinicalData, setClinicalData] = useState({
    vital_signs: [],
    medications: [],
    symptoms: [],
    procedures: [],
    timestamps: []
  });
  const [warnings, setWarnings] = useState([]);
  const [overrideNotes, setOverrideNotes] = useState("");
  const [showOverrideModal, setShowOverrideModal] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchRecord = async () => {
      try {
        const res = await api.getRecord(recordId);
        if (isMounted && res.success && res.data) {
          const rec = res.data;
          setRecord(rec);
          setCorrectedTranscript(rec.corrected_transcript || rec.machine_transcript || "");
          setClinicalData(rec.clinical_data || {
            vital_signs: [], medications: [], symptoms: [], procedures: [], timestamps: []
          });
          setWarnings(rec.validation_warnings || []);
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load clinical record.");
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchRecord();
    return () => { isMounted = false; };
  }, [recordId]);

  // Re-extract clinical entities from updated transcript
  const handleReExtract = async () => {
    setSaving(true);
    setError(null);
    try {
      const res = await api.extractClinical(correctedTranscript);
      if (res.success && res.data) {
        setClinicalData(res.data.entities);
        setWarnings(res.data.validation_warnings);
        setSuccessMsg("Clinical entities successfully re-extracted from edited transcript.");
      }
    } catch (err) {
      setError(err.message || "Failed to re-extract clinical entities.");
    } finally {
      setSaving(false);
    }
  };

  // Toggle verification state of a vital or medication
  const toggleItemVerification = (category, itemId) => {
    setClinicalData((prev) => {
      const list = prev[category] || [];
      const updated = list.map((item) => {
        if (item.id === itemId) {
          const nextState =
            item.verification_state === "Verified" ? "Rejected" :
            item.verification_state === "Rejected" ? "Uncertain" : "Verified";
          return { ...item, verification_state: nextState };
        }
        return item;
      });
      return { ...prev, [category]: updated };
    });
  };

  // Resolve Ambiguous Medication with selected candidate
  const handleResolveAmbiguity = (medId, chosenCanonical) => {
    setClinicalData((prev) => {
      const updatedMeds = (prev.medications || []).map((m) => {
        if (m.id === medId) {
          return {
            ...m,
            canonical_name: chosenCanonical,
            match_status: "RESOLVED_MANUAL",
            verification_state: "Verified"
          };
        }
        return m;
      });
      return { ...prev, medications: updatedMeds };
    });

    // Mark ambiguity warning as resolved
    setWarnings((prev) =>
      prev.map((w) => (w.item_id === medId ? { ...w, resolved: true } : w))
    );
  };

  // Toggle warning resolved state
  const handleToggleWarningResolved = (warningId) => {
    setWarnings((prev) =>
      prev.map((w) => (w.id === warningId ? { ...w, resolved: !w.resolved } : w))
    );
  };

  // Save changes to backend
  const handleSaveChanges = async (targetStatus = null) => {
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const payload = {
        corrected_transcript: correctedTranscript,
        clinical_data: clinicalData,
        status: targetStatus || record.status,
        review_decisions: {
          resolved_warning_ids: warnings.filter(w => w.resolved).map(w => w.id),
          override_notes: overrideNotes
        }
      };

      const res = await api.updateRecord(recordId, payload);
      if (res.success && res.data) {
        setRecord(res.data);
        setWarnings(res.data.validation_warnings);
        setSuccessMsg("Clinical review progress saved successfully.");
      }
    } catch (err) {
      setError(err.message || "Failed to update record.");
    } finally {
      setSaving(false);
    }
  };

  // Finalize & Approve Record
  const handleApprove = async () => {
    const criticalUnresolved = warnings.filter(
      w => w.severity === "CRITICAL" && !w.resolved
    );

    if (criticalUnresolved.length > 0 && !overrideNotes) {
      setShowOverrideModal(true);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      // First persist current edits
      await handleSaveChanges("Reviewed");

      const res = await api.approveRecord(recordId, {
        reviewer_id: "First Responder / Supervisor",
        override_notes: overrideNotes
      });

      if (res.success && res.data) {
        setRecord(res.data);
        setSuccessMsg("Record officially approved and signed off.");
        setShowOverrideModal(false);
      }
    } catch (err) {
      setError(err.message || "Approval rejected by server.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-slate-500">Loading clinical review...</div>;
  }

  if (!record) {
    return (
      <div className="p-12 text-center text-red-600">
        Record not found or database unreachable.
        <button onClick={onBack} className="block mx-auto mt-4 underline text-sm">
          Return to Dashboard
        </button>
      </div>
    );
  }

  const criticalWarnings = warnings.filter(w => w.severity === "CRITICAL" && !w.resolved);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Navigation & Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700"
            title="Back"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-slate-900">{record.call_number || "Field Record"}</span>
              <StatusBadge status={record.status} />
              {record.version > 1 && (
                <span className="text-xs bg-purple-100 text-purple-800 font-semibold px-2 py-0.5 rounded">
                  v{record.version}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500">
              Encounter ID: <span className="font-mono">{record.id}</span> • Unit: {record.responder_id}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => onNavigateTimeline(record.id)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold"
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Timeline</span>
          </button>
          <a
            href={api.getPdfUrl(record.id)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold"
          >
            <Download className="w-3.5 h-3.5" />
            <span>PDF Report</span>
          </a>
          <button
            onClick={() => handleSaveChanges()}
            disabled={saving || record.status === "Approved"}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-800 text-white text-xs font-semibold disabled:bg-slate-300"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save Progress</span>
          </button>
          {record.status !== "Approved" && (
            <button
              onClick={handleApprove}
              disabled={saving}
              className="flex items-center gap-1.5 px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-md active:scale-95 disabled:bg-slate-300"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Approve Record</span>
            </button>
          )}
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
      {successMsg && (
        <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Critical Warnings Alert Banner */}
      {criticalWarnings.length > 0 && (
        <div className="p-4 rounded-xl bg-red-50 border-2 border-red-300 text-red-900 space-y-2">
          <div className="flex items-center gap-2 font-bold text-sm">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <span>UNRESOLVED CRITICAL VALIDATION WARNINGS ({criticalWarnings.length})</span>
          </div>
          <p className="text-xs text-red-700">
            Field-to-Record enforces clinician review. The following clinical warnings require acknowledgment or correction prior to finalizing:
          </p>
          <ul className="list-disc list-inside text-xs space-y-1 pl-1">
            {criticalWarnings.map((w) => (
              <li key={w.id}>
                <span className="font-semibold">{w.category}: </span>
                {w.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Two-Column Grid: Transcript & Clinical Entities */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Transcript (5 Cols) */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <FileText className="w-4 h-4 text-clinical-teal-600" />
                <span>Field Narrative Transcript</span>
              </h2>
              <button
                onClick={handleReExtract}
                disabled={saving || record.status === "Approved"}
                className="inline-flex items-center gap-1 text-xs text-clinical-teal-700 hover:text-clinical-teal-800 font-semibold"
                title="Re-run regex & NLP entity extraction on edited transcript"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Re-Extract Entities</span>
              </button>
            </div>

            <textarea
              rows={8}
              value={correctedTranscript}
              onChange={(e) => setCorrectedTranscript(e.target.value)}
              disabled={record.status === "Approved"}
              className="w-full p-3 rounded-lg border border-slate-300 text-sm font-sans focus:ring-2 focus:ring-clinical-teal-500 bg-white"
            />

            {record.machine_transcript && record.machine_transcript !== correctedTranscript && (
              <div className="text-xs p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="font-semibold text-slate-600 block mb-1">Original Machine Audio Transcript:</span>
                <p className="font-mono text-slate-500 italic">"{record.machine_transcript}"</p>
              </div>
            )}
          </div>

          {/* Validation Warnings List */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-3">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-slate-600" />
              <span>Safety & Completeness Checks ({warnings.length})</span>
            </h3>

            {warnings.length === 0 ? (
              <p className="text-xs text-emerald-700 bg-emerald-50 p-3 rounded-lg">
                All automated validation rules passed cleanly.
              </p>
            ) : (
              <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                {warnings.map((w) => (
                  <div
                    key={w.id}
                    className={`p-3 rounded-lg border text-xs space-y-1.5 transition-colors ${
                      w.resolved
                        ? "bg-slate-50 border-slate-200 opacity-60"
                        : w.severity === "CRITICAL"
                        ? "bg-red-50/70 border-red-200"
                        : "bg-amber-50/70 border-amber-200"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <SeverityBadge severity={w.severity} />
                      <button
                        onClick={() => handleToggleWarningResolved(w.id)}
                        disabled={record.status === "Approved"}
                        className={`text-[11px] font-semibold px-2 py-0.5 rounded ${
                          w.resolved
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-slate-200 hover:bg-slate-300 text-slate-700"
                        }`}
                      >
                        {w.resolved ? "Acknowledged [OK]" : "Acknowledge"}
                      </button>
                    </div>
                    <p className="font-medium text-slate-800">{w.message}</p>
                    {w.recommendation && (
                      <p className="text-[11px] text-slate-500 italic">Rec: {w.recommendation}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Structured Clinical Cards (7 Cols) */}
        <div className="lg:col-span-7 space-y-5">
          {/* Physiological Vital Signs */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-slate-900">
                Physiological Vital Signs
              </h3>
              <span className="text-xs text-slate-400">Click pill to toggle verification</span>
            </div>

            {clinicalData.vital_signs.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-2">No vital signs extracted from transcript.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {clinicalData.vital_signs.map((v) => (
                  <div key={v.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-700">{v.name}</span>
                      <button
                        onClick={() => toggleItemVerification("vital_signs", v.id)}
                        disabled={record.status === "Approved"}
                        title="Click to toggle: Extracted -> Verified -> Rejected -> Uncertain"
                      >
                        <VerificationBadge state={v.verification_state || "Extracted"} />
                      </button>
                    </div>
                    <div className="text-lg font-bold text-clinical-teal-800 font-mono">
                      {v.value} <span className="text-xs font-normal text-slate-500">{v.unit}</span>
                    </div>
                    {v.source_phrase && (
                      <div className="text-[11px] text-slate-400 truncate italic">
                        Evidence: "{v.source_phrase}"
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Medications & Interventions */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-slate-900">
                Medications Administered & Assessed
              </h3>
              <span className="text-xs text-slate-400">Verified catalogue match</span>
            </div>

            {clinicalData.medications.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-2">No medication mentions detected.</p>
            ) : (
              <div className="space-y-3">
                {clinicalData.medications.map((m) => (
                  <div
                    key={m.id}
                    className={`p-3.5 rounded-lg border space-y-2 ${
                      m.match_status === "AMBIGUOUS"
                        ? "bg-amber-50/60 border-amber-300"
                        : "bg-slate-50 border-slate-200"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-slate-900">
                            {m.canonical_name || m.raw_mention}
                          </span>
                          {m.is_negated ? (
                            <span className="bg-rose-100 text-rose-800 text-[10px] font-bold px-2 py-0.5 rounded">
                              WITHHELD / DENIED
                            </span>
                          ) : (
                            <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded">
                              ADMINISTERED
                            </span>
                          )}
                          {m.pediatric_warning && (
                            <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-1.5 py-0.5 rounded">
                              Peds Warning
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Mentioned as: "{m.raw_mention}" • Dose: {m.dosage || "N/A"} {m.unit || ""} • Route: {m.route || "N/A"}
                        </p>
                      </div>

                      <button
                        onClick={() => toggleItemVerification("medications", m.id)}
                        disabled={record.status === "Approved"}
                      >
                        <VerificationBadge state={m.verification_state || "Extracted"} />
                      </button>
                    </div>

                    {/* Ambiguity Resolution Selector */}
                    {m.match_status === "AMBIGUOUS" && m.candidates && (
                      <div className="p-2.5 bg-amber-100/70 rounded border border-amber-300 text-xs space-y-1.5">
                        <span className="font-semibold text-amber-900 block">
                          Ambiguous Term: Select verified medication to commit:
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {m.candidates.map((cand) => (
                            <button
                              key={cand.canonical_name}
                              onClick={() => handleResolveAmbiguity(m.id, cand.canonical_name)}
                              className="px-2.5 py-1 bg-white hover:bg-clinical-teal-50 text-slate-800 border border-amber-300 hover:border-clinical-teal-500 rounded font-semibold text-xs shadow-sm"
                            >
                              Confirm {cand.canonical_name} ({cand.score}%)
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="text-[11px] text-slate-400">
                      Provenance: {m.provenance || "Local Catalogue"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Symptoms & Pertinent Negatives */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-3">
            <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
              Clinical Symptoms & Negative Findings
            </h3>

            {clinicalData.symptoms.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-2">No symptoms extracted.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {clinicalData.symptoms.map((s) => (
                  <span
                    key={s.id}
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${
                      s.is_negated
                        ? "bg-slate-100 text-slate-700 border-slate-300 line-through"
                        : "bg-teal-50 text-teal-800 border-teal-200"
                    }`}
                  >
                    {s.is_negated && <span className="no-underline text-rose-600 font-bold">DENIED:</span>}
                    <span>{s.symptom}</span>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Procedures & Interventions */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-3">
            <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
              Interventions & Procedures
            </h3>

            {clinicalData.procedures.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-2">No procedures extracted.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {clinicalData.procedures.map((p) => (
                  <span
                    key={p.id}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-clinical-navy-50 text-clinical-navy-800 border border-slate-300"
                  >
                    <span>{p.procedure}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Clinician Override Modal for Critical Warnings */}
      {showOverrideModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-red-600 font-bold text-base">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <span>Clinician Override Required</span>
            </div>
            <p className="text-xs text-slate-600">
              There are {criticalWarnings.length} unresolved critical warnings on this record.
              To approve this record, medical protocol requires an explicit clinician override explanation:
            </p>
            <textarea
              rows={3}
              value={overrideNotes}
              onChange={(e) => setOverrideNotes(e.target.value)}
              placeholder="e.g. Critical values confirmed accurate on scene with manual sphygmomanometer; medication verbally confirmed by medical control..."
              className="w-full p-3 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-red-500"
            />
            <div className="flex justify-end gap-2.5 pt-2">
              <button
                onClick={() => setShowOverrideModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleApprove}
                disabled={!overrideNotes.trim()}
                className="px-5 py-2 rounded-lg bg-red-600 hover:bg-red-700 disabled:bg-slate-300 text-white text-xs font-semibold shadow-md"
              >
                Submit Override & Finalize
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
