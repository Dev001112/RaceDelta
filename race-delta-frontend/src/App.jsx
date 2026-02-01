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

export default function App() {
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden">
      {/* Dynamic Background */}
      <div className="fixed inset-0 z-[-1] pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-900/10 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-cyan-900/10 rounded-full blur-[120px] animate-pulse delay-1000" />
      </div>

      <Navbar />

      <main className="flex-1 container mx-auto px-4 py-8 relative z-10">
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
          </Routes>
        </AnimatePresence>
      </main>

      <Footer />
    </div>
  );
}
