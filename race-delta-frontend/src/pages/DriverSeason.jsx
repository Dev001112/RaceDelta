import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchDriverSeason } from "../lib/api";

import DriverHeader from "../components/DriverHeader";
import RadarComparison from "../components/RadarComparison";
import PointsTrend from "../components/PointsTrend";
import QualiRaceDelta from "../components/QualiRaceDelta";

const cardStyle = {
  background: "linear-gradient(180deg, #121826, #0F1522)",
  borderRadius: 18,
  padding: "1.5rem",
  boxShadow: "0 20px 40px rgba(0,0,0,0.45)",
  border: "1px solid rgba(255,255,255,0.04)"
};

const SEASONS = [
  { label: "Current", value: "current" },
  { label: "2024", value: "2024" },
  { label: "2023", value: "2023" }
];

export default function DriverSeason() {
  const { code, season } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const resolvedSeason =
    season === "current" ? new Date().getFullYear() : Number(season);

  useEffect(() => {
    setData(null);
    setError(null);

    fetchDriverSeason(code, resolvedSeason)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [code, resolvedSeason]);

  if (error) {
    return <p style={{ color: "#ffb4b4" }}>{error}</p>;
  }

  if (!data) {
    return <p style={{ color: "#9CA3AF" }}>Loading season analytics…</p>;
  }

  const { driver, metrics, radar } = data;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0B0F14",
        padding: "1.5rem 2.25rem",
        color: "#E5E7EB"
      }}
    >
      {/* ================= HEADER BAR ================= */}
      <div
        style={{
          maxWidth: 1300,
          margin: "0 auto 1rem auto",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}
      >
        <h2 style={{ margin: 0, fontSize: 20 }}>
          Driver Season Analysis
        </h2>

        <select
          value={season}
          onChange={(e) =>
            navigate(`/driver/${code}/season/${e.target.value}`)
          }
          style={{
            background: "#0F1522",
            color: "#E5E7EB",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 8,
            padding: "6px 10px",
            fontSize: 13,
            cursor: "pointer"
          }}
        >
          {SEASONS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* ================= TOP GRID ================= */}
      <div
        style={{
          maxWidth: 1300,
          margin: "0 auto 1.25rem auto",
          display: "grid",
          gridTemplateColumns: "1fr 1.8fr",
          gap: "1.25rem"
        }}
      >
        {/* DRIVER CARD */}
        <div style={cardStyle}>
          <DriverHeader
            driver={driver}
            season={resolvedSeason}
            points={Number.isFinite(metrics.total_points) ? metrics.total_points : 0}
            position={metrics.championship_position}
          />

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "0.75rem",
              marginTop: "1rem",
              fontSize: 12,
              color: "#9CA3AF"
            }}
          >
            <div>
              <strong style={{ color: "#E5E7EB" }}>
                {metrics.wins ?? 0}
              </strong>
              <div>Wins</div>
            </div>

            <div>
              <strong style={{ color: "#E5E7EB" }}>
                {metrics.podiums ?? 0}
              </strong>
              <div>Podiums</div>
            </div>

            <div>
              <strong style={{ color: "#E5E7EB" }}>
                {metrics.total_points ?? 0}
              </strong>
              <div>Points</div>
            </div>
          </div>
        </div>

        {/* RADAR CARD */}
        <div style={cardStyle}>
          <h3 style={{ margin: 0, fontSize: 16 }}>
            Season Performance
          </h3>

          <div style={{ height: 260 }}>
            <RadarComparison radar={radar || {}} />
          </div>
        </div>
      </div>

      {/* ================= BOTTOM GRID ================= */}
      <div
        style={{
          maxWidth: 1300,
          margin: "0 auto",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "1.75rem"
        }}
      >
        <div style={cardStyle}>
          <PointsTrend pointsByRace={metrics.points_by_race || []} />
        </div>

        <div style={cardStyle}>
          <QualiRaceDelta deltas={metrics.q_vs_race?.by_race || []} />
        </div>
      </div>
    </div>
  );
}
