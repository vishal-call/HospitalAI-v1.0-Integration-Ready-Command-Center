"use client";

import React, { useEffect, useState } from "react";
import { 
  fetchWards, 
  fetchPatients, 
  admitPatient, 
  fetchPendingRecommendations,
  actionRecommendation,
  fetchActiveAlerts,
  acknowledgeAlert,
  fetchPartnerHospitals,
  Ward, 
  Patient, 
  PatientStatus,
  RecommendationDetail,
  Alert,
  PartnerHospital
} from "@/lib/api";
import WardOverview from "@/components/WardOverview";
import PatientTable from "@/components/PatientTable";
import ActionCenter from "@/components/ActionCenter";
import AlertFeed from "@/components/AlertFeed";
import PartnerNetwork from "@/components/PartnerNetwork";
import { PlusCircle, Activity, RefreshCw, Radio, UserPlus, LogOut, ShieldCheck, ShieldAlert, Heart, AlertOctagon, Layers, PlayCircle } from "lucide-react";
import { useAuth } from "../lib/AuthContext";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useWebSocket } from "@/hooks/useWebSocket";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from "recharts";
import Link from "next/link";

const admitSchema = z.object({
  name: z.string().min(1, "Patient name is required").max(100, "Name must be <= 100 characters"),
  age: z.number({ invalid_type_error: "Must be a valid integer" })
    .int()
    .min(0, "Age must be >= 0")
    .max(120, "Age must be <= 120"),
  gender: z.string().min(1, "Gender selection is required"),
  admission_reason: z.string().min(1, "Admission reason is required").max(255, "Reason must be <= 255 characters"),
  status: z.enum(["STABLE", "SERIOUS", "CRITICAL"]),
  target_ward_id: z.number({ invalid_type_error: "Must select a target ward" }).int(),
});

type AdmitFormData = z.infer<typeof admitSchema>;

// Static analytical mock history for trend rendering
const occupancyHistory = [
  { name: "00:00", ICU: 70, Emergency: 50, General: 60 },
  { name: "04:00", ICU: 75, Emergency: 65, General: 62 },
  { name: "08:00", ICU: 85, Emergency: 80, General: 65 },
  { name: "12:00", ICU: 90, Emergency: 72, General: 68 },
  { name: "16:00", ICU: 80, Emergency: 68, General: 70 },
  { name: "20:00", ICU: 85, Emergency: 75, General: 67 },
];

