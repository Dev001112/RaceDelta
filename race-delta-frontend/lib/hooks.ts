'use client'
import useSWR from 'swr'
import { fetcher } from './api'

export function useLiveLeaderboard(sessionId?: string, apiBase?: string, opts?: { refreshInterval?: number }) {
  const url = sessionId && apiBase ? `${apiBase}/session/${sessionId}/live` : null
  return useSWR(url, fetcher, { refreshInterval: opts?.refreshInterval ?? 3000 })
}

export function useSessionResults(sessionId?: string, apiBase?: string) {
  const url = sessionId && apiBase ? `${apiBase}/session/${sessionId}/results` : null
  return useSWR(url, fetcher, { refreshInterval: 4000 })
}
