import React, { useState, useEffect } from "react";
import {
  FileText, ArrowLeft, Download, ShieldCheck, Clock, User,
  Volume2, AlertTriangle, Edit3, CheckCircle2, History
} from "lucide-react";
import { api } from "../services/api";
import { StatusBadge, VerificationBadge } from "../components/StatusBadge";

export function RecordDetailsPage({ recordId, onBack, onNavigateReview, onNavigateTimeline }) {
  const [record, setRecord] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAmendModal, setShowAmendModal] = useState(false);
  const [amendReason, setAmendReason] = useState("");
  const [amendText, setAmendText] = useState("");
  const [isSubmittingAmend, setIsSubmittingAmend] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const loadDetails = async () => {
      try {
        const [recRes, auditRes] = await Promise.all([
          api.getRecord(recordId),
          api.getAuditTrail(recordId)
        ]);
        if (isMounted) {
          if (recRes.success && recRes.data) {
            setRecord(recRes.data);
            setAmendText(recRes.data.corrected_transcript || recRes.data.machine_transcript || "");
          }
          if (auditRes.success && auditRes.data) {
            setAuditLogs(auditRes.data);
          }
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load record details.");
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    loadDetails();
    return () => { isMounted = false; };
  }, [recordId]);

  const handleAmendSubmit = async () => {
    if (!amendReason.trim()) {
      alert("A clear clinical reason for amendment is mandatory.");
      return;
    }

    setIsSubmittingAmend(true);
    try {
      const res = await api.amendRecord(recordId, {
        reason: amendReason,
        corrected_transcript: amendText,
        clinical_data: record.clinical_data // Can be further updated in review
      });

      if (res.success && res.data) {
        setRecord(res.data);
        setShowAmendModal(false);
        setAmendReason("");
        // Reload audit trail
        const auditRes = await api.getAuditTrail(recordId);
        if (auditRes.success) setAuditLogs(auditRes.data);
      }
    } catch (err) {
      alert(err.message || "Failed to submit amendment.");
    } finally {
      setIsSubmittingAmend(false);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-slate-500">Loading record details...</div>;
  }

  if (!record) {
    return (
      <div className="p-12 text-center text-red-600">
        Record not found.
        <button onClick={onBack} className="block mx-auto mt-4 text-xs underline">Back</button>
      </div>
    );
  }

  const clinical = record.clinical_data || {};
  const audioUrl = api.getAudioUrl(record.audio_filename);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900">{record.call_number || "Field Record"}</h1>
              <StatusBadge status={record.status} />
              {record.version > 1 && (
                <span className="text-xs bg-purple-100 text-purple-800 font-bold px-2 py-0.5 rounded">
                  Version {record.version} (Amended)
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 font-mono mt-0.5">{record.id}</p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => onNavigateTimeline(record.id)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold"
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Timeline</span>
          </button>
          <button
            onClick={() => onNavigateReview(record.id)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-clinical-teal-50 hover:bg-clinical-teal-100 text-clinical-teal-700 text-xs font-semibold"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Clinical Review</span>
          </button>
          {record.status === "Approved" && (
            <button
              onClick={() => setShowAmendModal(true)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-purple-50 hover:bg-purple-100 text-purple-800 text-xs font-semibold"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Amend Record</span>
            </button>
          )}
          <a
            href={api.getPdfUrl(record.id)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-clinical-teal-600 hover:bg-clinical-teal-700 text-white text-xs font-semibold shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Official PDF</span>
          </a>
        </div>
      </div>

      {/* Audio Playback Box (if recording preserved) */}
      {audioUrl && (
        <div className="bg-slate-900 text-white p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center gap-3">
            <Volume2 className="w-5 h-5 text-clinical-teal-400" />
            <div>
              <p className="text-sm font-semibold">Preserved Field Audio Recording</p>
              <p className="text-xs text-slate-400 font-mono">
                {record.audio_filename} • {record.audio_duration_seconds}s
              </p>
            </div>
          </div>
          <audio controls src={audioUrl} className="h-8 max-w-xs w-full" />
        </div>
      )}

      {/* Field Narrative Card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-3">
        <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
          <FileText className="w-4 h-4 text-clinical-teal-600" />
          <span>Final Verified Clinical Narrative</span>
        </h2>
        <div className="p-4 bg-slate-50 rounded-lg text-slate-800 text-sm whitespace-pre-wrap font-sans border border-slate-200">
          {record.corrected_transcript || record.machine_transcript || "No transcript recorded"}
        </div>
      </div>

      {/* Extracted Clinical Data Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Vitals */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-3">
          <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
            Recorded Vitals
          </h3>
          {clinical.vital_signs?.length > 0 ? (
            <div className="space-y-2">
              {clinical.vital_signs.map((v) => (
                <div key={v.id} className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg text-xs">
                  <span className="font-semibold text-slate-700">{v.name}</span>
                  <span className="font-bold text-clinical-teal-800 font-mono text-sm">
                    {v.value} {v.unit}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">No vitals captured.</p>
          )}
        </div>

        {/* Medications */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-3">
          <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
            Medications Administered
          </h3>
          {clinical.medications?.length > 0 ? (
            <div className="space-y-2">
              {clinical.medications.map((m) => (
                <div key={m.id} className="p-2.5 bg-slate-50 rounded-lg text-xs flex items-center justify-between">
                  <div>
                    <span className="font-bold text-slate-800">{m.canonical_name || m.raw_mention}</span>
                    <span className="text-slate-500 ml-2">
                      {m.dosage || ""} {m.unit || ""} {m.route ? `via ${m.route}` : ""}
                    </span>
                  </div>
                  <span className={m.is_negated ? "text-rose-600 font-bold" : "text-emerald-700 font-bold"}>
                    {m.is_negated ? "WITHHELD" : "ADMINISTERED"}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">No medications recorded.</p>
          )}
        </div>
      </div>

      {/* Immutable Audit Trail Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
          <History className="w-4 h-4 text-clinical-teal-600" />
          <span>Immutable Traceability & Audit Log ({auditLogs.length})</span>
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="px-4 py-2.5">Timestamp (UTC)</th>
                <th className="px-4 py-2.5">Action</th>
                <th className="px-4 py-2.5">Actor</th>
                <th className="px-4 py-2.5">Payload Diff / Event Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 font-mono">
              {auditLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50/60">
                  <td className="px-4 py-2.5 text-slate-500 whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5 font-bold text-slate-800">{log.action}</td>
                  <td className="px-4 py-2.5 text-clinical-teal-700 font-semibold">{log.actor}</td>
                  <td className="px-4 py-2.5 text-slate-600 max-w-sm truncate">
                    {JSON.stringify(log.details)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Amendment Modal */}
      {showAmendModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Edit3 className="w-5 h-5 text-purple-600" />
              <span>Traceable Clinical Record Amendment</span>
            </h3>
            <p className="text-xs text-slate-600">
              Approved medical records cannot be overwritten silently. Any amendment creates a new version (v{record.version + 1}) and logs an immutable audit trail entry.
            </p>

            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700 uppercase">Reason for Amendment (Mandatory)</label>
              <input
                type="text"
                value={amendReason}
                onChange={(e) => setAmendReason(e.target.value)}
                placeholder="e.g. Added secondary vital signs recorded by triage..."
                className="w-full p-2.5 rounded-lg border border-slate-300 text-xs focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700 uppercase">Updated Narrative</label>
              <textarea
                rows={4}
                value={amendText}
                onChange={(e) => setAmendText(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-slate-300 text-xs focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="flex justify-end gap-2.5 pt-2">
              <button
                onClick={() => setShowAmendModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleAmendSubmit}
                disabled={isSubmittingAmend || !amendReason.trim()}
                className="px-5 py-2 rounded-lg bg-purple-700 hover:bg-purple-800 disabled:bg-slate-300 text-white text-xs font-semibold shadow-md"
              >
                {isSubmittingAmend ? "Submitting..." : "Submit Amendment"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
