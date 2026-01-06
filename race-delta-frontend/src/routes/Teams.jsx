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
    <div style={{ padding: 20 }}>
      <h2 style={{ color: "#fff", marginBottom: 12 }}>Teams</h2>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
          gap: 12
        }}
      >
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
