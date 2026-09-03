import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client from "../api/client";
import { getTeamColor } from "../lib/teamMeta";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ResponsiveContainer
} from "recharts";
import { Thermometer, Wind, Droplets, Trophy, Calendar, Compass, ArrowLeft } from "lucide-react";

// Format time duration helper (P1 = hh:mm:ss, others = +gap)
const formatDuration = (seconds, position, gap) => {
  if (position === 1) {
    if (!seconds) return "FINISHED";
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = (seconds % 60).toFixed(3);
    return hrs > 0 ? `${hrs}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(6, "0")}` : `${mins}:${secs.toString().padStart(6, "0")}`;
  }
  if (gap === 0 || gap === "0") return "FINISHED";
  if (typeof gap === "number") return `+${gap.toFixed(3)}s`;
  if (String(gap).includes("Lap")) return gap;
  return gap ? (String(gap).startsWith("+") ? gap : `+${gap}`) : "FINISHED";
};

export default function Race() {
  const { season, round } = useParams();
  const navigate = useNavigate();

  const [meeting, setMeeting] = useState(null);
  const [sessionKey, setSessionKey] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError("");
    setMeeting(null);
    setSessionKey(null);
    setAnalytics(null);

    // Step 1: Fetch all meetings for the season
    client.fetchRaces(season)
      .then((meetings) => {
        if (!mounted) return;
        if (!meetings || meetings.length === 0) {
          setError(`No meetings found for season ${season}.`);
          setLoading(false);
          return;
        }

        const gpMeetings = meetings.filter(
          (m) =>
            m.meeting_name &&
            !m.meeting_name.toLowerCase().includes("testing") &&
            !m.meeting_name.toLowerCase().includes("test")
        );
        const sorted = gpMeetings.sort((a, b) => new Date(a.date_start) - new Date(b.date_start));
        const roundIndex = parseInt(round) - 1;

        if (roundIndex < 0 || roundIndex >= sorted.length) {
          setError(`Invalid round ${round} for season ${season}. Max rounds: ${sorted.length}.`);
          setLoading(false);
          return;
        }

        const selectedMeeting = sorted[roundIndex];
        setMeeting(selectedMeeting);

        const mKey = selectedMeeting.meeting_key || selectedMeeting.key || selectedMeeting.id;
        
        // Step 2: Fetch sessions for this meeting
        return client.fetchSessions(mKey);
      })
      .then((sessions) => {
        if (!mounted) return;
        if (!sessions || sessions.length === 0) {
          setError("Failed to fetch sessions for this Grand Prix.");
          setLoading(false);
          return;
        }

        // Find the "Race" session
        const raceSession = sessions.find(
          // session_type is "Race" for the Sprint too - only session_name distinguishes them
          (s) => (s.session_name || "").toLowerCase() === "race"
        );

        if (!raceSession) {
          setError("Could not discover a completed Race session for this GP.");
          setLoading(false);
          return;
        }

        const sKey = raceSession.session_key || raceSession.key || raceSession.id;
        setSessionKey(sKey);

        // Step 3: Fetch race analytics
        return client.fetchRaceAnalytics(sKey);
      })
      .then((data) => {
        if (!mounted) return;
        if (data) {
          setAnalytics(data);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("Race details fetch error:", err);
        if (mounted) {
          setError("Failed to load race analytics. Telemetry database offline.");
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [season, round]);

  if (loading) {
    return (
      <div className="space-y-6 pt-4">
        <div className="h-6 w-32 bg-white/5 animate-pulse" />
        <div className="h-[100px] bg-white/5 animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-[400px] bg-white/5 animate-pulse" />
          <div className="h-[400px] bg-white/5 animate-pulse" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6 pt-4 font-broadcast">
        <button onClick={() => navigate("/")} className="btn-broadcast bg-white/5 hover:bg-white/10 text-white text-xs px-4 py-2 border border-[#22272c] flex items-center gap-2">
          <ArrowLeft size={12} /> Return to Dashboard
        </button>
        <div className="bg-red-500/10 border border-red-500/30 p-5 text-red-400 font-bold uppercase tracking-wider">
          ⚠️ {error}
        </div>
      </div>
    );
  }

  // Transform position chart data for Recharts
  const transformChartData = () => {
    if (!analytics?.position_chart?.timestamps || !analytics?.position_chart?.drivers) return [];
    
    const { timestamps, drivers } = analytics.position_chart;
    
    return timestamps.map((ts, idx) => {
      const point = { time: ts };
      Object.keys(drivers).forEach((driverNum) => {
        const driverInfo = analytics.results.find((r) => String(r.driver_number) === String(driverNum));
        const name = driverInfo ? driverInfo.driver_code : `D${driverNum}`;
        point[name] = drivers[driverNum][idx];
      });
      return point;
    });
  };

  const chartData = transformChartData();
  
  // Pick top 8 drivers to display on chart to prevent cluttering
  const getTopChartDrivers = () => {
    if (!analytics?.results) return [];
    return analytics.results
      .slice(0, 8)
      .map((r) => r.driver_code);
  };
  
  const chartDriversList = getTopChartDrivers();

  return (
    <div className="space-y-6 font-body">
      {/* ================= BROADCAST BACK BUTTON ================= */}
      <div>
        <button
          onClick={() => navigate("/")}
          className="btn-broadcast bg-[#121518] hover:bg-[#1a1e22] text-[#a1a1aa] hover:text-white text-xs px-3.5 py-1.5 border border-[#22272c] flex items-center gap-1.5"
        >
          <ArrowLeft size={12} /> BACK TO BROADCAST TOWER
        </button>
      </div>

      {/* ================= BROADCAST HEADLINE PANEL ================= */}
      <section className="bg-[#0d0f11] border border-[#22272c] p-6 relative overflow-hidden" data-tour="race-header">
        <div className="absolute top-0 left-0 h-full w-[3px] bg-[#ff1801]" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-[#ff1801] tracking-widest font-broadcast uppercase">
              <Compass size={12} />
              Round {round} // {season} Championship
            </div>
            <h1 className="text-3xl md:text-4xl font-black italic uppercase text-white font-broadcast tracking-tight mt-1">
              {meeting?.meeting_official_name || meeting?.meeting_name}
            </h1>
            <p className="text-slate-400 text-xs uppercase tracking-wider mt-1.5 font-broadcast">
              Location: {meeting?.location}, {meeting?.country_name} | Circuit: {meeting?.circuit_short_name}
            </p>
          </div>

          <div className="text-right hidden md:block">
            <span className="text-[12px] text-slate-500 font-bold uppercase tracking-widest font-broadcast">WINNER</span>
            <div className="text-3xl font-black italic text-[#ff1801] font-broadcast leading-none">
              {analytics?.results?.[0]?.driver_code || "N/A"}
            </div>
            <span className="text-xs text-slate-300 font-broadcast font-bold uppercase">{analytics?.results?.[0]?.driver_name}</span>
          </div>
        </div>
      </section>

      {/* ================= HORIZONTAL WEATHER/CONDITIONS STRIP ================= */}
      <section className="bg-[#0d0f11] border border-[#22272c] p-4 relative font-broadcast" data-tour="race-weather">
        <div className="absolute top-0 left-0 h-full w-[3px] bg-[#ff1801]" />
        
        <div className="flex flex-wrap items-center justify-around gap-6 text-center">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#ff1801]/10 text-[#ff1801]">
              <Thermometer size={16} />
            </div>
            <div className="text-left">
              <div className="text-[11px] text-slate-500 uppercase tracking-widest">AIR TEMP</div>
              <div className="text-base font-black text-white italic">{analytics?.weather?.avg_air_temp}°C</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/10 text-amber-500">
              <Thermometer size={16} />
            </div>
            <div className="text-left">
              <div className="text-[11px] text-slate-500 uppercase tracking-widest">TRACK TEMP</div>
              <div className="text-base font-black text-white italic">{analytics?.weather?.avg_track_temp}°C</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-500/10 text-cyan-400">
              <Droplets size={16} />
            </div>
            <div className="text-left">
              <div className="text-[11px] text-slate-500 uppercase tracking-widest">HUMIDITY</div>
              <div className="text-base font-black text-white italic">{analytics?.weather?.avg_humidity}%</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 text-blue-400">
              <Wind size={16} />
            </div>
            <div className="text-left">
              <div className="text-[11px] text-slate-500 uppercase tracking-widest">TRACK CONDITION</div>
              <div className="text-base font-black text-white italic">
                {analytics?.weather?.rainfall ? "WET (RAIN)" : "DRY"}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================= WINNER & BEST DRIVER CARDS ================= */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-broadcast" data-tour="race-cards">
        {/* WINNER CARD */}
        {analytics?.winner && (
          <div className="bg-[#0d0f11] border border-[#22272c] p-4 flex items-center justify-between relative overflow-hidden">
            <div className="absolute top-0 left-0 h-full w-[3px] bg-[#ff1801]" />
            <div className="flex-1">
              <span className="text-[12px] text-slate-500 uppercase tracking-widest font-bold">RACE WINNER</span>
              <h3 className="text-2xl font-black italic text-white uppercase mt-1">
                {analytics.winner.driver_name}
              </h3>
              <p className="text-xs text-[#ff1801] uppercase font-bold tracking-wider mt-0.5">
                {analytics.winner.team}
              </p>
              <div className="mt-3 text-sm font-bold text-slate-300">
                TIME: <span className="text-white font-black italic">{formatDuration(analytics.winner.duration, 1, 0)}</span>
              </div>
            </div>
            
            <div className="relative w-20 h-20 overflow-hidden border border-[#22272c] bg-[#121518] flex-none">
              {analytics.winner.headshot_url ? (
                <img
                  src={analytics.winner.headshot_url}
                  alt={analytics.winner.driver_name}
                  className="w-full h-full object-contain"
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center font-black text-xl text-[#ff1801]">
                  {analytics.winner.driver_code}
                </div>
              )}
            </div>
          </div>
        )}

        {/* BEST CLIMBER / DRIVER OF THE DAY CARD */}
        {analytics?.best_driver && (
          <div className="bg-[#0d0f11] border border-[#22272c] p-4 flex items-center justify-between relative overflow-hidden">
            <div className="absolute top-0 left-0 h-full w-[3px] bg-emerald-500" />
            <div className="flex-1">
              <span className="text-[12px] text-slate-500 uppercase tracking-widest font-bold font-broadcast">BEST CLIMBER // DRIVER OF THE DAY</span>
              <h3 className="text-2xl font-black italic text-white uppercase mt-1">
                {analytics.best_driver.driver_name}
              </h3>
              <p className="text-xs text-emerald-500 uppercase font-bold tracking-wider mt-0.5">
                {analytics.best_driver.team}
              </p>
              <div className="mt-3 text-sm font-bold text-slate-300">
                GAINED: <span className="text-emerald-500 font-black italic">+{analytics.best_driver.positions_gained} POSITIONS</span>
              </div>
            </div>
            
            <div className="relative w-20 h-20 overflow-hidden border border-[#22272c] bg-[#121518] flex-none">
              {analytics.best_driver.headshot_url ? (
                <img
                  src={analytics.best_driver.headshot_url}
                  alt={analytics.best_driver.driver_name}
                  className="w-full h-full object-contain"
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center font-black text-xl text-emerald-500">
                  {analytics.best_driver.driver_code}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ================= MAIN STRATEGIES & TELEMETRY CHART GRID ================= */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* POSITION CHART: 2/3 Width */}
        <section className="lg:col-span-2 bg-[#0d0f11] border border-[#22272c] p-4 flex flex-col relative" data-tour="position-chart">
          <div className="absolute top-0 left-0 h-[2px] w-full bg-[#ff1801]" />
          
          <div className="mb-4 border-b border-[#22272c] pb-2 flex justify-between items-center">
            <h2 className="text-base font-black uppercase italic tracking-wider text-white font-broadcast">
              Position Change Over Time // Lap Sample
            </h2>
            <span className="text-[12px] font-bold text-slate-400 font-broadcast tracking-wider">
              TOP 8 RUNNERS
            </span>
          </div>

          <div className="h-[320px] w-full">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ left: -10, right: 10, top: 10, bottom: 5 }}>
                  <CartesianGrid stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="time" stroke="#a1a1aa" tick={{ fontSize: 10, fontFamily: "Barlow Condensed" }} />
                  <YAxis
                    reversed={true}
                    domain={[1, 10]}
                    stroke="#a1a1aa"
                    tick={{ fontSize: 10, fontFamily: "Barlow Condensed" }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0d0f11",
                      border: "1px solid #22272c",
                      color: "#f4f4f5",
                      fontFamily: "Barlow Condensed",
                      fontSize: 12
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 10, fontFamily: "Barlow Condensed" }} />
                  {chartDriversList.map((driverName, idx) => {
                    const resultRow = analytics?.results.find((r) => r.driver_code === driverName);
                    const color = getTeamColor(resultRow?.team);
                    
                    return (
                      <Line
                        key={driverName}
                        type="monotone"
                        dataKey={driverName}
                        stroke={color}
                        strokeWidth={2}
                        dot={{ r: 2 }}
                        activeDot={{ r: 5 }}
                      />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm font-broadcast">
                NO TELEMETRY SIGNALS LOGGED FOR THIS SESSION
              </div>
            )}
          </div>
        </section>

        {/* TEAM STRATEGY TIMELINE: 1/3 Width */}
        <section className="bg-[#0d0f11] border border-[#22272c] p-4 flex flex-col relative" data-tour="stints">
          <div className="absolute top-0 left-0 h-[2px] w-full bg-[#ff1801]" />
          
          <div className="mb-4 border-b border-[#22272c] pb-2">
            <h2 className="text-base font-black uppercase italic tracking-wider text-white font-broadcast">
              Tyre Strategy Timeline
            </h2>
          </div>

          <div className="flex-1 overflow-y-auto max-h-[320px] pr-1 scrollbar-thin">
            {analytics?.stints && Object.keys(analytics.stints).length > 0 ? (
              <div className="space-y-4">
                {/* Tyre strategy component */}
                <div className="space-y-3 font-broadcast">
                  {Object.keys(analytics.stints).map((driverNum) => {
                    const driverStints = analytics.stints[driverNum];
                    const driverInfo = analytics.results.find((r) => String(r.driver_number) === String(driverNum));
                    if (!driverInfo) return null;
                    const code = driverInfo.driver_code;
                    const teamColor = getTeamColor(driverInfo.team);
                    
                    return (
                      <div key={driverNum} className="flex items-center gap-3">
                        <span className="w-10 text-xs font-bold text-white uppercase text-right" style={{ borderRight: `3px solid ${teamColor}`, paddingRight: 6 }}>
                          {code}
                        </span>
                        <div className="flex-grow h-4.5 bg-white/5 flex overflow-hidden">
                          {driverStints.map((stint, sIdx) => {
                            const totalLaps = stint.lap_end - stint.lap_start + 1;
                            const compound = stint.compound ? stint.compound.toUpperCase() : "UNKNOWN";
                            let color = "#7f8c8d";
                            if (compound.includes("SOFT")) color = "#ff1801";
                            else if (compound.includes("MEDIUM")) color = "#facc15";
                            else if (compound.includes("HARD")) color = "#f4f4f5";
                            else if (compound.includes("INTER")) color = "#22c55e";
                            else if (compound.includes("WET")) color = "#3b82f6";
                            
                            return (
                              <div
                                key={sIdx}
                                style={{ flexGrow: totalLaps, backgroundColor: color }}
                                className="h-full flex items-center justify-center text-[8px] font-black text-black border-r border-[#0d0f11]"
                                title={`${compound}: Laps ${stint.lap_start}-${stint.lap_end}`}
                              >
                                {totalLaps > 5 && `${compound[0]}${totalLaps}`}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Compounds key legend */}
                <div className="flex justify-between items-center text-[11px] font-bold uppercase text-slate-500 border-t border-[#1e2329] pt-3 font-broadcast">
                  <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 bg-[#ff1801]" /> SOFT</div>
                  <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 bg-[#facc15]" /> MED</div>
                  <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 bg-[#f4f4f5]" /> HARD</div>
                  <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 bg-[#22c55e]" /> INT</div>
                  <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 bg-[#3b82f6]" /> WET</div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm font-broadcast">
                NO STINT LOGS FOR THIS SESSION
              </div>
            )}
          </div>
        </section>

      </div>

      {/* ================= CLASSIFICATION RESULTS BOARD ================= */}
      <section className="bg-[#0d0f11] border border-[#22272c] relative" data-tour="results">
        <div className="absolute top-0 left-0 h-[2px] w-full bg-[#ff1801]" />
        
        <div className="p-4 border-b border-[#22272c] bg-[#121518] flex items-center gap-2">
          <Trophy size={16} className="text-[#ff1801]" />
          <h2 className="text-base font-black uppercase italic tracking-wider text-white font-broadcast">
            Official Classification Results
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-broadcast">
            <thead>
              <tr className="text-slate-500 border-b border-[#22272c] text-xs uppercase tracking-wider bg-[#121518]/50">
                <th className="p-4 w-12 text-center">POS</th>
                <th className="p-4 w-12 text-center">GRID</th>
                <th className="p-4 w-12 text-center">+/-</th>
                <th className="p-4">DRIVER</th>
                <th className="p-4">CONSTRUCTOR</th>
                <th className="p-4 text-center">LAPS</th>
                <th className="p-4 text-right">TIME / INTERVAL</th>
                <th className="p-4 text-right">PTS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2329] text-sm">
              {analytics?.results?.map((r) => {
                const teamColor = getTeamColor(r.team);
                const gridPos = (r.grid_position !== null && r.grid_position !== undefined) ? parseInt(r.grid_position) : null;
                const finalPos = (r.position !== null && r.position !== undefined) ? parseInt(r.position) : null;
                const diff = (gridPos !== null && finalPos !== null && !r.dnf && !r.dns && !r.dsq) ? (gridPos - finalPos) : null;
                
                return (
                  <tr key={r.driver_number} className="hover:bg-[#121518]/50 transition-colors">
                    {/* Position */}
                    <td className="p-4 text-center text-base font-black italic text-[#ff1801]">
                      {r.dnf ? (
                        <span className="text-red-500">DNF</span>
                      ) : r.dns ? (
                        <span className="text-slate-500">DNS</span>
                      ) : r.dsq ? (
                        <span className="text-red-700">DSQ</span>
                      ) : finalPos !== null ? (
                        finalPos < 10 ? `0${finalPos}` : finalPos
                      ) : (
                        "--"
                      )}
                    </td>

                    {/* Grid Position */}
                    <td className="p-4 text-center text-xs font-bold text-slate-500">
                      {gridPos !== null ? (gridPos < 10 ? `0${gridPos}` : gridPos) : "--"}
                    </td>

                    {/* Diff */}
                    <td className="p-4 text-center text-xs font-bold font-broadcast">
                      {diff > 0 ? (
                        <span className="text-emerald-500">▲{diff}</span>
                      ) : diff < 0 ? (
                        <span className="text-red-500">▼{Math.abs(diff)}</span>
                      ) : (
                        <span className="text-slate-600">-</span>
                      )}
                    </td>

                    {/* Driver */}
                    <td className="p-4 flex items-center gap-3">
                      <div className="w-1.5 h-6" style={{ backgroundColor: teamColor }} />
                      <div>
                        <span className="font-bold text-white uppercase">{r.driver_name}</span>
                        <span className="ml-2 px-1.5 py-0.5 bg-[#121518] border border-[#22272c] text-[12px] font-black text-slate-400">
                          {r.driver_code}
                        </span>
                        {r.is_fastest_lap && (
                          <span className="ml-2 px-1.5 py-0.5 bg-purple-500/10 border border-purple-500/30 text-purple-400 text-[11px] font-black tracking-widest uppercase">
                            FASTEST LAP
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Team */}
                    <td className="p-4 text-slate-400 uppercase tracking-wide">
                      {r.team}
                    </td>

                    {/* Laps */}
                    <td className="p-4 text-center font-bold text-slate-300">
                      {r.number_of_laps}
                    </td>

                    {/* Duration / Gap */}
                    <td className="p-4 text-right font-bold text-slate-200">
                      {r.dnf ? (
                        <span className="text-red-500 font-bold text-xs uppercase">DNF</span>
                      ) : r.dns ? (
                        <span className="text-slate-600 font-bold text-xs uppercase">DNS</span>
                      ) : r.dsq ? (
                        <span className="text-red-700 font-bold text-xs uppercase">DSQ</span>
                      ) : (
                        formatDuration(r.duration, r.position, r.gap_to_leader)
                      )}
                    </td>

                    {/* Points */}
                    <td className="p-4 text-right font-black italic text-white text-base">
                      {r.points > 0 ? `+${r.points}` : "0"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

    </div>
  );
}
