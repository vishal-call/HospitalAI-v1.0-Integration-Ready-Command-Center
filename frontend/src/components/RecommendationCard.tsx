import React from "react";
import { RecommendationDetail } from "@/lib/api";
import { Clock, ArrowRight, ShieldX, HelpCircle, Check, X, Loader2, Beaker } from "lucide-react";

interface RecommendationCardProps {
  rec: RecommendationDetail;
  isOptimistic: boolean;
  processingId: number | null;
  errorMsg?: string;
  isNurse: boolean;
  onApprove: (id: number) => void;
  onRejectPrompt: (id: number) => void;
  onFeedbackPrompt: (id: number) => void;
}

export default function RecommendationCard({
  rec,
  isOptimistic,
  processingId,
  errorMsg,
  isNurse,
  onApprove,
  onRejectPrompt,
  onFeedbackPrompt,
}: RecommendationCardProps) {
  const getScoreBadgeStyle = (score: number) => {
    if (score >= 8.0) return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
    if (score >= 4.0) return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
    return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
  };

  const getRecommendationMeta = () => {
    if (rec.recommendation_type === "CHAINED_TRANSFER") {
      return {
        type: "Chained Relocation",
        role: "DOCTOR",
        badgeStyle: "bg-purple-500/15 text-purple-400 border border-purple-500/25 animate-pulse"
      };
    }
    if (rec.partner_hospital_id) {
      return {
        type: "Inter-Hospital Transfer",
        role: "COORDINATOR",
        badgeStyle: "bg-rose-500/10 text-rose-400 border border-rose-500/20"
      };
    }
    const isTargetICU = 
      rec.target_bed?.bed_number?.startsWith("ICU") || 
      rec.target_bed_id === 1 || 
      (rec.reasoning && rec.reasoning.toLowerCase().includes("icu"));
      
    if (isTargetICU) {
      return {
        type: "Critical Escalation",
        role: "DOCTOR",
        badgeStyle: "bg-red-500/15 text-red-400 border border-red-500/25 animate-pulse"
      };
    }
    return {
      type: "Clinical Step-Down",
      role: "DOCTOR / COORDINATOR",
      badgeStyle: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
    };
  };

  const getRemainingTime = (expiresAtStr: string | null) => {
    if (!expiresAtStr) return null;
    const exp = new Date(expiresAtStr.replace("Z", "+00:00"));
    const now = new Date();
    const diff = exp.getTime() - now.getTime();
    if (diff <= 0) return "00:00";
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const meta = getRecommendationMeta();
  const isExpired = rec.expires_at ? getRemainingTime(rec.expires_at) === "00:00" : false;
  
  // Shadow Mode specific styling overrides
  const cardBorderClass = rec.is_shadow 
    ? "border-violet-500/40 bg-slate-900/80 bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,rgba(139,92,246,0.03)_10px,rgba(139,92,246,0.03)_20px)]"
    : "border-slate-800 bg-slate-950 hover:border-slate-700/80";

  return (
    <div
      className={`relative overflow-hidden rounded-xl border p-5 transition-all duration-300 ${
        isOptimistic 
          ? "border-slate-850 bg-slate-950/40 opacity-40 scale-[0.98] pointer-events-none" 
          : cardBorderClass
      }`}
    >
      {/* Accent Ribbon */}
      <div className={`absolute top-0 left-0 w-1 h-full ${
        rec.is_shadow ? "bg-violet-500" : 
        rec.partner_hospital_id ? "bg-rose-500" : 
        rec.target_bed?.bed_number?.startsWith("ICU") ? "bg-red-500" : "bg-emerald-500"
      }`} />

      {/* Shadow Mode Badge */}
      {rec.is_shadow && (
        <div className="flex items-center gap-1 mb-3 text-[10px] font-bold text-violet-300 bg-violet-900/30 border border-violet-500/20 px-2 py-1 rounded w-max tracking-wide">
          <Beaker className="h-3 w-3" />
          SHADOW MODE - VALIDATION ONLY
        </div>
      )}

      {/* Card Title & Type */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <h3 className="font-extrabold text-slate-100 text-sm">{rec.patient?.name || `Patient ID: ${rec.patient_id}`}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${rec.is_shadow ? 'bg-violet-500/10 text-violet-400 border border-violet-500/20' : meta.badgeStyle}`}>
              {meta.type}
            </span>
            {rec.expires_at && !rec.is_shadow && (
              <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border ${
                isExpired 
                  ? "bg-rose-500/20 text-rose-400 border-rose-500/30 animate-pulse" 
                  : "bg-slate-800 text-slate-300 border-slate-700"
              }`}>
                <Clock className="h-3 w-3" />
                {isExpired ? "EXPIRED" : getRemainingTime(rec.expires_at)}
              </span>
            )}
          </div>
        </div>
        <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full ${getScoreBadgeStyle(rec.criticality_score ?? ((rec as unknown) as { score?: number }).score ?? 0)}`}>
          EWS {(rec.criticality_score ?? ((rec as unknown) as { score?: number }).score ?? 0).toFixed(1)}
        </span>
      </div>

      {/* Transfer Details Card */}
      {rec.recommendation_type === "CHAINED_TRANSFER" ? (
        <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800/60 mb-3 space-y-2.5 text-xs">
          <div className="flex items-center justify-between text-slate-300 bg-purple-950/20 border border-purple-500/10 p-2 rounded-md">
            <span className="font-semibold text-purple-400">Step 1: ICU Step-Down</span>
            <div className="flex items-center gap-1.5">
              <span className="text-slate-300 font-medium">{rec.chained_patient?.name || "Stable Patient"}</span>
              <ArrowRight className="h-3 w-3 text-slate-500" />
              <span className="text-indigo-400 font-medium">{rec.chained_target_bed?.bed_number || "GW-3xx"}</span>
            </div>
          </div>
          <div className="flex items-center justify-between text-slate-300 bg-red-950/20 border border-red-500/10 p-2 rounded-md">
            <span className="font-semibold text-red-400">Step 2: ICU Escalation</span>
            <div className="flex items-center gap-1.5">
              <span className="text-slate-300 font-medium">{rec.patient?.name || "Critical Patient"}</span>
              <ArrowRight className="h-3 w-3 text-slate-500" />
              <span className="text-rose-400 font-semibold">{rec.target_bed?.bed_number || "ICU-1xx"}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800/60 mb-3 flex items-center justify-between text-xs text-slate-300">
          <div className="text-center flex-1">
            <span className="text-slate-500 block mb-1">Source Bed</span>
            <span className="font-medium text-slate-200">
              {rec.source_bed?.bed_number || (rec.patient?.current_bed_id ? `Bed ID: ${rec.patient.current_bed_id}` : "Unassigned")}
            </span>
          </div>
          <ArrowRight className="h-4 w-4 text-slate-500 mx-2 flex-shrink-0" />
          <div className="text-center flex-1">
            {rec.partner_hospital_id ? (
              <>
                <span className="text-rose-400 font-semibold block mb-1">Partner Network</span>
                <span className="font-medium text-rose-400">
                  {rec.partner_hospital?.name || "Partner Hospital"} ({(rec.partner_hospital?.distance_km ?? 5.2).toFixed(1)} km)
                </span>
              </>
            ) : (
              <>
                <span className="text-slate-500 block mb-1">Target Bed</span>
                <span className="font-medium text-indigo-400">{rec.target_bed?.bed_number || "ICU-108"}</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Expert Reasoning Text */}
      <div className="text-xs text-slate-400 bg-slate-900/20 border border-slate-800/40 rounded-lg p-3 mb-3 leading-relaxed">
        <span className="font-semibold text-slate-300 block mb-1">Clinical Reasoning:</span>
        {rec.reasoning}
      </div>

      {/* Role Warning & Lockouts (RBAC UI Layer) */}
      {!rec.is_shadow && (
        isNurse ? (
          <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-bold uppercase tracking-wider mb-2 select-none">
            <ShieldX className="h-4 w-4 shrink-0" />
            <span>Requires {meta.role} Clearance to approve</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono mb-2 uppercase select-none">
            <HelpCircle className="h-3.5 w-3.5" />
            <span>Authorized Action Role: {meta.role}</span>
          </div>
        )
      )}

      {/* Error Message */}
      {errorMsg && (
        <div className="text-xs bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-lg p-2.5 mb-3 flex items-start gap-1.5">
          <ShieldX className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2">
        {rec.is_shadow ? (
          <button
            onClick={() => onFeedbackPrompt(rec.id)}
            disabled={processingId !== null}
            className="flex-1 py-2 px-3 bg-violet-600/20 border border-violet-500/30 hover:bg-violet-600 hover:text-white text-violet-300 rounded-lg text-xs font-bold transition-all shadow-md flex items-center justify-center gap-1"
          >
            {processingId === rec.id ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Beaker className="h-3.5 w-3.5" />
            )}
            Provide Clinical Feedback
          </button>
        ) : (
          <>
            <button
              onClick={() => onRejectPrompt(rec.id)}
              disabled={processingId !== null || isNurse}
              className="flex-1 py-2 px-3 border border-slate-850 rounded-lg text-xs font-semibold text-slate-400 hover:bg-slate-900 hover:text-rose-400 disabled:opacity-30 transition-all flex items-center justify-center gap-1"
            >
              {processingId === rec.id && isOptimistic ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <X className="h-3.5 w-3.5" />
              )}
              Reject
            </button>
            <button
              onClick={() => onApprove(rec.id)}
              disabled={processingId !== null || isNurse || isExpired}
              className="flex-1 py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold disabled:opacity-30 transition-all flex items-center justify-center gap-1 shadow-md shadow-indigo-600/10"
            >
              {processingId === rec.id && isOptimistic ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Check className="h-3.5 w-3.5" />
              )}
              Approve
            </button>
          </>
        )}
      </div>
    </div>
  );
}
