"use client";

import { useState, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Upload, FileText, Activity, AlertCircle, CheckCircle2, ChevronRight, Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { previewCsvImport, commitCsvImport, CsvPreviewResponse, CsvCommitResponse } from "@/lib/api";

export default function CsvImportPage() {
  const searchParams = useSearchParams();
  const initialType = searchParams?.get("type") === "vitals" ? "vitals" : "patients";
  
  const [entityType, setEntityType] = useState<"patients" | "vitals">(initialType);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [previewResult, setPreviewResult] = useState<CsvPreviewResponse | null>(null);
  const [commitResult, setCommitResult] = useState<CsvCommitResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setPreviewResult(null);
      setCommitResult(null);
      setErrorMsg(null);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
      setPreviewResult(null);
      setCommitResult(null);
      setErrorMsg(null);
    }
  };

  const handlePreview = async () => {
    if (!file) return;
    setIsUploading(true);
    setErrorMsg(null);
    try {
      const res = await previewCsvImport(file, entityType);
      if (res.error) {
        setErrorMsg(res.error);
      } else {
        setPreviewResult(res);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to preview CSV file.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleCommit = async () => {
    if (!file || !previewResult || previewResult.valid_count === 0) return;
    setIsCommitting(true);
    setErrorMsg(null);
    try {
      const res = await commitCsvImport(file, entityType);
      setCommitResult(res);
      setFile(null); // Clear form on success
      setPreviewResult(null);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to commit CSV file.");
    } finally {
      setIsCommitting(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      <div className="flex items-center gap-4">
        <Link href="/integrations" className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-3xl font-bold text-white">CSV Import Engine</h1>
          <p className="text-slate-400 mt-1">Upload files from external systems to securely preview and validate data quality.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Upload Column */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
            
            <div className="space-y-3">
              <label className="text-sm font-medium text-slate-300">Entity Type</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => { setEntityType("patients"); setPreviewResult(null); }}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border transition-all ${
                    entityType === "patients" 
                      ? "border-teal-500 bg-teal-500/10 text-teal-400" 
                      : "border-slate-800 bg-slate-950 text-slate-500 hover:bg-slate-800"
                  }`}
                >
                  <FileText size={24} />
                  <span className="text-sm font-semibold">Patients</span>
                </button>
                <button
                  onClick={() => { setEntityType("vitals"); setPreviewResult(null); }}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border transition-all ${
                    entityType === "vitals" 
                      ? "border-cyan-500 bg-cyan-500/10 text-cyan-400" 
                      : "border-slate-800 bg-slate-950 text-slate-500 hover:bg-slate-800"
                  }`}
                >
                  <Activity size={24} />
                  <span className="text-sm font-semibold">Vitals</span>
                </button>
              </div>
            </div>

            <div className="space-y-3">
              <label className="text-sm font-medium text-slate-300">File Upload (.csv)</label>
              <div 
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-slate-700 hover:border-slate-500 bg-slate-950 rounded-xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition-colors group"
              >
                <input 
                  type="file" 
                  accept=".csv" 
                  className="hidden" 
                  ref={fileInputRef}
                  onChange={handleFileChange}
                />
                <div className="p-3 bg-slate-900 rounded-full text-slate-400 group-hover:text-slate-300 transition-colors">
                  <Upload size={24} />
                </div>
                <div className="text-center">
                  <p className="text-slate-300 font-medium">
                    {file ? file.name : "Click or drag CSV here"}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {file ? `${(file.size / 1024).toFixed(1)} KB` : "Max file size: 50MB"}
                  </p>
                </div>
              </div>
            </div>

            <button
              onClick={handlePreview}
              disabled={!file || isUploading}
              className="w-full flex items-center justify-center gap-2 py-3 bg-teal-600 hover:bg-teal-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-xl font-semibold transition-colors"
            >
              {isUploading ? <Loader2 size={18} className="animate-spin" /> : <ChevronRight size={18} />}
              {isUploading ? "Processing..." : "Generate Preview"}
            </button>
            
            {errorMsg && (
              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-start gap-2">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <p>{errorMsg}</p>
              </div>
            )}
          </div>
        </div>

        {/* Preview Column */}
        <div className="lg:col-span-2">
          {previewResult ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col h-full">
              
              <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  <ShieldCheck size={20} className="text-teal-400" />
                  Data Quality Report
                </h2>
                <div className="flex gap-4">
                  <div className="text-center">
                    <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Total Rows</p>
                    <p className="text-xl font-bold text-slate-200">{previewResult.total_rows}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Valid</p>
                    <p className="text-xl font-bold text-emerald-400">{previewResult.valid_count}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Invalid</p>
                    <p className="text-xl font-bold text-rose-400">{previewResult.invalid_count}</p>
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm whitespace-nowrap">
                  <thead className="bg-slate-900/50 text-slate-400">
                    <tr>
                      <th className="px-6 py-4 font-semibold w-16">Row</th>
                      <th className="px-6 py-4 font-semibold w-24">Status</th>
                      <th className="px-6 py-4 font-semibold">Validation Errors</th>
                      <th className="px-6 py-4 font-semibold">Raw JSON Payload</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {previewResult.rows.map((r, i) => (
                      <tr 
                        key={i} 
                        className={
                          r.is_valid 
                            ? "bg-emerald-500/5 hover:bg-emerald-500/10 transition-colors" 
                            : "bg-rose-500/10 hover:bg-rose-500/20 transition-colors"
                        }
                      >
                        <td className="px-6 py-4 text-slate-400 font-mono">#{r.row_number}</td>
                        <td className="px-6 py-4">
                          {r.is_valid ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400">
                              <CheckCircle2 size={14} /> Valid
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-400">
                              <AlertCircle size={14} /> Invalid
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          {!r.is_valid && r.errors.length > 0 ? (
                            <ul className="list-disc list-inside text-rose-400 space-y-1 font-medium text-xs whitespace-normal max-w-sm">
                              {r.errors.map((err, idx) => (
                                <li key={idx}>{err}</li>
                              ))}
                            </ul>
                          ) : (
                            <span className="text-slate-500 italic text-xs">No errors</span>
                          )}
                        </td>
                        <td className="px-6 py-4 font-mono text-xs text-slate-300">
                          <div className="max-w-md overflow-hidden text-ellipsis bg-slate-950 p-2 rounded-lg border border-slate-800">
                            {JSON.stringify(r.raw_data)}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {previewResult.rows.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                          No rows found in the CSV.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              
              <div className="p-6 bg-slate-950 border-t border-slate-800 flex justify-end">
                <button 
                  onClick={handleCommit}
                  disabled={previewResult.valid_count === 0 || isCommitting}
                  className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-lg font-semibold transition-colors flex items-center gap-2"
                >
                  {isCommitting ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
                  {isCommitting ? "Importing & Scoring..." : `Confirm & Import ${previewResult.valid_count} Rows`}
                </button>
              </div>

            </div>
          ) : commitResult ? (
            <div className="h-full border border-emerald-500/20 bg-emerald-500/5 rounded-2xl flex flex-col items-center justify-center p-12 text-center text-emerald-400">
              <CheckCircle2 size={64} className="mb-4 text-emerald-500" />
              <h3 className="text-2xl font-bold text-white mb-2">Import Successful</h3>
              <p className="max-w-md text-slate-300">
                Successfully processed <strong>{commitResult.valid_count}</strong> rows. The clinical engine has updated patient risk scores and generated tasks for any high-risk changes.
              </p>
              <div className="mt-6 flex items-center gap-4 text-sm text-slate-400">
                <span>Total: {commitResult.total_rows}</span>
                <span>•</span>
                <span className="text-emerald-400">Valid: {commitResult.valid_count}</span>
                <span>•</span>
                <span className="text-rose-400">Invalid: {commitResult.invalid_count}</span>
              </div>
            </div>
          ) : (
            <div className="h-full border-2 border-dashed border-slate-800 rounded-2xl flex flex-col items-center justify-center p-12 text-center text-slate-500 bg-slate-900/30">
              <ShieldCheck size={48} className="mb-4 text-slate-700" />
              <h3 className="text-xl font-semibold text-slate-400 mb-2">Awaiting File Preview</h3>
              <p className="max-w-sm">Upload a CSV file and click 'Generate Preview' to run the strict data validation rules engine.</p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

// Needed because ShieldCheck is not exported by default from lucide-react if not added above.
function ShieldCheckIcon(props: any) {
    return <ShieldCheck {...props} />;
}
