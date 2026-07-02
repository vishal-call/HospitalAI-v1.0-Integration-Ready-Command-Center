"use client";

import React, { useState } from "react";
import { ReconciliationIssue, resolveReconciliationIssue } from "@/lib/api";
import { AlertTriangle, Check, X, MessageSquare, Loader2, Info } from "lucide-react";

interface ReconciliationQueueProps {
  issues: ReconciliationIssue[];
  onIssueResolved: (id: number) => void;
}

export default function ReconciliationQueue({ issues, onIssueResolved }: ReconciliationQueueProps) {
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [resolutionNote, setResolutionNote] = useState<string>("");
  const [showNoteFor, setShowNoteFor] = useState<number | null>(null);

  const handleResolve = async (id: number, action: string) => {
    setResolvingId(id);
    try {
      await resolveReconciliationIssue(id, action, resolutionNote);
      onIssueResolved(id);
    } catch (err: any) {
      alert(err.message || "Failed to resolve issue");
    } finally {
      setResolvingId(null);
      setShowNoteFor(null);
      setResolutionNote("");
    }
  };

  if (issues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-500 bg-slate-900/30 rounded-xl border border-dashed border-slate-800">
        <Check size={48} className="mb-4 text-emerald-500/50" />
        <h3 className="text-xl font-medium text-slate-300">All Clear</h3>
        <p>No active reconciliation issues found.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950">
      <table className="w-full text-left text-sm text-slate-300">
        <thead className="bg-slate-900 text-slate-400 font-medium">
          <tr>
            <th className="px-6 py-4">Entity</th>
            <th className="px-6 py-4">Source System</th>
            <th className="px-6 py-4">Field Name</th>
            <th className="px-6 py-4">Internal Value</th>
            <th className="px-6 py-4">External Value</th>
            <th className="px-6 py-4">Severity</th>
            <th className="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {issues.map((issue) => (
            <tr key={issue.id} className="hover:bg-slate-900/50 transition-colors">
              <td className="px-6 py-4 font-medium text-white">
                {issue.entity_type} <span className="text-slate-500">#{issue.entity_id}</span>
              </td>
              <td className="px-6 py-4">{issue.source_system}</td>
              <td className="px-6 py-4 font-mono text-indigo-400">{issue.field_name}</td>
              <td className="px-6 py-4">
                <div className="px-2 py-1 bg-slate-800 rounded inline-block">
                  {issue.internal_value || <span className="text-slate-500 italic">None</span>}
                </div>
              </td>
              <td className="px-6 py-4">
                <div className="px-2 py-1 bg-amber-900/30 text-amber-400 border border-amber-900/50 rounded inline-block">
                  {issue.external_value}
                </div>
              </td>
              <td className="px-6 py-4">
                <span className={`px-2 py-1 text-xs font-semibold rounded-full flex items-center w-max gap-1
                  ${issue.severity === 'HIGH' ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-400'}`}>
                  {issue.severity === 'HIGH' ? <AlertTriangle size={12} /> : <Info size={12} />}
                  {issue.severity}
                </span>
              </td>
              <td className="px-6 py-4 text-right">
                {showNoteFor === issue.id ? (
                  <div className="flex flex-col items-end gap-2 min-w-[250px]">
                    <input
                      type="text"
                      placeholder="Optional resolution note..."
                      className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-indigo-500"
                      value={resolutionNote}
                      onChange={(e) => setResolutionNote(e.target.value)}
                      autoFocus
                    />
                    <div className="flex gap-2">
                      <button 
                        onClick={() => setShowNoteFor(null)}
                        className="px-3 py-1.5 text-slate-400 hover:text-white transition-colors"
                        disabled={resolvingId === issue.id}
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleResolve(issue.id, "ACCEPT_EXTERNAL")}
                        disabled={resolvingId === issue.id}
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded font-medium flex items-center gap-2"
                      >
                        {resolvingId === issue.id && <Loader2 size={14} className="animate-spin" />}
                        Accept External
                      </button>
                      <button
                        onClick={() => handleResolve(issue.id, "KEEP_INTERNAL")}
                        disabled={resolvingId === issue.id}
                        className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded font-medium flex items-center gap-2"
                      >
                        {resolvingId === issue.id && <Loader2 size={14} className="animate-spin" />}
                        Keep Internal
                      </button>
                    </div>
                  </div>
                ) : (
                  <button 
                    onClick={() => setShowNoteFor(issue.id)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Resolve...
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
