import { useNavigate } from "react-router-dom";

export default function DriverCard({ d }) {
  const navigate = useNavigate();

  if (!d?.code) return null;

  return (
    <div
      onClick={() => navigate(`/driver/${d.code}/season/current`)}
      style={{
        display: "flex",
        gap: 12,
        alignItems: "center",
        padding: 12,
        borderRadius: 10,
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.05)",
        cursor: "pointer"
      }}
    >
      <img
        src={d.photo}
        alt={d.name}
        loading="lazy"
        className="w-14 h-14 rounded-lg object-cover"
      />

      <div>
        <div style={{ fontSize: 16, fontWeight: 800 }}>
          {d.name}
        </div>
        <div style={{ fontSize: 13, color: "#9fb0c9" }}>
          {d.team} • #{d.number}
        </div>
      </div>
    </div>
  );
}
