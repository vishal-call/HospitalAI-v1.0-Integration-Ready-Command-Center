import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Patient, VitalsPayload, logPatientVitals } from "@/lib/api";
import { Loader2 } from "lucide-react";

interface VitalsFormProps {
  patient: Patient;
  idempotencyKey: string;
  onSuccess: () => void;
  onCancel: () => void;
}

const vitalsSchema = z.object({
  heart_rate: z.number({ invalid_type_error: "Must be a number" }).min(0).max(300),
  resp_rate: z.number({ invalid_type_error: "Must be a number" }).min(0).max(100),
  spo2: z.number({ invalid_type_error: "Must be a number" }).min(0).max(100),
  temperature: z.number({ invalid_type_error: "Must be a number" }).min(20).max(45).optional().or(z.literal("")),
  systolic_bp: z.number({ invalid_type_error: "Must be a number" }).min(0).max(300).optional().or(z.literal("")),
  consciousness_level: z.enum(["ALERT", "CVPU"]),
  oxygen_supplement: z.boolean(),
});

type VitalsFormData = z.infer<typeof vitalsSchema>;

export default function VitalsForm({ patient, idempotencyKey, onSuccess, onCancel }: VitalsFormProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isCritical = patient.status === "CRITICAL";
  const isSerious = patient.status === "SERIOUS";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<VitalsFormData>({
    resolver: zodResolver(vitalsSchema),
    defaultValues: {
      heart_rate: isCritical ? 135 : (isSerious ? 115 : 75),
      resp_rate: isCritical ? 32 : (isSerious ? 23 : 16),
      spo2: isCritical ? 85 : (isSerious ? 93 : 98),
      consciousness_level: "ALERT",
      oxygen_supplement: false,
    },
  });

  const onSubmit = async (data: VitalsFormData) => {
    setLoading(true);
    setError(null);
    try {
      const payload: VitalsPayload = {
        heart_rate: data.heart_rate,
        resp_rate: data.resp_rate,
        spo2: data.spo2,
        consciousness_level: data.consciousness_level,
        oxygen_supplement: data.oxygen_supplement,
        spo2_scale: data.oxygen_supplement ? 2 : 1, // Default scale handling based on oxygen
      };

      // Handle empty string optionals from form inputs
      if (data.temperature !== "" && data.temperature !== undefined) payload.temperature = data.temperature;
      if (data.systolic_bp !== "" && data.systolic_bp !== undefined) payload.systolic_bp = data.systolic_bp;

      await logPatientVitals(patient.id, payload, idempotencyKey);
      onSuccess();
    } catch (err: any) {
      setError(err.message || "Failed to log vitals.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {error && (
        <div className="p-3 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-slate-400 text-xs font-semibold mb-1">HEART RATE (BPM)</label>
          <input
            type="number"
            {...register("heart_rate", { valueAsNumber: true })}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
          />
          {errors.heart_rate && <p className="text-rose-400 text-xs mt-1">{errors.heart_rate.message}</p>}
        </div>

        <div>
          <label className="block text-slate-400 text-xs font-semibold mb-1">RESP RATE (BREATHS/MIN)</label>
          <input
            type="number"
            {...register("resp_rate", { valueAsNumber: true })}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
          />
          {errors.resp_rate && <p className="text-rose-400 text-xs mt-1">{errors.resp_rate.message}</p>}
        </div>

        <div>
          <label className="block text-slate-400 text-xs font-semibold mb-1">SPO2 (%)</label>
          <input
            type="number"
            {...register("spo2", { valueAsNumber: true })}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
          />
          {errors.spo2 && <p className="text-rose-400 text-xs mt-1">{errors.spo2.message}</p>}
        </div>

        <div>
          <label className="block text-slate-400 text-xs font-semibold mb-1">TEMPERATURE (°C)</label>
          <input
            type="number"
            step="0.1"
            placeholder="Optional"
            {...register("temperature", { 
              setValueAs: v => v === "" ? "" : parseFloat(v)
            })}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
          />
          {errors.temperature && <p className="text-rose-400 text-xs mt-1">{errors.temperature.message}</p>}
        </div>

        <div>
          <label className="block text-slate-400 text-xs font-semibold mb-1">SYSTOLIC BP</label>
          <input
            type="number"
            placeholder="Optional"
            {...register("systolic_bp", { 
              setValueAs: v => v === "" ? "" : parseInt(v, 10)
            })}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
          />
          {errors.systolic_bp && <p className="text-rose-400 text-xs mt-1">{errors.systolic_bp.message}</p>}
        </div>

        <div>
          <label className="block text-slate-400 text-xs font-semibold mb-1">CONSCIOUSNESS</label>
          <select
            {...register("consciousness_level")}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 text-sm focus:outline-none focus:border-slate-700"
          >
            <option value="ALERT">Alert</option>
            <option value="CVPU">CVPU (Confusion/Voice/Pain/Unresponsive)</option>
          </select>
          {errors.consciousness_level && <p className="text-rose-400 text-xs mt-1">{errors.consciousness_level.message}</p>}
        </div>
      </div>

      <div className="flex items-center gap-3 mt-2 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3">
        <input
          type="checkbox"
          id="oxygen_supplement"
          {...register("oxygen_supplement")}
          className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-slate-950"
        />
        <label htmlFor="oxygen_supplement" className="text-slate-300 text-sm font-medium cursor-pointer select-none">
          Patient is on supplemental oxygen
        </label>
      </div>

      <div className="flex gap-4 justify-end mt-6 pt-2 border-t border-slate-800">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-semibold transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2.5 bg-indigo-500 hover:bg-indigo-600 disabled:bg-indigo-500/50 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-indigo-500/10 flex items-center gap-2"
        >
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          Save Vitals
        </button>
      </div>
    </form>
  );
}
