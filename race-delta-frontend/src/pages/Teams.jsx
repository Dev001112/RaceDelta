import React, { useEffect, useState } from "react";
import TeamCard from "../components/TeamCard";
import { fetchTeams } from "../lib/api";

export default function Teams() {
  const [teams, setTeams] = useState([]);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    fetchTeams().then(data => {
      // Backend already returns clean teams
      setTeams(data);
    });
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ color: "#fff", marginBottom: 16 }}>Teams</h2>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
          gap: 16
        }}
      >
        {teams.map(team => (
          <TeamCard
            key={team.team}
            teamName={team.team}
            count={team.driver_count || team.count || 2}
            expanded={expanded === team.team}
            onToggle={() =>
              setExpanded(expanded === team.team ? null : team.team)
            }
          />
        ))}
      </div>
    </div>
  );
}
