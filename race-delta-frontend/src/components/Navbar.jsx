import React from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path) =>
    location.pathname === path || location.pathname.startsWith(path + "/");

  const linkBase =
    "relative text-sm transition-colors duration-150 hover:text-white";
  const pillBase =
    "px-3 py-1.5 rounded-full bg-slate-900/60 border border-slate-700/70 text-xs text-slate-300";

  return (
    <header className="sticky top-0 z-30 backdrop-blur-md bg-slate-950/70 border-b border-slate-800/70">
      <div className="container flex items-center justify-between py-3">
        {/* Logo + title */}
        <div className="flex items-center gap-3">
          <img
            src="/src/assets/logo-dark.svg"
            alt="RaceDelta"
            className="h-9 w-9 animate-[floatSlow_6s_ease-in-out_infinite]"
          />
          <Link to="/" className="text-lg font-semibold tracking-tight">
            RaceDelta
          </Link>
        </div>

        {/* Center nav */}
        <nav className="hidden md:flex items-center gap-6">
          <Link
            to="/drivers"
            className={`${linkBase} ${isActive("/drivers") ? "text-white" : "text-slate-300"}`}
          >
            Drivers
            {isActive("/drivers") && (
              <span className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent rounded-full" />
            )}
          </Link>
          <Link
            to="/teams"
            className={`${linkBase} ${isActive("/teams") ? "text-white" : "text-slate-300"}`}
          >
            Teams
            {isActive("/teams") && (
              <span className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent rounded-full" />
            )}
          </Link>
          <Link
            to="/stats"
            className={`${linkBase} ${isActive("/stats") ? "text-white" : "text-slate-300"}`}
          >
            Stats
            {isActive("/stats") && (
              <span className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent rounded-full" />
            )}
          </Link>
        </nav>

        {/* Right side search + tiny pill */}
        <div className="flex items-center gap-3">
          <div className={`${pillBase} hidden md:inline-flex items-center gap-2`}>
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Live telemetry (dev)
          </div>

          <input
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.target.value.trim()) {
                navigate(`/search?q=${encodeURIComponent(e.target.value.trim())}`);
                e.target.value = "";
              }
            }}
            placeholder="Search drivers, races, teams..."
            className="px-3 py-2 rounded-md text-xs w-40 sm:w-56
                       bg-slate-900/70 border border-slate-700/70
                       placeholder:text-slate-500 focus:outline-none
                       focus:ring-1 focus:ring-accent"
          />
        </div>
      </div>
    </header>
  );
}
