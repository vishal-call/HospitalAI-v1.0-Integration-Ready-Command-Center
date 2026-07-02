import React, { useState } from "react";
import { RecommendationDetail, submitDoctorFeedback, FeedbackType } from "@/lib/api";
import { Loader2, Beaker, X, Check } from "lucide-react";

interface FeedbackFormProps {
  recommendation: RecommendationDetail;
  onCancel: () => void;
  onSuccess: () => void;
}

const FEEDBACK_OPTIONS: { value: FeedbackType; label: string }[] = [
  { value: "USEFUL", label: "Clinically Useful" },
  { value: "TOO_SENSITIVE", label: "Too Sensitive" },
  { value: "TOO_LATE", label: "Too Late / Delayed" },
  { value: "INCORRECT_BASELINE", label: "Incorrect Baseline" },
  { value: "ALREADY_REVIEWED", label: "Already Reviewed" },
  { value: "NEEDS_ESCALATION", label: "Needs Escalation" },
];

export default function FeedbackForm({ recommendation, onCancel, onSuccess }: FeedbackFormProps) {
  const [selectedType, setSelectedType] = useState<FeedbackType | null>(null);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requiresComment = selectedType === "TOO_SENSITIVE" || selectedType === "INCORRECT_BASELINE";
  const isValid = selectedType !== null && (!requiresComment || comment.trim().length >= 5);

  const handleSubmit = async () => {
    if (!isValid) return;
    try {
      setLoading(true);
      setError(null);
      await submitDoctorFeedback(recommendation.patient_id, {
        recommendation_id: recommendation.id,
        score_record_id: (recommendation as any).score_record_id || null, // Best effort link if available
        feedback_type: selectedType!,
        comment: comment.trim() || null,
      });
      onSuccess();
    } catch (err: any) {
      setError(err.message || "Failed to submit feedback.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto bg-slate-900 border border-violet-500/30 rounded-2xl shadow-2xl p-6 relative">
      <div className="flex items-center gap-3 mb-5 border-b border-slate-800 pb-4">
        <div className="p-2 bg-violet-500/20 text-violet-400 rounded-lg">
          <Beaker className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-slate-100">Clinical Validation</h3>
          <p className="text-xs text-slate-400">Provide expert feedback on this shadow recommendation.</p>
        </div>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs p-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label className="block text-slate-400 text-xs font-semibold mb-2 uppercase tracking-wider">Evaluation</label>
          <div className="flex flex-wrap gap-2">
            {FEEDBACK_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setSelectedType(opt.value)}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
                  selectedType === opt.value
                    ? "bg-violet-600 border-violet-500 text-white"
                    : "bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-600 hover:bg-slate-800"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {requiresComment && (
          <div className="animate-in fade-in slide-in-from-top-2 duration-300">
            <label className="block text-slate-400 text-xs font-semibold mb-2 uppercase tracking-wider">
              Clinical Context (Required)
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Please explain the physiological reason (e.g. Patient has chronic COPD)..."
              rows={3}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-violet-500 resize-none"
            />
            <p className="text-[10px] text-slate-500 mt-1">Minimum 5 characters required for this feedback type.</p>
          </div>
        )}
        
        {!requiresComment && selectedType !== null && (
          <div className="animate-in fade-in slide-in-from-top-2 duration-300">
            <label className="block text-slate-400 text-xs font-semibold mb-2 uppercase tracking-wider">
              Additional Context (Optional)
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Any additional notes..."
              rows={2}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-violet-500 resize-none"
            />
          </div>
        )}

        <div className="flex gap-2 justify-end mt-6">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 border border-slate-800 text-slate-300 rounded-xl text-xs font-semibold hover:bg-slate-800 transition-colors flex items-center gap-1 disabled:opacity-50"
          >
            <X className="h-4 w-4" /> Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!isValid || loading}
            className="px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1 transition-colors shadow-md shadow-violet-900/20"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            Submit Feedback
          </button>
        </div>
      </div>
    </div>
  );
}
