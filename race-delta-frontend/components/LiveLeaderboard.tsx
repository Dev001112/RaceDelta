'use client'
import React from 'react'
import DriverCard from './DriverCard'
import { useLiveLeaderboard } from '../lib/hooks'

export default function LiveLeaderboard({ sessionId, apiBase }: { sessionId?: string, apiBase?: string }) {
  const { data, error, isLoading } = useLiveLeaderboard(sessionId, apiBase, { refreshInterval: 3000 })

  if (error) return <div className="p-4 text-red-600">Failed to load live leaderboard.</div>
  if (isLoading || !data) return <div className="p-6">Loading live leaderboard...</div>

  const drivers = data.drivers ?? data.results ?? []

  return (
    <section aria-labelledby="live-leaderboard" className="space-y-3">
      <h2 id="live-leaderboard" className="text-lg font-semibold">Live Leaderboard</h2>
      <div className="grid gap-2">
        {drivers.map((d: any, idx: number) => (
          <DriverCard
            key={d.id ?? d.driverId ?? idx}
            driver={{
              id: d.driverId ?? d.id ?? idx,
              name: d.name ?? `${d.givenName ?? ''} ${d.familyName ?? ''}`.trim() ?? d.driver,
              team: d.team ?? d.constructor,
              number: d.number ?? d.carNumber,
              time: d.bestTime ?? d.time,
              gap: d.gap,
              position: d.position ?? d.rank ?? idx + 1,
              avatarUrl: d.avatar,
            }}
          />
        ))}
      </div>
    </section>
  )
}
