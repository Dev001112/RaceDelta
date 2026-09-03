import React from "react";
import { Link, useLocation } from "react-router-dom";
import SeasonSelector from "./SeasonSelector";
import { BarChart3, Gauge, Users, Flag, Brain, Route, MessageSquare, HelpCircle } from "lucide-react";
import { startTour } from "./Tour";

export default function Navbar() {
  const location = useLocation();

  const navLinks = [
    { label: "Dashboard", path: "/", icon: Gauge },
    { label: "Compare", path: "/compare/drivers", icon: BarChart3 },
    { label: "Drivers", path: "/drivers", icon: Users },
    { label: "Teams", path: "/teams", icon: Flag },
    { label: "AI Lab", path: "/ai", icon: Brain },
    { label: "Strategy", path: "/strategy", icon: Route },
    { label: "Analyst", path: "/analyst", icon: MessageSquare },
  ];

  const isActive = (path) =>
    path === "/" ? location.pathname === "/" : location.pathname.startsWith(path);

  return (
    <header className="sticky top-0 z-50 bg-panel border-b border-line">
      <div className="container">
        <nav className="flex h-16 items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-3 min-w-fit">
            <div className="h-9 w-9 bg-f1 text-white grid place-items-center font-black italic text-lg font-broadcast">
              RD
            </div>
            <div className="leading-none font-broadcast">
              <div className="text-white font-black uppercase tracking-[0.08em] text-base italic">
                RaceDelta
              </div>
              <div className="text-[12px] uppercase tracking-[0.15em] text-zinc-400 font-bold">
                Telemetry Station
              </div>
            </div>
          </Link>

          <div className="hidden md:flex items-center border border-line bg-carbon p-0.5" data-tour="nav">
            {navLinks.map(({ label, path, icon: Icon }) => {
              const active = isActive(path);
              return (
                <Link
                  key={path}
                  to={path}
                  className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-black uppercase tracking-[0.05em] font-broadcast italic transition-all ${
                    active
                      ? "bg-f1 text-white"
                      : "text-zinc-400 hover:bg-raised hover:text-white"
                  }`}
                >
                  <Icon size={13} />
                  {label}
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-3" data-tour="season">
            <button type="button" onClick={startTour} title="Show the guide for this page"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 text-sm font-black uppercase tracking-[0.05em] font-broadcast italic border border-line text-muted hover:text-white hover:border-[#3a4048] transition-colors">
              <HelpCircle size={14} /> Guide
            </button>
            <SeasonSelector />
          </div>
        </nav>

        <div className="md:hidden flex gap-1 overflow-x-auto border-t border-line py-2">
          {navLinks.map(({ label, path }) => (
            <Link
              key={path}
              to={path}
              className={`px-3 py-2 text-sm font-black uppercase tracking-[0.05em] font-broadcast italic whitespace-nowrap ${
                isActive(path)
                  ? "bg-f1 text-white"
                  : "bg-raised text-zinc-400 border border-line"
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
    </header>
  );
}
