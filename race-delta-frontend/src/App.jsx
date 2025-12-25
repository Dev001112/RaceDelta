import React from "react";
import { Routes, Route } from "react-router-dom";

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
  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-white">
      <Navbar />

      <main className="flex-1 container mx-auto px-4 py-8">
        <Routes>
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
      </main>

      <Footer />
    </div>
  );
}
