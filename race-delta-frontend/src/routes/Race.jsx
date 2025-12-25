import React from 'react'
import { useParams } from 'react-router-dom'

export default function Race(){
  const { season, round } = useParams()
  return (
    <div>
      <h1 className="text-2xl font-semibold">Race: {season} — Round {round}</h1>
      <p className="muted text-sm mt-2">Summary, results table, lap delta visualizations will go here.</p>
    </div>
  )
}
