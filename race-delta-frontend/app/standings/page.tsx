'use client'
import React from 'react'
import StandingsTable from '../../components/StandingsTable'
import useSWR from 'swr'
import { getApiBase } from '../../lib/api'

const fetcher = (u:string)=>fetch(u).then(r=>r.json())

export default function StandingsPage(){
  const [base, setBase] = React.useState<string|null>(null)
  React.useEffect(()=>{ getApiBase().then(b=>setBase(b)) },[])
  const { data } = useSWR(base ? `${base}/standings/current` : null, fetcher, { refreshInterval: 60000 })
  return (
    <main className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Standings</h1>
      <StandingsTable standings={data ?? []} />
    </main>
  )
}
