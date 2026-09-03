import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  fetchDriverStandings,
  fetchConstructorStandings,
} from "../api/client";
import { useSeason } from "../context/SeasonContext";
import PageHeader from "../components/PageHeader";

/* ---------------- TEAM LOGOS ---------------- */
const TEAM_LOGOS = {
  "Red Bull Racing":
    "https://tse2.mm.bing.net/th/id/OIP.DqHZWIacAQu_4LJIhbmdKQHaHa?cb=ucfimg2&ucfimg=1&rs=1&pid=ImgDetMain&o=7&rm=3",
  Ferrari:
    "https://fabrikbrands.com/wp-content/uploads/F1-Team-logos-4.png",
  Mercedes:
    "https://fabrikbrands.com/wp-content/uploads/F1-Team-logos-5-751x469.png",
  McLaren:
    "https://static.vecteezy.com/system/resources/previews/020/500/445/original/mclaren-brand-logo-car-symbol-name-white-design-british-automobile-illustration-with-orange-background-free-vector.jpg",
  "Aston Martin":
    "https://i.pinimg.com/736x/81/dd/bd/81ddbddea449c0ebbb6d523fa65a61b4.jpg",
  Alpine:
    "https://fabrikbrands.com/wp-content/uploads/F1-Team-logos-6.png",
  Williams:
    "https://tse1.mm.bing.net/th/id/OIP.dvme6ehaY1Ub6ZM-Ip4mRAHaF9?cb=ucfimg2&ucfimg=1&rs=1&pid=ImgDetMain&o=7&rm=3",
  "Haas F1 Team":
    "https://fabrikbrands.com/wp-content/uploads/F1-Team-logos-9.png",
  "Kick Sauber":
    "https://cdn-8.motorsport.com/images/amp/0L17d5W2/s1000/logo-stakef1team-rgb-pos-1.jpg",
  RB:
    "https://www.planetf1.com/content/themes/planet2/img/png/teams/2024/racing-bulls.png",
};

/* ---------------- IMAGE COMPONENT ---------------- */
function Avatar({ src, size = 44, onClick }) {
  const [error, setError] = useState(false);

  if (!src || error) {
    return (
      <div
        onClick={onClick}
        style={{
          width: size,
          height: size,
          borderRadius: 8,
          background: "#1f2937",
          cursor: onClick ? "pointer" : "default",
        }}
      />
    );
  }

  return (
    <img
      src={src}
      alt=""
      onClick={onClick}
      onError={() => setError(true)}
      style={{
        width: size,
        height: size,
        borderRadius: 8,
        objectFit: "cover",
        cursor: onClick ? "pointer" : "default",
      }}
    />
  );
}

/* ---------------- DRIVERS TABLE ---------------- */
function DriversTable({ standings, season }) {
  const navigate = useNavigate();
  return (
    <table className="timing-table">
      <thead>
        <tr><th>Pos</th><th>Driver</th><th>Team</th><th className="num">Pts</th><th className="num">Wins</th></tr>
      </thead>
      <tbody>
        {standings.map((d) => (
          <tr key={d.position} className="cursor-pointer"
              onClick={() => navigate(`/driver/${d.driver_code}/season/${season || "current"}`)}>
            <td className="pos">{String(d.position).padStart(2, "0")}</td>
            <td>
              <div className="flex items-center gap-3">
                <Avatar src={d.headshot_url} size={40} />
                <div>
                  <div className="font-broadcast font-black uppercase text-white text-lg leading-tight">{d.driver_name}</div>
                  <div className="text-muted text-sm">{d.driver_code}</div>
                </div>
              </div>
            </td>
            <td>
              <span className="inline-flex items-center gap-2 hover:underline"
                    onClick={(e) => { e.stopPropagation(); navigate(`/teams/${d.constructor_id}`); }}>
                <Avatar src={TEAM_LOGOS[d.team] || null} size={28} />
                {d.team}
              </span>
            </td>
            <td className="num font-broadcast font-black text-white text-xl">{d.points}</td>
            <td className="num text-muted">{d.wins}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* ---------------- CONSTRUCTORS TABLE ---------------- */
function ConstructorsTable({ teams }) {
  const navigate = useNavigate();
  return (
    <table className="timing-table">
      <thead>
        <tr><th>Pos</th><th>Team</th><th className="num">Pts</th><th className="num">Wins</th></tr>
      </thead>
      <tbody>
        {teams.map((t) => (
          <tr key={t.position} className="cursor-pointer" onClick={() => navigate(`/teams/${t.constructor_id}`)}>
            <td className="pos">{String(t.position).padStart(2, "0")}</td>
            <td>
              <div className="flex items-center gap-3">
                <Avatar src={TEAM_LOGOS[t.team] || null} size={36} />
                <span className="font-broadcast font-black uppercase text-white text-lg">{t.team}</span>
              </div>
            </td>
            <td className="num font-broadcast font-black text-white text-xl">{t.points}</td>
            <td className="num text-muted">{t.wins}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* ---------------- MAIN ---------------- */
export default function Stats() {
  const { season } = useSeason();
  const [view, setView] = useState("drivers");
  const [driverStandings, setDriverStandings] = useState([]);
  const [constructorStandings, setConstructorStandings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (!season) return;
      setLoading(true);
      const [driversRes, constructorsRes] = await Promise.all([
        fetchDriverStandings(season),
        fetchConstructorStandings(season),
      ]);
      setDriverStandings(driversRes.standings || []);
      setConstructorStandings(constructorsRes.standings || []);
      setLoading(false);
    }
    load();
  }, [season]);

  const rows = view === "drivers" ? driverStandings : constructorStandings;

  return (
    <div className="py-6 space-y-6">
      <PageHeader kicker="Championship standings" title="F1 Standings" season={season}
        subtitle="Drivers' and constructors' tables for the selected season. Click a row to open the driver or team."
        actions={
          <select value={view} onChange={(e) => setView(e.target.value)} className="select-broadcast" aria-label="Standings table">
            <option value="drivers">Drivers</option>
            <option value="constructors">Constructors</option>
          </select>
        } />

      <section className="panel" data-tour="standings">
        <div className="panel-head">
          <div>
            <h2 className="panel-title">{view === "drivers" ? "Drivers' championship" : "Constructors' championship"}</h2>
            <p className="panel-subtitle">{loading ? "Loading…" : `${rows.length} classified`}</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          {loading
            ? <p className="p-4 text-muted animate-pulse">Loading standings…</p>
            : view === "drivers"
              ? <DriversTable standings={driverStandings} season={season} />
              : <ConstructorsTable teams={constructorStandings} />}
        </div>
      </section>
    </div>
  );
}
