import React, { useState } from "react";
import { Patient, logPatientVitals } from "@/lib/api";
import { Search, ArrowUpDown, ShieldAlert, Heart, Activity, ClipboardList, Loader2, ChevronRight } from "lucide-react";
import Link from "next/link";
import ClinicalTimeline from "./ClinicalTimeline";
import VitalsForm from "./VitalsForm";

interface PatientTableProps {
  patients: Patient[];
  onVitalsLogged?: () => void;
}



export default function PatientTable({ patients, onVitalsLogged }: PatientTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] = useState<"name" | "age" | "criticality_score">("criticality_score");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [expandedPatientId, setExpandedPatientId] = useState<number | null>(null);
  const [vitalsLoading, setVitalsLoading] = useState(false);
  const [vitalsError, setVitalsError] = useState<string | null>(null);
  const [vitalsIdempotencyKey, setVitalsIdempotencyKey] = useState<string>("");

  const handleOpenVitalsModal = (patient: Patient) => {
    setSelectedPatient(patient);
    setVitalsIdempotencyKey(window.crypto.randomUUID());
  };

  const handleVitalsSuccess = () => {
    setSelectedPatient(null);
    if (onVitalsLogged) {
      onVitalsLogged();
    }
  };

  // Search Filter
  const filteredPatients = patients.filter((patient) =>
    patient.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sorting
  const sortedPatients = [...filteredPatients].sort((a, b) => {
    let valueA = a[sortField];
    let valueB = b[sortField];

    if (typeof valueA === "string" && typeof valueB === "string") {
      return sortDirection === "asc"
        ? valueA.localeCompare(valueB)
        : valueB.localeCompare(valueA);
    }

    // Number comparisons
    return sortDirection === "asc"
      ? (valueA as number) - (valueB as number)
      : (valueB as number) - (valueA as number);
  });

  const handleSort = (field: "name" | "age" | "criticality_score") => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CRITICAL":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
            </span>
            CRITICAL
          </span>
        );
      case "SERIOUS":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <span className="h-2 w-2 rounded-full bg-amber-500"></span>
            SERIOUS
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
            STABLE
          </span>
        );
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 8.0) return "text-rose-400 font-bold bg-rose-500/5 px-2 py-0.5 rounded";
    if (score >= 4.0) return "text-amber-400 font-semibold bg-amber-500/5 px-2 py-0.5 rounded";
    return "text-emerald-400 font-medium bg-emerald-500/5 px-2 py-0.5 rounded";
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-6">
      {/* Search and Table Filters Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-100 tracking-tight">Active Admitted Patients</h2>
          <p className="text-slate-400 text-sm mt-1">Real-time status tracking and deterministic clinical criticality score matrix.</p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search patients..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-500 text-sm focus:outline-none focus:border-slate-700 transition-colors"
          />
        </div>
      </div>

      {/* Responsive Table Wrapper */}
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full border-collapse text-left text-sm text-slate-300">
          <thead className="bg-slate-950 text-slate-400 uppercase text-xs font-semibold tracking-wider border-b border-slate-800">
            <tr>
              <th className="py-4 px-6">
                <button
                  onClick={() => handleSort("name")}
                  className="flex items-center gap-1.5 hover:text-slate-200 transition-colors"
                >
                  Patient Name
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
              <th className="py-4 px-6">
                <button
                  onClick={() => handleSort("age")}
                  className="flex items-center gap-1.5 hover:text-slate-200 transition-colors"
                >
                  Age / Gender
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
              <th className="py-4 px-6">Admission Reason</th>
              <th className="py-4 px-6">Status Badge</th>
              <th className="py-4 px-6">
                <button
                  onClick={() => handleSort("criticality_score")}
                  className="flex items-center gap-1.5 hover:text-slate-200 transition-colors"
                >
                  Criticality Score
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
              <th className="py-4 px-6">Admitted At</th>
              <th className="py-4 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-900/20">
            {sortedPatients.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500">
                  No active patients found matching criteria.
                </td>
              </tr>
            ) : (
              sortedPatients.map((patient, index) => (
                <React.Fragment key={`${patient.id}-${index}`}>
                  <tr className="transition-colors hover:bg-slate-800/30">
                    <td className="py-4 px-6 font-semibold text-slate-100">{patient.name}</td>
                    <td className="py-4 px-6">
                      {patient.age}y / <span className="text-slate-400 capitalize">{patient.gender}</span>
                    </td>
                    <td className="py-4 px-6 text-slate-400 max-w-xs truncate" title={patient.admission_reason}>
                      {patient.admission_reason}
                    </td>
                    <td className="py-4 px-6">{getStatusBadge(patient.status)}</td>
                    <td className="py-4 px-6">
                      <span className={getScoreColor(patient.criticality_score)}>
                        {patient.criticality_score.toFixed(1)} / 10.0
                      </span>
                    </td>
                    <td className="py-4 px-6 text-slate-400">{formatDate(patient.admitted_at)}</td>
                    <td className="py-4 px-6 text-right space-x-2 whitespace-nowrap">
                      <button
                        onClick={() => setExpandedPatientId(expandedPatientId === patient.id ? null : patient.id)}
                        className={`inline-flex items-center gap-1 py-1.5 px-3 border font-semibold text-xs rounded-lg transition-all ${
                          expandedPatientId === patient.id 
                            ? 'bg-slate-800 border-slate-700 text-white' 
                            : 'bg-slate-950 border-slate-800 hover:bg-slate-900 text-slate-300 hover:text-indigo-400'
                        }`}
                      >
                        <Activity className="h-3.5 w-3.5" />
                        {expandedPatientId === patient.id ? 'Hide Timeline' : 'Timeline'}
                      </button>
                      <button
                        onClick={() => handleOpenVitalsModal(patient)}
                        className="inline-flex items-center gap-1 py-1.5 px-3 bg-slate-950 border border-slate-800 hover:bg-slate-900 text-slate-300 hover:text-indigo-400 font-semibold text-xs rounded-lg transition-all"
                      >
                        <ClipboardList className="h-3.5 w-3.5" />
                        Vitals
                      </button>
                      <Link
                        href={`/patients/${patient.id}`}
                        className="inline-flex items-center gap-1 py-1.5 px-3 bg-slate-950 border border-slate-800 hover:bg-slate-900 text-slate-300 hover:text-indigo-400 font-semibold text-xs rounded-lg transition-all"
                      >
                        Details
                        <ChevronRight className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                  </tr>
                  {expandedPatientId === patient.id && (
                    <tr className="bg-slate-900/40">
                      <td colSpan={7} className="p-0 border-b border-slate-800">
                        <div className="p-6">
                          <h4 className="text-sm font-bold text-slate-200 mb-4 border-b border-slate-800 pb-2">Clinical Audit Trail</h4>
                          <ClinicalTimeline patientId={patient.id} />
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Log Vitals Modal */}
      {selectedPatient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl relative">
            <h3 className="text-lg font-bold text-slate-100 tracking-tight mb-1">
              Log Clinical Vitals
            </h3>
            <p className="text-slate-400 text-xs mb-4">
              Enter raw vital signs for <strong className="text-slate-200">{selectedPatient.name}</strong>. Deterioration checks and EWS scoring run automatically.
            </p>

            <VitalsForm 
              patient={selectedPatient} 
              idempotencyKey={vitalsIdempotencyKey} 
              onSuccess={handleVitalsSuccess} 
              onCancel={() => setSelectedPatient(null)} 
            />
          </div>
        </div>
      )}
    </div>
  );
}
