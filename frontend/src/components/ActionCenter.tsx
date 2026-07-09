import React, { useState, useEffect } from "react";
import { RecommendationDetail, rejectRecommendation } from "@/lib/api";
import { ShieldAlert, ArrowRight, Check, X, ShieldAlert as AlertTriangle, Loader2, ShieldX, HelpCircle, Clock } from "lucide-react";
import RecommendationCard from "./RecommendationCard";
import FeedbackForm from "./FeedbackForm";

interface ActionCenterProps {
  recommendations: RecommendationDetail[];
  onActionComplete: () => void;
  actionRecommendation: (id: number, action: "APPROVE" | "REJECT", userId: number) => Promise<any>;
  activeUserId: number;
  userRole: string;
  disabled?: boolean;
}

export default function ActionCenter({
  recommendations,
  onActionComplete,
  actionRecommendation,
  activeUserId,
  userRole,
  disabled,
}: ActionCenterProps) {
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [errorMap, setErrorMap] = useState<Record<number, string>>({});
  
  // Optimistic UI state: keys are recommendation IDs
  const [optimisticState, setOptimisticState] = useState<Record<number, "APPROVE" | "REJECT">>({});
  
  // Floating toast notification state
  const [toast, setToast] = useState<string | null>(null);

  // Reject Modal State
  const [rejectModalId, setRejectModalId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  // Feedback Modal State
  const [feedbackModalId, setFeedbackModalId] = useState<number | null>(null);

  // Timer state for forcing re-renders every second
  const [, setNow] = useState(Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const isNurse = userRole === "NURSE";

  const handleAction = async (id: number, action: "APPROVE" | "REJECT", reason?: string) => {
    if (disabled || isNurse) return;

    // Trigger Optimistic UI (Dim card and show loading state)
    setOptimisticState((prev) => ({ ...prev, [id]: action }));
    setProcessingId(id);
    setErrorMap((prev) => ({ ...prev, [id]: "" }));

    try {
      if (action === "REJECT" && reason) {
        await rejectRecommendation(id, reason, activeUserId);
      } else {
        await actionRecommendation(id, action, activeUserId);
      }
      onActionComplete();
      // Remove from optimistic state after completion
      setOptimisticState((prev) => {
        const copy = { ...prev };
        delete copy[id];
        return copy;
      });
      if (action === "REJECT") {
        setRejectModalId(null);
        setRejectReason("");
      }
    } catch (err: any) {
      console.error("Action Center transaction error:", err);
      const errMsg = err.message || "";
      
      // Check for 409 Conflict or state machine warnings
      if (resilienceIsConflict(errMsg) || errMsg.includes("409") || errMsg.includes("Conflict")) {
        // Rollback optimistic state immediately
        setOptimisticState((prev) => {
          const copy = { ...prev };
          delete copy[id];
          return copy;
        });
        setToast(`Conflict: Recommendation already actioned by another clinician.`);
      } else {
        // Standard error handling
        setOptimisticState((prev) => {
          const copy = { ...prev };
          delete copy[id];
          return copy;
        });
        setErrorMap((prev) => ({
          ...prev,
          [id]: errMsg || `Failed to ${action.toLowerCase()} relocation.`,
        }));
      }
    } finally {
      setProcessingId(null);
    }
  };

  const resilienceIsConflict = (msg: string) => {
    const m = msg.toLowerCase();
    return m.includes("conflict") || m.includes("already") || m.includes("snagged") || m.includes("state");
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-6 h-full flex flex-col relative">
      {/* Toast Notification */}
      {toast && (
        <div className="absolute top-4 left-4 right-4 z-50 bg-rose-950/90 border border-rose-500/40 text-rose-200 text-xs px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2 backdrop-blur-md animate-in slide-in-from-top-3 duration-250">
          <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
          <span className="font-semibold">{toast}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center gap-2.5 mb-5 pb-4 border-b border-slate-800">
        <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          <ShieldAlert className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-100 tracking-tight flex items-center gap-2">
            HITL Action Center
            {recommendations.length > 0 && (
              <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold bg-indigo-500 text-white rounded-full">
                {recommendations.length}
              </span>
            )}
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">Relocation overrides requiring human coordinator authorization.</p>
        </div>
      </div>

      {/* Queue Body */}
      <div className="flex-1 overflow-y-auto space-y-4 max-h-[500px] pr-1 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
        {recommendations.length === 0 ? (
          <div className="h-40 flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl">
            <Check className="h-8 w-8 text-slate-600 mb-2" />
            <p className="text-slate-400 text-sm font-medium">All recommendations processed</p>
            <p className="text-slate-600 text-xs mt-1">Pending queue is currently clear.</p>
          </div>
        ) : (
          recommendations.map((rec) => (
            <RecommendationCard 
              key={rec.id}
              rec={rec}
              isOptimistic={optimisticState[rec.id] !== undefined}
              processingId={processingId}
              errorMsg={errorMap[rec.id]}
              isNurse={isNurse || !!disabled}
              onApprove={(id) => handleAction(id, "APPROVE")}
              onRejectPrompt={(id) => { setRejectModalId(id); setRejectReason(""); }}
              onFeedbackPrompt={(id) => setFeedbackModalId(id)}
            />
          ))
        )}
      </div>

      {/* Reject Modal Overlay */}
      {rejectModalId && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 rounded-2xl">
          <div className="w-full max-w-sm rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-2xl relative">
            <h3 className="text-lg font-bold text-slate-100 tracking-tight mb-2">Reject Recommendation</h3>
            <p className="text-xs text-slate-400 mb-4">Please provide a clinical reason for this manual override. Minimum 10 characters.</p>
            
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="E.g., Patient is stabilizing on current O2 flow..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-slate-700 h-24 resize-none mb-4"
            />
            
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setRejectModalId(null)}
                className="px-3 py-1.5 border border-slate-800 text-slate-300 rounded-lg text-xs font-semibold hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAction(rejectModalId, "REJECT", rejectReason)}
                disabled={processingId === rejectModalId || rejectReason.trim().length < 10}
                className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold flex items-center gap-1 transition-colors shadow-md shadow-rose-900/20"
              >
                {processingId === rejectModalId ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                Confirm Reject
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Feedback Modal Overlay */}
      {feedbackModalId && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 rounded-2xl">
          {recommendations.find(r => r.id === feedbackModalId) && (
            <FeedbackForm 
              recommendation={recommendations.find(r => r.id === feedbackModalId)!}
              onCancel={() => setFeedbackModalId(null)}
              onSuccess={() => {
                setFeedbackModalId(null);
                setToast("Clinical feedback submitted successfully.");
                onActionComplete(); // Can optionally trigger global refresh, websocket will clear it anyway
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}
