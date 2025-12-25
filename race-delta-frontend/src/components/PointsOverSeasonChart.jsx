import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from "recharts";

export default function PointsOverSeasonChart({
  rounds,
  driver1,
  driver2
}) {
  const data = rounds.map((r) => ({
    round: r.round,
    [driver1]: r.cumulative[driver1],
    [driver2]: r.cumulative[driver2]
  }));

  return (
    <div className="bg-[#0f172a] rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-4">
        Points Over Season
      </h3>

      <div className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis
              dataKey="round"
              tick={{ fill: "#9ca3af" }}
            />
            <YAxis tick={{ fill: "#9ca3af" }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#020617",
                border: "1px solid #1e293b"
              }}
            />
            <Line
              type="monotone"
              dataKey={driver1}
              stroke="#ef4444"
              strokeWidth={3}
              dot={false}
              isAnimationActive
            />
            <Line
              type="monotone"
              dataKey={driver2}
              stroke="#22c55e"
              strokeWidth={3}
              dot={false}
              isAnimationActive
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
