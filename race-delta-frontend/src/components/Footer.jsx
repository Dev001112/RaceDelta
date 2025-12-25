import React from 'react'

export default function Footer(){
  return (
    <footer className="mt-8">
      <div className="container py-6 muted text-sm flex justify-between">
        <div>© {new Date().getFullYear()} RaceDelta</div>
        <div>Minimal F1 analytics</div>
      </div>
    </footer>
  )
}
