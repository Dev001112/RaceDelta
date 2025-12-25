import React from 'react'

type Props = {
  driver: {
    id?: string | number;
    name: string;
    team?: string;
    number?: string | number;
    time?: string;
    gap?: string;
    position?: number;
    avatarUrl?: string;
  };
  compact?: boolean;
};

export default function DriverCard({ driver, compact = false }: Props) {
  return (
    <div className={`flex items-center gap-3 p-3 rounded-2xl shadow-sm border ${compact ? 'w-full' : 'max-w-sm'}`}>
      <img
        src={driver.avatarUrl || `/images/drivers/${driver.id || 'default'}.jpg`}
        alt={`${driver.name}`}
        className="w-12 h-12 rounded-full object-cover flex-none"
        loading="lazy"
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <div className="truncate">
            <div className="text-sm font-semibold leading-tight">{driver.name}</div>
            {driver.team && <div className="text-xs text-slate-500 truncate">{driver.team}</div>}
          </div>
          {driver.position && (
            <div className="ml-3 text-xs font-medium bg-slate-100 px-2 py-1 rounded-md">{driver.position}</div>
          )}
        </div>
        <div className="mt-1 text-xs text-slate-600 flex items-center gap-3">
          {driver.time && <span className="font-mono">{driver.time}</span>}
          {driver.gap && <span className="text-slate-500">+{driver.gap}</span>}
        </div>
      </div>
    </div>
  )
}
