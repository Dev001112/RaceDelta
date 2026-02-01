import React from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import FeaturedRaceCard from "../components/FeaturedRaceCard";
import { ArrowRight, Activity, TrendingUp, Calendar, Zap } from "lucide-react";

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
    <div className="space-y-16 py-8">
      {/* ================= HERO ================= */}
      <section className="relative overflow-hidden rounded-3xl bg-[#0b0f14] border border-white/5 p-8 md:p-16">
        {/* Background Effects */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[100px] pointer-events-none" />

        <div className="relative z-10 max-w-2xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-bold uppercase tracking-wider mb-6">
              <Zap size={12} className="fill-current" />
              Next Gen F1 Telemetry
            </div>

            <h1 className="text-5xl md:text-7xl font-bold leading-[1.1] tracking-tight mb-6 text-white">
              Data that <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600">
                tells the story
              </span>
            </h1>

            <p className="text-lg text-slate-400 leading-relaxed mb-8 max-w-lg">
              Go beyond the standings. Analyze pace, strategies, and telemetry battles with RaceDelta's advanced visual dashboard.
            </p>

            <div className="flex flex-wrap gap-4">
              <Button onClick={() => navigate("/compare/drivers")}>
                Compare Drivers <ArrowRight size={16} className="ml-2" />
              </Button>
              <Button variant="secondary" onClick={() => navigate("/teams")}>
                Explore Teams
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ================= QUICK STATS GRID ================= */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card onClick={() => navigate("/compare/drivers")} className="group">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 rounded-lg bg-orange-500/10 text-orange-500">
              <Activity size={20} />
            </div>
            <span className="text-xs text-slate-500 font-medium bg-white/5 px-2 py-1 rounded">LIVE</span>
          </div>
          <h3 className="text-xl font-bold text-white mb-2 group-hover:text-cyan-400 transition-colors">Compare Drivers</h3>
          <p className="text-sm text-slate-400">Head-to-head telemetry, pace analysis, and cornering speeds.</p>
        </Card>

        <Card onClick={() => navigate("/stats")}>
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
              <TrendingUp size={20} />
            </div>
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Season Trends</h3>
          <p className="text-sm text-slate-400">Visualizing championship battles and team development rates.</p>
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-500">
              <Calendar size={20} />
            </div>
            <span className="text-xs text-slate-500 font-medium">UPCOMING</span>
          </div>
          <h3 className="text-xl font-bold text-white mb-2 outline-dashed outline-1 outline-transparent">Race Monitor</h3>
          <p className="text-sm text-slate-400">Live lap times and gap analysis (Coming Soon).</p>
        </Card>
      </section>

      {/* ================= FEATURED RACES ================= */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">Featured Races</h2>
          <Button variant="ghost" onClick={() => navigate("/season/2025")}>View All →</Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sampleRaces.map((race) => (
            <FeaturedRaceCard key={race.title} race={race} />
          ))}

          {/* Promo Card */}
          <div className="hidden lg:block relative rounded-xl overflow-hidden bg-gradient-to-br from-cyan-900/40 to-blue-900/40 border border-white/10 p-8 flex flex-col justify-center">
            <div className="absolute inset-0 bg-[url('/src/assets/grid-pattern.svg')] opacity-30" />
            <div className="relative z-10">
              <h3 className="text-2xl font-bold text-white mb-2">Pro Analytics</h3>
              <p className="text-sm text-cyan-200 mb-6">
                Unlock deep dive metrics including tire degradation models and fuel-adjusted pace.
              </p>
              <Button variant="primary" className="w-full">Get Started</Button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
