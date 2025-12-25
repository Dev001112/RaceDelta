import React from 'react'

type Session = { id: string; name: string; time?: string; type?: string }

export default function SessionSelector({
  sessions,
  value,
  onChange,
}: {
  sessions: Session[];
  value?: string;
  onChange: (id: string) => void;
}) {
  return (
    <label className="inline-flex items-center gap-2">
      <span className="sr-only">Select session</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border px-3 py-2 text-sm"
        aria-label="Select session"
      >
        {sessions.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name} {s.time ? `— ${new Date(s.time).toLocaleString()}` : ''}
          </option>
        ))}
      </select>
    </label>
  )
}
