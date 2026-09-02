import React from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";

import Navbar from "./components/Navbar";
import Footer from "./components/Footer";

import Home from "./routes/Home";
import Race from "./routes/Race";
import Driver from "./routes/Driver";
import Drivers from "./routes/Drivers";
import Teams from "./routes/Teams";
import TeamDetail from "./routes/TeamDetail";
import Stats from "./routes/Stats";
import Search from "./routes/Search";

import DriverSeasonRoute from "./routes/DriverSeason";
import DriverComparison from "./pages/DriverComparison";
import DriverIntelligence from "./pages/DriverIntelligence";
import StrategyLab from "./pages/StrategyLab";
import RaceAnalyst from "./pages/RaceAnalyst";

export default function App() {
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col bg-[#050607]">
      <Navbar />

      <main className="flex-1 container py-6 sm:py-8">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            {/* Home */}
            <Route path="/" element={<Home />} />

            {/* Race */}
            <Route path="/race/:season/:round" element={<Race />} />

            {/* Drivers */}
            <Route path="/drivers" element={<Drivers />} />
            <Route path="/driver/:driverId" element={<Driver />} />
            <Route
              path="/driver/:code/season/:season"
              element={<DriverSeasonRoute />}
            />

            {/* Teams */}
            <Route path="/teams" element={<Teams />} />
            <Route path="/teams/:constructorId" element={<TeamDetail />} />

            {/* Stats & Search */}
            <Route path="/stats" element={<Stats />} />
            <Route path="/search" element={<Search />} />

            {/* Comparison */}
            <Route
              path="/compare/drivers"
              element={<DriverComparison />}
            />

            {/* AI Lab (Phase 3) */}
            <Route path="/ai" element={<DriverIntelligence />} />

            {/* Strategy Lab (Phase 4) */}
            <Route path="/strategy" element={<StrategyLab />} />

            {/* AI Race Analyst (Phase 5) */}
            <Route path="/analyst" element={<RaceAnalyst />} />
          </Routes>
        </AnimatePresence>
      </main>

      <Footer />
    </div>
  );
}
