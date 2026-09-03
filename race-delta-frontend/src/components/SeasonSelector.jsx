import React from "react";
import { useSeason } from "../context/SeasonContext";

export default function SeasonSelector() {
    const { season, setSeason, seasonOptions, loading, calendarSeason } = useSeason();

    if (loading) return (
        <div className="h-8 w-24 bg-slate-800/50 rounded animate-pulse" />
    );

    // Show "Live" badge if selected season is the current calendar year taking place
    const isLive = season === calendarSeason;

    return (
        <div className="flex items-center gap-3">
            {isLive && (
                <div className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[12px] font-bold tracking-wider uppercase whitespace-nowrap">
                    <span className="relative flex h-1.5 w-1.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                    </span>
                    Live Season
                </div>
            )}

            <div className="relative group">
                <select
                    value={season || ""}
                    onChange={(e) => setSeason(Number(e.target.value))}
                    className="appearance-none bg-slate-900/80 hover:bg-slate-800 border border-slate-700/70 text-slate-200 text-xs font-medium rounded-md pl-3 pr-8 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/50 transition-all cursor-pointer"
                >
                    {seasonOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                            {opt.label}
                        </option>
                    ))}
                </select>
                {/* Custom chevron */}
                <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500 group-hover:text-slate-400">
                    <svg width="10" height="6" viewBox="0 0 10 6" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                </div>
            </div>
        </div>
    );
}
