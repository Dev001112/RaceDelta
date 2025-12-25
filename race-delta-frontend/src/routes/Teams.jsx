import React, { useEffect, useState } from "react";
import { fetchTeams } from "../lib/api";
import TeamCard from "../components/TeamCard";

export default function Teams() {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTeams()
      .then((data) => {
        setTeams(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Teams fetch error:", err);
        setLoading(false);
      });
  }, []);

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
