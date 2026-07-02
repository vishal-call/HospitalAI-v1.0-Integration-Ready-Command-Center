"use client";

import Link from "next/link";
import { Upload, Activity, ShieldCheck, FileText, Database } from "lucide-react";

export default function IntegrationCenterPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in zoom-in duration-500">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-400 to-cyan-300">
          Integration Center
        </h1>
        <p className="text-slate-400 max-w-2xl text-lg">
          Manage secure data pipelines between the HospitalAI Command Center and external Hospital Information Systems (HIS).
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* CSV Patient Import */}
        <div className="group relative overflow-hidden rounded-2xl bg-slate-900 border border-slate-800 p-6 flex flex-col gap-4 hover:border-teal-500/50 transition-all duration-300">
          <div className="absolute inset-0 bg-gradient-to-b from-teal-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="flex justify-between items-start">
            <div className="p-3 bg-teal-500/10 rounded-xl text-teal-400">
              <FileText size={24} />
            </div>
            <span className="px-3 py-1 text-xs font-medium bg-emerald-500/20 text-emerald-400 rounded-full flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Ready
            </span>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Patient Directory (CSV)</h2>
            <p className="text-sm text-slate-400 mt-1">
              Batch import patient demographics and ward assignments safely.
            </p>
          </div>
          <div className="mt-auto pt-4 border-t border-slate-800">
            <Link 
              href="/integrations/csv-import?type=patients"
              className="flex w-full items-center justify-center gap-2 py-2 px-4 bg-teal-600 hover:bg-teal-500 text-white rounded-lg transition-colors font-medium"
            >
              <Upload size={18} />
              Upload CSV
            </Link>
          </div>
        </div>

        {/* CSV Vitals Import */}
        <div className="group relative overflow-hidden rounded-2xl bg-slate-900 border border-slate-800 p-6 flex flex-col gap-4 hover:border-cyan-500/50 transition-all duration-300">
          <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="flex justify-between items-start">
            <div className="p-3 bg-cyan-500/10 rounded-xl text-cyan-400">
              <Activity size={24} />
            </div>
            <span className="px-3 py-1 text-xs font-medium bg-emerald-500/20 text-emerald-400 rounded-full flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Ready
            </span>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Clinical Vitals (CSV)</h2>
            <p className="text-sm text-slate-400 mt-1">
              Bulk ingestion of historical or batch vitals telemetry.
            </p>
          </div>
          <div className="mt-auto pt-4 border-t border-slate-800">
            <Link 
              href="/integrations/csv-import?type=vitals"
              className="flex w-full items-center justify-center gap-2 py-2 px-4 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 hover:border-cyan-500/50 rounded-lg transition-colors font-medium"
            >
              <Upload size={18} />
              Upload CSV
            </Link>
          </div>
        </div>

        {/* API Ingestion */}
        <div className="group relative overflow-hidden rounded-2xl bg-slate-900 border border-slate-800 p-6 flex flex-col gap-4 hover:border-purple-500/50 transition-all duration-300">
          <div className="absolute inset-0 bg-gradient-to-b from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="flex justify-between items-start">
            <div className="p-3 bg-purple-500/10 rounded-xl text-purple-400">
              <Database size={24} />
            </div>
            <span className="px-3 py-1 text-xs font-medium bg-amber-500/20 text-amber-400 rounded-full flex items-center gap-1.5">
              <ShieldCheck size={14} />
              Read-Only
            </span>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Live API Ingestion</h2>
            <p className="text-sm text-slate-400 mt-1">
              Direct HL7/FHIR connection to external HIS for real-time telemetry.
            </p>
          </div>
          <div className="mt-auto pt-4 border-t border-slate-800">
            <button 
              disabled
              className="flex w-full items-center justify-center gap-2 py-2 px-4 bg-slate-800 text-slate-500 rounded-lg cursor-not-allowed font-medium border border-slate-800"
            >
              Configure (Phase 3)
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
