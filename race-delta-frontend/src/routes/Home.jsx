import React from "react";
import { useNavigate } from "react-router-dom";

import FeaturedRaceCard from "../components/FeaturedRaceCard";

// Temporary featured races (replace later with API)
const sampleRaces = [
  {
    title: "2025 Abu Dhabi GP",
    location: "Yas Marina",
    date: "2025-11-30",
    winner: "Max Verstappen",
    flag: "/src/assets/flags/uae.svg",
  },
  {
    title: "2025 British GP",
    location: "Silverstone",
    date: "2025-07-06",
    winner: "Lewis Hamilton",
    flag: "/src/assets/flags/uk.svg",
  },
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="space-y-8">
      {/* ================= HERO ================= */}
      <section className="card relative overflow-hidden">
        <div className="absolute -right-12 -top-12 w-40 h-40 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
        <div className="absolute -left-16 bottom-0 w-44 h-44 rounded-full bg-indigo-500/5 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col md:flex-row md:items-center md:justify-between gap-8">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
              F1 telemetry & race delta
            </p>

            <h1 className="mt-2 text-3xl md:text-4xl font-semibold leading-tight">
              See races as{" "}
              <span className="text-cyan-400">time series</span>, not just results.
            </h1>

            <p className="mt-3 text-sm text-slate-400 max-w-xl">
              RaceDelta turns lap times, sector splits and tyre stints into clean,
              minimal visual stories for every race weekend.
            </p>

            <div className="mt-5 flex flex-wrap gap-3 text-xs">
              <div className="badge">Latest: Abu Dhabi 2025</div>
              <div className="badge">Drivers: 20</div>
              <div className="badge">Teams: 10</div>
            </div>

            {/* CTA */}
            <button
              onClick={() => navigate("/compare/drivers")}
              className="
                mt-6 inline-flex items-center gap-2
                px-5 py-2.5 rounded-lg
                bg-cyan-500 text-black
                text-sm font-semibold
                hover:bg-cyan-400
                transition
              "
            >
              Compare drivers →
            </button>
          </div>

          {/* Quick Search */}
          <div className="w-full md:w-72">
            <div className="rounded-xl border border-slate-700/60 bg-slate-900/80 p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-3">
                <span>Quick search</span>
                <span>Ctrl + K</span>
              </div>

              <input
                placeholder="Search driver, race or team"
                className="
                  w-full px-3 py-2 rounded-md
                  bg-slate-950 border border-slate-700
                  text-xs text-white
                  placeholder:text-slate-500
                  focus:outline-none focus:ring-1 focus:ring-cyan-500
                "
              />

              <p className="mt-3 text-[11px] text-slate-400">
                Try:{" "}
                <span
                  className="text-cyan-400 cursor-pointer"
                  onClick={() =>
                    navigate("/compare/drivers")
                  }
                >
                  VER vs HAM Abu Dhabi
                </span>
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ================= QUICK CARDS ================= */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
        <div className="card card-hover">
          <div className="text-xs text-slate-400 mb-1">Weekend overview</div>
          <div className="text-lg font-semibold">Abu Dhabi 2025</div>
          <p className="mt-1 text-slate-400">
            Strategy summary, safety cars and stint performance.
          </p>
        </div>

        {/* CLICKABLE COMPARISON CARD */}
        <div
          className="card card-hover cursor-pointer"
          onClick={() => navigate("/compare/drivers")}
        >
          <div className="text-xs text-slate-400 mb-1">Driver comparison</div>
          <div className="text-lg font-semibold">VER vs HAM</div>
          <p className="mt-1 text-slate-400">
            Points progression and season head-to-head.
          </p>
        </div>

        <div className="card card-hover">
          <div className="text-xs text-slate-400 mb-1">Telemetry</div>
          <div className="text-lg font-semibold">Sector profiles</div>
          <p className="mt-1 text-slate-400">
            Braking points and minimum speeds per corner.
          </p>
        </div>
      </section>

      {/* ================= FEATURED ================= */}
      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <section>
            <h2 className="text-xl font-semibold mb-3">
              Featured races
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {sampleRaces.map((race) => (
                <FeaturedRaceCard
                  key={race.title}
                  race={race}
                />
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">
              Driver highlights
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="card card-hover">
                <div className="text-xs text-slate-400 mb-1">
                  Form trend
                </div>
                <div className="font-semibold">Max Verstappen</div>
                <p className="text-xs text-slate-400 mt-1">
                  Last 5 races: 1st · 1st · 2nd · 1st · 1st
                </p>
              </div>

              <div className="card card-hover">
                <div className="text-xs text-slate-400 mb-1">
                  Qualifying delta
                </div>
                <div className="font-semibold">Lando Norris</div>
                <p className="text-xs text-slate-400 mt-1">
                  Avg gap to teammate: −0.12s
                </p>
              </div>
            </div>
          </section>
        </div>

        {/* ================= SIDEBAR ================= */}
        <aside className="space-y-4">
          <section className="card">
            <h3 className="text-sm font-semibold mb-2">
              Filters
            </h3>
            <div className="space-y-2 text-xs text-slate-400">
              <div>
                Season:{" "}
                <span className="text-cyan-400 font-medium">
                  2025
                </span>
              </div>
              <div>Session: Race · Quali · Practice</div>
              <div>Metric: Lap time · Pace delta</div>
            </div>
          </section>

          <section className="card">
            <h3 className="text-sm font-semibold mb-2">
              Coming next
            </h3>
            <p className="text-xs text-slate-400">
              Live FastF1 / OpenF1 telemetry and deeper comparison views.
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
}
