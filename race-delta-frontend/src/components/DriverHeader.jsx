export default function DriverHeader({ driver, season, points, position }) {
  return (
    <div className="flex items-center gap-5">
      {driver.image
        ? <img src={driver.image} alt={driver.name} className="w-20 h-20 object-contain bg-raised border border-line" />
        : <div className="w-20 h-20 flex items-center justify-center bg-raised border border-line font-broadcast font-black text-white text-2xl">{driver.code}</div>}
      <div className="min-w-0">
        <h2 className="font-broadcast font-black italic uppercase text-white text-2xl leading-tight truncate">{driver.name || driver.code}</h2>
        <div className="text-muted">{driver.team || "–"}</div>
        <div className="flex flex-wrap gap-2 mt-2">
          <span className="chip">Season {season}</span>
          {Number.isFinite(position) && <span className="chip chip-live">P{position}</span>}
          {Number.isFinite(points) && <span className="chip">{points} pts</span>}
        </div>
      </div>
    </div>
  );
}
