import DriverCompareTable from "./DriverCompareTable";
import CompareInsight from "./CompareInsight";
import TrackMap from "./TrackMap";

/*
  One set of races (a track's visits, or every race under a condition) for two drivers:
  aggregate tiles, the averaged head-to-head table, and the race-by-race breakdown behind it.
*/

const fmt = (v, d = 3) => (v == null ? "–" : Number.isInteger(v) ? String(v) : Number(v).toFixed(d));
const signed = (v, d = 3) => (v == null ? "–" : `${v > 0 ? "+" : ""}${fmt(v, d)}s`);
export const finishLabel = (r) => (!r ? "–" : r.finish_position != null ? `P${r.finish_position}` : r.status || "DNF");
export const tableSide = (m) => ({ avg_lap_time: m.avg_pace_s, best_lap_time: m.best_lap_s, laps: m.total_laps, features: m });

export function ConditionChips({ r }) {
  return (
    <span className="inline-flex flex-wrap gap-1">
      <span className={`chip ${r.wet ? "chip-warn" : ""}`}>{r.wet ? "Wet" : "Dry"}</span>
      {r.safety_car && <span className="chip chip-warn">SC · {r.sc_laps} laps</span>}
      {r.virtual_safety_car && <span className="chip">VSC</span>}
      {r.hot && <span className="chip">Hot · {fmt(r.avg_track_temp, 0)}°C</span>}
      {r.cool && <span className="chip">Cool · {fmt(r.avg_track_temp, 0)}°C</span>}
    </span>
  );
}

export function Tile({ label, value, sub, good }) {
  return (
    <div className="stat-tile">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={good ? { color: "#22c55e" } : undefined}>{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function Cell({ row, won }) {
  if (!row) return <td className="num text-muted">no data</td>;
  return (
    <td className="num">
      <div className="font-broadcast font-bold text-lg" style={won ? { color: "#22c55e" } : undefined}>{finishLabel(row)}</div>
      <div className="text-muted text-sm">grid {row.grid_position ?? "–"} · {row.points ?? 0} pts</div>
    </td>
  );
}

export default function RaceSetComparison({ data, title, subtitle, mapCandidates }) {
  if (!data) return null;
  const { codes, aggregate: agg, races } = data;
  const a = codes.a, b = codes.b;
  const n = agg.races_compared;
  const delta = agg.avg_pace_delta_s;
  const paceLeader = delta == null || delta === 0 ? null : delta < 0 ? a : b;

  return (
    <div className="space-y-6">
      {n > 0 ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Tile label="Races compared" value={n} sub={`${races.length} in the set`} />
            <Tile label="Head-to-head" value={`${agg.wins[a]} – ${agg.wins[b]}`} sub={`${a} – ${b}${agg.wins.tie ? ` · ${agg.wins.tie} tied` : ""}`} />
            <Tile label="Avg pace delta" value={signed(delta)} sub={paceLeader ? `${paceLeader} faster per lap on average` : "level on average"} good={Boolean(paceLeader)} />
            <Tile label="Points in the set" value={`${fmt(agg.a.points, 0)} · ${fmt(agg.b.points, 0)}`} sub={`${a} · ${b}`} />
          </div>
          {mapCandidates?.length > 0 && <TrackMap candidates={mapCandidates} event={mapCandidates[0].track || mapCandidates[0].event} codes={codes} a={agg.a} b={agg.b} perRace={races} />}
          <CompareInsight driver1={a} driver2={b} races={races} context={title} a={agg.a} b={agg.b} perRace={races} />
          <DriverCompareTable aCode={a} bCode={b} a={tableSide(agg.a)} b={tableSide(agg.b)} title={title} subtitle={subtitle} />
        </>
      ) : (
        <div className="panel panel-plain p-6 text-center text-muted">
          No race in this set has telemetry for both drivers yet.
        </div>
      )}

      <section className="panel" data-tour="compare-breakdown">
        <div className="panel-head">
          <div>
            <h2 className="panel-title">Race by race</h2>
            <p className="panel-subtitle">Pace Δ is {a} minus {b} on average lap time: negative means {a} was faster.</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="timing-table">
            <thead>
              <tr><th>Race</th><th>Conditions</th><th className="num">{a}</th><th className="num">{b}</th><th className="num">Pace Δ</th><th>Winner</th></tr>
            </thead>
            <tbody>
              {races.map((r) => (
                <tr key={`${r.season}-${r.round}`}>
                  <td>
                    <div className="font-broadcast font-black uppercase text-white">{r.event}</div>
                    <div className="text-muted text-sm">{r.season} · R{r.round}{r.total_laps ? ` · ${r.total_laps} laps` : ""}</div>
                  </td>
                  <td><ConditionChips r={r} /></td>
                  <Cell row={r.a} won={r.winner === "A"} />
                  <Cell row={r.b} won={r.winner === "B"} />
                  <td className="num font-broadcast font-bold text-white">{signed(r.pace_delta_s)}</td>
                  <td className="font-broadcast font-black text-white">
                    {r.winner === "A" ? a : r.winner === "B" ? b : r.a && r.b ? "Tie" : "–"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
