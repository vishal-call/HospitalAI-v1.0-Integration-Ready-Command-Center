import React from "react";
import { PartnerHospital } from "@/lib/api";
import { Network, MapPin, Activity, CheckCircle, ShieldAlert } from "lucide-react";

interface PartnerNetworkProps {
  hospitals: PartnerHospital[];
}

export default function PartnerNetwork({ hospitals }: PartnerNetworkProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-6 flex flex-col h-full">
      <div className="flex items-center gap-2.5 mb-5 pb-4 border-b border-slate-800">
        <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          <Network className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-100 tracking-tight">
            Partner Network Status
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">Live external facility capacity and transfer availability.</p>
        </div>
      </div>

      <div className="flex-1 overflow-x-auto">
        <table className="w-full border-collapse text-left text-xs text-slate-300">
          <thead className="text-slate-500 uppercase font-semibold border-b border-slate-800/80">
            <tr>
              <th className="py-2 px-3 pl-0">Hospital</th>
              <th className="py-2 px-3">Distance</th>
              <th className="py-2 px-3 text-center">ICU Beds</th>
              <th className="py-2 px-3 text-center">General Beds</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 bg-slate-900/10">
            {hospitals.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-6 text-center text-slate-500">
                  No partner hospitals currently registered.
                </td>
              </tr>
            ) : (
              hospitals.map((hospital) => (
                <tr key={hospital.id} className="hover:bg-slate-800/20 transition-colors">
                  <td className="py-3 px-3 pl-0 font-semibold text-slate-200">
                    <div className="flex flex-col">
                      <span>{hospital.name}</span>
                      <span className="text-[10px] text-slate-500 font-normal flex items-center gap-1 mt-0.5">
                        <MapPin className="h-3 w-3" /> {hospital.location}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-3 font-medium text-slate-300">
                    {hospital.distance_km.toFixed(1)} km
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-bold text-[10px] ${
                        hospital.icu_beds_available > 0
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                      }`}
                    >
                      {hospital.icu_beds_available > 0 ? (
                        <>
                          <CheckCircle className="h-2.5 w-2.5" />
                          {hospital.icu_beds_available} Avail
                        </>
                      ) : (
                        <>
                          <ShieldAlert className="h-2.5 w-2.5" />
                          Full
                        </>
                      )}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-bold text-[10px] ${
                        hospital.general_beds_available > 0
                          ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                          : "bg-slate-800 text-slate-400 border border-slate-700/50"
                      }`}
                    >
                      {hospital.general_beds_available} Avail
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
