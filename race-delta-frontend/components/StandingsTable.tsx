import React from 'react'

export default function StandingsTable({ standings }: { standings: any[] }) {
  if (!standings || standings.length === 0) return <div className="p-4">No standings available.</div>

  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="min-w-full divide-y">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs">Pos</th>
            <th className="px-4 py-2 text-left text-xs">Driver</th>
            <th className="px-4 py-2 text-left text-xs">Team</th>
            <th className="px-4 py-2 text-right text-xs">Points</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y">
          {standings.map((row: any, idx: number) => (
            <tr key={row.driverId ?? idx}>
              <td className="px-4 py-3">{row.position ?? idx + 1}</td>
              <td className="px-4 py-3">
                <div className="font-medium">{row.name ?? `${row.givenName ?? ''} ${row.familyName ?? ''}`.trim()}</div>
                <div className="text-xs text-slate-500">{row.number ? `#${row.number}` : ''}</div>
              </td>
              <td className="px-4 py-3">{row.team ?? row.constructor}</td>
              <td className="px-4 py-3 text-right font-mono">{row.points ?? '0'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
