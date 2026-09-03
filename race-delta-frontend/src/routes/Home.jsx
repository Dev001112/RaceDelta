import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSeason } from "../context/SeasonContext";
import client from "../api/client";
import { getTeamColor } from "../lib/teamMeta";
import { Zap, GitCompare, Trophy, Calendar, ChevronRight } from "lucide-react";



export default function Home() {
  const navigate = useNavigate();
  const { season, isOffseason } = useSeason();

  const [drivers, setDrivers] = useState([]);
  const [schedule, setSchedule] = useState([]);
  const [driverStandings, setDriverStandings] = useState([]);
  const [constructorStandings, setConstructorStandings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Compare widget state
  const [compareD1, setCompareD1] = useState("");
  const [compareD2, setCompareD2] = useState("");

  // Dynamically order schedule starting from the latest completed GP (going backward), followed by upcoming ones (going forward)
  const getOrderedSchedule = () => {
    if (!schedule || schedule.length === 0) return [];

    // Filter out cancelled meetings
    const activeRaces = schedule.filter((r) => !r.is_cancelled);

    // Completed races: is_completed is true
    const completed = activeRaces.filter((r) => r.is_completed);
    // Upcoming races: is_completed is false
    const upcoming = activeRaces.filter((r) => !r.is_completed);

    // Sort completed in reverse chronological order (latest first)
    const completedSorted = [...completed].sort((a, b) => new Date(b.date) - new Date(a.date));

    // Sort upcoming in chronological order (closest first)
    const upcomingSorted = [...upcoming].sort((a, b) => new Date(a.date) - new Date(b.date));

    return [...completedSorted, ...upcomingSorted];
  };

  useEffect(() => {
    if (!season) return;
    setLoading(true);
    setError("");

    Promise.all([
      client.fetchDrivers(season),
      client.fetchDriverStandings(season),
      client.fetchConstructorStandings(season),
      client.fetchRaces(season),
    ])
      .then(([driversList, driverRes, constructorRes, racesList]) => {
        setDrivers(driversList || []);
        setDriverStandings(driverRes.standings || []);
        setConstructorStandings(constructorRes.standings || []);
        setSchedule(racesList || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Dashboard data load error:", err);
        setError("Failed to sync live broadcast feed. Reconnecting...");
        setLoading(false);
      });
  }, [season]);

  const handleCompareSubmit = (e) => {
    e.preventDefault();
    if (!compareD1 || !compareD2) return;
    if (compareD1 === compareD2) {
      alert("Please select two different drivers to run comparison telemetry.");
      return;
    }
    navigate(`/compare/drivers?d1=${compareD1}&d2=${compareD2}&season=${season}`);
  };

  // Format driver last name to uppercase like F1 broadcast graphics
  const formatBroadcastName = (fullName) => {
    if (!fullName) return "";
    const parts = fullName.trim().split(" ");
    if (parts.length === 1) return parts[0].toUpperCase();
    const lastName = parts.slice(1).join(" ").toUpperCase();
    return (
      <span>
        {parts[0]} <span className="font-black">{lastName}</span>
      </span>
    );
  };

  if (loading) {
    return (
      <div className="space-y-6 pt-4">
        {/* Loading skeleton */}
        <div className="h-10 w-48 bg-white/5 animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-[600px] bg-white/5 animate-pulse" />
          <div className="h-[600px] bg-white/5 animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ================= BROADCAST TOP SUB-HEADER ================= */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-[#22272c] pb-4 gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold tracking-[0.2em] text-[#ff1801] uppercase font-broadcast">
            <Zap size={12} className="fill-current animate-pulse" />
            Live Telemetry Broadcast Centre
          </div>
          <h1 className="text-4xl md:text-5xl font-black italic tracking-tight uppercase text-white font-broadcast mt-1">
            F1 Dashboard <span className="text-gray-400">//{season}</span>
          </h1>
        </div>

        {isOffseason && (
          <div className="flex items-center gap-1.5 px-3 py-1 bg-[#facc15]/10 border border-[#facc15]/30 text-[#facc15] text-xs font-bold uppercase tracking-wider font-broadcast">
            Off-Season Archive Mode
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 p-4 text-red-400 text-sm font-semibold uppercase tracking-wider font-broadcast">
          ⚠️ {error}
        </div>
      )}

      {/* ================= HORIZONTAL SCHEDULE STRIP ================= */}
      <section className="bg-[#0d0f11] border border-[#22272c] p-4 relative overflow-hidden" data-tour="calendar">
        <div className="absolute top-0 left-0 h-full w-[3px] bg-[#ff1801]" />
        <div className="flex items-center gap-2 mb-3">
          <Calendar size={14} className="text-[#ff1801]" />
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 font-broadcast">
            Season Race Calendar & Winners
          </h3>
        </div>
        
        <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-white/10">
          {getOrderedSchedule().map((s) => (
            <div
              key={s.round}
              onClick={() => navigate(`/race/${season}/${s.round}`)}
              className="flex-none w-[170px] bg-[#121518] border border-[#22272c] hover:border-[#ff1801] p-3 text-xs font-broadcast relative cursor-pointer hover:bg-[#1a1e22] transition-all"
            >
              <div className="absolute top-0 right-0 px-1.5 py-0.5 bg-white/5 text-[11px] font-bold text-slate-500">
                R{s.round}
              </div>
              <div className="font-bold text-white uppercase truncate pr-6">{s.race}</div>
              <div className="text-slate-400 text-[12px] uppercase tracking-wider">{s.circuit}</div>
              
              <div className="mt-2 flex items-center justify-between border-t border-[#22272c] pt-2">
                <span className="text-[12px] text-slate-500 uppercase tracking-widest">WINNER</span>
                <span className="font-black text-[#ff1801] tracking-wider">{s.winner}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ================= MAIN CONTENT GRID ================= */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* DRIVER STANDINGS: TIMING TOWER STYLE (2/3 width) */}
        <section className="lg:col-span-2 lg:h-0 lg:min-h-full bg-[#0d0f11] border border-[#22272c] flex flex-col relative" data-tour="tower">
          <div className="absolute top-0 left-0 h-[2px] w-full bg-[#ff1801]" />
          
          <div className="p-4 border-b border-[#22272c] flex justify-between items-center bg-[#121518]">
            <div className="flex items-center gap-2">
              <Trophy size={16} className="text-[#ff1801]" />
              <h2 className="text-lg font-black uppercase italic tracking-wider text-white font-broadcast">
                Driver Championship Tower
              </h2>
            </div>
            <span className="text-[13px] font-bold text-slate-400 font-broadcast tracking-wider">
              {driverStandings.length} DRIVERS ACTIVE
            </span>
          </div>

          <div className="flex-1 min-h-0 divide-y divide-[#1e2329] overflow-y-auto max-h-[600px] lg:max-h-none scrollbar-thin">
            {driverStandings.map((d) => {
              const teamColor = d.team_colour || getTeamColor(d.team || d.constructor_id);
              
              return (
                <div
                  key={d.driver_code}
                  onClick={() => navigate(`/driver/${d.driver_code}/season/${season}`)}
                  className="flex items-center justify-between p-3.5 hover:bg-[#121518] transition-colors cursor-pointer group timing-strip"
                  style={{ borderLeft: `4px solid ${teamColor}` }}
                >
                  {/* Position & Identity */}
                  <div className="flex items-center gap-4">
                    <div className="w-8 text-center text-lg font-black italic text-[#ff1801]">
                      {d.position < 10 ? `0${d.position}` : d.position}
                    </div>
                    
                    <div className="flex items-center gap-3">
                      {d.headshot_url ? (
                        <img
                          src={d.headshot_url}
                          alt={d.driver_name}
                          className="w-10 h-10 object-contain bg-[#121518] border border-[#22272c] rounded-none"
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                      ) : (
                        <div className="w-10 h-10 flex items-center justify-center bg-[#1e2329] font-black text-white text-xs">
                          {d.driver_code}
                        </div>
                      )}
                      
                      <div>
                        <div className="text-sm text-slate-300 font-bold uppercase tracking-wide group-hover:text-white transition-colors">
                          {formatBroadcastName(d.driver_name)}
                        </div>
                        <div className="text-[12px] text-slate-500 uppercase tracking-widest">
                          {d.team}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Stats Detail */}
                  <div className="flex items-center gap-8">
                    <div className="hidden sm:block text-right">
                      <div className="text-[12px] text-slate-500 uppercase tracking-wider">WINS</div>
                      <div className="text-xs font-bold text-slate-300">{d.wins || 0}</div>
                    </div>
                    <div className="text-right min-w-[70px]">
                      <div className="text-[12px] text-slate-500 uppercase tracking-wider">POINTS</div>
                      <div className="text-base font-black text-white italic tracking-wider">
                        {d.points}
                      </div>
                    </div>
                    <ChevronRight size={14} className="text-slate-600 group-hover:text-[#ff1801] transition-colors" />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* RIGHT COLUMN: CONSTRUCTORS & COMPARE TOOL (1/3 width) */}
        <div className="space-y-6">
          
          {/* QUICK COMPARE TOOL */}
          <section className="bg-[#0d0f11] border border-[#22272c] p-4 relative" data-tour="compare">
            <div className="absolute top-0 left-0 h-full w-[3px] bg-[#ff1801]" />
            
            <div className="flex items-center gap-2 mb-4 border-b border-[#22272c] pb-2">
              <GitCompare size={16} className="text-[#ff1801]" />
              <h2 className="text-base font-black uppercase italic tracking-wider text-white font-broadcast">
                Telemetry Comparison Run
              </h2>
            </div>

            <form onSubmit={handleCompareSubmit} className="space-y-4">
              <div>
                <label className="block text-[12px] text-slate-400 uppercase tracking-widest font-broadcast mb-1.5">
                  Primary Driver (A)
                </label>
                <select
                  value={compareD1}
                  onChange={(e) => setCompareD1(e.target.value)}
                  className="w-full bg-[#121518] border border-[#22272c] p-2.5 text-xs text-white uppercase font-broadcast focus:outline-none focus:border-[#ff1801]"
                  required
                >
                  <option value="">-- SELECT DRIVER A --</option>
                  {drivers.map((d) => (
                    <option key={d.code} value={d.code}>
                      {d.number} - {d.name} ({d.team})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[12px] text-slate-400 uppercase tracking-widest font-broadcast mb-1.5">
                  Comparison Driver (B)
                </label>
                <select
                  value={compareD2}
                  onChange={(e) => setCompareD2(e.target.value)}
                  className="w-full bg-[#121518] border border-[#22272c] p-2.5 text-xs text-white uppercase font-broadcast focus:outline-none focus:border-[#ff1801]"
                  required
                >
                  <option value="">-- SELECT DRIVER B --</option>
                  {drivers.map((d) => (
                    <option key={d.code} value={d.code}>
                      {d.number} - {d.name} ({d.team})
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                className="w-full bg-[#ff1801] hover:bg-[#d01300] text-white text-xs font-black uppercase italic tracking-wider py-3 px-4 transition-colors font-broadcast flex items-center justify-center gap-2 btn-broadcast"
              >
                <GitCompare size={14} /> Run Telemetry Delta
              </button>
            </form>
          </section>

          {/* CONSTRUCTOR STANDINGS */}
          <section className="bg-[#0d0f11] border border-[#22272c] flex flex-col relative" data-tour="constructors">
            <div className="absolute top-0 left-0 h-[2px] w-full bg-[#ff1801]" />
            
            <div className="p-4 border-b border-[#22272c] bg-[#121518]">
              <h2 className="text-base font-black uppercase italic tracking-wider text-white font-broadcast">
                Constructor Standings
              </h2>
            </div>

            <div className="divide-y divide-[#1e2329]">
              {constructorStandings.map((c) => {
                const teamColor = c.team_colour || getTeamColor(c.team || c.constructor_id);
                
                return (
                  <div
                    key={c.team}
                    className="flex items-center justify-between p-3 hover:bg-[#121518] transition-colors cursor-default"
                    style={{ borderLeft: `3px solid ${teamColor}` }}
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-5 text-center text-sm font-black italic text-slate-400">
                        {c.position}
                      </span>
                      <span className="text-xs font-bold text-white uppercase tracking-wider font-broadcast">
                        {c.team}
                      </span>
                    </div>
                    
                    <div className="text-right">
                      <span className="text-sm font-black text-white italic tracking-wider font-broadcast">
                        {c.points} <span className="text-[11px] text-slate-500 font-bold tracking-normal not-italic">PTS</span>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
