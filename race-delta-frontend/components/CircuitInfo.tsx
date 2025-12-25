import React from 'react'

export default function CircuitInfo({ circuit }: any) {
  if (!circuit) return (
    <aside className="p-4 rounded-xl border shadow-sm">
      <div className="text-sm text-slate-500">No circuit data available.</div>
    </aside>
  )
  const { name, location, country, lengthKm, lapRecord, turns, imageUrl } = circuit
  return (
    <aside className="p-4 rounded-xl border shadow-sm">
      <div className="flex gap-4">
        <img src={imageUrl ?? '/images/circuits/default.jpg'} alt={`${name} circuit`} className="w-32 h-20 rounded-md object-cover" loading="lazy" />
        <div>
          <h3 className="text-lg font-semibold">{name}</h3>
          <div className="text-xs text-slate-600">{location}{country ? `, ${country}` : ''}</div>
          <div className="mt-2 text-sm">Length: {lengthKm ?? '—'} km • Turns: {turns ?? '—'}</div>
          {lapRecord && <div className="mt-1 text-xs text-slate-500">Lap record: {lapRecord.driver} — {lapRecord.time} ({lapRecord.year})</div>}
        </div>
      </div>
    </aside>
  )
}
