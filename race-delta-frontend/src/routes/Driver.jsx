import React from 'react'
import { useParams } from 'react-router-dom'

export default function Driver(){
  const { driverId } = useParams()
  return (
    <div className="grid md:grid-cols-3 gap-6">
      <div className="md:col-span-2">
        <h1 className="text-2xl font-semibold mb-2">Driver: {driverId}</h1>
        <p className="muted text-sm mb-4">Profile, season form, lap comparison charts.</p>
        <div className="card">Detailed stats and charts will appear here.</div>
      </div>
      <aside className="card">
        <div className="flex flex-col items-center gap-4">
          <img src="/src/assets/drivers/ver.svg" alt="photo" className="w-36 h-36 rounded-full object-cover" />
          <div className="text-lg font-semibold">Max Verstappen</div>
          <div className="muted text-sm">Red Bull Racing</div>
        </div>
      </aside>
    </div>
  )
}
