"use client";

import React from "react";
import { Activity, ShieldCheck, HeartPulse, LogOut } from "lucide-react";
import { useAuth } from "@/lib/AuthContext";
import NotificationTray from "./NotificationTray";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function GlobalNavbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  if (!user || pathname === '/') return null; // Don't render navbar if not logged in or on landing page

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center justify-between shadow-sm shadow-slate-900/50">
      <div className="flex items-center gap-6">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-extrabold text-xl tracking-tight text-white flex items-center gap-2">
              HospitalAI <span className="text-indigo-400 font-medium text-xs bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">OPERATIONS COMMAND</span>
            </h1>
            <p className="text-xs text-slate-400 font-medium hidden sm:block">Human-in-the-Loop Operational Resource Management Platform</p>
          </div>
        </Link>

        {/* Global Navigation Links */}
        <div className="hidden md:flex items-center gap-1 ml-4 border-l border-slate-800 pl-6">
          <Link 
            href="/dashboard" 
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${pathname === '/dashboard' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
          >
            Dashboard
          </Link>
          <Link 
            href="/response-center" 
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${pathname === '/response-center' ? 'bg-rose-500/10 text-rose-400' : 'text-slate-400 hover:text-rose-400 hover:bg-rose-500/10'}`}
          >
            <HeartPulse className="h-4 w-4" />
            Response Center
          </Link>
          {user.role === "ADMIN" && (
            <Link 
              href="/admin" 
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${pathname === '/admin' ? 'bg-indigo-500/10 text-indigo-400' : 'text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10'}`}
            >
              Admin Control
            </Link>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* The Notification Tray injected here */}
        <NotificationTray />

        {/* User Profile Info */}
        <div className="flex items-center gap-2.5 px-3 py-1 bg-slate-900/50 border border-slate-800/80 rounded-xl text-xs">
          <div className="h-7 w-7 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div className="flex flex-col text-left">
            <span className="font-bold text-slate-200">{user.username}</span>
            <span className="text-[10px] text-emerald-400 font-mono tracking-wider uppercase">{user.role}</span>
          </div>
        </div>

        <button
          onClick={logout}
          className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-rose-950/25 hover:border-rose-550/30 text-slate-400 hover:text-rose-400 transition-all"
          title="Log Out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
