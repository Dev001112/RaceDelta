import React from 'react'

export default function Hero(){
  return (
    <section className="bg-gradient-to-r from-white to-slate-50 p-6 rounded-lg mb-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-primary">RaceDelta</h1>
          <p className="mt-2 text-gray-600 max-w-xl">Minimal F1 analytics — fast insights, lap deltas, telemetry summaries and driver comparisons.</p>
        </div>
        <div className="w-full md:w-1/2">
          <input placeholder="Search drivers, races, teams..." className="w-full px-4 py-3 border rounded-md" />
        </div>
      </div>
    </section>
  )
}
