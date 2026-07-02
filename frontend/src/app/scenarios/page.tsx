"use client";

import React, { useState } from "react";
import { useAuth } from "../../lib/AuthContext";
import { triggerScenario } from "@/lib/api";
import { ShieldAlert, ArrowLeft, RefreshCw, Database, Users, AlertOctagon, Heart, CheckCircle2, ShieldCheck, PlayCircle } from "lucide-react";
import Link from "next/link";

interface ScenarioCard {
  id: string;
  name: string;
  description: string;
  impact: string;
  icon: React.ComponentType<any>;
  color: string;
  btnText: string;
}

export default function ScenariosPage() {
  const { user, loading: authLoading } = useAuth();
  
  const [loadingScenario, setLoadingScenario] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const showToast = (type: "success" | "error", message: string) => {
    setToast({ type, message });
    setTimeout(() => {
      setToast(null);
    }, 4000);
  };

  const handleTrigger = async (scenarioId: string) => {
    try {
      setLoadingScenario(scenarioId);
      const res = await triggerScenario(scenarioId);
      showToast("success", res.message || "Scenario executed successfully.");
    } catch (err: any) {
      showToast("error", err.message || "Failed to trigger scenario.");
    } finally {
      setLoadingScenario(null);
    }
  };

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
              You do not possess the required administrative clearance to manipulate clinical scenarios or database baseline configurations. This action has been flagged.
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

  const scenarioCards: ScenarioCard[] = [
    {
      id: "reset_data",
      name: "Restore Database Baseline",
      description: "Purges all patient logs, alert overrides, and audit trails. Reseeds the database to a clean, default seeding state.",
      impact: "Destructive. Wipes all live states and resets occupancy charts.",
      icon: Database,
      color: "border-indigo-500/20 hover:border-indigo-500/50 bg-indigo-500/5 text-indigo-400",
      btnText: "Wipe & Reseed DB"
    },
    {
      id: "fill_icu",
      name: "ICU saturation (100% capacity)",
      description: "Instantly floods vacant ICU beds with dummy patients possessing serious scores. Triggers high-capacity alarms immediately.",
      impact: "Forces inter-hospital transfer recommendations for new critical admissions.",
      icon: Users,
      color: "border-amber-500/20 hover:border-amber-500/50 bg-amber-500/5 text-amber-400",
      btnText: "Fill ICU Wards"
    },
    {
      id: "spawn_critical_emergency",
      name: "Trigger Emergency Case",
      description: "Admits a patient directly to an emergency bed with severe oxygen depletion (SpO2 85%, HR 135). Instantly calculates EWS 10.0 score.",
      impact: "Triggers Score Spike & Low Oxygen warnings. Demands ICU transfer request.",
      icon: AlertOctagon,
      color: "border-rose-500/20 hover:border-rose-500/50 bg-rose-500/5 text-rose-400",
      btnText: "Spawn Critical Patient"
    },
    {
      id: "spawn_stable_icu",
      name: "Stabilize ICU Patient",
      description: "Locates an active patient in the ICU ward and updates vitals to normal bounds (Score 2.0). Creates a step-down candidate.",
      impact: "Prompts step-down recommendation evaluations to release critical care resource.",
      icon: Heart,
      color: "border-emerald-500/20 hover:border-emerald-500/50 bg-emerald-500/5 text-emerald-400",
      btnText: "Stabilize Patient"
    },
    {
      id: "clear_alerts",
      name: "Resolve Alerts Ledger",
      description: "Acknowledges all active clinical alerts and rejects outstanding patient recommendations in the database.",
      impact: "Purges current command center warning feeds to a clean, idle state.",
      icon: ShieldCheck,
      color: "border-sky-500/20 hover:border-sky-500/50 bg-sky-500/5 text-sky-400",
      btnText: "Clear Dashboard Feeds"
    },
    {
      id: "trigger_chained_chain",
      name: "Trigger ICU Step-Down Chain",
      description: "Wipes database, fills the ICU, places a stable patient in ICU bed 12, and admits a critical GW patient, triggering a chained relocation.",
      impact: "Simulates dual-step step-down and escalation workflows atomically.",
      icon: PlayCircle,
      color: "border-purple-500/20 hover:border-purple-500/50 bg-purple-500/5 text-purple-400",
      btnText: "Trigger Chain"
    }
  ];

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
              Demo Scenario Controls
              <span className="text-[10px] bg-emerald-500/10 text-emerald-400 font-bold px-2 py-0.5 rounded border border-emerald-500/25 uppercase tracking-wider">Simulations</span>
            </h1>
            <p className="text-xs text-slate-400 font-medium">Manipulate database states instantly to evaluate edge cases, triggers, and transfers.</p>
          </div>
        </div>
      </header>

      {/* Main Panel Content */}
      <div className="max-w-5xl w-full mx-auto p-6 md:p-8 space-y-6 flex-1">
        
        {/* Floating notifications */}
        {toast && (
          <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4.5 py-3.5 rounded-xl border shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-bottom-5 duration-200 max-w-sm ${
            toast.type === "success" 
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" 
              : "bg-rose-500/10 border-rose-500/20 text-rose-400"
          }`}>
            {toast.type === "success" ? <CheckCircle2 className="h-5 w-5 shrink-0" /> : <AlertOctagon className="h-5 w-5 shrink-0" />}
            <p className="text-xs font-bold leading-normal">{toast.message}</p>
          </div>
        )}

        <div className="bg-slate-900/40 border border-slate-850 rounded-2xl p-5 md:p-6 backdrop-blur-xl flex flex-col md:flex-row gap-5 items-start md:items-center justify-between">
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-white">Scenario Simulation Guidelines</h3>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed font-medium">
              These commands force immediate state modifications in the active database. When a scenario is executed, the backend broadcasts changes across the WebSocket pipeline, syncing client monitors instantly without manual reloads.
            </p>
          </div>
        </div>

        {/* Scenarios Grid */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {scenarioCards.map((sc) => {
            const Icon = sc.icon;
            const isExecuting = loadingScenario === sc.id;

            return (
              <div
                key={sc.id}
                className={`rounded-2xl border bg-slate-900/20 p-6 flex flex-col justify-between transition-all backdrop-blur-md hover:bg-slate-900/40 ${sc.color}`}
              >
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-850 flex items-center justify-center">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h4 className="font-extrabold text-sm text-white tracking-tight">{sc.name}</h4>
                  </div>
                  
                  <div className="space-y-2">
                    <p className="text-slate-350 text-xs font-medium leading-relaxed">{sc.description}</p>
                    <div className="text-[10px] bg-slate-950/80 rounded-lg p-2.5 border border-slate-850 text-slate-400">
                      <span className="font-bold text-slate-500 mr-1 uppercase">IMPACT:</span>
                      {sc.impact}
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-850/50 flex items-center justify-end">
                  <button
                    onClick={() => handleTrigger(sc.id)}
                    disabled={loadingScenario !== null}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-slate-950 border border-slate-800 hover:border-slate-700 disabled:opacity-40 text-slate-200 hover:text-white rounded-xl text-xs font-bold transition-all shadow-md active:scale-95"
                  >
                    {isExecuting ? (
                      <RefreshCw className="h-3.5 w-3.5 animate-spin text-indigo-400" />
                    ) : (
                      <PlayCircle className="h-3.5 w-3.5" />
                    )}
                    {isExecuting ? "Executing..." : sc.btnText}
                  </button>
                </div>
              </div>
            );
          })}
        </section>
      </div>
    </main>
  );
}
