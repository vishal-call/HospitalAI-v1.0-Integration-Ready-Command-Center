"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";
import { useAdminMetrics } from "@/hooks/useAdminMetrics";
import { 
  ArrowLeft, 
  ShieldAlert, 
  ShieldCheck, 
  PlusCircle, 
  Trash2, 
  Activity, 
  Clock, 
  AlertCircle, 
  CheckCircle,
  Database,
  RefreshCw,
  UserCheck,
  Settings,
  Info
} from "lucide-react";
import { WardType, BedStatus, UserRole } from "@/lib/api";

export default function AdminPage() {
  const { user, loading: authLoading } = useAuth();
  const {
    isLoading,
    error,
    summaryMetrics,
    wardsList,
    bedsList,
    refreshAnalytics,
    refreshWardsAndBeds,
    loadAllData,
    handleAddWard,
    handleRemoveWard,
    handleAddBed,
    handleRemoveBed,
    handleUpdateStaffRole
  } = useAdminMetrics();

  // Toast / Local Notifications state
  const [toastMsg, setToastMsg] = useState<{ text: string; isError: boolean } | null>(null);

  // Modal / Form states
  const [isWardModalOpen, setIsWardModalOpen] = useState(false);
  const [isBedModalOpen, setIsBedModalOpen] = useState(false);
  const [isStaffModalOpen, setIsStaffModalOpen] = useState(false);

  // Form input states
  const [wardForm, setWardForm] = useState({ name: "", type: "ICU" as WardType, capacity: 5 });
  const [bedForm, setBedForm] = useState({ bed_number: "", ward_id: 0, status: "AVAILABLE" as BedStatus });
  const [staffForm, setStaffForm] = useState({ email: "", role: "COORDINATOR" as UserRole });

  const [formSubmitting, setFormSubmitting] = useState(false);

  const showToast = (text: string, isError = false) => {
    setToastMsg({ text, isError });
    setTimeout(() => setToastMsg(null), 5000);
  };

  // Sync ward selection when wards are loaded
  useEffect(() => {
    if (wardsList.length > 0 && bedForm.ward_id === 0) {
      setBedForm(prev => ({ ...prev, ward_id: wardsList[0].id }));
    }
  }, [wardsList, bedForm.ward_id]);

  // Authorization Shield
  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4 text-slate-400">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-400" />
        <p className="font-semibold text-sm">Verifying credentials and security status...</p>
      </div>
    );
  }

  if (!user || user.role !== "ADMIN") {
    return (
      <div className="min-h-[85vh] bg-slate-950 flex flex-col items-center justify-center text-center p-6 text-slate-100">
        <div className="absolute top-0 left-0 w-full h-[400px] bg-radial-gradient from-rose-950/10 via-slate-950/0 to-slate-950/0 pointer-events-none" />
        <div className="h-16 w-16 rounded-2xl bg-rose-500/10 text-rose-500 flex items-center justify-center border border-rose-500/20 mb-6 animate-pulse">
          <ShieldAlert className="h-8 w-8" />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight mb-2 text-white">403 Forbidden</h1>
        <p className="text-slate-400 max-w-md mb-6 text-sm">
          Security Clearance Violation. Administrative privileges are required to access this subsystem.
        </p>
        <Link href="/" className="px-5 py-2.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded-xl font-semibold text-xs text-slate-200 transition-all flex items-center gap-2">
          <ArrowLeft className="h-4 w-4" /> Return to Command Center
        </Link>
      </div>
    );
  }

  // Action handlers
  const onCreateWardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!wardForm.name.trim() || wardForm.capacity <= 0) {
      showToast("Please provide a valid ward name and capacity.", true);
      return;
    }
    setFormSubmitting(true);
    try {
      await handleAddWard(wardForm);
      showToast(`Ward "${wardForm.name}" created successfully.`, false);
      setWardForm({ name: "", type: "ICU", capacity: 5 });
      setIsWardModalOpen(false);
    } catch (err: any) {
      showToast(err.message || "Failed to create ward.", true);
    } finally {
      setFormSubmitting(false);
    }
  };

  const onDeleteWard = async (id: number, name: string) => {
    if (!confirm(`Are you sure you want to decommission ward "${name}"?`)) return;
    try {
      await handleRemoveWard(id);
      showToast(`Ward "${name}" has been decommissioned.`, false);
    } catch (err: any) {
      showToast(err.message || "Failed to decommission ward.", true);
    }
  };

  const onCreateBedSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bedForm.bed_number.trim() || bedForm.ward_id === 0) {
      showToast("Please provide a valid bed identifier.", true);
      return;
    }
    setFormSubmitting(true);
    try {
      await handleAddBed(bedForm);
      showToast(`Bed "${bedForm.bed_number}" provisioned successfully.`, false);
      setBedForm(prev => ({ ...prev, bed_number: "" }));
      setIsBedModalOpen(false);
    } catch (err: any) {
      showToast(err.message || "Failed to provision bed.", true);
    } finally {
      setFormSubmitting(false);
    }
  };

  const onDeleteBed = async (id: number, bedNumber: string) => {
    if (!confirm(`Are you sure you want to remove bed "${bedNumber}"?`)) return;
    try {
      await handleRemoveBed(id);
      showToast(`Bed "${bedNumber}" has been removed from inventory.`, false);
    } catch (err: any) {
      showToast(err.message || "Failed to remove bed.", true);
    }
  };

  const onUpdateStaffSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!staffForm.email.trim()) {
      showToast("Please enter a valid staff email address.", true);
      return;
    }
    setFormSubmitting(true);
    try {
      await handleUpdateStaffRole(staffForm.email, staffForm.role);
      showToast(`Staff role updated for ${staffForm.email} to ${staffForm.role}.`, false);
      setStaffForm({ email: "", role: "COORDINATOR" });
      setIsStaffModalOpen(false);
    } catch (err: any) {
      showToast(err.message || "Failed to update staff role.", true);
    } finally {
      setFormSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans relative pb-28">
      {/* Background radial gradient decoration */}
      <div className="absolute top-0 left-0 w-full h-[600px] bg-radial-gradient from-indigo-950/10 via-slate-950/0 to-slate-950/0 pointer-events-none" />

      {/* Global Toast Alert Box */}
      {toastMsg && (
        <div className={`fixed top-24 right-6 z-50 flex items-center gap-3 px-5 py-4 rounded-xl border backdrop-blur-lg shadow-2xl transition-all duration-300 animate-in slide-in-from-right-8 ${
          toastMsg.isError 
            ? "bg-rose-950/80 border-rose-500/30 text-rose-200" 
            : "bg-emerald-950/80 border-emerald-500/30 text-emerald-200"
        }`}>
          {toastMsg.isError ? <AlertCircle className="h-5 w-5 text-rose-400" /> : <CheckCircle className="h-5 w-5 text-emerald-400" />}
          <span className="text-sm font-semibold">{toastMsg.text}</span>
        </div>
      )}

      <div className="flex flex-col space-y-8 p-6 max-w-7xl w-full mx-auto flex-1">
        {/* Navigation & Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-900 pb-6">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-850 hover:text-white transition-all text-slate-400" title="Back to Dashboard">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
                Admin Control Center
                <span className="text-[10px] uppercase font-mono tracking-widest text-indigo-400 border border-indigo-500/20 bg-indigo-500/5 px-2 py-0.5 rounded-md">SysConfig</span>
              </h1>
              <p className="text-xs text-slate-400 font-medium">Decommission wards, provision beds, and audit operational performance</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadAllData}
              disabled={isLoading}
              className="flex items-center gap-2 px-3 py-2 bg-slate-900 border border-slate-850 hover:bg-slate-800 text-slate-300 disabled:opacity-50 rounded-xl text-xs font-semibold transition-all"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin text-indigo-400" : ""}`} />
              Sync State
            </button>
            <button
              onClick={() => setIsStaffModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 text-indigo-300 rounded-xl text-xs font-semibold transition-all"
            >
              <UserCheck className="h-3.5 w-3.5" />
              Adjust Staff Role
            </button>
          </div>
        </div>

        {/* ZONE A: Operational Analytics (The ROI Dashboard) */}
        <section className="space-y-4">
          <h2 className="text-xs uppercase font-mono tracking-widest text-slate-400 flex items-center gap-2 font-bold">
            <Activity className="h-4 w-4 text-indigo-400" />
            System Telemetry & AI Performance
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Acceptance Rate Card */}
            <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md relative overflow-hidden flex flex-col justify-between h-32">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-semibold uppercase">AI Acceptance Rate</span>
                <span className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <CheckCircle className="h-4 w-4" />
                </span>
              </div>
              <div className="flex items-baseline gap-2 mt-4">
                <span className={`text-3xl font-extrabold tracking-tight ${
                  (summaryMetrics?.ai_acceptance_rate ?? 0) >= 80 ? "text-emerald-400 drop-shadow-[0_0_12px_rgba(16,185,129,0.15)]" : "text-amber-400"
                }`}>
                  {summaryMetrics ? `${summaryMetrics.ai_acceptance_rate.toFixed(1)}%` : "0.0%"}
                </span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1">Acceptance of AI relocation recommendations</p>
            </div>

            {/* Response Time Card */}
            <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md relative overflow-hidden flex flex-col justify-between h-32">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-semibold uppercase">Median Response Time</span>
                <span className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <Clock className="h-4 w-4" />
                </span>
              </div>
              <div className="flex items-baseline gap-2 mt-4">
                <span className="text-3xl font-extrabold tracking-tight text-white">
                  {summaryMetrics ? `${summaryMetrics.median_response_time_seconds.toFixed(2)}s` : "0.00s"}
                </span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1">Time elapsed before human triage action</p>
            </div>

            {/* Total Alerts Triggered */}
            <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md relative overflow-hidden flex flex-col justify-between h-32">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-semibold uppercase">Total Alerts Triggered</span>
                <span className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <AlertCircle className="h-4 w-4" />
                </span>
              </div>
              <div className="flex items-baseline gap-2 mt-4">
                <span className="text-3xl font-extrabold tracking-tight text-white">
                  {summaryMetrics ? summaryMetrics.alert_triggered_count : 0}
                </span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1">Clinical threshold violations recorded</p>
            </div>

            {/* Recommendations Actioned */}
            <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md relative overflow-hidden flex flex-col justify-between h-32">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-semibold uppercase">Recommendations Actioned</span>
                <span className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <Database className="h-4 w-4" />
                </span>
              </div>
              <div className="flex items-baseline gap-2 mt-4">
                <span className="text-3xl font-extrabold tracking-tight text-white">
                  {summaryMetrics 
                    ? summaryMetrics.approved_count + summaryMetrics.rejected_count + summaryMetrics.expired_count 
                    : 0}
                </span>
                {summaryMetrics && (
                  <span className="text-xs text-slate-400 font-medium">
                    (Approve: {summaryMetrics.approved_count} / Reject: {summaryMetrics.rejected_count})
                  </span>
                )}
              </div>
              <p className="text-[10px] text-slate-500 mt-1">AI suggestions actioned or expired</p>
            </div>
          </div>
        </section>

        {/* ZONE B: Capacity & Resource Management (Wards & Beds) */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Active Wards Card */}
          <div className="lg:col-span-5 bg-slate-900/30 border border-slate-850 rounded-2xl backdrop-blur-md p-6 flex flex-col">
            <div className="flex items-center justify-between mb-4 border-b border-slate-850 pb-4">
              <div>
                <h3 className="font-extrabold text-sm text-white">Active Wards</h3>
                <p className="text-[10px] text-slate-400 font-medium">Configure Wards and capacity parameters</p>
              </div>
              <button
                onClick={() => setIsWardModalOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-xs font-semibold transition-all"
              >
                <PlusCircle className="h-3.5 w-3.5" /> Create Ward
              </button>
            </div>

            <div className="overflow-x-auto min-h-[300px]">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-slate-500 text-[10px] font-mono tracking-wider uppercase border-b border-slate-850">
                    <th className="pb-3">Ward Name</th>
                    <th className="pb-3">Type</th>
                    <th className="pb-3 text-center">Beds / Capacity</th>
                    <th className="pb-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-850/50">
                  {wardsList.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-12 text-center text-xs text-slate-500">
                        No active clinical wards configured.
                      </td>
                    </tr>
                  ) : (
                    wardsList.map((ward) => (
                      <tr key={ward.id} className="text-xs hover:bg-slate-900/10 transition-colors">
                        <td className="py-4 font-bold text-slate-200">{ward.name}</td>
                        <td className="py-4 text-slate-350">
                          <span className="px-2 py-0.5 bg-slate-800 border border-slate-750 rounded text-[9px] font-semibold text-slate-300">
                            {ward.type}
                          </span>
                        </td>
                        <td className="py-4 text-center font-semibold text-slate-200">
                          {ward.occupied_beds_count} / {ward.capacity}
                        </td>
                        <td className="py-4 text-right">
                          <button
                            onClick={() => onDeleteWard(ward.id, ward.name)}
                            className="p-1.5 rounded-lg bg-slate-900 hover:bg-rose-950/30 border border-slate-850 hover:border-rose-500/20 text-slate-400 hover:text-rose-400 transition-all"
                            title="Decommission Ward"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bed Inventory Card */}
          <div className="lg:col-span-7 bg-slate-900/30 border border-slate-850 rounded-2xl backdrop-blur-md p-6 flex flex-col">
            <div className="flex items-center justify-between mb-4 border-b border-slate-850 pb-4">
              <div>
                <h3 className="font-extrabold text-sm text-white">Bed Inventory</h3>
                <p className="text-[10px] text-slate-400 font-medium">Manage and provision individual clinical spaces</p>
              </div>
              <button
                onClick={() => {
                  if (wardsList.length === 0) {
                    showToast("Configure at least one ward first before provisioning beds.", true);
                    return;
                  }
                  setIsBedModalOpen(true);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-xs font-semibold transition-all"
              >
                <PlusCircle className="h-3.5 w-3.5" /> Provision Bed
              </button>
            </div>

            <div className="overflow-x-auto min-h-[300px]">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-slate-500 text-[10px] font-mono tracking-wider uppercase border-b border-slate-850">
                    <th className="pb-3">Bed Number</th>
                    <th className="pb-3">Ward</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-850/50">
                  {bedsList.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-12 text-center text-xs text-slate-500">
                        No active beds provisioned.
                      </td>
                    </tr>
                  ) : (
                    bedsList.map((bed) => {
                      const wardName = wardsList.find((w) => w.id === bed.ward_id)?.name || `Ward ID ${bed.ward_id}`;
                      
                      // Colored status styles
                      let statusBadge = "bg-slate-800 text-slate-400 border-slate-750";
                      if (bed.status === "AVAILABLE") statusBadge = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
                      else if (bed.status === "OCCUPIED") statusBadge = "bg-indigo-500/10 text-indigo-400 border-indigo-500/20";
                      else if (bed.status === "MAINTENANCE" || bed.status === "CLEANING") statusBadge = "bg-amber-500/10 text-amber-400 border-amber-500/20";

                      return (
                        <tr key={bed.id} className="text-xs hover:bg-slate-900/10 transition-colors">
                          <td className="py-4 font-bold text-slate-200">{bed.bed_number}</td>
                          <td className="py-4 text-slate-350">{wardName}</td>
                          <td className="py-4">
                            <span className={`px-2 py-0.5 border rounded text-[9px] font-bold ${statusBadge}`}>
                              {bed.status}
                            </span>
                          </td>
                          <td className="py-4 text-right">
                            <button
                              onClick={() => onDeleteBed(bed.id, bed.bed_number)}
                              className="p-1.5 rounded-lg bg-slate-900 hover:bg-rose-950/30 border border-slate-850 hover:border-rose-500/20 text-slate-400 hover:text-rose-400 transition-all"
                              title="Delete Bed"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>

      {/* MODALS PANEL */}

      {/* Create Ward Modal */}
      {isWardModalOpen && (
        <div className="fixed inset-0 bg-slate-950/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
            <h3 className="text-base font-extrabold text-white mb-1">Create Ward</h3>
            <p className="text-[10px] text-slate-400 mb-6">Provision a new clinical ward configuration</p>

            <form onSubmit={onCreateWardSubmit} className="space-y-4">
              <div>
                <label className="block text-[10px] text-slate-400 font-semibold mb-1">WARD NAME / LABEL</label>
                <input
                  type="text"
                  value={wardForm.name}
                  onChange={(e) => setWardForm({ ...wardForm, name: e.target.value })}
                  placeholder="e.g. ICU Wing Beta"
                  className="w-full bg-slate-950 border border-slate-850 rounded-xl px-4 py-2 text-slate-200 placeholder-slate-600 text-sm focus:outline-none focus:border-slate-700"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] text-slate-400 font-semibold mb-1">WARD TYPE</label>
                  <select
                    value={wardForm.type}
                    onChange={(e) => setWardForm({ ...wardForm, type: e.target.value as WardType })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
                  >
                    <option value="ICU">ICU</option>
                    <option value="GENERAL">GENERAL</option>
                    <option value="EMERGENCY">EMERGENCY</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-slate-400 font-semibold mb-1">CAPACITY (BEDS)</label>
                  <input
                    type="number"
                    min={1}
                    value={wardForm.capacity}
                    onChange={(e) => setWardForm({ ...wardForm, capacity: parseInt(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-4 py-2 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
                    required
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-850">
                <button
                  type="button"
                  onClick={() => setIsWardModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-750 text-slate-300 rounded-xl text-xs font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition-colors"
                >
                  {formSubmitting ? "Saving..." : "Save Ward"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Provision Bed Modal */}
      {isBedModalOpen && (
        <div className="fixed inset-0 bg-slate-950/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
            <h3 className="text-base font-extrabold text-white mb-1">Provision Bed</h3>
            <p className="text-[10px] text-slate-400 mb-6">Add a new bed to active clinical spaces</p>

            <form onSubmit={onCreateBedSubmit} className="space-y-4">
              <div>
                <label className="block text-[10px] text-slate-400 font-semibold mb-1">BED NUMBER / IDENTIFIER</label>
                <input
                  type="text"
                  value={bedForm.bed_number}
                  onChange={(e) => setBedForm({ ...bedForm, bed_number: e.target.value })}
                  placeholder="e.g. ICU-BETA-102"
                  className="w-full bg-slate-950 border border-slate-850 rounded-xl px-4 py-2 text-slate-200 placeholder-slate-600 text-sm focus:outline-none focus:border-slate-700"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] text-slate-400 font-semibold mb-1">WARD</label>
                  <select
                    value={bedForm.ward_id}
                    onChange={(e) => setBedForm({ ...bedForm, ward_id: parseInt(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
                  >
                    {wardsList.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-slate-400 font-semibold mb-1">INITIAL STATUS</label>
                  <select
                    value={bedForm.status}
                    onChange={(e) => setBedForm({ ...bedForm, status: e.target.value as BedStatus })}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
                  >
                    <option value="AVAILABLE">AVAILABLE</option>
                    <option value="CLEANING">CLEANING</option>
                    <option value="MAINTENANCE">MAINTENANCE</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-850">
                <button
                  type="button"
                  onClick={() => setIsBedModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-750 text-slate-300 rounded-xl text-xs font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition-colors"
                >
                  {formSubmitting ? "Provisioning..." : "Provision Bed"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Staff Update Modal */}
      {isStaffModalOpen && (
        <div className="fixed inset-0 bg-slate-950/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
            <h3 className="text-base font-extrabold text-white mb-1">Adjust Staff Role</h3>
            <p className="text-[10px] text-slate-400 mb-6">Modify user credentials and role configuration mappings</p>

            <form onSubmit={onUpdateStaffSubmit} className="space-y-4">
              <div>
                <label className="block text-[10px] text-slate-400 font-semibold mb-1">EMAIL ADDRESS</label>
                <input
                  type="email"
                  value={staffForm.email}
                  onChange={(e) => setStaffForm({ ...staffForm, email: e.target.value })}
                  placeholder="e.g. staff.member@hospitalai.com"
                  className="w-full bg-slate-950 border border-slate-850 rounded-xl px-4 py-2 text-slate-200 placeholder-slate-600 text-sm focus:outline-none focus:border-slate-700"
                  required
                />
              </div>

              <div>
                <label className="block text-[10px] text-slate-400 font-semibold mb-1">NEW RBAC ROLE</label>
                <select
                  value={staffForm.role}
                  onChange={(e) => setStaffForm({ ...staffForm, role: e.target.value as UserRole })}
                  className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-slate-700 font-bold"
                >
                  <option value="ADMIN" className="text-red-400">ADMIN</option>
                  <option value="COORDINATOR" className="text-indigo-400">COORDINATOR</option>
                  <option value="DOCTOR" className="text-blue-400">DOCTOR</option>
                  <option value="NURSE" className="text-emerald-400">NURSE</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-850">
                <button
                  type="button"
                  onClick={() => setIsStaffModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-750 text-slate-300 rounded-xl text-xs font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition-colors"
                >
                  {formSubmitting ? "Saving..." : "Update Role"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
