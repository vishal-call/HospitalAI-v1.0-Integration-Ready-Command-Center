"use client";

import React, { useEffect, useState } from "react";
import { ClinicalEvent, getPatientTimeline } from "@/lib/api";
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  FileSignature, 
  ArrowRightLeft,
  UserPlus
} from "lucide-react";

interface ClinicalTimelineProps {
  patientId: number;
}

export default function ClinicalTimeline({ patientId }: ClinicalTimelineProps) {
  const [events, setEvents] = useState<ClinicalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTimeline() {
      try {
        setLoading(true);
        const data = await getPatientTimeline(patientId);
        setEvents(data);
        setError(null);
      } catch (err: any) {
        setError(err.message || "Failed to load timeline.");
      } finally {
        setLoading(false);
      }
    }
    loadTimeline();
  }, [patientId]);

  if (loading) {
    return (
      <div className="flex justify-center p-8 animate-pulse text-slate-500 text-sm font-medium">
        Loading clinical timeline...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-400 text-sm">
        {error}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="text-slate-500 text-sm p-4 text-center">
        No clinical events found.
      </div>
    );
  }

  const getEventIcon = (type: string) => {
    switch (type) {
      case "ADMISSION":
        return <UserPlus className="w-4 h-4 text-emerald-400" />;
      case "VITALS_RECORDED":
        return <Activity className="w-4 h-4 text-sky-400" />;
      case "ALERT_TRIGGERED":
        return <AlertTriangle className="w-4 h-4 text-rose-400" />;
      case "RECOMMENDATION_GENERATED":
        return <FileSignature className="w-4 h-4 text-amber-400" />;
      case "RECOMMENDATION_APPROVED":
        return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
      case "RECOMMENDATION_REJECTED":
        return <XCircle className="w-4 h-4 text-rose-500" />;
      case "TRANSFER_COMPLETED":
        return <ArrowRightLeft className="w-4 h-4 text-indigo-400" />;
      default:
        return <Activity className="w-4 h-4 text-slate-400" />;
    }
  };

  const formatTime = (ts: string) => {
    const d = new Date(ts.replace("Z", "+00:00"));
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (ts: string) => {
    const d = new Date(ts.replace("Z", "+00:00"));
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <div className="relative border-l-2 border-slate-800 ml-3 pl-6 py-2 space-y-8">
      {events.map((evt, idx) => (
        <div key={evt.id} className="relative group">
          {/* Timeline Node */}
          <div className="absolute -left-[35px] top-1 bg-slate-900 border-2 border-slate-800 rounded-full p-1.5 shadow-lg">
            {getEventIcon(evt.event_type)}
          </div>
          
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-1">
            <h4 className="text-slate-200 font-bold text-sm tracking-tight">{evt.event_type.replace(/_/g, ' ')}</h4>
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
              <span>{formatDate(evt.timestamp)}</span>
              <span className="text-slate-400">{formatTime(evt.timestamp)}</span>
            </div>
          </div>
          
          <p className="text-slate-400 text-sm leading-relaxed mb-3">{evt.description}</p>
          
          {/* Metadata Block */}
          {evt.event_metadata && Object.keys(evt.event_metadata).length > 0 && (
            <div className="bg-slate-950/50 rounded-lg p-3 border border-slate-800/50">
              {evt.event_type === "VITALS_RECORDED" && evt.event_metadata?.vitals && (
                <div className="flex gap-4">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Heart Rate</span>
                    <span className="text-sky-400 font-mono text-sm">{evt.event_metadata?.vitals?.hr} bpm</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">SpO2</span>
                    <span className="text-emerald-400 font-mono text-sm">{evt.event_metadata?.vitals?.spo2}%</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">EWS Score</span>
                    <span className="text-amber-400 font-mono text-sm">{evt.event_metadata?.new_score?.toFixed(1)}</span>
                  </div>
                </div>
              )}

              {evt.event_type === "RECOMMENDATION_REJECTED" && evt.event_metadata?.override_reason && (
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Override Reason</span>
                  <span className="text-rose-300/80 text-xs italic">"{evt.event_metadata?.override_reason}"</span>
                </div>
              )}

              {/* Generic Fallback for other metadata */}
              {evt.event_type !== "VITALS_RECORDED" && evt.event_type !== "RECOMMENDATION_REJECTED" && (
                <div className="flex flex-wrap gap-x-4 gap-y-2">
                  {Object.entries(evt.event_metadata).map(([key, val]) => {
                    if (typeof val === 'object') return null;
                    return (
                      <div key={key} className="flex gap-1.5 items-center">
                        <span className="text-[10px] text-slate-500 font-mono">{key}:</span>
                        <span className="text-xs text-slate-300 font-mono">{String(val)}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
