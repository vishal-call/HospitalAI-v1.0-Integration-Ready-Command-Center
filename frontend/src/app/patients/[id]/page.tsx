"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { fetchPatient, Patient, ScoreRecord } from "@/lib/api";
import ScoreExplanationCard from "@/components/ScoreExplanationCard";
import ClinicalTimeline from "@/components/ClinicalTimeline";
import PatientBaselineCard from "@/components/PatientBaselineCard";
import { ArrowLeft, User, Activity, Loader2 } from "lucide-react";
import Link from "next/link";
import { useWebSocket } from "@/hooks/useWebSocket";

export default function PatientDetailsPage() {
  const params = useParams();
  const id = parseInt(params.id as string, 10);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [scoreRecord, setScoreRecord] = useState<ScoreRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPatient = async () => {
    try {
      setLoading(true);
      const data = await fetchPatient(id);
      setPatient(data);
      if (data.score_record) {
        setScoreRecord(data.score_record);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load patient details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isNaN(id)) {
      loadPatient();
    }
  }, [id]);

  // Listen for WebSocket updates to this patient's vitals
  const wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
  const wsUrl = typeof window !== "undefined" ? `${wsBaseUrl}/ws/dashboard` : "";
  useWebSocket(wsUrl, (payload: any) => {
    if (payload.type === "PATIENT_UPDATED" && payload.data.patient_id === id) {
      loadPatient(); // reload to get the new score explanation
    }
    if (payload.type === "VITALS_RECORDED" && payload.data.patient_id === id) {
      loadPatient();
    }
    if (payload.type === "DELTA_REHYDRATION") {
       // if we want to be safe, just reload
       loadPatient();
    }
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4 text-slate-400">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
        <p className="font-semibold text-sm">Loading patient dossier...</p>
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4 text-slate-400">
        <p className="text-rose-400">{error || "Patient not found."}</p>
        <Link href="/" className="text-indigo-400 hover:underline">Return to Dashboard</Link>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center gap-4">
        <Link href="/" className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:border-slate-700 transition-all text-slate-400 hover:text-slate-200">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="font-extrabold text-xl tracking-tight text-white flex items-center gap-2">
            Patient Dossier
          </h1>
          <p className="text-xs text-slate-400 font-medium">Detailed Clinical Intelligence</p>
        </div>
      </header>

      <div className="flex-1 max-w-5xl w-full mx-auto p-6 md:p-8 space-y-8">
        {/* Patient Identity Header */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-xl flex items-center gap-6">
          <div className="h-16 w-16 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20 shrink-0">
            <User className="h-8 w-8" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight">{patient.name}</h2>
            <div className="flex items-center gap-4 mt-1 text-sm font-medium text-slate-400">
              <span>{patient.age}y / {patient.gender}</span>
              <span className="w-1.5 h-1.5 rounded-full bg-slate-700"></span>
              <span className="truncate max-w-md">{patient.admission_reason}</span>
            </div>
          </div>
        </div>

        {/* Patient Baseline Config */}
        <section className="space-y-4">
          <PatientBaselineCard patientId={patient.id} />
        </section>

        {/* Score Explanation Card */}
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-slate-200 tracking-tight flex items-center gap-2">
            <Activity className="h-5 w-5 text-indigo-400" />
            Current Clinical Status
          </h2>
          <ScoreExplanationCard scoreRecord={scoreRecord} />
        </section>

        {/* Clinical Timeline */}
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-slate-200 tracking-tight flex items-center gap-2">
            <Activity className="h-5 w-5 text-emerald-400" />
            Clinical Timeline & Audit Trail
          </h2>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-xl">
            <ClinicalTimeline patientId={patient.id} />
          </div>
        </section>
      </div>
    </main>
  );
}
