import React, { useState } from "react";
import { Alert } from "@/lib/api";
import { Bell, Check, X, ShieldAlert, Heart, Radio, Activity, Loader2 } from "lucide-react";

interface AlertFeedProps {
  alerts: Alert[];
  onAcknowledgeComplete: () => void;
  acknowledgeAlert: (id: number) => Promise<any>;
}

export default function AlertFeed({
  alerts,
  onAcknowledgeComplete,
  acknowledgeAlert,
}: AlertFeedProps) {
  const [processingId, setProcessingId] = useState<number | null>(null);

  const handleDismiss = async (id: number) => {
    setProcessingId(id);
    try {
      await acknowledgeAlert(id);
      onAcknowledgeComplete();
    } catch (err) {
      console.error("Failed to dismiss alert:", err);
    } finally {
      setProcessingId(null);
    }
  };

  const getAlertStyle = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return {
          card: "bg-rose-950/40 border-rose-500/30 hover:border-rose-500/50",
          iconContainer: "bg-rose-500/10 text-rose-400 border border-rose-500/20",
          badge: "bg-rose-500/20 text-rose-300 border border-rose-500/30",
          ping: "bg-rose-400",
        };
      case "HIGH":
        return {
          card: "bg-amber-950/30 border-amber-500/30 hover:border-amber-500/50",
          iconContainer: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
          badge: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
          ping: "bg-amber-400",
        };
      default:
        return {
          card: "bg-slate-900/60 border-slate-800 hover:border-slate-700",
          iconContainer: "bg-slate-800/80 text-slate-400 border border-slate-700/50",
          badge: "bg-slate-800 text-slate-300 border border-slate-700/50",
          ping: "bg-slate-500",
        };
    }
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case "LOW_OXYGEN":
        return <Activity className="h-4 w-4" />;
      case "SCORE_SPIKE":
        return <ShieldAlert className="h-4 w-4" />;
      default:
        return <Radio className="h-4 w-4" />;
    }
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-6 flex flex-col h-full">
      <div className="flex items-center gap-2.5 mb-5 pb-4 border-b border-slate-800">
        <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <Bell className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-100 tracking-tight flex items-center gap-2">
            Active Warning Alerts
            {alerts.length > 0 && (
              <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold bg-rose-500 text-white rounded-full">
                {alerts.length}
              </span>
            )}
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">Real-time alerts for patient deterioration and capacity anomalies.</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 max-h-[350px] pr-1 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
        {alerts.length === 0 ? (
          <div className="h-32 flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl">
            <Check className="h-8 w-8 text-slate-600 mb-2" />
            <p className="text-slate-400 text-sm font-medium">No active warnings</p>
            <p className="text-slate-600 text-xs mt-1">Telemetry suggests all patient parameters are safe.</p>
          </div>
        ) : (
          alerts.map((alert) => {
            const styles = getAlertStyle(alert.severity);
            return (
              <div
                key={alert.id}
                className={`relative overflow-hidden rounded-xl border p-4 transition-all duration-200 ${styles.card}`}
              >
                {/* Ping warning dot */}
                <span className="absolute top-4 right-4 flex h-2 w-2">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${styles.ping}`}></span>
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${styles.ping}`}></span>
                </span>

                <div className="flex gap-3">
                  <div className={`p-2 rounded-lg self-start ${styles.iconContainer}`}>
                    {getAlertIcon(alert.alert_type)}
                  </div>
                  <div className="flex-1 min-w-0 pr-4">
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <span className="font-bold text-slate-200 text-xs tracking-wide">
                        {alert.alert_type.replace("_", " ")}
                      </span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.25 rounded uppercase tracking-wider ${styles.badge}`}>
                        {alert.severity}
                      </span>
                    </div>

                    <p className="text-slate-300 text-xs leading-relaxed mb-3">
                      {alert.message}
                    </p>

                    <div className="flex items-center justify-between gap-4">
                      <span className="text-[10px] text-slate-500 font-medium">
                        {new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                      <button
                        onClick={() => handleDismiss(alert.id)}
                        disabled={processingId !== null}
                        className="py-1 px-2.5 rounded bg-slate-950 hover:bg-slate-900 border border-slate-800 text-[10px] font-semibold text-slate-400 hover:text-slate-200 transition-all flex items-center gap-1"
                      >
                        {processingId === alert.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <X className="h-3 w-3" />
                        )}
                        Acknowledge
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
