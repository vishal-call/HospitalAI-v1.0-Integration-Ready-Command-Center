"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "../../lib/AuthContext";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const { login, user } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      router.push("/");
    }
  }, [user, router]);

  const demoAccounts = [
    {
      role: "Coordinator",
      email: "coord@hospitalai.com",
      desc: "Approve recommendations and step-downs",
    },
    {
      role: "Doctor",
      email: "doctor@hospitalai.com",
      desc: "Approve recommendations and step-downs",
    },
    {
      role: "Nurse",
      email: "nurse@hospitalai.com",
      desc: "Telemetry views only (Action Center read-only)",
    },
  ];

  const handleDemoClick = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("password123");
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please enter both email and password.");
      return;
    }
    
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || "Authentication failed. Check your connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 p-6 font-sans antialiased text-slate-100">
      {/* Background gradients */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[40%] -left-[20%] w-[80%] h-[80%] rounded-full bg-emerald-950/15 blur-[120px]" />
        <div className="absolute -bottom-[40%] -right-[20%] w-[80%] h-[80%] rounded-full bg-teal-950/15 blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-4xl grid md:grid-cols-2 gap-8 items-center bg-slate-900/60 border border-slate-800/80 rounded-2xl p-8 backdrop-blur-xl shadow-2xl">
        
        {/* Left column: Welcome / Information */}
        <div className="space-y-6 flex flex-col justify-center h-full">
          <div>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-3 uppercase tracking-wider">
              System Secure
            </span>
            <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
              Hospital<span className="text-emerald-400">AI</span>
            </h1>
            <p className="mt-3 text-slate-400 text-sm leading-relaxed">
              Operational Command Center. Secure clinical orchestration, Early Warning Scoring (EWS), and Human-in-the-Loop capacity management.
            </p>
          </div>

          {/* Interactive Demo Credentials list */}
          <div className="space-y-3">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
              Demo Credentials
            </h2>
            <div className="grid gap-2">
              {demoAccounts.map((account) => (
                <button
                  key={account.role}
                  type="button"
                  onClick={() => handleDemoClick(account.email)}
                  className="flex flex-col items-start text-left p-3 rounded-lg border border-slate-800 bg-slate-900/40 hover:bg-slate-800/60 hover:border-slate-700/80 transition-all duration-200"
                >
                  <div className="flex justify-between w-full items-center">
                    <span className="text-xs font-bold text-emerald-400">{account.role}</span>
                    <span className="text-[10px] text-slate-500 font-mono">pwd: password123</span>
                  </div>
                  <span className="text-sm font-medium text-slate-300 mt-0.5">{account.email}</span>
                  <span className="text-[10px] text-slate-500 mt-1">{account.desc}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right column: Login Form */}
        <div className="border-t md:border-t-0 md:border-l border-slate-800/80 pt-6 md:pt-0 md:pl-8 flex flex-col justify-center h-full">
          <h2 className="text-xl font-bold text-white mb-6">Staff Access Login</h2>

          {error && (
            <div className="p-3 mb-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Staff Email Address
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="doctor@hospitalai.com"
                className="w-full bg-slate-950/80 border border-slate-800 rounded-lg py-2.5 px-4 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500/50 transition-colors"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Security Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-950/80 border border-slate-800 rounded-lg py-2.5 px-4 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500/50 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center py-2.5 px-4 mt-6 rounded-lg bg-emerald-500 text-slate-950 text-sm font-semibold hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
              ) : (
                "Authorize Access"
              )}
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}
