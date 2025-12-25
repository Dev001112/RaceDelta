'use client'
import React, { useEffect, useState } from 'react'
import LiveLeaderboard from '../components/LiveLeaderboard'
import PodiumWidget from '../components/PodiumWidget'
import CircuitInfo from '../components/CircuitInfo'
import StandingsTable from '../components/StandingsTable'
import SessionSelector from '../components/SessionSelector'
import useSWR from 'swr'
import { getApiBase } from '../lib/api'

const fetcher = (u: string) => fetch(u).then(r => r.json())

export default function Page() {
  const [apiBase, setApiBase] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    getApiBase().then(base => { if (mounted) setApiBase(base) })
    return () => { mounted = false }
  }, [])

  const sessionsUrl = apiBase ? `${apiBase}/sessions` : null
  const { data: meta } = useSWR(sessionsUrl, fetcher, { refreshInterval: 15000 })

  const [sessionId, setSessionId] = useState<string | undefined>(() => undefined)

  useEffect(() => {
    if (meta?.sessions?.length && !sessionId) {
      setSessionId(meta.sessions[0].id)
    }
  }, [meta, sessionId])

  const resultsUrl = apiBase && sessionId ? `${apiBase}/session/${sessionId}/results` : null
  const { data: results } = useSWR(resultsUrl, fetcher, { refreshInterval: 4000 })

  const podium = results ? results.slice(0,3).map((r:any)=>({ name: r.name || r.driver, team: r.team, time: r.time })) : []
  const circuit = meta?.currentCircuit ?? null
  const standings = meta?.standings ?? []

  return (
    <main className="container mx-auto p-6 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">RaceDelta — Live</h1>
        <div>
          <SessionSelector sessions={meta?.sessions ?? []} value={sessionId} onChange={(id)=>setSessionId(id)} />
        </div>
      </header>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <LiveLeaderboard sessionId={sessionId} apiBase={apiBase} />
        </div>

        <aside className="space-y-4">
          <PodiumWidget podium={podium} />
          <CircuitInfo circuit={circuit} />
        </aside>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Standings</h2>
        <StandingsTable standings={standings} />
      </section>
    </main>
  )
}
