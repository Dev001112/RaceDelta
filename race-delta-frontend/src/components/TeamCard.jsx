import React from "react";
import { useNavigate } from "react-router-dom";
import { TEAM_LOGOS } from "../lib/teamLogos";

/* ---------------------------------------
   Normalize team names for logo mapping
---------------------------------------- */
const normalizeTeamName = (name) => {
  if (!name) return name;

  if (name.includes("Red Bull")) return "Red Bull";
  if (name.includes("Mercedes")) return "Mercedes";
  if (name.includes("Ferrari")) return "Ferrari";
  if (name.includes("McLaren")) return "McLaren";
  if (name.includes("Aston")) return "Aston Martin";
  if (name.includes("Alpine")) return "Alpine F1 Team";
  if (name.includes("Williams")) return "Williams";
  if (name.includes("Haas")) return "Haas F1 Team";
  if (name.includes("RB")) return "RB F1 Team";
  if (name.includes("Sauber")) return "Sauber";

  return name;
};

function TeamCard({ team }) {
  const navigate = useNavigate();
  if (!team) return null;

  const normalizedName = normalizeTeamName(team.team_name);
  const logo = TEAM_LOGOS[normalizedName];

  return (
    <div
      onClick={() => navigate(`/teams/${team.constructor_id}`)}
      style={{
        borderRadius: 12,
        padding: 14,
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01))",
        border: "1px solid rgba(255,255,255,0.06)",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        minHeight: 170,
        cursor: "pointer"
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {/* Logo */}
        {logo ? (
          <img
            src={logo}
            alt={team.team_name}
            style={{
              width: 56,
              height: 56,
              objectFit: "contain",
              background: "#111",
              borderRadius: 8,
              padding: 6
            }}
            onError={(e) => (e.currentTarget.style.display = "none")}
          />
        ) : (
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 8,
              background: "#222",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontSize: 20,
              fontWeight: 700
            }}
          >
            {team.team_name?.[0] || "?"}
          </div>
        )}

        {/* Team name + nationality */}
        <div>
          <div style={{ color: "#fff", fontWeight: 800, fontSize: 16 }}>
            {team.team_name}
          </div>
          <div style={{ fontSize: 12, color: "#9fb0c9" }}>
            {team.nationality}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div style={{ fontSize: 12, color: "#9fb0c9" }}>
        Position: <strong>{team.position}</strong>
      </div>

      <div style={{ fontSize: 12, color: "#9fb0c9" }}>
        Points: <strong>{team.points}</strong>
      </div>

      <div style={{ fontSize: 12, color: "#9fb0c9" }}>
        Wins: <strong>{team.wins}</strong>
      </div>
    </div>
  );
}

export default TeamCard;
