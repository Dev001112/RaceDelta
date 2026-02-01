import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSeason } from "../context/SeasonContext";
import client from "../api/client";
import Card from "../components/ui/Card";
import { User, Flag } from "lucide-react";

/* ---------------------------------
   Driver Card (Modern)
---------------------------------- */
function DriverCard({ d, season }) {
  const navigate = useNavigate();

  if (!d?.code) return null;

  return (
    <Card
      onClick={() => navigate(`/driver/${d.code}/season/${season || "current"}`)}
      className="flex items-center gap-4 group"
    >
      <div className="relative">
        <div className="w-16 h-16 rounded-xl overflow-hidden bg-slate-800 ring-2 ring-white/5 group-hover:ring-cyan-500/50 transition-all">
          {d.photo ? (
            <img
              src={d.photo}
              alt={d.name}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-700 to-slate-800 text-slate-400 font-bold text-xl">
              {d.name?.[0]}
            </div>
          )}
        </div>
        {/* Team Color Strip */}
        <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-slate-900 flex items-center justify-center border border-slate-700 text-[10px] font-bold text-white shadow-lg z-10">
          {d.number}
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <h3 className="text-lg font-bold text-white truncate group-hover:text-cyan-400 transition-colors">
          {d.name}
        </h3>
        <p className="text-sm text-slate-400 truncate">{d.team}</p>

        {/* Country (Placeholder/If available) */}
        {d.country && (
          <div className="flex items-center gap-1 mt-1 text-xs text-slate-500 uppercase tracking-wider">
            <span>{d.country}</span>
          </div>
        )}
      </div>

      <div className="text-slate-600 group-hover:text-cyan-500 transition-colors">
        →
      </div>
    </Card>
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
    <div className="py-8 space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h2 className="text-3xl font-bold text-white tracking-tight">
            Driver Lineup <span className="text-cyan-500">{season}</span>
          </h2>
          <p className="text-slate-400 mt-2">
            Explore profiles, career stats and season performance.
            {isOffseason && <span className="ml-2 text-amber-500 text-sm font-medium bg-amber-500/10 px-2 py-0.5 rounded">Off-Season View</span>}
          </p>
        </div>

        <div className="px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-slate-400">
          {drivers.length} Drivers Confirmed
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {drivers.map((d) => (
          <DriverCard key={d.code} d={d} season={season} />
        ))}
      </div>
    </div>
  );
}
