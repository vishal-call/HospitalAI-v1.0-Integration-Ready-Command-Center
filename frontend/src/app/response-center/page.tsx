"use client";

import React, { useEffect, useState } from "react";
import { 
  fetchActiveAlerts, 
  acknowledgeAlert, 
  resolveAlert,
  AlertResponse 
} from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import ResponseAlertCard from "@/components/ResponseAlertCard";
import { useWebSocket } from "@/hooks/useWebSocket";
import { AlertOctagon, HeartPulse, ShieldAlert, Loader2 } from "lucide-react";

export default function ResponseCenterPage() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [loading, setLoading] = useState(true);

  // Initial Fetch
  const loadAlerts = async () => {
    try {
      const data = await fetchActiveAlerts();
      setAlerts(data);
    } catch (err) {
      console.error("Failed to load alerts", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      loadAlerts();
    }
  }, [user]);

  // WebSocket for Immutable Updates
  const wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
  const wsUrl = typeof window !== "undefined" && user ? `${wsBaseUrl}/ws/dashboard` : "";
  useWebSocket(wsUrl, (payload: any) => {
    if (["ALERT_ACKNOWLEDGED", "ALERT_RESOLVED", "ALERT_ESCALATED", "SLA_BREACHED"].includes(payload.type)) {
      setAlerts((prev) => {
        // If it's resolved/dismissed, we can remove it or keep it in a terminal state
        // We'll update the item in place so it flows to the next column or disappears
        const eventAlert = payload.data.alert || payload.data;
        const exists = prev.find(a => a.id === eventAlert.id);
        
        if (exists) {
          return prev.map(a => a.id === eventAlert.id ? { ...a, ...eventAlert } : a);
        } else {
          // New alert generated
          return [eventAlert, ...prev];
        }
      });
    }
    // Also listen to ALERT_TRIGGERED which might just be a standard alert
    if (payload.type === "ALERT_TRIGGERED") {
      setAlerts((prev) => {
        const eventAlert = payload.data.alert || payload.data;
        if (!prev.find(a => a.id === eventAlert.id)) {
          return [eventAlert, ...prev];
        }
        return prev;
      });
    }
  });

  const handleAcknowledge = async (id: number) => {
    // Optimistic update
    setAlerts((prev) => prev.map(a => a.id === id ? { ...a, status: "ACKNOWLEDGED" } : a));
    try {
      await acknowledgeAlert(id);
    } catch (err) {
      console.error(err);
      loadAlerts(); // rollback
    }
  };

  const handleResolve = async (id: number, note: string) => {
    // Optimistic update
    setAlerts((prev) => prev.filter(a => a.id !== id));
    try {
      await resolveAlert(id, { resolution_note: note });
    } catch (err) {
      console.error(err);
      loadAlerts(); // rollback
    }
  };

  if (!user) return null;

  // Filter columns
  const requiresAck = alerts.filter(a => ["CREATED", "ASSIGNED"].includes(a.status));
  const inProgress = alerts.filter(a => ["ACKNOWLEDGED", "IN_PROGRESS"].includes(a.status));
  const escalated = alerts.filter(a => a.status === "ESCALATED");

  return (
    <main className="flex-1 bg-slate-950 p-6 overflow-hidden flex flex-col h-[calc(100vh-73px)]">
      <div className="mb-6 flex items-center gap-3">
        <HeartPulse className="h-6 w-6 text-rose-500" />
        <h2 className="text-2xl font-extrabold text-slate-100 tracking-tight">Closed-Loop Response Center</h2>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-6 overflow-hidden">
          
          {/* Column 1: Requires Acknowledgement */}
          <div className="flex flex-col bg-slate-900/40 rounded-2xl border border-slate-800/80 overflow-hidden">
            <div className="p-4 border-b border-slate-800/80 bg-slate-900/80 flex justify-between items-center">
              <h3 className="font-bold text-slate-200 flex items-center gap-2">
                <AlertOctagon className="h-4 w-4 text-amber-500" />
                Requires Action
              </h3>
              <span className="bg-amber-500/10 text-amber-500 text-xs px-2 py-0.5 rounded-full font-semibold">
                {requiresAck.length}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
              {requiresAck.length === 0 && (
                <p className="text-slate-500 text-sm text-center mt-10">No pending alerts.</p>
              )}
              {requiresAck.map(alert => (
                <ResponseAlertCard 
                  key={alert.id} 
                  alert={alert} 
                  onAcknowledge={handleAcknowledge} 
                  onResolve={handleResolve} 
                />
              ))}
            </div>
          </div>

          {/* Column 2: In Progress */}
          <div className="flex flex-col bg-slate-900/40 rounded-2xl border border-slate-800/80 overflow-hidden">
            <div className="p-4 border-b border-slate-800/80 bg-slate-900/80 flex justify-between items-center">
              <h3 className="font-bold text-slate-200 flex items-center gap-2">
                <HeartPulse className="h-4 w-4 text-emerald-500" />
                In Progress
              </h3>
              <span className="bg-emerald-500/10 text-emerald-500 text-xs px-2 py-0.5 rounded-full font-semibold">
                {inProgress.length}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
              {inProgress.length === 0 && (
                <p className="text-slate-500 text-sm text-center mt-10">No alerts in progress.</p>
              )}
              {inProgress.map(alert => (
                <ResponseAlertCard 
                  key={alert.id} 
                  alert={alert} 
                  onAcknowledge={handleAcknowledge} 
                  onResolve={handleResolve} 
                />
              ))}
            </div>
          </div>

          {/* Column 3: Escalated */}
          <div className="flex flex-col bg-slate-900/40 rounded-2xl border border-rose-900/30 overflow-hidden shadow-lg shadow-rose-900/10">
            <div className="p-4 border-b border-rose-900/50 bg-rose-950/20 flex justify-between items-center">
              <h3 className="font-bold text-slate-200 flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-rose-500" />
                Escalated
              </h3>
              <span className="bg-rose-500/10 text-rose-500 text-xs px-2 py-0.5 rounded-full font-semibold">
                {escalated.length}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-800 bg-rose-950/5">
              {escalated.length === 0 && (
                <p className="text-slate-500 text-sm text-center mt-10">No escalated alerts.</p>
              )}
              {escalated.map(alert => (
                <ResponseAlertCard 
                  key={alert.id} 
                  alert={alert} 
                  onAcknowledge={handleAcknowledge} 
                  onResolve={handleResolve} 
                />
              ))}
            </div>
          </div>

        </div>
      )}
    </main>
  );
}
