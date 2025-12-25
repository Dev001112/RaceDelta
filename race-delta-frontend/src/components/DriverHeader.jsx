export default function DriverHeader({
  driver,
  season,
  points,
  position
}) {
  return (
    <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
      {/* DRIVER IMAGE */}
      <img
        src={driver.image}
        alt={driver.name}
        style={{
          width: 64,
          height: 64,
          borderRadius: "50%",
          border: "2px solid #ef4444"
        }}
      />

      <div>
        {/* NAME */}
        <h2
          style={{
            margin: 0,
            fontSize: 18,   // 🔽 back to original
            fontWeight: 600
          }}
        >
          {driver.name}
        </h2>

        {/* TEAM */}
        <div style={{ fontSize: 12, color: "#9CA3AF" }}>
          {driver.team}
        </div>

        {/* SEASON + POSITION */}
        <div
          style={{
            display: "flex",
            gap: 6,
            marginTop: 6,
            alignItems: "center"
          }}
        >
          <span
            style={{
              fontSize: 11,
              padding: "3px 10px",
              borderRadius: 999,
              background: "#7f1d1d",
              color: "#fecaca"
            }}
          >
            Season {season}
          </span>

          {Number.isFinite(position) && (
            <span
              style={{
                fontSize: 11,
                padding: "3px 10px",
                borderRadius: 999,
                background: "#111827",
                color: "#E5E7EB",
                border: "1px solid rgba(255,255,255,0.15)",
                fontWeight: 600
              }}
            >
              P{position}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
