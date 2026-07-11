import React, { useEffect, useState } from "react";
import { Patient, ScoreRecord, fetchPatient } from "@/lib/api";
import { X, Loader2, Heart, Activity, Thermometer, ShieldAlert, AlertTriangle, UserCheck } from "lucide-react";

interface PatientDetailsModalProps {
  patient: Patient;
  onClose: () => void;
}

export default function PatientDetailsModal({ patient, onClose }: PatientDetailsModalProps) {
  const [detailedPatient, setDetailedPatient] = useState<(Patient & { score_record?: ScoreRecord | null }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await fetchPatient(patient.id);
        setDetailedPatient(data);
      } catch (err: any) {
        const errMsg = err.message || "";
        if (errMsg.includes("Failed to fetch")) {
          setError("Network Error: Could not reach the server. Please check your Vercel Environment Variables and Render CORS configuration.");
        } else {
          setError(errMsg || "Failed to load patient dossier.");
        }
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [patient.id]);

  const getRiskColor = (band?: string) => {
    switch (band) {
      case "HIGH":
        return "text-rose-400 bg-rose-500/10 border-rose-500/20";
      case "MEDIUM":
        return "text-amber-400 bg-amber-500/10 border-amber-500/20";
      case "LOW":
        return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
      default:
        return "text-slate-400 bg-slate-800 border-slate-700";
    }
  };

  const getScoreCircleColor = (band?: string) => {
    switch (band) {
      case "HIGH":
        return "border-rose-500 text-rose-400 bg-rose-500/5";
      case "MEDIUM":
        return "border-amber-500 text-amber-400 bg-amber-500/5";
      case "LOW":
        return "border-emerald-500 text-emerald-400 bg-emerald-500/5";
      default:
        return "border-slate-700 text-slate-400";
    }
  };

  const scoreRecord = detailedPatient?.score_record;
  const breakdown = scoreRecord?.explanation?.parameter_breakdown || {};
  const redFlags = scoreRecord?.explanation?.red_flags || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="w-full max-w-2xl rounded-2xl border border-white/10 bg-slate-900/95 p-6 shadow-2xl relative text-slate-100 backdrop-blur-md">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg bg-slate-950/50 border border-slate-800 text-slate-400 hover:text-white hover:border-slate-700 transition-colors"
          aria-label="Close modal"
        >
          <X className="h-5 w-5" />
        </button>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-slate-400">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
            <p className="text-sm font-medium">Fetching live clinical dossier...</p>
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <p className="text-rose-400 font-semibold mb-4">{error}</p>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-950 border border-slate-850 hover:bg-slate-900 text-slate-300 rounded-xl text-sm transition-all"
            >
              Close Window
            </button>
          </div>
        ) : (
          <div>
            {/* Header Identity */}
            <div className="flex items-start gap-4 mb-6 pr-8">
              <div className="h-12 w-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20 shrink-0">
                <UserCheck className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold tracking-tight text-white">{detailedPatient?.name}</h3>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs font-medium text-slate-400">
                  <span>ID: #{detailedPatient?.id}</span>
                  <span className="w-1 h-1 rounded-full bg-slate-700"></span>
                  <span>{detailedPatient?.age}y / {detailedPatient?.gender}</span>
                  <span className="w-1 h-1 rounded-full bg-slate-700"></span>
                  <span className="text-indigo-400">
                    Bed Assignment: {detailedPatient?.current_bed_id ? `Bed #${detailedPatient.current_bed_id}` : "Unassigned"}
                  </span>
                </div>
              </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* Left Column: EWS Indicator */}
              <div className="flex flex-col items-center justify-center p-5 rounded-2xl border border-slate-800 bg-slate-950/40 text-center">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">EWS Score</span>
                <div className={`h-24 w-24 rounded-full border-4 flex flex-col items-center justify-center ${getScoreCircleColor(scoreRecord?.risk_band)}`}>
                  <span className="text-3xl font-black tracking-tight">
                    {scoreRecord?.clinical_score ?? 0}
                  </span>
                  <span className="text-[10px] font-bold uppercase opacity-80">NEWS2</span>
                </div>
                <div className={`mt-3 px-3 py-1 rounded-full border text-[10px] font-bold tracking-wide uppercase ${getRiskColor(scoreRecord?.risk_band)}`}>
                  {scoreRecord?.risk_band ?? "LOW"} RISK
                </div>
                <div className="mt-4 text-[11px] text-slate-500 leading-relaxed">
                  Operational priority is <span className="font-semibold text-slate-300">{(detailedPatient?.criticality_score ?? 0.0).toFixed(1)}/10.0</span>.
                </div>
              </div>

              {/* Right Column: Vitals Parameters Grid */}
              <div className="md:col-span-2 space-y-4">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2">
                  Parameters & Telemetry Vitals
                </h4>

                {Object.keys(breakdown).length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-6 text-slate-500 border border-dashed border-slate-800 rounded-xl">
                    <Activity className="h-6 w-6 mb-2 opacity-30" />
                    <span className="text-xs">No vital sign parameters recorded yet.</span>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(breakdown).map(([param, data]: [string, any]) => {
                      const isRedFlag = redFlags.includes(param);
                      return (
                        <div
                          key={param}
                          className={`flex items-center justify-between p-3 rounded-xl border ${
                            isRedFlag ? "bg-rose-950/30 border-rose-500/30" : "bg-slate-950/30 border-slate-850"
                          }`}
                        >
                          <div className="flex flex-col">
                            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wide">
                              {param.replace(/_/g, " ")}
                            </span>
                            <span className="text-xs font-semibold text-slate-200 mt-0.5">
                              {data.value} {data.scale ? `(Scale ${data.scale})` : ""}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            {isRedFlag && <AlertTriangle className="h-3.5 w-3.5 text-rose-500" />}
                            <span className={`text-sm font-bold ${isRedFlag ? "text-rose-500" : (data.score > 0 ? "text-amber-500" : "text-emerald-500")}`}>
                              +{data.score}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Admission Context */}
            <div className="mt-6 p-4 rounded-xl border border-slate-800 bg-slate-950/20">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">Reason for Admission</span>
              <p className="text-xs text-slate-300 leading-relaxed">
                {detailedPatient?.admission_reason || "No details provided."}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
