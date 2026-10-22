import React, { useEffect, useState } from "react";
import { Mic, FileText, CheckCircle2, Clock, AlertTriangle, ArrowRight, ShieldCheck, Download, Users, BarChart3 } from "lucide-react";
import { api } from "../services/api";
import { StatusBadge } from "../components/StatusBadge";

export function Dashboard({ onNavigate, onSelectRecord }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [systemHealth, setSystemHealth] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const loadDashboardData = async () => {
      try {
        const [recsRes, healthRes] = await Promise.all([
          api.listRecords({ limit: 10 }),
          api.getHealth()
        ]);
        if (isMounted) {
          setRecords(recsRes.data || []);
          setSystemHealth(healthRes);
        }
      } catch (err) {
        console.error("Dashboard data load error:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    loadDashboardData();
    return () => { isMounted = false; };
  }, []);

  const totalCount = records.length;
  const pendingCount = records.filter(r => r.status === "Needs Review" || r.status === "Draft").length;
  const approvedCount = records.filter(r => r.status === "Approved" || r.status === "Amended").length;

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-clinical-navy-900 to-clinical-teal-900 rounded-2xl p-6 sm:p-8 text-white shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 bg-clinical-teal-500/20 text-clinical-teal-200 px-3 py-1 rounded-full text-xs font-semibold border border-clinical-teal-400/30">
            <ShieldCheck className="w-3.5 h-3.5" />
            100% Offline Pre-Hospital Documentation
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Field-to-Record Assistant
          </h1>
          <p className="text-slate-300 text-sm max-w-xl">
            Voice-to-structured clinical event documentation for first responders. All speech recognition, clinical entity extraction, and report compilation run strictly locally on this device.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => onNavigate("voice")}
            className="flex items-center gap-2 px-5 py-3 rounded-xl bg-clinical-teal-600 hover:bg-clinical-teal-500 text-white font-semibold text-sm shadow-md transition-all active:scale-95"
          >
            <Mic className="w-4 h-4" />
            <span>New Voice Record</span>
          </button>
          <button
            onClick={() => onNavigate("patients")}
            className="flex items-center gap-2 px-4 py-3 rounded-xl bg-clinical-navy-800 hover:bg-clinical-navy-700 text-slate-200 font-semibold text-sm border border-slate-700"
          >
            <Users className="w-4 h-4" />
            <span>Patients</span>
          </button>
          <button
            onClick={() => onNavigate("records")}
            className="flex items-center gap-2 px-4 py-3 rounded-xl bg-clinical-navy-800 hover:bg-clinical-navy-700 text-slate-200 font-semibold text-sm border border-slate-700"
          >
            <FileText className="w-4 h-4" />
            <span>Browse Records</span>
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Records</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{totalCount}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center text-slate-600">
            <FileText className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-amber-200 bg-amber-50/30 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-amber-700 uppercase tracking-wider">Needs Review</p>
            <p className="text-2xl font-bold text-amber-900 mt-1">{pendingCount}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center text-amber-600">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-emerald-200 bg-emerald-50/30 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-emerald-700 uppercase tracking-wider">Approved / Finalized</p>
            <p className="text-2xl font-bold text-emerald-900 mt-1">{approvedCount}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-600">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Backend & Whisper</p>
            <p className="text-sm font-bold text-slate-800 mt-1 flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              {systemHealth?.status === "healthy" ? "Healthy (Offline)" : "Initializing"}
            </p>
            <p className="text-[11px] text-slate-400 mt-0.5">SQLite & Faster-Whisper</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-clinical-teal-50 flex items-center justify-center text-clinical-teal-600">
            <ShieldCheck className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Recent Records Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Recent Field Encounters</h2>
            <p className="text-xs text-slate-500 mt-0.5">First responder field documentations captured locally</p>
          </div>
          <button
            onClick={() => onNavigate("records")}
            className="flex items-center gap-1.5 text-xs font-semibold text-clinical-teal-700 hover:text-clinical-teal-800"
          >
            <span>View All</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm">Loading field records...</div>
        ) : records.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <FileText className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-700">No field records created yet</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Record voice notes or upload field dispatches to automatically extract structured clinical events.
            </p>
            <button
              onClick={() => onNavigate("voice")}
              className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-clinical-teal-600 hover:bg-clinical-teal-700 text-white text-xs font-semibold"
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Create First Record</span>
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 font-semibold text-xs border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3.5">Record ID / Incident</th>
                  <th className="px-6 py-3.5">Date & Time</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Field Narrative Snippet</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {records.map((rec) => (
                  <tr key={rec.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-semibold text-slate-900">{rec.call_number || "EMS Call"}</div>
                      <div className="text-xs font-mono text-slate-400">{rec.id}</div>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-600">
                      {new Date(rec.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={rec.status} />
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-600 max-w-xs truncate">
                      {rec.corrected_transcript || rec.machine_transcript || "No transcript"}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button
                        onClick={() => onSelectRecord(rec.id, "review")}
                        className="px-3 py-1.5 rounded bg-clinical-teal-50 hover:bg-clinical-teal-100 text-clinical-teal-700 text-xs font-semibold transition-colors"
                      >
                        Review
                      </button>
                      <button
                        onClick={() => onSelectRecord(rec.id, "details")}
                        className="px-3 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
                      >
                        Details
                      </button>
                      <a
                        href={api.getPdfUrl(rec.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold"
                        title="Export PDF Report"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>PDF</span>
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
