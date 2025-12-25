import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  fetchDriverStandings,
  fetchConstructorStandings,
} from "../lib/api";

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
function DriversTable({ standings }) {
  const navigate = useNavigate();

  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="text-left text-slate-400 border-b border-slate-800">
          <th className="py-3">Pos</th>
          <th>Driver</th>
          <th>Team</th>
          <th className="text-right">Pts</th>
          <th className="text-right">Wins</th>
        </tr>
      </thead>

      <tbody>
        {standings.map((d) => {
          const teamLogo = TEAM_LOGOS[d.team] || null;

          return (
            <tr
              key={d.position}
              className="border-b border-slate-900 hover:bg-slate-900/40"
            >
              <td className="py-4 font-semibold">{d.position}</td>

              {/* DRIVER */}
              <td className="py-4">
                <div className="flex items-center gap-3">
                  <Avatar
                    src={d.headshot_url}
                    size={48}
                    onClick={() =>
                      navigate(`/driver/${d.driver_code}/season/current`)
                    }
                  />
                  <div>
                    <div
                      className="font-semibold text-white hover:underline cursor-pointer"
                      onClick={() =>
                        navigate(`/driver/${d.driver_code}/season/current`)
                      }
                    >
                      {d.driver_name}
                    </div>
                    <div className="text-xs text-slate-400">
                      {d.driver_code}
                    </div>
                  </div>
                </div>
              </td>

              {/* TEAM */}
              <td className="py-4">
                <div className="flex items-center gap-3">
                  <Avatar
                    src={teamLogo}
                    size={36}
                    onClick={() =>
                      navigate(`/teams/${d.constructor_id}`)
                    }
                  />
                  <span
                    className="hover:underline cursor-pointer"
                    onClick={() =>
                      navigate(`/teams/${d.constructor_id}`)
                    }
                  >
                    {d.team}
                  </span>
                </div>
              </td>

              <td className="py-4 text-right font-semibold">
                {d.points}
              </td>

              <td className="py-4 text-right text-slate-300">
                {d.wins}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/* ---------------- CONSTRUCTORS TABLE ---------------- */
function ConstructorsTable({ teams }) {
  const navigate = useNavigate();

  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="text-left text-slate-400 border-b border-slate-800">
          <th className="py-3">Pos</th>
          <th>Team</th>
          <th className="text-right">Pts</th>
          <th className="text-right">Wins</th>
        </tr>
      </thead>

      <tbody>
        {teams.map((t) => {
          const logo = TEAM_LOGOS[t.team] || null;

          return (
            <tr
              key={t.position}
              className="border-b border-slate-900 hover:bg-slate-900/40"
            >
              <td className="py-4 font-semibold">{t.position}</td>

              <td className="py-4">
                <div className="flex items-center gap-3">
                  <Avatar
                    src={logo}
                    size={40}
                    onClick={() =>
                      navigate(`/teams/${t.constructor_id}`)
                    }
                  />
                  <span
                    className="font-semibold hover:underline cursor-pointer"
                    onClick={() =>
                      navigate(`/teams/${t.constructor_id}`)
                    }
                  >
                    {t.team}
                  </span>
                </div>
              </td>

              <td className="py-4 text-right font-semibold">
                {t.points}
              </td>

              <td className="py-4 text-right text-slate-300">
                {t.wins}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/* ---------------- MAIN ---------------- */
export default function Stats() {
  const [view, setView] = useState("drivers");
  const [driverStandings, setDriverStandings] = useState([]);
  const [constructorStandings, setConstructorStandings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);

      const [driversRes, constructorsRes] = await Promise.all([
        fetchDriverStandings(),
        fetchConstructorStandings(),
      ]);

      setDriverStandings(driversRes.standings || []);
      setConstructorStandings(constructorsRes.standings || []);
      setLoading(false);
    }

    load();
  }, []);

  if (loading) {
    return <div className="p-8 text-slate-400">Loading standings…</div>;
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold text-white">
          F1 Standings
        </h1>

        <select
          value={view}
          onChange={(e) => setView(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm"
        >
          <option value="drivers">Drivers</option>
          <option value="constructors">Constructors</option>
        </select>
      </div>

      {view === "drivers" ? (
        <DriversTable standings={driverStandings} />
      ) : (
        <ConstructorsTable teams={constructorStandings} />
      )}
    </div>
  );
}
