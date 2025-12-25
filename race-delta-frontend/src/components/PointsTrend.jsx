import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer
} from "recharts";

export default function PointsTrend({ pointsByRace }) {
  const data = pointsByRace.map((r) => ({
    round: r.round,
    points: r.points
  }));

  return (
    <>
      {/* TITLE */}
      <h3 style={{ marginBottom: 4 }}>Points Over Season</h3>

      {/* SUBTITLE */}
      <p
        style={{
          fontSize: 12,
          color: "#9CA3AF",
          marginBottom: 12
        }}
      >
        Race-by-race consistency and volatility
      </p>

      {/* CHART */}
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid stroke="rgba(255,255,255,0.08)" />
          <XAxis
            dataKey="round"
            stroke="#9CA3AF"
            tick={{ fontSize: 11 }}
          />
          <YAxis
            stroke="#9CA3AF"
            tick={{ fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              background: "#0F1522",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 8,
              color: "#E5E7EB"
            }}
          />
          <Line
            type="monotone"
            dataKey="points"
            stroke="#38BDF8"
            strokeWidth={2.5}
            dot={{ r: 3, fill: "#38BDF8" }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </>
  );
}
