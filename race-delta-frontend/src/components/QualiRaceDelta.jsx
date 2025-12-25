import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell
} from "recharts";

export default function QualiRaceDelta({ deltas }) {
  // Ensure clean numeric data
  const data = (deltas || []).map((d) => ({
    round: d.round,
    delta: Number(d.delta)
  }));

  return (
    <div>
      <h3 style={{ marginBottom: 4 }}>Qualifying → Race Delta</h3>
      <p style={{ fontSize: 12, color: "#9CA3AF", marginBottom: 12 }}>
        Positions gained or lost on race day
      </p>

      <div style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="round" />
            <YAxis />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.4)" />

            {/* Tooltip */}
            <Tooltip
              formatter={(value) => [`${value}`, "Position Change"]}
              labelFormatter={(label) => `Round ${label}`}
            />

            <Bar
              dataKey="delta"
              minPointSize={4}
              radius={[6, 6, 6, 6]}
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.delta < 0 ? "#EF4444" : "#22C55E"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
