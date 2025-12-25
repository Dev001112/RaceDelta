import React from 'react'

export default function FeaturedRaceCard({race}){
  return (
    <div className="card hover:shadow-md transition animate-fade-in-up">
      <div className="flex items-center gap-4">
        <div className="w-16 h-12 img-placeholder overflow-hidden rounded">
          <img src={race.flag} alt="flag" className="w-full h-full object-cover" />
        </div>
        <div>
          <div className="text-xs muted">{race.location} — {race.date}</div>
          <div className="mt-1 font-semibold">{race.title}</div>
          <div className="mt-2 muted text-sm">Winner: <span className="accent">{race.winner}</span></div>
        </div>
      </div>
    </div>
  )
}
