import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, Cell, CartesianGrid } from "recharts";

/* Season timeline for two drivers: cumulative points per round and the head-to-head count. */
const COLORS = ["#ff1801", "#38bdf8"];
const AXIS = { fontSize: 12, fill: "#b4b7bf" };
const TIP = { background: "#0d0f11", border: "1px solid #22272c" };

export default function CompareCharts({ data, driver1, driver2 }) {
  if (!data || !data.rounds || data.rounds.length === 0) {
    return <div className="panel panel-plain p-4 text-muted">No season timeline available yet.</div>;
  }

  const pointsOverSeason = data.rounds.map((r) => ({
    round: r.round,
    [driver1]: r.cumulative[driver1],
    [driver2]: r.cumulative[driver2],
  }));
  const headToHead = [
    { name: driver1, wins: data.head_to_head[driver1] || 0 },
    { name: driver2, wins: data.head_to_head[driver2] || 0 },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6" data-tour="compare-charts">
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="panel-title">Points over the season</h2>
            <p className="panel-subtitle">Cumulative championship points by round</p>
          </div>
        </div>
        <div className="panel-body h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={pointsOverSeason} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="round" tick={AXIS} stroke="#22272c" />
              <YAxis tick={AXIS} stroke="#22272c" width={44} />
              <Tooltip contentStyle={TIP} labelFormatter={(l) => `Round ${l}`} />
              <Legend />
              <Line type="monotone" dataKey={driver1} stroke={COLORS[0]} strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey={driver2} stroke={COLORS[1]} strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="panel-title">Season head-to-head</h2>
            <p className="panel-subtitle">Races finished ahead of the other driver</p>
          </div>
        </div>
        <div className="panel-body h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={headToHead} layout="vertical" margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" horizontal={false} />
              <XAxis type="number" allowDecimals={false} tick={AXIS} stroke="#22272c" />
              <YAxis dataKey="name" type="category" tick={{ ...AXIS, fontSize: 14, fontWeight: 700 }} stroke="#22272c" width={56} />
              <Tooltip contentStyle={TIP} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
              <Bar dataKey="wins" isAnimationActive={false} barSize={38} label={{ position: "right", fill: "#fff", fontSize: 14, fontWeight: 700 }}>
                {headToHead.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
