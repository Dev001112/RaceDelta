import React from "react";
import { useNavigate } from "react-router-dom";
import { TEAM_LOGOS } from "../lib/teamLogos";
import { getTeamColor } from "../lib/teamMeta";

function TeamCard({ team }) {
  const navigate = useNavigate();
  if (!team) return null;

  const teamColor = getTeamColor(team.team_name || team.constructor_id);
  const logo = TEAM_LOGOS[team.team_name] || TEAM_LOGOS[team.constructor_id] || null;

  return (
    <div
      onClick={() => navigate(`/teams/${team.constructor_id}`)}
      className="bg-panel border border-line p-4 flex flex-col justify-between cursor-pointer group hover:bg-raised transition-colors relative"
      style={{
        borderLeft: `4px solid ${teamColor}`,
        minHeight: 150
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        {/* Logo */}
        {logo ? (
          <img
            src={logo}
            alt={team.team_name}
            className="w-14 h-14 object-contain bg-raised border border-line p-1.5"
            onError={(e) => (e.currentTarget.style.display = "none")}
          />
        ) : (
          <div className="w-14 h-14 flex items-center justify-center bg-[#1e2329] text-white font-bold font-broadcast text-xl border border-line">
            {team.team_name?.[0] || "?"}
          </div>
        )}

        {/* Team name + nationality */}
        <div className="font-broadcast">
          <div className="text-white font-black uppercase text-base italic leading-tight group-hover:text-f1 transition-colors">
            {team.team_name}
          </div>
          <div className="text-[12px] text-slate-500 uppercase tracking-widest mt-0.5">
            {team.nationality}
          </div>
        </div>
      </div>

      {/* Stats horizontal strip */}
      <div className="grid grid-cols-3 gap-2 border-t border-[#1e2329] pt-3 mt-3 font-broadcast text-center">
        <div>
          <div className="text-[11px] text-slate-500 uppercase tracking-wider">POS</div>
          <div className="text-sm font-black italic text-white">
            {team.position < 10 ? `0${team.position}` : team.position}
          </div>
        </div>
        
        <div>
          <div className="text-[11px] text-slate-500 uppercase tracking-wider">PTS</div>
          <div className="text-sm font-black italic text-white">{team.points}</div>
        </div>

        <div>
          <div className="text-[11px] text-slate-500 uppercase tracking-wider">WINS</div>
          <div className="text-sm font-black italic text-f1">{team.wins}</div>
        </div>
      </div>
    </div>
  );
}

export default TeamCard;