export default function DashboardPage() {
  const { user, loading: authLoading, logout } = useAuth();
  const [wards, setWards] = useState<Ward[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationDetail[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [partnerHospitals, setPartnerHospitals] = useState<PartnerHospital[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Admission Modal State & Idempotency Key
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [admitLoading, setAdmitLoading] = useState(false);
  const [admitError, setAdmitError] = useState<string | null>(null);
  const [admitIdempotencyKey, setAdmitIdempotencyKey] = useState<string>("");

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AdmitFormData>({
    resolver: zodResolver(admitSchema),
    defaultValues: {
      name: "",
      age: 45,
      gender: "Male",
      admission_reason: "",
      status: "STABLE",
      target_ward_id: 3,
    }
  });

  // Generate a fresh idempotency key when the admission modal opens
  useEffect(() => {
    if (isModalOpen) {
      setAdmitIdempotencyKey(window.crypto.randomUUID());
    }
  }, [isModalOpen]);

  // Load Initial REST Data
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [wardsData, patientsData, recsData, alertsData, partnersData] = await Promise.all([
        fetchWards(),
        fetchPatients(),
        fetchPendingRecommendations(),
        fetchActiveAlerts(),
        fetchPartnerHospitals()
      ]);
      setWards(wardsData);
      setPatients(patientsData);
      setRecommendations(recsData);
      setAlerts(alertsData);
      setPartnerHospitals(partnersData);
    } catch (err: any) {
      setError(err.message || "Failed to retrieve telemetry data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user) return;
    loadData();
  }, [user]);

  // WebSockets Live Listener - Binds streams directly into local React state arrays
  const wsUrl = typeof window !== "undefined" && user ? `ws://${window.location.hostname}:8000/ws/dashboard` : "";
  const { connected: wsConnected, metrics: wsMetrics } = useWebSocket(
    wsUrl,
    (payload) => {
      console.log(`WebSocket event stream received: ${payload.type}`, payload);

      if (payload.type === "PATIENT_ADMITTED") {
        const newPatient = payload.data;
        setPatients((prev) => [newPatient, ...prev.filter(p => p.id !== newPatient.id)]);
        if (payload.recommendation) {
          setRecommendations((prev) => [payload.recommendation, ...prev.filter(r => r.id !== payload.recommendation.id)]);
        }
        // background sync to verify bed/ward states
        fetchWards().then(setWards);
      } 
      
      else if (payload.type === "PATIENT_UPDATED") {
        const updated = payload.data;
        setPatients((prev) => prev.map(p => p.id === updated.patient_id ? { ...p, ...updated } : p));
        if (payload.recommendation) {
          setRecommendations((prev) => [payload.recommendation, ...prev.filter(r => r.id !== payload.recommendation.id)]);
        }
        fetchWards().then(setWards);
      } 
      
      else if (payload.type === "RECOMMENDATION_ACTIONED") {
        const actionedId = payload.data.recommendation_id;
        setRecommendations((prev) => prev.filter(r => r.id !== actionedId));
        // Refresh wards and patients to show correct bed status
        fetchWards().then(setWards);
        fetchPatients().then(setPatients);
      } 
      
      else if (payload.type === "ALERT_TRIGGERED") {
        // payload.data is a list of Alerts
        setAlerts((prev) => {
          const incoming = payload.data as Alert[];
          const filtered = prev.filter(a => !incoming.find(i => i.id === a.id));
          return [...incoming, ...filtered];
        });
      } 
      
      else if (payload.type === "RECOMMENDATION_GENERATED" || payload.type === "SHADOW_RECOMMENDATION_GENERATED") {
        const newRec = payload.data as RecommendationDetail;
        setRecommendations((prev) => [newRec, ...prev.filter(r => r.id !== newRec.id)]);
      }
      
      else if (payload.type === "ALERT_ACKNOWLEDGED") {
        const ackId = payload.data.alert_id;
        setAlerts((prev) => prev.filter(a => a.id !== ackId));
      } 
      
      else if (payload.type === "BED_UPDATED") {
        const updatedBed = payload.data;
        setWards((prevWards) => 
          prevWards.map((w) => {
            if (w.id === updatedBed.ward_id) {
              const updatedBeds = w.beds?.map((b) => 
                b.id === updatedBed.bed_id 
                  ? { ...b, status: updatedBed.status, patient_id: updatedBed.patient_id, patient: updatedBed.patient } 
                  : b
              ) || [];
              return { ...w, beds: updatedBeds };
            }
            return w;
          })
        );
      }

      else if (payload.type === "DELTA_REHYDRATION") {
        const { alerts: deltaAlerts, recommendations: deltaRecs } = payload.data;
        if (deltaAlerts && deltaAlerts.length > 0) {
          setAlerts((prev) => {
            const filtered = prev.filter(a => !deltaAlerts.find((da: any) => da.id === a.id));
            return [...deltaAlerts, ...filtered];
          });
        }
        if (deltaRecs && deltaRecs.length > 0) {
          setRecommendations((prev) => {
            const filtered = prev.filter(r => !deltaRecs.find((dr: any) => dr.id === r.id));
            return [...deltaRecs, ...filtered];
          });
        }
        // background sync database collections
        fetchWards().then(setWards);
        fetchPatients().then(setPatients);
      }
    }
  );

  const handleAdmitSubmit = async (data: AdmitFormData) => {
    try {
      setAdmitLoading(true);
      setAdmitError(null);
      await admitPatient(data, admitIdempotencyKey);
      setIsModalOpen(false);
      reset();
      await loadData();
    } catch (err: any) {
      setAdmitError(err.message || "Admission request failed.");
    } finally {
      setAdmitLoading(false);
    }
  };

  // Dynamic stats calculation for premium KPI panel
  const totalPatients = patients.length;
  const criticalCount = patients.filter(p => p.status === "CRITICAL").length;
  const seriousCount = patients.filter(p => p.status === "SERIOUS").length;
  const stableCount = patients.filter(p => p.status === "STABLE").length;

  const icuWard = wards.find(w => w.type === "ICU");
  const icuOccupancyRate = icuWard ? Math.round((icuWard.occupied_beds_count / icuWard.capacity) * 100) : 0;
  const emergencyCount = wards.find(w => w.type === "EMERGENCY")?.occupied_beds_count || 0;
  const availableBedsCount = wards.reduce((sum, w) => sum + (w.capacity - w.occupied_beds_count), 0);
  const activeAlertsCount = alerts.length;

  const ewsDistribution = [
    { status: "Stable (< 4.0)", count: patients.filter(p => p.criticality_score < 4.0).length },
    { status: "Serious (4.0 - 7.9)", count: patients.filter(p => p.criticality_score >= 4.0 && p.criticality_score < 8.0).length },
    { status: "Critical (>= 8.0)", count: patients.filter(p => p.criticality_score >= 8.0).length },
  ];

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4 text-slate-400">
        <RefreshCw className="h-8 w-8 animate-spin text-emerald-400" />
        <p className="font-semibold text-sm">Verifying staff security authorization...</p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      
      {/* Reconnecting Glassmorphic Banner */}
      {!wsConnected && (
        <div className="bg-rose-950/80 border-b border-rose-500/20 text-rose-200 text-xs px-4 py-2 flex items-center justify-center gap-2 backdrop-blur-md sticky top-0 z-50 animate-in slide-in-from-top duration-300">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
          </span>
          <span className="font-bold tracking-wide uppercase">Reconnecting to live telemetry feed...</span>
        </div>
      )}

      {/* Background Gradient Ornaments */}
      <div className="absolute top-0 left-0 w-full h-[600px] bg-radial-gradient from-indigo-900/10 via-slate-950/0 to-slate-950/0 pointer-events-none" />
      {/* Main Dashboard Workspace */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 space-y-8">
        
        {/* Page Actions */}
        <div className="flex justify-end items-center gap-4">
          <button
            onClick={loadData}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:border-slate-700 transition-all text-slate-300"
            title="Refresh Data"
          >
            <RefreshCw className="h-4 w-4" />
          </button>

          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white rounded-xl font-semibold text-sm shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/35 transition-all duration-300 scale-100 hover:scale-[1.02]"
          >
            <UserPlus className="h-4 w-4" />
            Admit Patient
          </button>
        </div>
        
        {/* KPI Cards section */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-xl">
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5">
              <Heart className="h-3.5 w-3.5 text-emerald-400" />
              Patient Census
            </span>
            <div className="text-3xl font-extrabold text-white mt-2 tracking-tight flex items-baseline gap-2">
              {totalPatients}
              <span className="text-xs font-normal text-slate-500">
                ({criticalCount}c / {seriousCount}s / {stableCount}st)
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium mt-1">Active bed placement sessions</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-xl">
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-indigo-400" />
              Beds Available
            </span>
            <div className="text-3xl font-extrabold text-white mt-2 tracking-tight">
              {availableBedsCount}
            </div>
            <p className="text-xs text-slate-500 font-medium mt-1">Vacant emergency/ward spaces</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-xl">
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5">
              <ShieldAlert className="h-3.5 w-3.5 text-rose-450" />
              ICU Utilization
            </span>
            <div className="text-3xl font-extrabold text-rose-400 mt-2 tracking-tight">
              {icuOccupancyRate}%
            </div>
            <p className="text-xs text-rose-500/80 font-medium mt-1">Requires critical triage monitoring</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-xl">
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5">
              <AlertOctagon className="h-3.5 w-3.5 text-amber-400 animate-pulse" />
              Active Alert Feed
            </span>
            <div className="text-3xl font-extrabold text-amber-400 mt-2 tracking-tight">
              {activeAlertsCount}
            </div>
            <p className="text-xs text-amber-500/80 font-medium mt-1">Requires Human-in-the-Loop review</p>
          </div>
        </section>

        {/* Analytics Charts Panel */}
        {!loading && (
          <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* EWS Distribution Graph */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
              <h3 className="text-sm font-bold text-white mb-4">Patient Criticality EWS Distribution</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ewsDistribution}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="status" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                    <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", color: "#f8fafc" }} />
                    <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Occupancy Trends Graph */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
              <h3 className="text-sm font-bold text-white mb-4">24-Hour Ward Occupancy Trends</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={occupancyHistory}>
                    <defs>
                      <linearGradient id="colorIcu" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorEmergency" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", color: "#f8fafc" }} />
                    <Legend verticalAlign="top" height={36} />
                    <Area type="monotone" dataKey="ICU" stroke="#f43f5e" fillOpacity={1} fill="url(#colorIcu)" strokeWidth={2} />
                    <Area type="monotone" dataKey="Emergency" stroke="#f59e0b" fillOpacity={1} fill="url(#colorEmergency)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>
        )}

        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-4 text-slate-400">
            <RefreshCw className="h-8 w-8 animate-spin text-indigo-400" />
            <p className="font-semibold text-sm">Synchronizing clinical dashboard telemetry...</p>
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-6 text-rose-400 flex flex-col gap-2">
            <h3 className="font-bold text-lg">Platform Error</h3>
            <p>{error}</p>
            <button onClick={loadData} className="mt-2 text-sm underline text-left hover:text-rose-300">
              Retry Connection
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Main Content Pane */}
            <div className="lg:col-span-8 space-y-8">
              {/* Wards Telemetry section */}
              <section className="space-y-4">
                <h2 className="text-lg font-bold text-slate-200 tracking-tight flex items-center gap-2">
                  <Radio className="h-4 w-4 text-indigo-400 animate-pulse" />
                  Hospital Ward Utilization Overview
                </h2>
                <ErrorBoundary title="Ward Overview Telemetry">
                  <WardOverview wards={wards} onBedUpdate={loadData} />
                </ErrorBoundary>
              </section>

              {/* Partner Network Status section */}
              <section className="space-y-4">
                <ErrorBoundary title="Partner Network Status">
                  <PartnerNetwork hospitals={partnerHospitals} />
                </ErrorBoundary>
              </section>

              {/* Patients list section */}
              <section className="space-y-4">
                <ErrorBoundary title="Patient Records Registry">
                  <PatientTable patients={patients} onVitalsLogged={loadData} />
                </ErrorBoundary>
              </section>
            </div>

            {/* Action Center Sidebar Pane */}
            <div className="lg:col-span-4 lg:sticky lg:top-24 space-y-8">
              <ErrorBoundary title="Active Deterioration Alerts">
                <AlertFeed 
                  alerts={alerts}
                  onAcknowledgeComplete={loadData}
                  acknowledgeAlert={acknowledgeAlert}
                />
              </ErrorBoundary>
              
              <ErrorBoundary title="HITL Relocation Actions">
                <ActionCenter 
                  recommendations={recommendations}
                  onActionComplete={loadData}
                  actionRecommendation={actionRecommendation}
                  activeUserId={user.id}
                  userRole={user.role}
                />
              </ErrorBoundary>
            </div>
          </div>
        )}
      </div>

      {/* Patient Admission Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl relative">
            <h3 className="text-xl font-bold text-slate-100 tracking-tight mb-4">Admit New Patient</h3>
            
            {admitError && (
              <div className="p-3 mb-4 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
                {admitError}
              </div>
            )}

            <form onSubmit={handleSubmit(handleAdmitSubmit)} className="space-y-4">
              <div>
                <label className="block text-slate-400 text-xs font-semibold mb-1">PATIENT FULL NAME</label>
                <input
                  type="text"
                  {...register("name")}
                  placeholder="e.g. Samuel Henderson"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 placeholder-slate-600 text-sm focus:outline-none focus:border-slate-700"
                />
                {errors.name && (
                  <p className="text-rose-400 text-xs mt-1">{errors.name.message}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 text-xs font-semibold mb-1">AGE</label>
                  <input
                    type="number"
                    {...register("age", { valueAsNumber: true })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
                  />
                  {errors.age && (
                    <p className="text-rose-400 text-xs mt-1">{errors.age.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-slate-400 text-xs font-semibold mb-1">GENDER</label>
                  <select
                    {...register("gender")}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                  {errors.gender && (
                    <p className="text-rose-400 text-xs mt-1">{errors.gender.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-slate-400 text-xs font-semibold mb-1">ADMISSION DIAGNOSIS / REASON</label>
                <textarea
                  {...register("admission_reason")}
                  placeholder="Describe details for clinical intake..."
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 placeholder-slate-600 text-sm focus:outline-none focus:border-slate-700 resize-none"
                />
                {errors.admission_reason && (
                  <p className="text-rose-400 text-xs mt-1">{errors.admission_reason.message}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 text-xs font-semibold mb-1">INITIAL STATUS</label>
                  <select
                    {...register("status")}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-slate-700 font-semibold"
                  >
                    <option value="STABLE" className="text-emerald-500">STABLE</option>
                    <option value="SERIOUS" className="text-amber-500">SERIOUS</option>
                    <option value="CRITICAL" className="text-rose-500">CRITICAL</option>
                  </select>
                  {errors.status && (
                    <p className="text-rose-400 text-xs mt-1">{errors.status.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-slate-400 text-xs font-semibold mb-1">TARGET WARD</label>
                  <select
                    {...register("target_ward_id", { valueAsNumber: true })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
                  >
                    {wards.map((ward) => (
                      <option key={ward.id} value={ward.id}>
                        {ward.name} ({ward.type})
                      </option>
                    ))}
                  </select>
                  {errors.target_ward_id && (
                     <p className="text-rose-400 text-xs mt-1">{errors.target_ward_id.message}</p>
                  )}
                </div>
              </div>

              <div className="flex gap-4 justify-end mt-6">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={admitLoading}
                  className="px-4 py-2.5 bg-indigo-500 hover:bg-indigo-600 disabled:bg-indigo-500/50 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-indigo-600/10 flex items-center gap-2"
                >
                  {admitLoading && <RefreshCw className="h-4 w-4 animate-spin" />}
                  Confirm Intake
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
