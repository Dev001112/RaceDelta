import React, { useEffect, useState } from "react";
import { fetchTeams } from "../api/client";
import TeamCard from "../components/TeamCard";
import { useSeason } from "../context/SeasonContext";

export default function Teams() {
  const { season } = useSeason();
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!season) return;
    setLoading(true);

    fetchTeams(season)
      .then((data) => {
        setTeams(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Teams fetch error:", err);
        setLoading(false);
      });
  }, [season]);

  if (loading) {
    return <div style={{ padding: 20, color: "#cbd5e1" }}>Loading teams…</div>;
  }

  if (!teams.length) {
    return <div style={{ padding: 20, color: "#cbd5e1" }}>No teams found.</div>;
  }

  return (
    <div className="py-8 space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-line pb-4">
        <div>
          <h2 className="text-4xl font-black italic uppercase text-white font-broadcast tracking-tight">
            Constructor Championship <span className="text-slate-400">//{season}</span>
          </h2>
          <p className="text-slate-400 mt-1.5 text-sm">
            F1 constructor standings, points accumulation, and factory profiles.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-4" data-tour="team-grid">
        {teams.map((team) => (
          <TeamCard
            key={team.constructor_id}
            team={team}
          />
        ))}
      </div>
    </div>
  );
}
