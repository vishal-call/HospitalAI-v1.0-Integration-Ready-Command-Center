import React from "react";
import { ScoreRecord } from "@/lib/api";
import { ShieldAlert, AlertTriangle, CheckCircle2, Activity } from "lucide-react";

interface ScoreExplanationCardProps {
  scoreRecord?: ScoreRecord | null;
}

export default function ScoreExplanationCard({ scoreRecord }: ScoreExplanationCardProps) {
  if (!scoreRecord) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 flex flex-col items-center justify-center text-slate-500 py-12">
        <Activity className="h-8 w-8 mb-3 opacity-20" />
        <p>No recent clinical score available.</p>
      </div>
    );
  }

  const { explanation, risk_band, clinical_score, operational_priority } = scoreRecord;
  const breakdown = explanation?.parameter_breakdown || {};
  const redFlags = explanation?.red_flags || [];

  const getRiskColor = (band: string) => {
    switch (band) {
      case "HIGH": return "text-rose-500 bg-rose-500/10 border-rose-500/20";
      case "MEDIUM": return "text-amber-500 bg-amber-500/10 border-amber-500/20";
      case "LOW": return "text-emerald-500 bg-emerald-500/10 border-emerald-500/20";
      default: return "text-slate-400 bg-slate-800 border-slate-700";
    }
  };

  const riskClass = getRiskColor(risk_band);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
      {/* Header */}
      <div className="border-b border-slate-800 p-6 flex items-start justify-between bg-slate-900/40">
        <div>
          <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2 tracking-tight">
            <ShieldAlert className={`h-5 w-5 ${risk_band === 'HIGH' ? 'text-rose-500' : 'text-indigo-400'}`} />
            Clinical Scoring Engine
          </h3>
          <p className="text-sm text-slate-400 mt-1">NEWS2 Two-Layer Architecture</p>
        </div>
        
        <div className="flex gap-4 text-right">
          <div className={`px-4 py-2 rounded-xl border ${riskClass} flex flex-col items-end`}>
            <span className="text-[10px] font-bold uppercase tracking-wider opacity-80 mb-0.5">Risk Band</span>
            <span className="text-xl font-extrabold tracking-tight">{risk_band}</span>
          </div>
          
          <div className="px-4 py-2 rounded-xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-400 flex flex-col items-end">
            <span className="text-[10px] font-bold uppercase tracking-wider opacity-80 mb-0.5">Clinical Score</span>
            <span className="text-xl font-extrabold tracking-tight">{clinical_score}</span>
          </div>
        </div>
      </div>

      <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Parameter Breakdown */}
        <div className="md:col-span-2 space-y-4">
          <h4 className="text-sm font-bold text-slate-200 uppercase tracking-wider border-b border-slate-800 pb-2">
            Parameter Breakdown
          </h4>
          
          {Object.keys(breakdown).length === 0 ? (
            <p className="text-slate-500 text-sm">No parameter breakdown available.</p>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              {Object.entries(breakdown).map(([param, data]: [string, any]) => {
                const isRedFlag = redFlags.includes(param);
                return (
                  <div key={param} className={`flex items-center justify-between p-3 rounded-xl border ${isRedFlag ? 'bg-rose-950/30 border-rose-500/30' : 'bg-slate-950/50 border-slate-800'}`}>
                    <div className="flex flex-col">
                      <span className="text-xs text-slate-400 font-medium uppercase tracking-wide">
                        {param.replace(/_/g, " ")}
                      </span>
                      <span className="text-sm font-semibold text-slate-200 mt-0.5">
                        {data.value} {data.scale ? `(Scale ${data.scale})` : ''}
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {isRedFlag && <AlertTriangle className="h-4 w-4 text-rose-500" />}
                      <span className={`text-lg font-bold ${isRedFlag ? 'text-rose-500' : (data.score > 0 ? 'text-amber-500' : 'text-emerald-500')}`}>
                        +{data.score}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Operational & Flags sidebar */}
        <div className="space-y-6">
          <div className="bg-slate-950 rounded-xl p-5 border border-slate-800">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              Operational Priority
            </h4>
            <div className="flex items-end gap-1">
              <span className="text-3xl font-extrabold text-white tracking-tight">
                {operational_priority.toFixed(1)}
              </span>
              <span className="text-slate-500 font-semibold mb-1">/ 10.0</span>
            </div>
            <p className="text-xs text-slate-500 mt-2 leading-relaxed">
              This normalized priority score is used by the Orchestrator for hospital resource routing and bed allocation.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
              Red Flag Alerts
            </h4>
            {redFlags.length === 0 ? (
              <div className="flex items-center gap-2 text-emerald-500/80 text-sm font-medium bg-emerald-500/5 p-3 rounded-lg border border-emerald-500/10">
                <CheckCircle2 className="h-4 w-4" />
                No single parameter scored 3.
              </div>
            ) : (
              redFlags.map(flag => (
                <div key={flag} className="flex items-center gap-2 text-rose-400 text-sm font-medium bg-rose-500/5 p-3 rounded-lg border border-rose-500/10">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span className="capitalize">{flag.replace(/_/g, " ")} Triggered</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
