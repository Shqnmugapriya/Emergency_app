import React from "react";

export function StatusBadge({ status }) {
  const configs = {
    "Draft": {
      bg: "bg-slate-100 text-slate-700 border-slate-300",
      dot: "bg-slate-400"
    },
    "Needs Review": {
      bg: "bg-amber-50 text-amber-800 border-amber-300",
      dot: "bg-amber-500"
    },
    "Reviewed": {
      bg: "bg-indigo-50 text-indigo-800 border-indigo-300",
      dot: "bg-indigo-500"
    },
    "Approved": {
      bg: "bg-emerald-50 text-emerald-800 border-emerald-300",
      dot: "bg-emerald-500"
    },
    "Amended": {
      bg: "bg-purple-50 text-purple-800 border-purple-300",
      dot: "bg-purple-500"
    }
  };

  const current = configs[status] || configs["Draft"];

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${current.bg}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${current.dot}`}></span>
      {status}
    </span>
  );
}

export function SeverityBadge({ severity }) {
  const configs = {
    "CRITICAL": "bg-red-100 text-red-800 border-red-300",
    "WARNING": "bg-amber-100 text-amber-800 border-amber-300",
    "INFO": "bg-blue-100 text-blue-800 border-blue-300"
  };

  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${configs[severity] || configs["INFO"]}`}>
      {severity}
    </span>
  );
}

export function VerificationBadge({ state }) {
  const configs = {
    "Extracted": "bg-slate-100 text-slate-700 border-slate-200",
    "Verified": "bg-emerald-100 text-emerald-800 border-emerald-300",
    "Uncertain": "bg-amber-100 text-amber-800 border-amber-300",
    "Unknown": "bg-gray-100 text-gray-700 border-gray-300",
    "Rejected": "bg-rose-100 text-rose-800 border-rose-300"
  };

  return (
    <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${configs[state] || configs["Extracted"]}`}>
      {state}
    </span>
  );
}
