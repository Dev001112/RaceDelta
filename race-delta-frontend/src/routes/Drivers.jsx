import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSeason } from "../context/SeasonContext";
import client from "../api/client";
import Card from "../components/ui/Card";
import { User, Flag } from "lucide-react";

import { getTeamColor } from "../lib/teamMeta";

/* ---------------------------------
   Driver Card (F1 Broadcast Style)
---------------------------------- */
function DriverCard({ d, season }) {
  const navigate = useNavigate();

  if (!d?.code) return null;
  const teamColor = getTeamColor(d.team);

  // Format name: uppercase last name for broadcast style
  const formatBroadcastName = (fullName) => {
    if (!fullName) return "";
    const parts = fullName.trim().split(" ");
    if (parts.length === 1) return parts[0].toUpperCase();
    const lastName = parts.slice(1).join(" ").toUpperCase();
    return (
      <span>
        {parts[0]} <span className="font-black">{lastName}</span>
      </span>
    );
  };

  return (
    <div
      onClick={() => navigate(`/driver/${d.code}/season/${season || "current"}`)}
      className="bg-panel border border-line p-3.5 flex items-center justify-between cursor-pointer group hover:bg-raised transition-colors timing-strip relative"
      style={{
        borderLeft: `4px solid ${teamColor}`
      }}
    >
      <div className="flex items-center gap-4">
        {/* Driver Photo/Fallback */}
        <div className="relative">
          <div className="w-12 h-12 overflow-hidden bg-raised border border-line flex items-center justify-center">
            {d.photo ? (
              <img
                src={d.photo}
                alt={d.name}
                className="w-full h-full object-contain"
                loading="lazy"
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
            ) : (
              <div className="text-white font-black text-xs font-broadcast">
                {d.code}
              </div>
            )}
          </div>
          {/* Driver Number Badge */}
          <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-carbon flex items-center justify-center border border-line text-[11px] font-black text-white italic font-broadcast">
            {d.number}
          </div>
        </div>

        {/* Identity block */}
        <div className="font-broadcast leading-tight">
          <h3 className="text-sm font-bold text-white uppercase tracking-wide group-hover:text-f1 transition-colors">
            {formatBroadcastName(d.name)}
          </h3>
          <p className="text-[12px] text-slate-500 uppercase tracking-widest mt-0.5">{d.team}</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {d.country && (
          <span className="hidden sm:inline text-[11px] font-bold text-slate-500 uppercase tracking-widest bg-white/5 border border-line px-2 py-0.5 font-broadcast">
            {d.country}
          </span>
        )}
        <div className="text-slate-600 group-hover:text-f1 transition-colors font-broadcast font-bold">
          →
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------
   Drivers Page (Refactored)
---------------------------------- */
export default function Drivers() {
  const { season, isOffseason } = useSeason();
  const [drivers, setDrivers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    if (!season) return;

    setLoading(true);
    client.fetchDrivers(season)
      .then((list) => {
        if (!alive) return;
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
  }, [season]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-8">
        {[...Array(9)].map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-white/5 animate-pulse" />
        ))}
      </div>
    );
  }

  if (err) {
    return (
      <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg">
        {err}
      </div>
    );
  }

  return (
    <div className="py-8 space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-line pb-4">
        <div>
          <h2 className="text-4xl font-black italic uppercase text-white font-broadcast tracking-tight">
            Driver Lineup <span className="text-slate-400">//{season}</span>
          </h2>
          <p className="text-slate-400 mt-1.5 text-sm">
            Explore profiles, career statistics and season performance telemetry.
            {isOffseason && <span className="ml-2 text-flag text-xs font-bold bg-flag/10 px-2 py-0.5 border border-flag/20 font-broadcast uppercase">Off-Season Archive</span>}
          </p>
        </div>

        <div className="px-3 py-1 bg-raised border border-line text-xs font-bold text-slate-400 font-broadcast uppercase tracking-wider">
          {drivers.length} Drivers Logged
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-tour="driver-grid">
        {drivers.map((d) => (
          <DriverCard key={d.code} d={d} season={season} />
        ))}
      </div>
    </div>
  );
}
