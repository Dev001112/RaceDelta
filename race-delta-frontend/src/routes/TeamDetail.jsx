import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchTeamDetail } from "../lib/api";
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
    return <div style={{ color: "#cbd5e1" }}>Loading team…</div>;
  }

  if (!team) {
    return <div style={{ color: "#cbd5e1" }}>Team not found.</div>;
  }

  const logo = TEAM_LOGOS[team.team_name];

  return (
    <div style={{ padding: 24 }}>
      <button onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        ← Back
      </button>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        {logo && (
          <img
            src={logo}
            alt={team.team_name}
            style={{ width: 90, objectFit: "contain" }}
          />
        )}
        <div>
          <h1>{team.team_name}</h1>
          <div style={{ color: "#9fb0c9" }}>{team.nationality}</div>
        </div>
      </div>

      {/* Metadata */}
      <div style={{ marginTop: 16 }}>
        <p><b>Team Principal:</b> {team.team_principal}</p>
        <p><b>Engine:</b> {team.engine}</p>
        <p><b>Car:</b> {team.car}</p>
      </div>

      {/* Stats */}
      <div style={{ marginTop: 16 }}>
        <p>Position: <b>{team.position}</b></p>
        <p>Points: <b>{team.points}</b></p>
        <p>Wins: <b>{team.wins}</b></p>
      </div>

      {/* Drivers */}
      <h3 style={{ marginTop: 24 }}>Drivers</h3>
      <div style={{ display: "flex", gap: 16 }}>
        {team.drivers.length ? (
          team.drivers.map((d) => (
            <div key={d.code} style={{ textAlign: "center" }}>
              {d.headshot_url && (
                <img
                  src={d.headshot_url}
                  alt={d.name}
                  style={{
                    width: 72,
                    height: 72,
                    borderRadius: "50%",
                    objectFit: "cover"
                  }}
                />
              )}
              <div>{d.name}</div>
            </div>
          ))
        ) : (
          <div>No drivers available</div>
        )}
      </div>
    </div>
  );
}
