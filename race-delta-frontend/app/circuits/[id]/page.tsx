'use client'
import React from 'react'
import useSWR from 'swr'
import { getApiBase } from '../../../lib/api'

const fetcher = (u:string)=>fetch(u).then(r=>r.json())

export default function CircuitPage({ params }: any){
  const id = params.id
  const [base, setBase] = React.useState<string|null>(null)
  React.useEffect(()=>{ getApiBase().then(b=>setBase(b)) },[])
  const { data } = useSWR(base ? `${base}/circuits/${id}` : null, fetcher, { refreshInterval: 60000 })
  return (
    <main className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Circuit — {id}</h1>
      <pre className="bg-slate-100 p-4 rounded">{JSON.stringify(data ?? {message: 'no data'}, null, 2)}</pre>
    </main>
  )
}
