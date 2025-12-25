import React from 'react';

export default function Filters({ season, onSeasonChange, onTeamChange }) {
  return (
    <div className="p-3 border rounded space-y-3">
      <div>
        <label className="text-sm text-gray-600 block">Season</label>
        <select
          value={season}
          onChange={(e) => onSeasonChange && onSeasonChange(e.target.value)}
          className="mt-1 w-full px-3 py-2 border rounded"
        >
          {Array.from({length:6}).map((_,i) => {
            const s = 2025 - i;
            return <option key={s} value={s}>{s}</option>;
          })}
        </select>
      </div>

      <div>
        <label className="text-sm text-gray-600 block">Team (optional)</label>
        <input onChange={(e)=> onTeamChange && onTeamChange(e.target.value)} placeholder="e.g. Red Bull" className="mt-1 w-full px-3 py-2 border rounded" />
      </div>
    </div>
  );
}
