import { TEAM_LOGOS } from "../lib/teamLogos";

function DriverPanel({ driver }) {
  return (
    <div className="panel panel-plain p-3 flex items-center gap-4 min-w-0">
      {driver.photo && <img src={driver.photo} alt={driver.name} className="w-14 h-14 object-contain bg-raised border border-line" />}
      <div className="min-w-0">
        <div className="font-broadcast font-black italic uppercase text-white text-lg truncate">{driver.name}</div>
        <div className="text-muted">{driver.team}</div>
      </div>
      {TEAM_LOGOS[driver.team] && <img src={TEAM_LOGOS[driver.team]} alt={driver.team} className="ml-auto h-10 hidden sm:block" />}
    </div>
  );
}

export default function CompareHeader({ leftDriver, rightDriver, onCompare, disabled }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-center">
      <DriverPanel driver={leftDriver} />
      {onCompare
        ? <button type="button" onClick={onCompare} disabled={disabled} className="btn-primary justify-center">Run comparison →</button>
        : <div className="font-broadcast font-black italic text-3xl text-f1 text-center px-2" aria-hidden="true">VS</div>}
      <DriverPanel driver={rightDriver} />
    </div>
  );
}
