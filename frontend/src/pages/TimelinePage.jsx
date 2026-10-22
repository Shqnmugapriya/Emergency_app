import React, { useEffect, useState } from "react";
import { Clock, ArrowLeft, Mic, Cpu, CheckCircle, AlertTriangle, Download, Calendar } from "lucide-react";
import { api } from "../services/api";
import { StatusBadge } from "../components/StatusBadge";

export function TimelinePage({ recordId, onBack, onNavigateReview }) {
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const fetchTimelineData = async () => {
      try {
        const res = await api.getRecord(recordId);
        if (isMounted && res.success && res.data) {
          setRecord(res.data);
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load record timeline.");
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchTimelineData();
    return () => { isMounted = false; };
  }, [recordId]);

  if (loading) {
    return <div className="p-12 text-center text-slate-500">Compiling chronological timeline...</div>;
  }

  if (!record) {
    return (
      <div className="p-12 text-center text-red-600">
        Record not found.
        <button onClick={onBack} className="block mx-auto mt-4 text-xs underline">Back</button>
      </div>
    );
  }

  // Construct milestone timeline items
  const milestones = [
    {
      title: "Audio Captured in Field",
      type: "recording",
      icon: Mic,
      color: "bg-teal-500 text-white",
      time: record.recording_time || record.created_at,
      details: `Field recording created by ${record.responder_id}. Duration: ${record.audio_duration_seconds || 0} seconds.`
    },
    {
      title: "Speech-to-Text Transcription",
      type: "transcription",
      icon: Cpu,
      color: "bg-indigo-500 text-white",
      time: record.transcription_time || record.created_at,
      details: `Processed locally by faster-whisper (${record.transcription_metadata?.model_used || "base"}). Language: ${record.transcription_metadata?.language || "en"}.`
    },
    {
      title: "Clinical Entity Extraction & Validation",
      type: "validation",
      icon: AlertTriangle,
      color: "bg-amber-500 text-white",
      time: record.updated_at || record.created_at,
      details: `${record.clinical_data?.vital_signs?.length || 0} vitals, ${record.clinical_data?.medications?.length || 0} medications extracted. ${record.validation_warnings?.length || 0} validation checks performed.`
    },
    {
      title: "Clinician Verification & Review",
      type: "review",
      icon: CheckCircle,
      color: record.reviewed_at ? "bg-emerald-500 text-white" : "bg-slate-300 text-slate-600",
      time: record.reviewed_at || "Pending Clinician Review",
      details: record.reviewed_at ? "Human verified clinical findings and acknowledged warnings." : "Encounter awaiting clinical confirmation."
    },
    {
      title: "Final Approval & Signature",
      type: "approval",
      icon: CheckCircle,
      color: record.approved_at ? "bg-emerald-600 text-white" : "bg-slate-300 text-slate-600",
      time: record.approved_at || "Pending Final Approval",
      details: record.approved_at ? `Record finalized and locked as version ${record.version}.` : "Pending final supervisory approval."
    }
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900">Encounter Timeline</h1>
              <StatusBadge status={record.status} />
            </div>
            <p className="text-xs text-slate-500">Incident: {record.call_number} • ID: {record.id}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigateReview(record.id)}
            className="px-3 py-2 rounded-lg bg-clinical-teal-600 hover:bg-clinical-teal-700 text-white text-xs font-semibold"
          >
            Review Clinical Data
          </button>
          <a
            href={api.getPdfUrl(record.id)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold"
          >
            <Download className="w-3.5 h-3.5" />
            <span>PDF</span>
          </a>
        </div>
      </div>

      {/* Timeline Card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 sm:p-8">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-8 flex items-center gap-2">
          <Calendar className="w-4 h-4 text-clinical-teal-600" />
          <span>Chronological Provenance & Audit Milestones</span>
        </h2>

        <div className="relative border-l-2 border-slate-200 ml-4 sm:ml-6 space-y-8 pb-4">
          {milestones.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div key={idx} className="relative pl-6 sm:pl-8 group">
                {/* Node icon */}
                <div className={`absolute -left-3.5 top-0 w-7 h-7 rounded-full flex items-center justify-center shadow-md ${item.color}`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>

                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 hover:border-slate-300 transition-colors">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <span className="font-bold text-sm text-slate-800">{item.title}</span>
                    <span className="text-xs font-mono text-slate-500">
                      {item.time ? (item.time.includes("T") ? new Date(item.time).toLocaleString() : item.time) : "N/A"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-2">{item.details}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
