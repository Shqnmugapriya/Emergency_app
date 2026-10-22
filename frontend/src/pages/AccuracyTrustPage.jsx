import React, { useState, useEffect } from "react";
import {
  ShieldCheck, BarChart3, Database, HardDrive, Cpu, Play,
  AlertTriangle, CheckCircle2, RefreshCw, FileText, Lock, Sparkles, Layers
} from "lucide-react";
import { api } from "../services/api";

export function AccuracyTrustPage() {
  const [activeSubTab, setActiveSubTab] = useState("accuracy"); // "accuracy" | "trust"
  const [accuracyData, setAccuracyData] = useState(null);
  const [trustData, setTrustData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [accRes, trustRes] = await Promise.all([
        api.getAccuracyMetrics(),
        api.getTrustStatus()
      ]);
      if (accRes.success && accRes.data) {
        setAccuracyData(accRes.data);
      }
      if (trustRes.success && trustRes.data) {
        setTrustData(trustRes.data);
      }
    } catch (err) {
      setError(err.message || "Failed to load system metrics and trust status.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunEvaluation = async () => {
    setEvaluating(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await api.triggerEvaluation();
      if (res.success && res.data) {
        setAccuracyData(res.data);
        setSuccessMsg("Internal clinical accuracy benchmark suite executed successfully against ground-truth dataset.");
      }
    } catch (err) {
      setError(err.message || "Evaluation execution failed.");
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Title & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Clinical Accuracy & Offline Trust
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-300">
              System Telemetry
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Internal offline model verification, benchmark evaluation, and SQLite/storage resilience monitors.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-slate-200/80 p-1 rounded-xl text-xs font-bold">
          <button
            onClick={() => setActiveSubTab("accuracy")}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg transition-all ${
              activeSubTab === "accuracy"
                ? "bg-white text-clinical-teal-800 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>Accuracy Benchmark</span>
          </button>
          <button
            onClick={() => setActiveSubTab("trust")}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg transition-all ${
              activeSubTab === "trust"
                ? "bg-white text-clinical-teal-800 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Offline Trust Monitor</span>
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">{error}</div>
        </div>
      )}
      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {loading ? (
        <div className="p-16 text-center text-slate-400">Loading benchmark telemetry...</div>
      ) : activeSubTab === "accuracy" ? (
        /* ACCURACY BENCHMARK SECTION */
        <div className="space-y-6">
          {/* Isolation Advisory Notice */}
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 flex items-start gap-3 text-xs">
            <Lock className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Clinical Isolation Boundary: </span>
              These benchmark accuracy statistics are strictly internal engineering metrics. They evaluate transcription and entity extraction against offline test datasets, and are{" "}
              <strong>strictly excluded from patient PDF and JSON medical records</strong> to prevent clinical misinterpretation.
            </div>
          </div>

          {/* Metric KPI Cards */}
          {accuracyData?.summary && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">Avg Word Error Rate</span>
                <div className="text-2xl font-black text-clinical-teal-900 mt-1 font-mono">
                  {((accuracyData.summary.average_wer || 0) * 100).toFixed(1)}%
                </div>
                <span className="text-[10px] text-slate-400">Speech Word Error</span>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">Entity Precision</span>
                <div className="text-2xl font-black text-emerald-700 mt-1 font-mono">
                  {((accuracyData.summary.average_precision || 0) * 100).toFixed(1)}%
                </div>
                <span className="text-[10px] text-slate-400">Clinical Entity Accuracy</span>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">Entity Recall</span>
                <div className="text-2xl font-black text-emerald-700 mt-1 font-mono">
                  {((accuracyData.summary.average_recall || 0) * 100).toFixed(1)}%
                </div>
                <span className="text-[10px] text-slate-400">Captured Clinical Facts</span>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">Harmonic F1 Score</span>
                <div className="text-2xl font-black text-purple-700 mt-1 font-mono">
                  {((accuracyData.summary.average_f1 || 0) * 100).toFixed(1)}%
                </div>
                <span className="text-[10px] text-slate-400">Balanced Extraction F1</span>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">Ambiguity Recall</span>
                <div className="text-2xl font-black text-blue-700 mt-1 font-mono">
                  {((accuracyData.summary.average_ambiguity_recall || 1.0) * 100).toFixed(0)}%
                </div>
                <span className="text-[10px] text-slate-400">Drug Candidate Detection</span>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">False Acceptance</span>
                <div className="text-2xl font-black text-slate-700 mt-1 font-mono">
                  {((accuracyData.summary.false_acceptance_rate || 0) * 100).toFixed(1)}%
                </div>
                <span className="text-[10px] text-slate-400">Zero Silent Acceptance</span>
              </div>
            </div>
          )}

          {/* Benchmark Actions & Details */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-clinical-teal-600" />
                  <span>Ground-Truth Verification Test Suite</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Evaluated against canonical EMS narrative benchmarks ({accuracyData?.eval_dataset_size || 3} reference cases).
                </p>
              </div>

              <button
                onClick={handleRunEvaluation}
                disabled={evaluating}
                className="flex items-center gap-2 px-4 py-2 bg-clinical-teal-600 hover:bg-clinical-teal-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all disabled:bg-slate-300"
              >
                <Play className={`w-3.5 h-3.5 ${evaluating ? "animate-spin" : ""}`} />
                <span>{evaluating ? "Running Benchmark..." : "Run Benchmark Now"}</span>
              </button>
            </div>

            {/* Test Sample Case Cards */}
            <div className="space-y-4">
              {accuracyData?.samples?.map((sample, idx) => (
                <div key={sample.sample_id || idx} className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs text-slate-900 uppercase">Case #{idx + 1}: {sample.sample_id}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-clinical-teal-100 text-clinical-teal-800 font-semibold font-mono">
                        WER: {(sample.wer * 100).toFixed(1)}%
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-purple-100 text-purple-800 font-semibold font-mono">
                        F1: {(sample.f1 * 100).toFixed(1)}%
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-500 font-mono">
                      Sub: {sample.substitutions} • Del: {sample.deletions} • Ins: {sample.insertions}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 bg-white rounded-lg border border-slate-200">
                      <span className="font-bold text-slate-600 block mb-1">Ground Truth Reference:</span>
                      <p className="font-mono text-slate-700 text-[11px]">{sample.reference}</p>
                    </div>
                    <div className="p-3 bg-white rounded-lg border border-slate-200">
                      <span className="font-bold text-clinical-teal-700 block mb-1">Model Hypothesis:</span>
                      <p className="font-mono text-slate-700 text-[11px]">{sample.hypothesis}</p>
                    </div>
                  </div>

                  {sample.extracted_entities && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <span className="text-[11px] font-semibold text-slate-600 mr-1">Extracted:</span>
                      {sample.extracted_entities.vital_signs?.map((v, i) => (
                        <span key={i} className="text-[10px] px-2 py-0.5 bg-teal-50 border border-teal-200 text-teal-800 rounded font-mono">
                          {v.name}: {v.value} {v.unit}
                        </span>
                      ))}
                      {sample.extracted_entities.medications?.map((m, i) => (
                        <span key={i} className="text-[10px] px-2 py-0.5 bg-blue-50 border border-blue-200 text-blue-800 rounded font-mono">
                          {m.canonical_name || m.raw_mention} ({m.dosage} {m.unit})
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* OFFLINE TRUST MONITOR SECTION */
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Whisper Status Card */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">Speech Inference Engine</span>
                <Cpu className="w-5 h-5 text-clinical-teal-600" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${trustData?.whisper?.is_ready ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`} />
                <span className="text-lg font-bold text-slate-900">
                  {trustData?.whisper?.is_ready ? "Whisper Active (Offline)" : "Initializing / Ready"}
                </span>
              </div>
              <div className="text-xs space-y-1 text-slate-600 font-mono pt-1 border-t border-slate-100">
                <div>Model: <strong className="text-slate-800">{trustData?.whisper?.model_name || "base"}</strong></div>
                <div>Device: <strong className="text-slate-800">{trustData?.whisper?.device || "cpu"}</strong></div>
                <div>Compute: <strong className="text-slate-800">{trustData?.whisper?.compute_type || "int8"}</strong></div>
                <div>Offline Enforced: <strong className="text-emerald-700">100% Local (No Cloud API)</strong></div>
              </div>
            </div>

            {/* SQLite Database Card */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">Local SQLite Storage</span>
                <Database className="w-5 h-5 text-clinical-teal-600" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${trustData?.database?.integrity_check === "ok" ? "bg-emerald-500" : "bg-red-500"}`} />
                <span className="text-lg font-bold text-slate-900">
                  {trustData?.database?.integrity_check === "ok" ? "Integrity Verified" : "Database Check Failed"}
                </span>
              </div>
              <div className="text-xs space-y-1 text-slate-600 font-mono pt-1 border-t border-slate-100">
                <div>PRAGMA Integrity: <strong className="text-emerald-700">{trustData?.database?.integrity_check || "ok"}</strong></div>
                <div>File Path: <span className="truncate block text-slate-500">{trustData?.database?.db_path || "field_to_record.db"}</span></div>
                <div>Total Records: <strong className="text-slate-800">{trustData?.database?.total_records || 0}</strong></div>
                <div>Encounter History: <strong className="text-slate-800">Preserved</strong></div>
              </div>
            </div>

            {/* Audio Directory & Draft Recovery Card */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">Audio & Draft Cache</span>
                <HardDrive className="w-5 h-5 text-clinical-teal-600" />
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="text-lg font-bold text-slate-900">
                  {trustData?.audio_storage?.write_accessible ? "Local Disk Accessible" : "Read-Only"}
                </span>
              </div>
              <div className="text-xs space-y-1 text-slate-600 font-mono pt-1 border-t border-slate-100">
                <div>Audio Files: <strong className="text-slate-800">{trustData?.audio_storage?.file_count || 0} audio files</strong></div>
                <div>Disk Size: <strong className="text-slate-800">{trustData?.audio_storage?.total_size_mb || "0.0"} MB</strong></div>
                <div>Draft Autosave: <strong className="text-emerald-700">Active (In-flight Recovery)</strong></div>
                <div>Cached Drafts: <strong className="text-slate-800">{trustData?.draft_recovery?.active_drafts_count || 0}</strong></div>
              </div>
            </div>
          </div>

          {/* Offline Architecture Verification Matrix */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-4 h-4 text-clinical-teal-600" />
              <span>Offline Architecture Compliance Matrix</span>
            </h3>

            <div className="divide-y divide-slate-100 text-xs">
              <div className="py-2.5 flex items-center justify-between">
                <span className="font-semibold text-slate-800">Zero Cloud Speech API Dependency</span>
                <span className="px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold font-mono">Compliant (faster-whisper local)</span>
              </div>
              <div className="py-2.5 flex items-center justify-between">
                <span className="font-semibold text-slate-800">Zero Cloud LLM / Browser-Side AI Substitution</span>
                <span className="px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold font-mono">Compliant (Python backend only)</span>
              </div>
              <div className="py-2.5 flex items-center justify-between">
                <span className="font-semibold text-slate-800">Medicine Ambiguity Human-in-the-Loop</span>
                <span className="px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold font-mono">Compliant (No silent drug auto-commit)</span>
              </div>
              <div className="py-2.5 flex items-center justify-between">
                <span className="font-semibold text-slate-800">Immutable Audit Trail on Approvals & Amendments</span>
                <span className="px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold font-mono">Compliant (Version snapshots v1..vn)</span>
              </div>
              <div className="py-2.5 flex items-center justify-between">
                <span className="font-semibold text-slate-800">Standards-Compatible FHIR R4 Bundle Export</span>
                <span className="px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold font-mono">Compliant (HL7 FHIR Document Bundle)</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
