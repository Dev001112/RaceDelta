import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchTeamDetail } from "../api/client";
import { TEAM_LOGOS } from "../lib/teamLogos";

export default function TeamDetail() {
  const { constructorId } = useParams();
  const navigate = useNavigate();
  const [team, setTeam] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTeamDetail(constructorId)
      .then(setTeam)
      .catch((e) => console.error("Team detail fetch error:", e))
      .finally(() => setLoading(false));
  }, [constructorId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh] text-slate-400 animate-pulse">
        Loading team details...
      </div>
    );
  }

  if (!team) {
    return (
      <div className="flex items-center justify-center min-h-[50vh] text-slate-400">
        Team not found.
      </div>
    );
  }

  const logo = TEAM_LOGOS[team.team_name];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      {/* Back Button */}
      <button
        onClick={() => navigate(-1)}
        className="text-slate-400 hover:text-white transition-colors flex items-center gap-2 mb-4"
      >
        <span>←</span> Back
      </button>

      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start gap-8">

        {/* Team Identity */}
        <div className="flex items-center gap-6">
          {logo && (
            <div className="bg-white/5 p-4 rounded-xl border border-white/10">
              <img
                src={logo}
                alt={team.team_name}
                className="w-24 h-24 object-contain"
              />
            </div>
          )}
          <div>
            <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
              {team.team_name}
            </h1>
            <div className="text-xl text-slate-400 mt-2 font-medium">
              {team.nationality}
            </div>
          </div>
        </div>

        {/* Car Image (Hero) */}
        {team.car_image && (
          <div className="relative z-10 -mt-4 md:-mt-8">
            <img
              src={team.car_image}
              alt={`${team.car} Car`}
              className="w-full max-w-[500px] h-auto object-contain drop-shadow-[0_20px_40px_rgba(0,0,0,0.6)] hover:scale-105 transition-transform duration-500"
            />
          </div>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Championship Position" value={team.position} highlight />
        <StatCard label="Points" value={team.points} />
        <StatCard label="Wins" value={team.wins} />
        <StatCard label="Car Model" value={team.car || "N/A"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Details */}
        <div className="bg-[#0f172a]/50 p-6 rounded-2xl border border-white/5 space-y-4 h-fit">
          <h3 className="text-xl font-bold text-white mb-4">Team Info</h3>
          <InfoRow label="Team Principal" value={team.team_principal} />
          <InfoRow label="Engine" value={team.engine} />
          <InfoRow label="Chassis" value={team.car} />
        </div>

        {/* Right Column: Drivers */}
        <div className="lg:col-span-2">
          <h3 className="text-xl font-bold text-white mb-6">Driver Lineup</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {team.drivers.length ? (
              team.drivers.map((d) => (
                <div
                  key={d.code}
                  className="bg-[#0f172a] p-6 rounded-2xl border border-white/10 flex items-center gap-6 hover:border-blue-500/50 transition-colors group"
                >
                  {d.headshot_url ? (
                    <img
                      src={d.headshot_url}
                      alt={d.name}
                      className="w-20 h-20 rounded-full object-cover border-2 border-white/10 group-hover:border-blue-500 transition-colors"
                    />
                  ) : (
                    <div className="w-20 h-20 rounded-full bg-slate-800 flex items-center justify-center text-xs text-slate-500">
                      No Photo
                    </div>
                  )}

                  <div>
                    <div className="text-3xl font-bold text-white/10 absolute right-6 top-1/2 -translate-y-1/2 group-hover:text-white/20 transition-colors select-none">
                      {d.driver_number}
                    </div>
                    <div className="text-xl font-bold text-white relative z-10">{d.name}</div>
                    <div className="text-blue-400 text-sm font-medium">Racing Driver</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-2 text-slate-500 italic">No drivers announced yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Simple internal components for cleaner JSX
function StatCard({ label, value, highlight = false }) {
  return (
    <div className={`p-5 rounded-xl border ${highlight ? 'bg-gradient-to-br from-blue-600/20 to-blue-900/10 border-blue-500/30' : 'bg-[#0f172a] border-white/5'}`}>
      <div className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-3xl font-bold ${highlight ? 'text-blue-400' : 'text-white'}`}>{value}</div>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between items-center border-b border-white/5 pb-3 last:border-0">
      <span className="text-slate-400">{label}</span>
      <span className="text-white font-medium text-right">{value || "N/A"}</span>
    </div>
  );
}
