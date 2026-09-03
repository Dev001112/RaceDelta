import React from 'react'

export default function Footer() {
  return (
    <footer className="mt-10 border-t border-line">
      <div className="container py-6 text-muted text-sm flex flex-wrap justify-between gap-2">
        <div>© {new Date().getFullYear()} RaceDelta</div>
        <div>AI-powered Formula 1 intelligence · built on FastF1, OpenF1 and Ergast data</div>
      </div>
    </footer>
  )
}
