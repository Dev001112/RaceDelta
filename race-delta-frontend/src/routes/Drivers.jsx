import { useEffect, useState } from "react";
import client from "../api/client";
import { useNavigate } from "react-router-dom";

/* ---------------------------------
   Driver Card (frontend-normalized)
---------------------------------- */
function DriverCard({ d }) {
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
        cursor: "pointer",
        transition: "background 0.2s ease"
      }}
      onMouseEnter={(e) =>
        (e.currentTarget.style.background = "rgba(255,255,255,0.06)")
      }
      onMouseLeave={(e) =>
        (e.currentTarget.style.background = "rgba(255,255,255,0.03)")
      }
    >
      {d.photo ? (
        <img
          src={d.photo}
          alt={d.name}
          loading="lazy"
          style={{
            width: 56,
            height: 56,
            borderRadius: 8,
            objectFit: "cover",
            background: "#111"
          }}
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
            fontWeight: 800,
            fontSize: 18
          }}
        >
          {d.name?.[0] || "?"}
        </div>
      )}

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

/* ---------------------------------
   Drivers Page
---------------------------------- */
export default function Drivers() {
  const [drivers, setDrivers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;

    client.fetchDrivers()
      .then((list) => {
        if (!alive) return;
        console.log("DRIVERS (normalized):", list);
        setDrivers(list);
        setLoading(false);
      })
      .catch((e) => {
        console.error(e);
        if (alive) {
          setErr("Failed to load drivers");
          setLoading(false);
        }
      });

    return () => {
      alive = false;
    };
  }, []);

  if (loading) {
    return <div style={{ padding: 20 }}>Loading drivers…</div>;
  }

  if (err) {
    return (
      <div style={{ padding: 20, color: "#ffb4b4" }}>
        {err}
      </div>
    );
  }

  return (
    <div style={{ padding: 20 }}>
      <h2 style={{ color: "#fff", marginBottom: 6 }}>
        Drivers — Current Season
      </h2>

      <div style={{ color: "#9fb0c9", marginBottom: 14 }}>
        {drivers.length} drivers
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
          gap: 12
        }}
      >
        {drivers.map((d) => (
          <DriverCard key={d.code} d={d} />
        ))}
      </div>
    </div>
  );
}
