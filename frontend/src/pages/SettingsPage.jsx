import React, { useState, useEffect } from "react";
import {
  Settings, ShieldCheck, Activity, Cpu, Database, Search,
  RefreshCw, CheckCircle, AlertCircle, HardDrive, Pill
} from "lucide-react";
import { api } from "../services/api";

export function SettingsPage() {
  const [health, setHealth] = useState(null);
  const [whisperStatus, setWhisperStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [modelSwitching, setModelSwitching] = useState(false);
  const [switchMessage, setSwitchMessage] = useState(null);

  // Medicine search test state
  const [searchQuery, setSearchQuery] = useState("paracetamol");
  const [searchResult, setSearchResult] = useState(null);
  const [isSearching, setIsSearching] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const [hRes, wRes] = await Promise.all([
        api.getHealth(),
        api.getTranscriptionStatus()
      ]);
      setHealth(hRes);
      setWhisperStatus(wRes.data);
    } catch (err) {
      console.error("Failed to load settings data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    handleTestMedicineSearch("paracetamol");
  }, []);

  const handleSwitchModel = async (modelName) => {
    setModelSwitching(true);
    setSwitchMessage(null);
    try {
      const res = await api.loadTranscriptionModel(modelName);
      if (res.success) {
        setSwitchMessage(`Whisper model successfully switched to '${modelName}' (${res.status.device}).`);
        setWhisperStatus(res.status);
      }
    } catch (err) {
      setSwitchMessage(`Failed to switch model: ${err.message}`);
    } finally {
      setModelSwitching(false);
    }
  };

  const handleTestMedicineSearch = async (queryToSearch) => {
    const q = queryToSearch !== undefined ? queryToSearch : searchQuery;
    if (!q.trim()) return;
    setIsSearching(true);
    try {
      const res = await api.searchMedicines(q);
      if (res.success) {
        setSearchResult(res.data);
      }
    } catch (err) {
      console.error("Search error:", err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          System Diagnostics & Configuration
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Monitor offline speech engine, local SQLite database, and verified clinical catalogue.
        </p>
      </div>

      {switchMessage && (
        <div className="p-4 rounded-lg bg-teal-50 border border-teal-200 text-teal-800 text-sm flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-teal-600 shrink-0" />
          <span>{switchMessage}</span>
        </div>
      )}

      {/* Grid of System Modules */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Module 1: Faster-Whisper Speech Engine */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2.5">
              <Cpu className="w-5 h-5 text-clinical-teal-600" />
              <h2 className="text-base font-bold text-slate-900">Speech-to-Text Engine</h2>
            </div>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              {whisperStatus?.is_ready ? "Engine Ready" : whisperStatus?.status || "Unknown"}
            </span>
          </div>

          <div className="space-y-2 text-xs text-slate-600">
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="font-semibold text-slate-500">Engine Type:</span>
              <span className="font-mono font-bold text-slate-800">faster-whisper (CTranslate2)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="font-semibold text-slate-500">Active Model:</span>
              <span className="font-mono font-bold text-clinical-teal-700">{whisperStatus?.model_name || "base"}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="font-semibold text-slate-500">Execution Device:</span>
              <span className="font-mono text-slate-800">{whisperStatus?.device?.toUpperCase() || "CPU"}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="font-semibold text-slate-500">Compute Quantization:</span>
              <span className="font-mono text-slate-800">{whisperStatus?.compute_type || "int8"} (Optimized for laptops)</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="font-semibold text-slate-500">Cloud Dependency:</span>
              <span className="font-semibold text-emerald-700">None (100% Air-Gapped Local)</span>
            </div>
          </div>

          {/* Model Switcher */}
          <div className="pt-2 border-t border-slate-100">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2">
              Switch Whisper Model Size
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => handleSwitchModel("tiny")}
                disabled={modelSwitching || whisperStatus?.model_name === "tiny"}
                className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                  whisperStatus?.model_name === "tiny"
                    ? "bg-clinical-teal-700 text-white border-clinical-teal-700"
                    : "bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-300"
                }`}
              >
                Tiny (~75MB)
              </button>
              <button
                onClick={() => handleSwitchModel("base")}
                disabled={modelSwitching || whisperStatus?.model_name === "base"}
                className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                  whisperStatus?.model_name === "base"
                    ? "bg-clinical-teal-700 text-white border-clinical-teal-700"
                    : "bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-300"
                }`}
              >
                Base (~145MB - Recommended)
              </button>
            </div>
          </div>
        </div>

        {/* Module 2: SQLite Database & Storage */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2.5">
              <Database className="w-5 h-5 text-clinical-teal-600" />
              <h2 className="text-base font-bold text-slate-900">Database & Storage</h2>
            </div>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              {health?.database?.status === "healthy" ? "Connected" : "Error"}
            </span>
          </div>

          <div className="space-y-2 text-xs text-slate-600">
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="font-semibold text-slate-500">Database Engine:</span>
              <span className="font-mono font-bold text-slate-800">SQLite 3 (Local Encrypted-Ready)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="font-semibold text-slate-500">Database Health:</span>
              <span className="font-semibold text-slate-800">{health?.database?.details || "Accessible"}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="font-semibold text-slate-500">Reports Directory:</span>
              <span className="font-mono text-slate-800">data/reports/ (PDF & JSON)</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="font-semibold text-slate-500">Audio Retention:</span>
              <span className="font-mono text-slate-800">data/audio/ (Secure UUIDs)</span>
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-600 space-y-1">
            <span className="font-bold text-slate-800 block">Data Privacy Guarantee:</span>
            <span>All audio files, field notes, and structured clinical records remain strictly within this machine. No external telemetry or cloud storage is enabled.</span>
          </div>
        </div>
      </div>

      {/* Module 3: Verified Medicine Catalogue & Ambiguity Testing Tool */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2.5">
            <Pill className="w-5 h-5 text-clinical-teal-600" />
            <div>
              <h2 className="text-base font-bold text-slate-900">Verified Medicine Catalogue & Ambiguity Engine</h2>
              <p className="text-xs text-slate-500">WHO Model List (23rd Ed. 2023) / Pre-Hospital EMS Guidelines v1.2.0</p>
            </div>
          </div>
          <span className="text-xs bg-clinical-teal-50 text-clinical-teal-800 font-bold px-2.5 py-1 rounded-full border border-clinical-teal-200">
            RapidFuzz Assisted • Human Gated
          </span>
        </div>

        {/* Search Test Sandbox */}
        <div className="space-y-3">
          <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
            Test Medicine Lookup & Ambiguity Detection Sandbox
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleTestMedicineSearch()}
                placeholder="Try: 'Paracetamol', 'Panadol', 'Advil', 'paramol' (fuzzy), or 'par'..."
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-clinical-teal-500"
              />
            </div>
            <button
              onClick={() => handleTestMedicineSearch()}
              disabled={isSearching}
              className="px-4 py-2 bg-clinical-teal-600 hover:bg-clinical-teal-700 text-white text-xs font-semibold rounded-lg shadow-sm"
            >
              Search
            </button>
          </div>

          {/* Quick preset buttons */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-500 font-medium">Quick Test Cases:</span>
            {["Paracetamol", "Tylenol (Alias)", "paramol (Fuzzy)", "Morphine", "Epinephrine", "Naloxone"].map((term) => (
              <button
                key={term}
                onClick={() => {
                  const clean = term.split(" ")[0];
                  setSearchQuery(clean);
                  handleTestMedicineSearch(clean);
                }}
                className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-[11px] font-semibold"
              >
                {term}
              </button>
            ))}
          </div>

          {/* Result Card */}
          {searchResult && (
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2 mt-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900 text-sm">
                    {searchResult.matched_canonical || "No Exact Match"}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    searchResult.status === "EXACT" ? "bg-emerald-100 text-emerald-800" :
                    searchResult.status === "ALIAS" ? "bg-indigo-100 text-indigo-800" :
                    searchResult.status === "AMBIGUOUS" ? "bg-amber-100 text-amber-800" :
                    "bg-slate-200 text-slate-700"
                  }`}>
                    Match Status: {searchResult.status}
                  </span>
                </div>
                <span className="font-mono text-slate-500">
                  Confidence: {searchResult.confidence_score}%
                </span>
              </div>

              {searchResult.status === "AMBIGUOUS" && (
                <div className="p-2.5 bg-amber-50 border border-amber-300 rounded text-amber-800 font-medium">
                  {searchResult.ambiguity_reason} — Human confirmation mandatory! RapidFuzz is prohibited from silently committing this match.
                </div>
              )}

              {searchResult.candidates && searchResult.candidates.length > 0 && (
                <div className="space-y-1 pt-1">
                  <span className="font-semibold text-slate-600 block">Candidate Matches:</span>
                  <div className="flex flex-wrap gap-2">
                    {searchResult.candidates.map((c) => (
                      <span key={c.canonical_name} className="px-2 py-1 bg-white border border-slate-200 rounded text-[11px] font-mono">
                        {c.canonical_name} ({c.score}%)
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="text-[11px] text-slate-400 pt-1">
                Provenance: {searchResult.provenance}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
