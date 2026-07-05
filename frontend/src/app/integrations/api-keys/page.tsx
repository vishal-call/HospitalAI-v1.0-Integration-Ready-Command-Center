"use client";

import React, { useState, useEffect } from "react";
import { ArrowLeft, Key, Plus, ShieldAlert, Trash2, Check, Copy } from "lucide-react";
import Link from "next/link";
import { getApiKeys, createApiKey, revokeApiKey, ApiKey } from "@/lib/api";

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  
  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [newName, setNewName] = useState("");
  const [newScopes, setNewScopes] = useState<string[]>(["vitals.write"]);

  // Raw key display state
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    setIsLoading(true);
    try {
      const data = await getApiKeys();
      setKeys(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setIsCreating(true);
    try {
      const result = await createApiKey(newName, newScopes);
      setNewlyCreatedKey(result.raw_key);
      setShowModal(false);
      setNewName("");
      fetchKeys();
    } catch (err) {
      alert("Failed to create API key");
    } finally {
      setIsCreating(false);
    }
  };

  const handleRevoke = async (id: number) => {
    if (!confirm("Are you sure you want to revoke this API key? This will immediately break any integrations using it.")) return;
    try {
      await revokeApiKey(id);
      fetchKeys();
    } catch (err) {
      alert("Failed to revoke API key");
    }
  };

  const copyToClipboard = () => {
    if (newlyCreatedKey) {
      navigator.clipboard.writeText(newlyCreatedKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/integrations" className="text-sm font-medium text-slate-400 hover:text-white flex items-center gap-2 mb-4 transition-colors w-max">
            <ArrowLeft size={16} /> Back to Integration Center
          </Link>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-indigo-500/20 rounded-lg border border-indigo-500/30">
              <Key size={24} className="text-indigo-400" />
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight">API Keys</h1>
          </div>
          <p className="text-slate-400">Manage authenticating credentials for live API integrations.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 shadow-lg shadow-indigo-900/20 border border-indigo-500/50"
        >
          <Plus size={16} /> Generate New Key
        </button>
      </div>

      {newlyCreatedKey && (
        <div className="p-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 shadow-lg">
          <div className="flex gap-4">
            <div className="p-2 rounded-full bg-rose-500/20 text-rose-400 h-max">
              <ShieldAlert size={24} />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-rose-400 mb-1">Save your API key securely</h3>
              <p className="text-sm text-slate-300 mb-4">
                Please copy this key and store it securely. For your protection, you will <strong>never be able to see it again</strong> after you leave or refresh this page.
              </p>
              
              <div className="flex items-center gap-2 mb-4">
                <div className="px-4 py-3 bg-slate-950 border border-slate-800 rounded-lg font-mono text-emerald-400 text-lg flex-1 break-all">
                  {newlyCreatedKey}
                </div>
                <button
                  onClick={copyToClipboard}
                  className="p-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors border border-slate-700 h-full"
                  title="Copy to clipboard"
                >
                  {copied ? <Check size={20} className="text-emerald-400" /> : <Copy size={20} />}
                </button>
              </div>

              <button
                onClick={() => setNewlyCreatedKey(null)}
                className="text-sm font-medium text-slate-400 hover:text-white transition-colors"
              >
                I have saved my key securely
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950 shadow-lg">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-900 text-slate-400 font-medium">
            <tr>
              <th className="px-6 py-4">Name</th>
              <th className="px-6 py-4">Key Prefix</th>
              <th className="px-6 py-4">Scopes</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Created At</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                  Loading API keys...
                </td>
              </tr>
            ) : keys.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                  No API keys generated yet.
                </td>
              </tr>
            ) : (
              keys.map((key) => (
                <tr key={key.id} className="hover:bg-slate-900/50 transition-colors">
                  <td className="px-6 py-4 font-medium text-white">{key.name}</td>
                  <td className="px-6 py-4 font-mono text-slate-400">{key.key_prefix}...</td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      {key.scopes.map(scope => (
                        <span key={scope} className="px-2 py-1 bg-indigo-500/20 text-indigo-400 rounded text-xs border border-indigo-500/30">
                          {scope}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {key.is_active ? (
                      <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-xs font-semibold border border-emerald-500/30">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-slate-800 text-slate-400 rounded-full text-xs font-semibold border border-slate-700">
                        Revoked
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-slate-400">
                    {new Date(key.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {key.is_active && (
                      <button
                        onClick={() => handleRevoke(key.id)}
                        className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded transition-colors"
                        title="Revoke Key"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-4">Generate API Key</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Key Name</label>
                  <input
                    type="text"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                    placeholder="e.g. ICU Vitals Monitor A"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Permissions</label>
                  <div className="bg-slate-950 border border-slate-700 rounded-lg p-3">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input 
                        type="checkbox" 
                        className="w-4 h-4 rounded border-slate-600 text-indigo-600 focus:ring-indigo-500 bg-slate-800"
                        checked={newScopes.includes("vitals.write")}
                        onChange={(e) => {
                          if (e.target.checked) setNewScopes(["vitals.write"]);
                          else setNewScopes([]);
                        }}
                      />
                      <span className="text-sm font-medium text-white">vitals.write</span>
                    </label>
                    <p className="text-xs text-slate-500 mt-1 ml-7">Allows writing vitals to patient records.</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="p-4 bg-slate-950/50 border-t border-slate-800 flex justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
                disabled={isCreating}
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!newName.trim() || isCreating}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-indigo-900/20 border border-indigo-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCreating ? "Generating..." : "Generate Key"}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
