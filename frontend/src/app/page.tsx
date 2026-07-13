"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Activity, 
  ArrowRight, 
  Layers, 
  ShieldCheck, 
  Zap, 
  ArrowUpRight, 
  Cpu, 
  X, 
  BookOpen, 
  Workflow,
  Lock,
  ChevronDown,
  Network
} from "lucide-react";
import { useAuth } from "@/lib/AuthContext";

export default function LandingPage() {
  const { user } = useAuth();
  const [isWhitepaperOpen, setIsWhitepaperOpen] = useState(false);
  const [openAccordion, setOpenAccordion] = useState<number | null>(null);

  // Animations configuration
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { y: 25, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { type: "spring" as const, stiffness: 100, damping: 16 }
    }
  };

  const scrollRevealVariants = {
    hidden: { y: 35, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] as const }
    }
  };

  const faqItems = [
    {
      q: "How does the platform address HIPAA Compliance?",
      a: "HospitalAI enforces strict data security policies, encrypting all data in transit using TLS 1.3 and all data at rest using AES-256 transparent database encryption. User authentication is secured via HttpOnly, Secure JWT cookies, preventing XSS-based clinical token theft, while session audits are written to an immutable event ledger."
    },
    {
      q: "How is route-level clinical access restricted?",
      a: "The API layer enforces a cryptographic, role-based access control (RBAC) model. Roles like DOCTOR and NURSE grant read-only telemetry views, COORDINATORS hold permissions to approve patient relocations, and ADMIN roles are required to decommission wards, provision beds, or patch staff credentials."
    },
    {
      q: "How does the system ensure double-allocation bed prevention?",
      a: "HospitalAI's transaction layers utilize database-level pessimistic locking. When a coordinator begins reviewing a patient recommendation, the target bed row is locked at the database transaction boundary, preventing parallel triage coordinators from double-admitting or allocating that same clinical space."
    }
  ];

  return (
    <div className="min-h-screen bg-[#050505] text-slate-100 font-sans relative overflow-hidden selection:bg-emerald-500/20 selection:text-emerald-300">
      
      {/* BACKGROUND glowing atmosphere mesh */}
      <div className="absolute top-[-15%] left-[-10%] w-[55%] h-[55%] rounded-full bg-emerald-500/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[15%] right-[-10%] w-[65%] h-[65%] rounded-full bg-blue-600/10 blur-[130px] pointer-events-none" />
      <div className="absolute top-[25%] left-[35%] w-[400px] h-[400px] rounded-full bg-indigo-500/5 blur-[120px] pointer-events-none" />

      {/* FLOATING PILL NAVBAR */}
      <motion.nav 
        initial={{ y: -30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: "spring", stiffness: 120, delay: 0.2 }}
        className="w-full max-w-4xl mx-auto px-4 pt-6 sticky top-0 z-50 pointer-events-none"
      >
        <div className="w-full bg-white/5 backdrop-blur-3xl border border-white/10 rounded-full px-6 py-3 flex items-center justify-between shadow-2xl shadow-black/80 pointer-events-auto">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
              <Activity className="h-4.5 w-4.5 text-white" />
            </div>
            <span className="font-extrabold text-base tracking-tight text-white flex items-center gap-1.5">
              HospitalAI
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse shadow-glow shadow-emerald-400/50" />
            </span>
          </Link>

          {/* Links */}
          <div className="hidden sm:flex items-center gap-6">
            <a href="#features" className="text-xs font-semibold text-slate-400 hover:text-white transition-colors">Subsystems</a>
            <a href="#telemetry" className="text-xs font-semibold text-slate-400 hover:text-white transition-colors">Telemetry</a>
            <a href="#faq" className="text-xs font-semibold text-slate-400 hover:text-white transition-colors">Compliance</a>
          </div>

          {/* CTA */}
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Link 
              href={user ? "/dashboard" : "/login"}
              className="flex items-center gap-1.5 px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-[#050505] rounded-full text-xs font-bold shadow-lg transition-all"
            >
              Access System
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </motion.div>
        </div>
      </motion.nav>

      {/* HERO SECTION */}
      <section className="max-w-7xl mx-auto px-6 pt-16 pb-20 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-center">
          
          {/* Left Column (60% width equivalent) */}
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="lg:col-span-7 flex flex-col items-start text-left"
          >
            {/* Tag */}
            <motion.div 
              variants={itemVariants}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold tracking-wider uppercase mb-8"
            >
              <Cpu className="h-3 w-3" /> Intelligent Clinical Logistics & Telemetry
            </motion.div>

            {/* Headline */}
            <motion.h1 
              variants={itemVariants}
              className="text-4xl sm:text-6xl font-black tracking-tight leading-[1.08] mb-6 bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60"
            >
              Autonomous Clinical <br />
              Intelligence.
            </motion.h1>

            {/* Subheadline */}
            <motion.p 
              variants={itemVariants}
              className="text-sm sm:text-base text-slate-400 max-w-xl leading-relaxed mb-10"
            >
              Anticipate patient deterioration and automate bed capacity via live HL7/FHIR streams. A perfect balance between scientific precision and autonomous orchestration.
            </motion.p>

            {/* Action CTAs */}
            <motion.div variants={itemVariants} className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
              <motion.div whileHover={{ scale: 1.02, boxShadow: "0 0 20px rgba(16, 185, 129, 0.4)" }} whileTap={{ scale: 0.98 }} className="w-full sm:w-auto">
                <Link 
                  href={user ? "/dashboard" : "/login"}
                  className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-3.5 bg-emerald-500 text-[#050505] font-extrabold text-sm rounded-full transition-all"
                >
                  Access Command Center
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </motion.div>
              <motion.button 
                whileHover={{ scale: 1.02, backgroundColor: "rgba(255,255,255,0.08)" }} 
                whileTap={{ scale: 0.98 }}
                onClick={() => setIsWhitepaperOpen(true)}
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-3.5 bg-white/5 border border-white/10 text-white font-bold text-sm rounded-full transition-all"
              >
                View Architecture
                <BookOpen className="h-4 w-4" />
              </motion.button>
            </motion.div>
          </motion.div>

          {/* Right Column (40% width equivalent) - Visual Centerpiece */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, delay: 0.4 }}
            className="lg:col-span-5 w-full flex justify-center relative"
          >
            {/* The Main AWSMD Glass container */}
            <div className="w-full aspect-square bg-white/5 backdrop-blur-3xl border border-white/10 shadow-2xl rounded-[2rem] flex items-center justify-center p-6 relative overflow-hidden">
              
              {/* Matrix dots grid background */}
              <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:20px_20px] opacity-25" />

              {/* Pulsing Gradient Orbs in background */}
              <motion.div
                animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.5, 0.3] }}
                transition={{ repeat: Infinity, duration: 6, ease: "easeInOut" }}
                className="h-48 w-48 rounded-full bg-emerald-500 blur-[100px] absolute top-10 left-10 pointer-events-none"
              />
              <motion.div
                animate={{ scale: [1, 1.15, 1], opacity: [0.3, 0.5, 0.3] }}
                transition={{ repeat: Infinity, duration: 8, ease: "easeInOut" }}
                className="h-48 w-48 rounded-full bg-blue-600 blur-[100px] absolute bottom-10 right-10 pointer-events-none"
              />

              {/* Slow 360-degree rotating abstract constellation mesh */}
              <motion.div 
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 20, ease: "linear" }}
                className="w-[80%] h-[80%] relative z-10 flex items-center justify-center"
              >
                <svg className="w-full h-full text-slate-400" viewBox="0 0 200 200" fill="none">
                  {/* Concentric rings */}
                  <circle cx="100" cy="100" r="80" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
                  <circle cx="100" cy="100" r="50" stroke="rgba(255,255,255,0.07)" strokeWidth="1" />
                  <circle cx="100" cy="100" r="20" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                  {/* Constellation lines */}
                  <line x1="100" y1="20" x2="150" y2="60" stroke="rgba(16, 185, 129, 0.25)" strokeWidth="1" />
                  <line x1="150" y1="60" x2="160" y2="130" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                  <line x1="160" y1="130" x2="100" y2="180" stroke="rgba(59, 130, 246, 0.25)" strokeWidth="1" />
                  <line x1="100" y1="180" x2="40" y2="130" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                  <line x1="40" y1="130" x2="50" y2="60" stroke="rgba(16, 185, 129, 0.25)" strokeWidth="1" />
                  <line x1="50" y1="60" x2="100" y2="20" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                  {/* Inner links to core */}
                  <line x1="100" y1="100" x2="100" y2="20" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
                  <line x1="100" y1="100" x2="150" y2="60" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
                  <line x1="100" y1="100" x2="160" y2="130" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
                  <line x1="100" y1="100" x2="100" y2="180" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
                  {/* Core nodes */}
                  <circle cx="100" cy="20" r="4" fill="#10b981" />
                  <circle cx="150" cy="60" r="3" fill="#ffffff" />
                  <circle cx="160" cy="130" r="4" fill="#3b82f6" />
                  <circle cx="100" cy="180" r="3" fill="#ffffff" />
                  <circle cx="40" cy="130" r="4" fill="#10b981" />
                  <circle cx="50" cy="60" r="3" fill="#3b82f6" />
                  <circle cx="100" cy="100" r="5" fill="#6366f1" />
                </svg>
              </motion.div>
            </div>

            {/* FLOATING DATA WIDGETS (Micro-Glass) */}
            <motion.div 
              animate={{ y: [0, -8, 0] }}
              transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
              className="absolute top-8 -left-8 bg-white/5 border border-white/10 backdrop-blur-3xl rounded-full px-4 py-2 flex items-center gap-2 shadow-2xl z-20"
            >
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-[9px] font-mono font-bold text-slate-200">🟢 Live HL7/FHIR Sync</span>
            </motion.div>

            <motion.div 
              animate={{ y: [0, 8, 0] }}
              transition={{ repeat: Infinity, duration: 6, ease: "easeInOut" }}
              className="absolute bottom-16 -right-6 bg-white/5 border border-white/10 backdrop-blur-3xl rounded-full px-4 py-2 flex items-center gap-2 shadow-2xl z-20"
            >
              <span className="h-2 w-2 rounded-full bg-blue-500" />
              <span className="text-[9px] font-mono font-bold text-slate-200">1.13s Median Latency</span>
            </motion.div>
          </motion.div>

        </div>
      </section>

      {/* THE STAGGERED BENTO GRID */}
      <motion.section 
        id="features"
        variants={scrollRevealVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-100px" }}
        className="max-w-7xl mx-auto px-6 py-20 relative z-10 border-t border-white/5"
      >
        <div className="flex flex-col items-center text-center mb-16">
          <h2 className="text-xs uppercase font-mono tracking-widest text-indigo-400 font-bold mb-3">Enterprise Bento Grid</h2>
          <h3 className="text-2xl sm:text-4xl font-black text-white">Biotech Logistical Architecture</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          
          {/* Block 1 (col-span-8): Predictive Early Warning (EWS) */}
          <motion.div 
            whileHover={{ y: -5, borderColor: "rgba(255,255,255,0.2)" }}
            className="md:col-span-8 bg-white/5 border border-white/10 rounded-[2rem] p-8 backdrop-blur-3xl flex flex-col justify-between min-h-[300px] transition-colors relative overflow-hidden shadow-2xl"
          >
            <div className="absolute top-0 right-0 w-[150px] h-[150px] bg-indigo-500/5 rounded-full blur-[60px] pointer-events-none" />
            <div className="flex items-center justify-between mb-4">
              <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Zap className="h-5 w-5" />
              </div>
              <span className="text-[9px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">NEWS2 Compliance</span>
            </div>
            <div>
              <h4 className="font-extrabold text-lg text-white mb-2">Predictive Early Warning Scoring (EWS)</h4>
              <p className="text-xs text-slate-400 leading-relaxed max-w-xl">
                FastAPI asynchronous loops evaluate patient vitals logs continuously. Renders subsecond EWS warnings to clinical coordinators, flagging deterioration before it manifests physically.
              </p>
            </div>

            {/* Mock Time Series Chart */}
            <div className="w-full h-24 overflow-hidden mt-6 relative rounded-xl bg-slate-950/20 border border-white/5">
              {/* Left fade gradient cover */}
              <div className="absolute top-0 left-0 bottom-0 w-16 bg-gradient-to-r from-slate-950/80 to-transparent z-20 pointer-events-none" />
              {/* Right fade gradient cover */}
              <div className="absolute top-0 right-0 bottom-0 w-16 bg-gradient-to-l from-slate-950/80 to-transparent z-20 pointer-events-none" />
              
              <motion.svg 
                className="w-[200%] h-full text-emerald-400 absolute top-0 left-0" 
                viewBox="0 0 1000 100" 
                fill="none"
                animate={{ x: ["0%", "-50%"] }}
                transition={{
                  duration: 8,
                  repeat: Infinity,
                  ease: "linear"
                }}
              >
                <path d="M0 50 Q 125 10, 250 50 T 500 50 Q 625 10, 750 50 T 1000 50" stroke="#10b981" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
              </motion.svg>
            </div>
          </motion.div>

          {/* Block 2 (col-span-4): Multi-Agent Logistics */}
          <motion.div 
            whileHover={{ y: -5, borderColor: "rgba(255,255,255,0.2)" }}
            className="md:col-span-4 bg-white/5 border border-white/10 rounded-[2rem] p-8 backdrop-blur-3xl flex flex-col justify-between min-h-[300px] transition-colors shadow-2xl"
          >
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Workflow className="h-5 w-5" />
            </div>
            <div>
              <h4 className="font-extrabold text-lg text-white mb-2">Multi-Agent Logistics</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Autonomous orchestrators negotiate capacity constraints across partner networks, planning step-down relocations and inter-hospital moves.
              </p>
            </div>
          </motion.div>

          {/* Block 3 (col-span-4): Zero-Trust Architecture */}
          <motion.div 
            whileHover={{ y: -5, borderColor: "rgba(255,255,255,0.2)" }}
            className="md:col-span-4 bg-white/5 border border-white/10 rounded-[2rem] p-8 backdrop-blur-3xl flex flex-col justify-between min-h-[300px] transition-colors shadow-2xl"
          >
            <div className="h-10 w-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Lock className="h-5 w-5" />
            </div>
            <div>
              <h4 className="font-extrabold text-lg text-white mb-2">Zero-Trust Security</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Protected via secure TLS 1.3 handshakes, cryptographically signed cookies, and route-level role authorizations (RBAC).
              </p>
            </div>
          </motion.div>

          {/* Block 4 (col-span-8): Automated Bed Allocation */}
          <motion.div 
            whileHover={{ y: -5, borderColor: "rgba(255,255,255,0.2)" }}
            className="md:col-span-8 bg-white/5 border border-white/10 rounded-[2rem] p-8 backdrop-blur-3xl flex flex-col justify-between min-h-[300px] transition-colors relative overflow-hidden shadow-2xl"
          >
            <div className="absolute bottom-0 right-0 w-[150px] h-[150px] bg-emerald-500/5 rounded-full blur-[60px] pointer-events-none" />
            <div className="flex items-center justify-between mb-4">
              <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <Network className="h-5 w-5" />
              </div>
              <span className="text-[9px] font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">DB Locking</span>
            </div>
            <div>
              <h4 className="font-extrabold text-lg text-white mb-2">Automated Bed Allocation</h4>
              <p className="text-xs text-slate-400 leading-relaxed max-w-xl">
                Implements database-level row locks to eliminate allocation conflicts. When a transfer suggestion is initiated, target beds are reserved instantly, securing clinical spaces with zero collision.
              </p>
            </div>
          </motion.div>

        </div>
      </motion.section>

      {/* OPERATIONAL PERFORMANCE BANNER */}
      <motion.section 
        id="telemetry"
        variants={scrollRevealVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-100px" }}
        className="max-w-7xl mx-auto px-6 py-12 relative z-10"
      >
        <div className="w-full bg-white/5 border border-white/10 rounded-[2rem] p-8 sm:p-12 backdrop-blur-3xl relative overflow-hidden shadow-2xl flex flex-col sm:flex-row items-center justify-between gap-8">
          <div className="max-w-md">
            <h3 className="font-extrabold text-xl text-white mb-2">Outcome Telemetry Logs</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              HospitalAI measures performance logging directly to demonstrate saving metrics and data-rate latencies.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-8 sm:gap-16">
            <div className="text-center sm:text-left">
              <div className="text-3xl sm:text-4xl font-black text-emerald-400 drop-shadow-[0_0_12px_rgba(16,185,129,0.15)]">1.13s</div>
              <div className="text-[9px] text-slate-500 uppercase tracking-widest font-mono mt-1">Median AI Response</div>
            </div>
            <div className="text-center sm:text-left">
              <div className="text-3xl sm:text-4xl font-black text-indigo-400 drop-shadow-[0_0_12px_rgba(99,102,241,0.15)]">100%</div>
              <div className="text-[9px] text-slate-500 uppercase tracking-widest font-mono mt-1">Telemetry Retention</div>
            </div>
            <div className="text-center sm:text-left">
              <div className="text-3xl sm:text-4xl font-black text-white">Zero-Ops</div>
              <div className="text-[9px] text-slate-500 uppercase tracking-widest font-mono mt-1">Capacity Scaling</div>
            </div>
          </div>
        </div>
      </motion.section>

      {/* COMPLIANCE SECTION */}
      <motion.section 
        id="faq"
        variants={scrollRevealVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-100px" }}
        className="max-w-4xl mx-auto px-6 py-20 relative z-10 border-t border-white/5"
      >
        <div className="flex flex-col items-center text-center mb-12">
          <h2 className="text-xs uppercase font-mono tracking-widest text-indigo-400 font-bold mb-3">Compliance & Security</h2>
          <h3 className="text-2xl sm:text-3xl font-extrabold text-white">Trust & Governance Architecture</h3>
        </div>

        <div className="space-y-4">
          {faqItems.map((item, idx) => {
            const isOpen = openAccordion === idx;
            return (
              <div 
                key={idx}
                className="bg-white/5 border border-white/10 rounded-[2rem] overflow-hidden transition-all duration-300 shadow-2xl"
              >
                <button
                  onClick={() => setOpenAccordion(isOpen ? null : idx)}
                  className="w-full px-6 py-5 flex items-center justify-between text-left font-bold text-sm sm:text-base text-white hover:bg-white/[0.01] transition-colors"
                >
                  <span>{item.q}</span>
                  <ChevronDown className={`h-4.5 w-4.5 text-slate-450 transition-transform duration-300 ${isOpen ? "rotate-180 text-white" : ""}`} />
                </button>
                
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: "easeInOut" }}
                    >
                      <div className="px-6 pb-6 pt-2 text-xs sm:text-sm text-slate-400 border-t border-white/5 leading-relaxed">
                        {item.a}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </motion.section>

      {/* FOOTER */}
      <footer className="max-w-7xl mx-auto px-6 py-12 relative z-10 text-center border-t border-white/5">
        <p className="text-[10px] text-slate-600 font-mono">
          &copy; {new Date().getFullYear()} HospitalAI INC. ALL RIGHTS RESERVED. CERTIFIED HYBRID DATA PIPELINES.
        </p>
      </footer>

      {/* WHITEPAPER MODAL OVERLAY */}
      <AnimatePresence>
        {isWhitepaperOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-[#07070a]/90 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto"
          >
            <motion.div 
              initial={{ scale: 0.95, y: 15 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 15 }}
              transition={{ type: "spring", duration: 0.5 }}
              className="bg-slate-950 border border-white/10 rounded-2xl w-full max-w-3xl p-6 sm:p-8 shadow-2xl relative max-h-[85vh] overflow-y-auto flex flex-col"
            >
              {/* Close Button */}
              <button 
                onClick={() => setIsWhitepaperOpen(false)}
                className="absolute top-6 right-6 p-1.5 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>

              <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-6">
                <div className="h-8 w-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <ShieldCheck className="h-4.5 w-4.5" />
                </div>
                <div>
                  <h3 className="font-extrabold text-base text-white">Enterprise Security & Governance</h3>
                  <p className="text-[10px] text-slate-500 font-mono">Whitepaper // Certified HIPAA Protocols</p>
                </div>
              </div>

              {/* Scrollable document text */}
              <div className="text-slate-350 text-xs leading-relaxed space-y-6 overflow-y-auto flex-1 pr-2 max-h-[60vh] scrollbar-thin">
                <section className="space-y-2">
                  <h4 className="font-bold text-white uppercase tracking-wider text-[10px] text-indigo-400">1. Executive Summary</h4>
                  <p>
                    HospitalAI is architected with a &quot;Security-First, Zero-Trust&quot; methodology, designed to meet the rigorous compliance standards of modern healthcare networks (HIPAA, HITECH, GDPR). The platform ensures strict data isolation, immutable auditability, and encrypted telemetry pipelines.
                  </p>
                </section>
                <section className="space-y-2">
                  <h4 className="font-bold text-white uppercase tracking-wider text-[10px] text-indigo-400">2. Data Protection (In-Transit and At-Rest)</h4>
                  <p>
                    <strong>Data in Transit:</strong> All client-to-server and server-to-database communication is strictly enforced over <strong>TLS 1.3</strong>. WebSockets (<code>wss://</code>) utilize secure handshake protocols to prevent man-in-the-middle (MITM) interception of live telemetry.
                  </p>
                  <p>
                    <strong>Data at Rest:</strong> The PostgreSQL database utilizes transparent <strong>AES-256 encryption</strong> for all stored volumes and automated backups. No API keys, database credentials, or cryptographic salts are stored in the codebase; secrets are injected dynamically via secure PaaS Environment Variables.
                  </p>
                </section>
                <section className="space-y-2">
                  <h4 className="font-bold text-white uppercase tracking-wider text-[10px] text-indigo-400">3. Identity & Access Management (IAM)</h4>
                  <p>
                    <strong>Enterprise Single Sign-On (SSO):</strong> HospitalAI supports OpenID Connect (OIDC) and OAuth2, allowing integration with hospital identity providers (Microsoft Entra ID, Okta, PingIdentity).
                  </p>
                  <p>
                    <strong>Strict Role-Based Access Control (RBAC):</strong> The system enforces a rigid hierarchy of permissions at the API router level:
                  </p>
                  <ul className="list-disc pl-5 space-y-1">
                    <li><code>ADMIN</code>: System configuration, Ward/Bed logistics, and Analytics.</li>
                    <li><code>COORDINATOR</code>: Authorization of AI-recommended patient transfers.</li>
                    <li><code>CLINICIAN</code>: Read-only access to clinical recommendations and telemetry.</li>
                  </ul>
                </section>
                <section className="space-y-2">
                  <h4 className="font-bold text-white uppercase tracking-wider text-[10px] text-indigo-400">4. Immutable Auditability & Telemetry</h4>
                  <p>
                    Every administrative action and clinical mutation generates a permanent record in the database. The system utilizes an <code>OperationalLog</code> architecture to track exactly when an AI recommendation was generated, what the EWS score was, and which specific human Coordinator approved or rejected the transfer.
                  </p>
                </section>
              </div>

              <div className="mt-6 pt-4 border-t border-white/5 flex justify-end">
                <button 
                  onClick={() => setIsWhitepaperOpen(false)}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition-colors"
                >
                  Acknowledge and Close
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
