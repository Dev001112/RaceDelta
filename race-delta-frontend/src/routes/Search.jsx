import React from 'react'
import { useLocation, Link } from 'react-router-dom'

function useQuery(){
  return new URLSearchParams(useLocation().search)
}

export default function Search(){
  const q = useQuery().get('q') || ''
  return (
    <div>
      <h1 className="text-2xl font-semibold">Search results for "{q}"</h1>
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
        <Link to="/driver/VER" className="block"><div className="card p-3">Max Verstappen — Driver</div></Link>
        <Link to="/race/2025/1" className="block"><div className="card p-3">2025 Abu Dhabi GP — Race</div></Link>
      </div>
    </div>
  )
}
