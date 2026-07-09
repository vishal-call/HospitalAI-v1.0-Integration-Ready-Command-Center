import React, { useState, useEffect } from "react";
import { useTelemetry } from "@/lib/TelemetryContext";
import { Clock, AlertTriangle } from "lucide-react";

export default function TimeTravelSlider() {
  const { isHistorical, historicalTime, enterTimeTravel, exitTimeTravel } = useTelemetry();
  
  const maxMinutes = 720; // 12 hours max
  const [minutesAgo, setMinutesAgo] = useState(0); // 0 means live/present
  
  useEffect(() => {
    if (!isHistorical) {
      setMinutesAgo(0);
    }
  }, [isHistorical]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value);
    setMinutesAgo(val);
  };

  const handleRelease = async () => {
    if (minutesAgo === 0) {
      await exitTimeTravel();
    } else {
      const targetDate = new Date(Date.now() - minutesAgo * 60 * 1000);
      await enterTimeTravel(targetDate.toISOString());
    }
  };

  const getDisplayTime = () => {
    if (minutesAgo === 0) return "Present (Live)";
    const targetDate = new Date(Date.now() - minutesAgo * 60 * 1000);
    return targetDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ` (${minutesAgo} min ago)`;
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-slate-950/90 border-t border-slate-800/80 px-6 py-4 backdrop-blur-xl shadow-2xl flex flex-col md:flex-row items-center gap-4 transition-all duration-300">
      <div className="flex items-center gap-3 shrink-0">
        <div className={`p-2 rounded-xl ${isHistorical ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'} transition-colors`}>
          <Clock className="h-5 w-5" />
        </div>
        <div>
          <span className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase block">Timeline Playback</span>
          <span className={`text-sm font-bold tracking-tight ${isHistorical ? 'text-amber-400' : 'text-slate-200'}`}>
            {getDisplayTime()}
          </span>
        </div>
      </div>

      <div className="flex-1 w-full flex items-center gap-4">
        <span className="text-xs text-slate-500 font-medium shrink-0">12h ago</span>
        <input
          type="range"
          min="0"
          max={maxMinutes}
          step="5"
          value={minutesAgo}
          onChange={handleChange}
          onMouseUp={handleRelease}
          onTouchEnd={handleRelease}
          className="flex-1 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500 focus:outline-none focus:ring-0"
          style={{
            background: `linear-gradient(to right, #4f46e5 0%, #4f46e5 ${((maxMinutes - minutesAgo) / maxMinutes) * 100}%, #1e293b ${((maxMinutes - minutesAgo) / maxMinutes) * 100}%, #1e293b 100%)`,
            transform: 'rotate(180deg)'
          }}
        />
        <span className="text-xs text-emerald-400 font-semibold shrink-0 flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Live
        </span>
      </div>

      {isHistorical && (
        <button
          onClick={async () => {
            setMinutesAgo(0);
            await exitTimeTravel();
          }}
          className="shrink-0 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-indigo-900/30"
        >
          Return to Live
        </button>
      )}
    </div>
  );
}
