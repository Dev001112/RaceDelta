import React, { useEffect, useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import SeasonSelector from "./SeasonSelector";
import { Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const isActive = (path) =>
    location.pathname === path || location.pathname.startsWith(path + "/");

  const navLinks = [
    { label: "Drivers", path: "/drivers" },
    { label: "Teams", path: "/teams" },
    { label: "Stats", path: "/stats" },
    { label: "Compare", path: "/compare/drivers" }
  ];

  return (
    <div className={`sticky top-0 z-50 w-full transition-all duration-300 ${scrolled ? "py-4" : "py-6"}`}>
      <div className="container">
        <nav
          className={`
            w-full rounded-2xl border transition-all duration-300
            flex items-center justify-between px-6 py-3
            ${scrolled
              ? "bg-[#0b0f14]/80 border-white/10 backdrop-blur-xl shadow-lg shadow-cyan-900/5 support-[backdrop-filter]:bg-[#0b0f14]/60"
              : "bg-transparent border-transparent"
            }
          `}
        >
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative w-8 h-8">
              <div className="absolute inset-0 bg-cyan-500 rounded-lg blur opacity-20 group-hover:opacity-40 transition-opacity animate-pulse" />
              <img
                src="/src/assets/logo-dark.svg"
                alt="RaceDelta"
                className="relative z-10 w-full h-full object-contain group-hover:scale-110 transition-transform duration-500"
              />
            </div>
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              RaceDelta
            </span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1 bg-white/5 p-1 rounded-full border border-white/5 backdrop-blur-md">
            {navLinks.map((link) => {
              const active = isActive(link.path);
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className="relative px-5 py-1.5 text-sm font-medium rounded-full transition-colors z-10"
                >
                  {active && (
                    <motion.div
                      layoutId="navBlob"
                      className="absolute inset-0 bg-white/10 rounded-full"
                      transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    />
                  )}
                  <span className={active ? "text-white" : "text-slate-400 hover:text-white"}>
                    {link.label}
                  </span>
                </Link>
              );
            })}
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-4">
            <SeasonSelector />

            <div className="relative hidden sm:block group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-cyan-400 transition-colors" />
              <input
                type="text"
                placeholder="Search..."
                className="w-48 bg-white/5 border border-white/10 rounded-full pl-9 pr-4 py-1.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 focus:bg-white/10 transition-all"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && e.target.value.trim()) {
                    navigate(`/search?q=${encodeURIComponent(e.target.value.trim())}`);
                    e.target.value = "";
                  }
                }}
              />
            </div>
          </div>
        </nav>
      </div>
    </div>
  );
}
