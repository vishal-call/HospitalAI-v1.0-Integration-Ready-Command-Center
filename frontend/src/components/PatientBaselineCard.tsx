import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Loader2, Activity, Edit3, X, Check, Info } from "lucide-react";
import { fetchPatientBaseline, upsertPatientBaseline, PatientBaselineResponse } from "@/lib/api";

const baselineSchema = z.object({
  baseline_spo2: z.number().min(50).max(100).nullable().optional(),
  baseline_heart_rate: z.number().min(30).max(250).nullable().optional(),
  baseline_systolic_bp: z.number().min(50).max(300).nullable().optional(),
  baseline_respiratory_rate: z.number().min(5).max(60).nullable().optional(),
  notes: z.string().max(255).nullable().optional(),
}).refine(data => 
  data.baseline_spo2 !== null || 
  data.baseline_heart_rate !== null || 
  data.baseline_systolic_bp !== null || 
  data.baseline_respiratory_rate !== null || 
  (data.notes && data.notes.trim() !== ""),
  { message: "At least one baseline parameter or note must be provided." }
);

type BaselineFormData = z.infer<typeof baselineSchema>;

export default function PatientBaselineCard({ patientId }: { patientId: number }) {
  const [baseline, setBaseline] = useState<PatientBaselineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<BaselineFormData>({
    resolver: zodResolver(baselineSchema),
    defaultValues: {
      baseline_spo2: null,
      baseline_heart_rate: null,
      baseline_systolic_bp: null,
      baseline_respiratory_rate: null,
      notes: ""
    }
  });

  const loadBaseline = async () => {
    try {
      setLoading(true);
      const data = await fetchPatientBaseline(patientId);
      if (data) {
        setBaseline(data);
        reset({
          baseline_spo2: data.baseline_spo2 ?? null,
          baseline_heart_rate: data.baseline_heart_rate ?? null,
          baseline_systolic_bp: data.baseline_systolic_bp ?? null,
          baseline_respiratory_rate: data.baseline_respiratory_rate ?? null,
          notes: data.notes ?? ""
        });
      }
    } catch (err) {
      console.error("Failed to load baseline", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBaseline();
  }, [patientId]);

  const onSubmit = async (data: BaselineFormData) => {
    try {
      setSubmitError(null);
      const res = await upsertPatientBaseline(patientId, data);
      setBaseline(res);
      setIsEditing(false);
    } catch (err: any) {
      setSubmitError(err.message || "Failed to update baseline.");
    }
  };

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 flex justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-indigo-400" />
      </div>
    );
  }

  return (
    <div className={`rounded-2xl border transition-all ${baseline ? 'border-violet-500/30 bg-violet-950/10' : 'border-slate-800 bg-slate-900/40'} p-6 backdrop-blur-xl`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-lg font-bold text-slate-200 tracking-tight">
          <Activity className={`h-5 w-5 ${baseline ? 'text-violet-400' : 'text-slate-400'}`} />
          Physiological Baselines
        </div>
        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="p-2 rounded-lg bg-slate-800/50 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <Edit3 className="h-4 w-4" />
          </button>
        )}
      </div>

      {baseline && !isEditing && (
        <div className="bg-violet-500/10 border border-violet-500/20 text-violet-300 px-3 py-2 rounded-lg text-xs font-semibold flex items-start gap-2 mb-4">
          <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <p>
            An active baseline is overriding the default NEWS2 algorithm. The scoring engine automatically recalibrates to these personalized parameters.
          </p>
        </div>
      )}

      {isEditing ? (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {submitError && (
            <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              {submitError}
            </div>
          )}
          {errors.root && (
             <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs">
              {errors.root.message}
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-400 text-[10px] font-bold mb-1 uppercase tracking-wider">Target SpO2 (%)</label>
              <input
                type="number"
                {...register("baseline_spo2", { setValueAs: v => v === "" || isNaN(v) ? null : parseInt(v, 10) })}
                placeholder="e.g. 88"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-violet-500"
              />
              {errors.baseline_spo2 && <p className="text-rose-400 text-[10px] mt-1">{errors.baseline_spo2.message}</p>}
            </div>
            <div>
              <label className="block text-slate-400 text-[10px] font-bold mb-1 uppercase tracking-wider">Resting HR (bpm)</label>
              <input
                type="number"
                {...register("baseline_heart_rate", { setValueAs: v => v === "" || isNaN(v) ? null : parseInt(v, 10) })}
                placeholder="e.g. 60"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-violet-500"
              />
              {errors.baseline_heart_rate && <p className="text-rose-400 text-[10px] mt-1">{errors.baseline_heart_rate.message}</p>}
            </div>
            <div>
              <label className="block text-slate-400 text-[10px] font-bold mb-1 uppercase tracking-wider">Target Systolic BP</label>
              <input
                type="number"
                {...register("baseline_systolic_bp", { setValueAs: v => v === "" || isNaN(v) ? null : parseInt(v, 10) })}
                placeholder="e.g. 110"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-violet-500"
              />
              {errors.baseline_systolic_bp && <p className="text-rose-400 text-[10px] mt-1">{errors.baseline_systolic_bp.message}</p>}
            </div>
            <div>
              <label className="block text-slate-400 text-[10px] font-bold mb-1 uppercase tracking-wider">Resting Resp Rate</label>
              <input
                type="number"
                {...register("baseline_respiratory_rate", { setValueAs: v => v === "" || isNaN(v) ? null : parseInt(v, 10) })}
                placeholder="e.g. 14"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-violet-500"
              />
              {errors.baseline_respiratory_rate && <p className="text-rose-400 text-[10px] mt-1">{errors.baseline_respiratory_rate.message}</p>}
            </div>
          </div>
          <div>
            <label className="block text-slate-400 text-[10px] font-bold mb-1 uppercase tracking-wider">Clinical Notes (e.g. COPD)</label>
            <textarea
              {...register("notes")}
              placeholder="e.g., Chronic COPD, use Scale 2"
              rows={2}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-violet-500 resize-none"
            />
            {errors.notes && <p className="text-rose-400 text-[10px] mt-1">{errors.notes.message}</p>}
          </div>

          <div className="flex justify-end gap-2 mt-4">
            <button
              type="button"
              onClick={() => {
                setIsEditing(false);
                reset();
              }}
              className="px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:bg-slate-800 text-xs font-semibold"
            >
              <X className="h-4 w-4 inline mr-1" /> Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold flex items-center gap-1 shadow-md shadow-violet-600/20 disabled:opacity-50"
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              Save Baseline
            </button>
          </div>
        </form>
      ) : baseline ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-950/50 border border-slate-800/60 p-3 rounded-lg flex flex-col">
            <span className="text-[10px] font-bold text-slate-500 uppercase">SpO2 Target</span>
            <span className="text-lg font-bold text-violet-400">{baseline.baseline_spo2 ? `${baseline.baseline_spo2}%` : '--'}</span>
          </div>
          <div className="bg-slate-950/50 border border-slate-800/60 p-3 rounded-lg flex flex-col">
            <span className="text-[10px] font-bold text-slate-500 uppercase">Heart Rate Target</span>
            <span className="text-lg font-bold text-violet-400">{baseline.baseline_heart_rate ? `${baseline.baseline_heart_rate} bpm` : '--'}</span>
          </div>
          <div className="bg-slate-950/50 border border-slate-800/60 p-3 rounded-lg flex flex-col">
            <span className="text-[10px] font-bold text-slate-500 uppercase">Resp Rate Target</span>
            <span className="text-lg font-bold text-violet-400">{baseline.baseline_respiratory_rate ? `${baseline.baseline_respiratory_rate} /min` : '--'}</span>
          </div>
          <div className="bg-slate-950/50 border border-slate-800/60 p-3 rounded-lg flex flex-col">
            <span className="text-[10px] font-bold text-slate-500 uppercase">Systolic BP</span>
            <span className="text-lg font-bold text-violet-400">{baseline.baseline_systolic_bp ? `${baseline.baseline_systolic_bp} mmHg` : '--'}</span>
          </div>
          {baseline.notes && (
            <div className="col-span-2 md:col-span-4 bg-slate-950/50 border border-slate-800/60 p-3 rounded-lg">
              <span className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Clinical Notes</span>
              <span className="text-sm font-medium text-slate-300">{baseline.notes}</span>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-6 border border-dashed border-slate-800 rounded-xl">
          <p className="text-slate-500 text-sm mb-2">No personalized baselines set.</p>
          <button
            onClick={() => setIsEditing(true)}
            className="text-violet-400 hover:text-violet-300 text-xs font-bold transition-colors"
          >
            + Add Baseline Context
          </button>
        </div>
      )}
    </div>
  );
}
