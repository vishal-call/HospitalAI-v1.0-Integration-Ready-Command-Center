"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "../../lib/AuthContext";
import { fetchAuditLogs, fetchHealthMetrics, AuditLog, HealthMetrics } from "@/lib/api";
import { ShieldAlert, Activity, RefreshCw, ArrowLeft, Search, FileSpreadsheet, Server, Radio, Database, AlertCircle } from "lucide-react";
import Link from "next/link";

export default function ObservabilityPage() {
  const { user, loading: authLoading } = useAuth();
  
  const [metrics, setMetrics] = useState<HealthMetrics | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Search Filters
  const [userIdFilter, setUserIdFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [correlationFilter, setCorrelationFilter] = useState("");
  
  // Collapsed JSON row state
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const loadObservabilityData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [metricsData, logsData] = await Promise.all([
        fetchHealthMetrics(),
        fetchAuditLogs()
      ]);
      setMetrics(metricsData);
      setLogs(logsData);
    } catch (err: any) {
      setError(err.message || "Failed to load observability data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role === "ADMIN") {
      loadObservabilityData();
      const interval = setInterval(loadObservabilityData, 10000); // refresh every 10s
      return () => clearInterval(interval);
    }
  }, [user]);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4 text-slate-400">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-400" />
        <p className="font-semibold text-sm">Verifying administrator credentials...</p>
      </div>
    );
  }

  // Strict RBAC route protection
  if (!user || user.role !== "ADMIN") {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6 selection:bg-rose-500/30 selection:text-rose-250">
        <div className="w-full max-w-md rounded-2xl border border-rose-500/20 bg-rose-500/5 p-8 text-center space-y-5 shadow-2xl backdrop-blur-xl animate-in zoom-in-95 duration-200">
          <div className="mx-auto w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <div className="space-y-2">
            <h1 className="text-xl font-bold tracking-tight text-white">403 Forbidden Access</h1>
            <p className="text-slate-400 text-xs leading-relaxed font-medium">
              You do not possess the required administrative clearance to access the platform audit trails and telemetry systems. This security incident has been logged.
            </p>
          </div>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 hover:text-white rounded-xl text-xs font-bold transition-all shadow-lg"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Return to Command Center
          </Link>
        </div>
      </main>
    );
  }

  // Filter logs locally based on search variables
  const filteredLogs = logs.filter((log) => {
    return (
      (!userIdFilter || log.user_id?.toLowerCase().includes(userIdFilter.toLowerCase())) &&
      (!actionFilter || log.action.toLowerCase().includes(actionFilter.toLowerCase())) &&
      (!entityFilter || log.entity_type.toLowerCase().includes(entityFilter.toLowerCase())) &&
      (!correlationFilter || log.correlation_id?.toLowerCase().includes(correlationFilter.toLowerCase()))
    );
  });

  const getActionBadgeStyle = (action: string) => {
    if (action.includes("APPROVE")) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/25";
    if (action.includes("REJECT") || action.includes("CONFLICT")) return "bg-rose-500/10 text-rose-400 border-rose-500/25";
    if (action.includes("ADMIT")) return "bg-sky-500/10 text-sky-400 border-sky-500/25";
    if (action.includes("ACKNOWLEDGE")) return "bg-amber-500/10 text-amber-400 border-amber-500/25";
    return "bg-indigo-500/10 text-indigo-400 border-indigo-500/25";
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      
      {/* Background gradient */}
      <div className="absolute top-0 left-0 w-full h-[600px] bg-radial-gradient from-slate-900/20 via-slate-950/0 to-slate-950/0 pointer-events-none" />

      {/* Header bar */}
      <header className="border-b border-slate-850 bg-slate-950/70 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white transition-all"
            title="Return to Command Center"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="font-extrabold text-lg tracking-tight text-white flex items-center gap-2">
              Observability & Distributed Traces
              <span className="text-[10px] bg-indigo-500/10 text-indigo-400 font-bold px-2 py-0.5 rounded border border-indigo-500/25 uppercase tracking-wider">ADMIN OVERVIEW</span>
            </h1>
            <p className="text-xs text-slate-400 font-medium">Real-time database transaction pools, transaction retry telemetry, and audit event logs.</p>
          </div>
        </div>

        <button
          onClick={loadObservabilityData}
          disabled={loading}
          className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 rounded-xl text-xs font-semibold shadow transition-all"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-indigo-400' : 'text-slate-400'}`} />
          Refresh
        </button>
      </header>

      {/* Layout Content */}
      <div className="max-w-7xl w-full mx-auto p-6 md:p-8 space-y-8 flex-1">
        
        {error && (
          <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Metrics Row */}
        <section className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-xl">
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5">
              <Database className="h-3.5 w-3.5 text-indigo-400" />
              DB Connections
            </span>
            <div className="text-2xl font-extrabold text-white mt-2 tracking-tight">
              {metrics ? `${metrics.db_checked_out} / ${metrics.db_pool_size}` : "..."}
            </div>
            <p className="text-[10px] text-slate-500 font-medium mt-1">Checked out / pool size (overflow: {metrics?.db_overflow || 0})</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-xl">
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5">
              <Radio className="h-3.5 w-3.5 text-emerald-400" />
              Live WS Clients
            </span>
            <div className="text-2xl font-extrabold text-white mt-2 tracking-tight">
              {metrics ? metrics.active_websocket_clients : "..."}
            </div>
            <p className="text-[10px] text-slate-500 font-medium mt-1">Connected dashboard sessions</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-xl">
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-amber-400" />
              Transaction Retries
            </span>
            <div className="text-2xl font-extrabold text-amber-400 mt-2 tracking-tight">
              {metrics ? metrics.recent_transaction_retries : "..."}
            </div>
            <p className="text-[10px] text-slate-500 font-medium mt-1">Tenacity rollback deadlock retries</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-xl">
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5">
              <Server className="h-3.5 w-3.5 text-indigo-400" />
              Trace Volume
            </span>
            <div className="text-2xl font-extrabold text-white mt-2 tracking-tight">
              {logs.length}
            </div>
            <p className="text-[10px] text-slate-500 font-medium mt-1">Total indexed audit traces</p>
          </div>
        </section>

        {/* Audit Filter Panel */}
        <section className="border border-slate-850 bg-slate-900/40 rounded-2xl p-5 backdrop-blur-md grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-[10px] font-bold text-slate-450 uppercase tracking-wider mb-1.5">USER ID</label>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-650" />
              <input
                type="text"
                placeholder="e.g. coordinator"
                value={userIdFilter}
                onChange={(e) => setUserIdFilter(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-650 focus:outline-none focus:border-slate-700 font-medium"
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-450 uppercase tracking-wider mb-1.5">ACTION</label>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-650" />
              <input
                type="text"
                placeholder="e.g. ACTION_APPROVE"
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-650 focus:outline-none focus:border-slate-700 font-medium"
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-450 uppercase tracking-wider mb-1.5">ENTITY TYPE</label>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-650" />
              <input
                type="text"
                placeholder="e.g. patient"
                value={entityFilter}
                onChange={(e) => setEntityFilter(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-650 focus:outline-none focus:border-slate-700 font-medium"
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-450 uppercase tracking-wider mb-1.5">CORRELATION ID</label>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-650" />
              <input
                type="text"
                placeholder="Search trace ID..."
                value={correlationFilter}
                onChange={(e) => setCorrelationFilter(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-650 focus:outline-none focus:border-slate-700 font-medium"
              />
            </div>
          </div>
        </section>

        {/* Audit Logs Table Ledger */}
        <section className="border border-slate-850 bg-slate-900/20 rounded-2xl overflow-hidden backdrop-blur-md">
          <div className="px-6 py-4 border-b border-slate-850 bg-slate-900/40 flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <FileSpreadsheet className="h-4.5 w-4.5 text-indigo-400" />
              System Audit Trail Ledger
            </h3>
            <span className="text-[10px] font-semibold bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full uppercase tracking-wider">
              {filteredLogs.length} matching events
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-950/80 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-850">
                  <th className="px-6 py-3.5">Timestamp</th>
                  <th className="px-6 py-3.5">Action</th>
                  <th className="px-6 py-3.5">User</th>
                  <th className="px-6 py-3.5">Entity</th>
                  <th className="px-6 py-3.5">Correlation Trace ID</th>
                  <th className="px-6 py-3.5 text-right">Data payload</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-850/60 text-xs text-slate-350">
                {filteredLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-slate-500 font-medium">
                      No matching audit records located in system trace index.
                    </td>
                  </tr>
                ) : (
                  filteredLogs.map((log) => {
                    const isExpanded = expandedRow === log.id;
                    const logDate = new Date(log.created_at).toLocaleString();

                    return (
                      <React.Fragment key={log.id}>
                        <tr className="hover:bg-slate-900/30 transition-colors">
                          <td className="px-6 py-3.5 font-mono text-[11px] text-slate-400">{logDate}</td>
                          <td className="px-6 py-3.5">
                            <span className={`inline-block text-[10px] font-extrabold px-2 py-0.5 rounded border uppercase tracking-wider ${getActionBadgeStyle(log.action)}`}>
                              {log.action}
                            </span>
                          </td>
                          <td className="px-6 py-3.5 font-semibold text-slate-200">{log.user_id || "System"}</td>
                          <td className="px-6 py-3.5">
                            <span className="font-mono text-slate-400">{log.entity_type}</span>
                            {log.entity_id !== null && (
                              <span className="ml-1 bg-slate-800/80 border border-slate-700/50 text-[10px] text-indigo-400 px-1.5 py-0.5 rounded-md font-bold font-mono">
                                ID {log.entity_id}
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-3.5">
                            <button
                              onClick={() => setCorrelationFilter(log.correlation_id || "")}
                              className="font-mono text-[10px] text-indigo-400 bg-indigo-500/5 border border-indigo-500/10 hover:border-indigo-500/40 px-2 py-0.5 rounded transition-all"
                            >
                              {log.correlation_id || "N/A"}
                            </button>
                          </td>
                          <td className="px-6 py-3.5 text-right">
                            <button
                              onClick={() => setExpandedRow(isExpanded ? null : log.id)}
                              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 underline"
                            >
                              {isExpanded ? "Hide Details" : "View Details"}
                            </button>
                          </td>
                        </tr>

                        {isExpanded && (
                          <tr className="bg-slate-950/40">
                            <td colSpan={6} className="px-6 py-4">
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                                <div className="space-y-1.5">
                                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">STATE BEFORE TRANSACTION</span>
                                  <pre className="bg-slate-950 border border-slate-850 rounded-xl p-3.5 overflow-x-auto text-[11px] text-rose-350 max-h-[160px] scrollbar-thin">
                                    {log.before_data ? JSON.stringify(JSON.parse(log.before_data), null, 2) : "NULL"}
                                  </pre>
                                </div>
                                <div className="space-y-1.5">
                                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">STATE AFTER TRANSACTION</span>
                                  <pre className="bg-slate-950 border border-slate-850 rounded-xl p-3.5 overflow-x-auto text-[11px] text-emerald-350 max-h-[160px] scrollbar-thin">
                                    {log.after_data ? JSON.stringify(JSON.parse(log.after_data), null, 2) : "NULL"}
                                  </pre>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
