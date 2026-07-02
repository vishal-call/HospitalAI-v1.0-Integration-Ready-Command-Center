"use client";

import React, { useEffect, useState, useRef } from "react";
import { Bell } from "lucide-react";
import { NotificationResponse, fetchUnreadNotifications } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAuth } from "@/lib/AuthContext";

export default function NotificationTray() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<NotificationResponse[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [pulse, setPulse] = useState(false);
  const trayRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (trayRef.current && !trayRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Initial fetch
  useEffect(() => {
    if (user) {
      fetchUnreadNotifications().then(setNotifications).catch(console.error);
    }
  }, [user]);

  // WebSocket listener
  const wsUrl = typeof window !== "undefined" && user ? `ws://${window.location.hostname}:8000/ws/dashboard` : "";
  useWebSocket(wsUrl, (payload) => {
    if (payload.type === "NOTIFICATION_CREATED") {
      setNotifications((prev) => [payload.data, ...prev]);
      // Trigger animation
      setPulse(true);
      setTimeout(() => setPulse(false), 2000);
    }
  });

  return (
    <div className="relative" ref={trayRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-full hover:bg-slate-800 transition-colors focus:outline-none"
      >
        <Bell className={`h-5 w-5 text-slate-300 ${pulse ? 'animate-bounce text-emerald-400' : ''}`} />
        {notifications.length > 0 && (
          <span className="absolute top-1 right-1 h-2.5 w-2.5 bg-rose-500 rounded-full border-2 border-slate-950 animate-in zoom-in duration-300"></span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50">
          <div className="p-3 border-b border-slate-800 flex justify-between items-center bg-slate-800/50">
            <h3 className="text-sm font-bold text-slate-200">Notifications</h3>
            <span className="text-xs bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full">{notifications.length} Unread</span>
          </div>
          <div className="flex flex-col">
            {notifications.length === 0 ? (
              <div className="p-4 text-center text-slate-500 text-sm">
                No new notifications
              </div>
            ) : (
              notifications.map((notif) => (
                <div key={notif.id} className="p-3 border-b border-slate-800/50 hover:bg-slate-800/50 transition-colors cursor-pointer">
                  <p className="text-xs font-semibold text-slate-300">{notif.title}</p>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{notif.message}</p>
                  <p className="text-[10px] text-slate-500 mt-2">
                    {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
