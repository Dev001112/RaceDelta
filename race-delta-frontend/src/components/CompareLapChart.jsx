import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, ReferenceArea } from "recharts";

/* Lap-by-lap race pace for two drivers. Pit laps are left out, safety-car windows are shaded. */
const COLORS = { a: "#ff1801", b: "#38bdf8" };

export default function CompareLapChart({ laps, codes, event }) {
  if (!laps || !codes) return null;
  const la = laps[codes.a] || [];
  const lb = laps[codes.b] || [];
  if (!la.length && !lb.length) {
    return <div className="panel panel-plain p-4 text-muted">No lap data stored for this race.</div>;
  }

  const byLap = new Map();
  const put = (rows, key) => rows.forEach((l) => {
    const row = byLap.get(l.lap) || { lap: l.lap };
    row[key] = l.pit ? null : l.lap_time_s;
    row.sc = row.sc || l.sc;
    row.vsc = row.vsc || l.vsc;
    byLap.set(l.lap, row);
  });
  put(la, codes.a);
  put(lb, codes.b);
  const data = [...byLap.values()].sort((x, y) => x.lap - y.lap);

  // contiguous SC / VSC windows
  const bands = [];
  let cur = null;
  data.forEach((d) => {
    const kind = d.sc ? "SC" : d.vsc ? "VSC" : null;
    if (kind && cur && cur.kind === kind && cur.to === d.lap - 1) cur.to = d.lap;
    else if (kind) { cur = { kind, from: d.lap, to: d.lap }; bands.push(cur); }
    else cur = null;
  });

  // y-axis: keep the racing laps readable, let SC laps run off the top
  const times = data.flatMap((d) => [d[codes.a], d[codes.b]]).filter((v) => v != null).sort((x, y) => x - y);
  const yMin = times.length ? Math.floor(times[0] - 0.5) : "auto";
  const yMax = times.length ? Math.ceil(times[Math.floor(times.length * 0.9)] + 2) : "auto";
  const pits = { [codes.a]: la.filter((l) => l.pit).map((l) => l.lap), [codes.b]: lb.filter((l) => l.pit).map((l) => l.lap) };

  return (
    <section className="panel" data-tour="compare-laps">
      <div className="panel-head">
        <div>
          <h2 className="panel-title">Lap by lap</h2>
          <p className="panel-subtitle">{event} · pit laps left out · yellow bands are safety car, grey are virtual safety car</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(pits).map(([c, ls]) => <span key={c} className="chip">{c} pit in/out laps: {ls.length ? ls.join(", ") : "none"}</span>)}
        </div>
      </div>
      <div className="panel-body h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 16, bottom: 4, left: 0 }}>
            {bands.map((bnd, i) => (
              <ReferenceArea key={i} x1={bnd.from} x2={bnd.to} fill={bnd.kind === "SC" ? "#facc15" : "#9ca3af"} fillOpacity={0.14} />
            ))}
            <XAxis dataKey="lap" tick={{ fontSize: 12, fill: "#b4b7bf" }} stroke="#22272c" />
            <YAxis domain={[yMin, yMax]} allowDataOverflow tick={{ fontSize: 12, fill: "#b4b7bf" }} stroke="#22272c" width={56}
                   tickFormatter={(v) => Number(v).toFixed(1)} />
            <Tooltip contentStyle={{ background: "#0d0f11", border: "1px solid #22272c" }}
                     formatter={(v) => (v == null ? "–" : `${Number(v).toFixed(3)}s`)} labelFormatter={(l) => `Lap ${l}`} />
            <Legend />
            <Line type="monotone" dataKey={codes.a} stroke={COLORS.a} strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
            <Line type="monotone" dataKey={codes.b} stroke={COLORS.b} strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
