"use client";

import React, { useState, useEffect } from "react";
import { ArrowLeft, ShieldCheck, AlertCircle, HeartPulse, ShieldAlert, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import ReconciliationQueue from "@/components/ReconciliationQueue";
import { 
  getDataQualityMetrics, 
  getReconciliationIssues, 
  DataQualityMetrics, 
  ReconciliationIssue 
} from "@/lib/api";

export default function DataQualityPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "queue">("overview");
  const [metrics, setMetrics] = useState<DataQualityMetrics | null>(null);
  const [issues, setIssues] = useState<ReconciliationIssue[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [m, i] = await Promise.all([
        getDataQualityMetrics(),
        getReconciliationIssues()
      ]);
      setMetrics(m);
      setIssues(i);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load data");
    } finally {
      setIsLoading(false);
    }
  };

  const handleIssueResolved = (id: number) => {
    // Optimistically update UI
    setIssues(prev => prev.filter(issue => issue.id !== id));
    if (metrics) {
      setMetrics({
        ...metrics,
        active_issues: Math.max(0, metrics.active_issues - 1)
      });
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      <div className="flex items-center justify-between">
        <div>
          <Link href="/integrations" className="text-sm font-medium text-slate-400 hover:text-white flex items-center gap-2 mb-4 transition-colors w-max">
            <ArrowLeft size={16} /> Back to Integration Center
          </Link>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-indigo-500/20 rounded-lg border border-indigo-500/30">
              <ShieldCheck size={24} className="text-indigo-400" />
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight">Data Quality Center</h1>
          </div>
          <p className="text-slate-400">Monitor integration health and resolve external data conflicts.</p>
        </div>
      </div>

      <div className="flex gap-4 border-b border-slate-800 pb-px">
        <button
          onClick={() => setActiveTab("overview")}
          className={`pb-4 px-2 text-sm font-medium transition-colors border-b-2 ${
            activeTab === "overview" 
              ? "border-indigo-500 text-indigo-400" 
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab("queue")}
          className={`pb-4 px-2 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === "queue" 
              ? "border-indigo-500 text-indigo-400" 
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Reconciliation Queue
          {issues.length > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 text-xs">
              {issues.length}
            </span>
          )}
        </button>
      </div>

      {isLoading ? (
        <div className="h-64 flex items-center justify-center text-slate-500">
          Loading metrics...
        </div>
      ) : errorMsg ? (
        <div className="p-6 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400">
          <AlertCircle className="inline-block mr-2" size={20} />
          {errorMsg}
        </div>
      ) : (
        <>
          {activeTab === "overview" && metrics && (
            <div className="space-y-6">
              
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                
                {/* Score Card */}
                <div className="md:col-span-1 p-6 rounded-2xl border border-slate-800 bg-slate-900/50 flex flex-col items-center justify-center text-center shadow-lg">
                  <h3 className="text-slate-400 font-medium mb-4">Data Quality Score</h3>
                  <div className="relative w-32 h-32 flex items-center justify-center rounded-full border-8 border-slate-800">
                    <div 
                      className={`absolute inset-0 rounded-full border-8 ${
                        metrics.data_quality_score >= 90 ? 'border-emerald-500' :
                        metrics.data_quality_score >= 70 ? 'border-amber-500' : 'border-rose-500'
                      }`}
                      style={{ clipPath: `inset(${100 - metrics.data_quality_score}% 0 0 0)` }}
                    />
                    <div className="relative z-10 text-3xl font-bold text-white">
                      {metrics.data_quality_score}<span className="text-lg text-slate-400">%</span>
                    </div>
                  </div>
                </div>

                {/* Metrics Cards */}
                <div className="md:col-span-3 grid grid-cols-1 sm:grid-cols-3 gap-6">
                  
                  <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 shadow-lg flex flex-col justify-between">
                    <div className="flex items-start justify-between">
                      <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400">
                        <HeartPulse size={20} />
                      </div>
                    </div>
                    <div className="mt-4">
                      <div className="text-3xl font-bold text-white">{metrics.missing_vitals}</div>
                      <div className="text-sm text-slate-400 mt-1">Missing Vitals (12h)</div>
                    </div>
                  </div>

                  <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 shadow-lg flex flex-col justify-between">
                    <div className="flex items-start justify-between">
                      <div className="p-2 rounded-lg bg-rose-500/20 text-rose-400">
                        <AlertCircle size={20} />
                      </div>
                    </div>
                    <div className="mt-4">
                      <div className="text-3xl font-bold text-white">{metrics.failed_imports}</div>
                      <div className="text-sm text-slate-400 mt-1">Failed Imports (24h)</div>
                    </div>
                  </div>

                  <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 shadow-lg flex flex-col justify-between">
                    <div className="flex items-start justify-between">
                      <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
                        <ShieldAlert size={20} />
                      </div>
                    </div>
                    <div className="mt-4">
                      <div className="text-3xl font-bold text-white">{metrics.active_issues}</div>
                      <div className="text-sm text-slate-400 mt-1">Active Reconciliation Issues</div>
                    </div>
                  </div>

                </div>
              </div>

            </div>
          )}

          {activeTab === "queue" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-white">Active Conflicts</h2>
                <button 
                  onClick={fetchData}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors"
                >
                  Refresh Queue
                </button>
              </div>
              <ReconciliationQueue 
                issues={issues} 
                onIssueResolved={handleIssueResolved}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
