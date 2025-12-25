import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar
} from "recharts";


export default function CompareCharts({ data, driver1, driver2 }) {
  if (!data || !data.rounds || data.rounds.length === 0) {
    return (
      <div className="bg-[#0b1220] rounded-xl p-6 text-gray-400">
        No chart data available
      </div>
    );
  }

  /* ---------------------------------------------
     Points over season (derived)
  --------------------------------------------- */
  const pointsOverSeason = data.rounds.map((r) => ({
    round: r.round,
    [driver1]: r.cumulative[driver1],
    [driver2]: r.cumulative[driver2]
  }));

  /* ---------------------------------------------
     Head to head (derived)
  --------------------------------------------- */
  const headToHead = [
    {
      name: driver1,
      wins: data.head_to_head[driver1] || 0
    },
    {
      name: driver2,
      wins: data.head_to_head[driver2] || 0
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

      {/* Points Over Season */}
      <div className="bg-[#0b1220] rounded-xl p-6 shadow-lg">
        <h3 className="font-semibold mb-4">
          Points Over Season
        </h3>

        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={pointsOverSeason}>
            <XAxis dataKey="round" />
            <YAxis />
            <Tooltip />
            <Line
              type="monotone"
              dataKey={driver1}
              stroke="#22c55e"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey={driver2}
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Head to Head */}
      <div className="bg-[#0b1220] rounded-xl p-6 shadow-lg">
        <h3 className="font-semibold mb-4">
          Season Head-to-Head
        </h3>

        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={headToHead} layout="vertical">
            <XAxis type="number" />
            <YAxis dataKey="name" type="category" />
            <Tooltip />
            <Bar dataKey="wins" fill="#38bdf8" />
          </BarChart>
        </ResponsiveContainer>
      </div>

    </div>
  );
}
