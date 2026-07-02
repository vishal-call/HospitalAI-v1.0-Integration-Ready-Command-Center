import React, { useState } from "react";
import { Ward, Bed, BedStatus, updateBedStatus } from "@/lib/api";
import { Activity, ShieldAlert, BedDouble, User, Info, Check } from "lucide-react";

interface WardOverviewProps {
  wards: Ward[];
  onBedUpdate?: () => void;
}

export default function WardOverview({ wards, onBedUpdate }: WardOverviewProps) {
  const [selectedBed, setSelectedBed] = useState<Bed | null>(null);
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const getWardIcon = (type: string) => {
    switch (type) {
      case "ICU":
        return <ShieldAlert className="h-5 w-5 text-rose-400" />;
      case "EMERGENCY":
        return <Activity className="h-5 w-5 text-amber-400" />;
      default:
        return <BedDouble className="h-5 w-5 text-emerald-400" />;
    }
  };

  const getWardBadgeStyle = (type: string) => {
    switch (type) {
      case "ICU":
        return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
      case "EMERGENCY":
        return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
      default:
        return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    }
  };

  const getProgressColor = (rate: number) => {
    if (rate >= 85) return "bg-gradient-to-r from-rose-500 to-red-600";
    if (rate >= 60) return "bg-gradient-to-r from-amber-500 to-orange-600";
    return "bg-gradient-to-r from-emerald-500 to-teal-600";
  };

  const getBedStatusStyle = (status: BedStatus) => {
    switch (status) {
      case "AVAILABLE":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20";
      case "OCCUPIED":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30 hover:bg-rose-500/20";
      case "CLEANING":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20";
      case "RESERVED":
        return "bg-sky-500/10 text-sky-400 border-sky-500/30 hover:bg-sky-500/20";
      case "MAINTENANCE":
        return "bg-slate-700/20 text-slate-400 border-slate-700/40 hover:bg-slate-700/30";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700";
    }
  };

  const getBedStatusLabel = (status: BedStatus) => {
    switch (status) {
      case "AVAILABLE":
        return "Available";
      case "OCCUPIED":
        return "Occupied";
      case "CLEANING":
        return "Cleaning";
      case "RESERVED":
        return "Reserved";
      case "MAINTENANCE":
        return "Maintenance";
      default:
        return status;
    }
  };

  const handleStatusChange = async (bedId: number, newStatus: BedStatus) => {
    try {
      setUpdating(true);
      setUpdateError(null);
      await updateBedStatus(bedId, newStatus);
      if (onBedUpdate) {
        onBedUpdate();
      }
      setSelectedBed(null);
    } catch (err) {
      setUpdateError(err instanceof Error ? err.message : "Failed to update bed status.");
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Ward Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {wards.map((ward) => {
          const utilRate = ward.utilization_rate;
          return (
            <div
              key={ward.id}
              className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-6 transition-all duration-300 hover:border-slate-700 hover:shadow-lg hover:shadow-black/20"
            >
              {/* Glow effect */}
              <div className={`absolute top-0 right-0 -mr-6 -mt-6 h-24 w-24 rounded-full blur-2xl opacity-10 ${
                ward.type === 'ICU' ? 'bg-rose-500' : ward.type === 'EMERGENCY' ? 'bg-amber-500' : 'bg-emerald-500'
              }`} />

              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-slate-800/80 border border-slate-700/50">
                    {getWardIcon(ward.type)}
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-100 text-lg tracking-tight">{ward.name}</h3>
                    <span className={`inline-block text-xs font-semibold px-2 py-0.5 mt-1 rounded-full uppercase tracking-wider ${getWardBadgeStyle(ward.type)}`}>
                      {ward.type}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-6">
                <div className="flex justify-between items-baseline mb-2">
                  <span className="text-slate-400 text-sm font-medium">Bed Utilization</span>
                  <span className="text-slate-100 font-bold text-lg">{utilRate}%</span>
                </div>

                <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-700/30">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ease-out ${getProgressColor(utilRate)}`}
                    style={{ width: `${utilRate}%` }}
                  />
                </div>

                <div className="flex justify-between items-center mt-4 text-xs text-slate-400 font-medium">
                  <span>Occupied: <strong className="text-slate-200">{ward.occupied_beds_count}</strong></span>
                  <span>Total Capacity: <strong className="text-slate-200">{ward.capacity}</strong></span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bed Grid Map */}
      <div className="border border-slate-850 bg-slate-900/40 rounded-2xl p-6 backdrop-blur-md">
        <h3 className="text-md font-bold text-white mb-6 flex items-center gap-2">
          <BedDouble className="h-5 w-5 text-indigo-400" />
          Interactive Bed Allocation Matrix
        </h3>

        <div className="space-y-8">
          {wards.map((ward) => (
            <div key={ward.id} className="border-t border-slate-800/60 pt-6 first:border-none first:pt-0">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-sm font-bold text-slate-200 uppercase tracking-wider">{ward.name}</span>
                <span className="text-xs font-semibold bg-slate-800 text-slate-400 px-2 py-0.5 rounded-md">
                  {ward.beds?.length || 0} slots
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
                {ward.beds?.map((bed) => (
                  <button
                    key={bed.id}
                    onClick={() => setSelectedBed(bed)}
                    className={`flex flex-col text-left p-3 rounded-xl border transition-all select-none relative group ${getBedStatusStyle(bed.status)}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-slate-100">{bed.bed_number}</span>
                      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70 group-hover:scale-125 transition-transform"></span>
                    </div>
                    <span className="text-[10px] uppercase font-bold tracking-wider mt-1 opacity-80">
                      {getBedStatusLabel(bed.status)}
                    </span>
                    {bed.patient && (
                      <span className="text-xs truncate font-semibold text-white/90 mt-1.5 flex items-center gap-1">
                        <User className="h-3 w-3 shrink-0 opacity-60" />
                        {bed.patient.name}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bed Interactive Popover Modal */}
      {selectedBed && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BedDouble className="h-5 w-5 text-indigo-400" />
                <h4 className="font-extrabold text-slate-100">Slot Override: {selectedBed.bed_number}</h4>
              </div>
              <button
                onClick={() => setSelectedBed(null)}
                className="text-slate-400 hover:text-white text-sm font-semibold transition-colors"
              >
                Close
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-5">
              {/* Patient info if occupied */}
              {selectedBed.patient ? (
                <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 text-xs font-medium">Occupant Details</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      selectedBed.patient.status === 'CRITICAL' 
                        ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' 
                        : selectedBed.patient.status === 'SERIOUS'
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    }`}>
                      {selectedBed.patient.status}
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    <p className="text-sm font-extrabold text-white">{selectedBed.patient.name}</p>
                    <div className="flex gap-4 text-xs text-slate-400 font-medium">
                      <span>Age: <strong className="text-slate-200">{selectedBed.patient.age}</strong></span>
                      <span>Gender: <strong className="text-slate-200">{selectedBed.patient.gender}</strong></span>
                      <span>EWS Score: <strong className="text-indigo-400">{selectedBed.patient.criticality_score}/10</strong></span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-3 bg-slate-950/40 border border-slate-800 p-4 rounded-xl text-xs text-slate-400 leading-relaxed font-medium">
                  <Info className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                  <p>
                    This bed is currently unoccupied. You can manually adjust the maintenance or cleaning status. Occupied status can only be set through the Patient Admission or recommendation actions.
                  </p>
                </div>
              )}

              {/* Status updater */}
              {!selectedBed.patient && (
                <div className="space-y-2">
                  <label className="text-xs text-slate-400 font-bold uppercase tracking-wider block">Bed Operational State</label>
                  <div className="grid grid-cols-2 gap-2">
                    {(["AVAILABLE", "CLEANING", "RESERVED", "MAINTENANCE"] as BedStatus[]).map((st) => (
                      <button
                        key={st}
                        onClick={() => handleStatusChange(selectedBed.id, st)}
                        disabled={updating}
                        className={`flex items-center justify-between p-3 rounded-xl border text-xs font-bold transition-all ${
                          selectedBed.status === st 
                            ? "bg-indigo-500/10 border-indigo-500/40 text-indigo-400"
                            : "bg-slate-950/40 border-slate-800 hover:border-slate-700 text-slate-300"
                        }`}
                      >
                        <span>{getBedStatusLabel(st)}</span>
                        {selectedBed.status === st && <Check className="h-3.5 w-3.5 text-indigo-400 shrink-0" />}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {updateError && (
                <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs p-3 rounded-xl font-medium">
                  {updateError}
                </div>
              )}
            </div>

            {/* Footer */}
            {selectedBed.patient && (
              <div className="px-6 py-4 bg-slate-950/60 border-t border-slate-800 text-right">
                <button
                  onClick={() => setSelectedBed(null)}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white rounded-xl shadow-lg shadow-indigo-600/20 transition-all"
                >
                  Acknowledge
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
