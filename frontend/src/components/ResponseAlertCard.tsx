"use client";

import React, { useState, useEffect } from "react";
import { AlertResponse } from "@/lib/api";
import { Clock, CheckCircle, ShieldAlert } from "lucide-react";

interface ResponseAlertCardProps {
  alert: AlertResponse;
  onAcknowledge: (id: number) => Promise<void>;
  onResolve: (id: number, note: string) => Promise<void>;
}

export default function ResponseAlertCard({ alert, onAcknowledge, onResolve }: ResponseAlertCardProps) {
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const [resolving, setResolving] = useState(false);
  const [resolutionNote, setResolutionNote] = useState("");
  const [loading, setLoading] = useState(false);

  // SLA Timer Logic
  useEffect(() => {
    if (!alert.sla_due_at) return;
    
    // Initial calculation deferred to avoid sync state update in effect
    const dueTime = new Date(alert.sla_due_at).getTime();
    setTimeout(() => setTimeLeft(dueTime - Date.now()), 0);

    // Only set interval if alert is not resolved or dismissed
    if (["RESOLVED", "DISMISSED", "FALSE_ALARM"].includes(alert.status)) {
      return;
    }

    const intervalId = setInterval(() => {
      const remaining = dueTime - Date.now();
      setTimeLeft(remaining);
    }, 1000);

    return () => clearInterval(intervalId);
  }, [alert.sla_due_at, alert.status]);

  const formatTimeLeft = (ms: number) => {
    if (ms < 0) return "OVERDUE";
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}m ${seconds.toString().padStart(2, '0')}s`;
  };

  const handleAcknowledge = async () => {
    setLoading(true);
    try {
      await onAcknowledge(alert.id);
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!resolutionNote.trim()) return;
    setLoading(true);
    try {
      await onResolve(alert.id, resolutionNote);
    } finally {
      setLoading(false);
    }
  };

  // Determine SLA Style based on time left
  const isOverdue = timeLeft !== null && timeLeft < 0;
  const isUrgent = timeLeft !== null && timeLeft >= 0 && timeLeft < 60000; // < 1 min

  let borderStyle = "border-slate-700/50";
  let bgStyle = "bg-slate-900/50";
  let timeStyle = "text-slate-400";
  let timeIconClass = "text-slate-500";

  if (isOverdue && !["RESOLVED", "DISMISSED", "FALSE_ALARM"].includes(alert.status)) {
    borderStyle = "border-rose-500 shadow-sm shadow-rose-500/20";
    bgStyle = "bg-rose-950/20";
    timeStyle = "text-rose-500 font-bold animate-pulse";
    timeIconClass = "text-rose-500 animate-pulse";
  } else if (isUrgent && !["RESOLVED", "DISMISSED", "FALSE_ALARM"].includes(alert.status)) {
    borderStyle = "border-amber-500/50 shadow-sm shadow-amber-500/20";
    bgStyle = "bg-amber-950/10";
    timeStyle = "text-amber-500 font-bold";
    timeIconClass = "text-amber-500";
  }

  // Override for Escalated
  if (alert.status === "ESCALATED") {
    borderStyle = "border-rose-600/80 shadow-md shadow-rose-900/40";
    bgStyle = "bg-rose-950/30";
  }

  const patientName = alert.patient?.name || "Unknown Patient";

  const severityColor = 
    alert.severity === "CRITICAL" ? "text-rose-500" :
    alert.severity === "HIGH" ? "text-orange-500" :
    alert.severity === "MEDIUM" ? "text-amber-500" : "text-blue-500";

  return (
    <div className={`p-4 rounded-xl border ${borderStyle} ${bgStyle} transition-all duration-300 backdrop-blur-sm relative overflow-hidden group`}>
      {alert.status === "ESCALATED" && (
        <div className="absolute top-0 right-0 left-0 bg-gradient-to-r from-rose-900/80 to-rose-600/80 text-white text-[10px] font-bold uppercase tracking-widest py-0.5 px-3 flex items-center justify-center gap-1">
          <ShieldAlert className="h-3 w-3" />
          Escalated to {alert.assigned_to_role || "ADMIN"}
        </div>
      )}

      <div className={`flex justify-between items-start mb-3 ${alert.status === "ESCALATED" ? "mt-4" : ""}`}>
        <div>
          <h3 className="text-sm font-bold text-slate-200">{patientName}</h3>
          <p className="text-xs text-slate-400 flex items-center gap-2 mt-1">
            <span className={`font-semibold ${severityColor}`}>{alert.alert_type.replace(/_/g, ' ')}</span>
            <span>&bull;</span>
            <span className="truncate">{alert.message}</span>
          </p>
        </div>
        
        {timeLeft !== null && !["RESOLVED", "DISMISSED", "FALSE_ALARM"].includes(alert.status) && (
          <div className="flex flex-col items-end shrink-0 pl-3">
            <div className={`flex items-center gap-1.5 ${timeStyle} bg-slate-950/50 px-2 py-1 rounded-md border border-slate-800`}>
              <Clock className={`h-3.5 w-3.5 ${timeIconClass}`} />
              <span className="text-xs tracking-wider">{formatTimeLeft(timeLeft)}</span>
            </div>
            <span className="text-[9px] text-slate-500 mt-1 uppercase tracking-widest">SLA Countdown</span>
          </div>
        )}
      </div>

      {/* State Machine Actions */}
      <div className="mt-4 pt-3 border-t border-slate-800/50">
        {["CREATED", "ASSIGNED"].includes(alert.status) && (
          <button
            onClick={handleAcknowledge}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors disabled:opacity-50"
          >
            <CheckCircle className="h-4 w-4" />
            {loading ? "Acknowledging..." : "Acknowledge Alert"}
          </button>
        )}

        {["ACKNOWLEDGED", "IN_PROGRESS"].includes(alert.status) && !resolving && (
          <button
            onClick={() => setResolving(true)}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors"
          >
            <CheckCircle className="h-4 w-4" />
            Resolve Incident
          </button>
        )}

        {resolving && (
          <div className="animate-in slide-in-from-top-2 duration-200">
            <textarea
              autoFocus
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 mb-2 focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
              placeholder="Clinical resolution note (required)..."
              rows={2}
              value={resolutionNote}
              onChange={(e) => setResolutionNote(e.target.value)}
            />
            <div className="flex gap-2">
              <button
                onClick={() => setResolving(false)}
                className="flex-1 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleResolve}
                disabled={loading || !resolutionNote.trim()}
                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors disabled:opacity-50"
              >
                {loading ? "Saving..." : "Submit Resolution"}
              </button>
            </div>
          </div>
        )}

        {["RESOLVED", "DISMISSED", "FALSE_ALARM"].includes(alert.status) && (
          <div className="text-xs text-slate-400 italic">
            Resolved: {alert.resolution_note || alert.status}
          </div>
        )}
      </div>
    </div>
  );
}
