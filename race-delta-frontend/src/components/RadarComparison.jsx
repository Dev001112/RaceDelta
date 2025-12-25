import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer
} from "recharts";

/**
 * Display labels for radar axes
 * Keys MUST match backend radar schema
 */
const LABELS = {
  consistency: "Consistency",
  points_efficiency: "Points",
  racecraft: "Racecraft",
  reliability: "Reliability",
  winning_impact: "Impact"
};

export default function RadarComparison({ radar = {} }) {
  /**
   * Normalize + sanitize radar data
   * Ensures:
   * - No NaN
   * - No undefined
   * - Always numeric [0–100]
   */
  const data = Object.keys(LABELS).map((key) => {
    const raw = Number(radar[key]);
    return {
      metric: key,
      value: Number.isFinite(raw) ? raw : 0
    };
  });

  return (
    <ResponsiveContainer width="100%" height="100%">
      <RadarChart
        data={data}
        outerRadius={85}
        margin={{ top: 12, right: 24, bottom: 12, left: 24 }}
      >
        {/* Grid */}
        <PolarGrid stroke="rgba(255,255,255,0.15)" />

        {/* Axis labels */}
        <PolarAngleAxis
          dataKey="metric"
          tickFormatter={(v) => LABELS[v] || v}
          tick={{
            fill: "#9CA3AF",
            fontSize: 11,
            fontWeight: 500
          }}
        />

        {/* Radius */}
        <PolarRadiusAxis
          domain={[0, 100]}
          tick={false}
          axisLine={false}
        />

        {/* Driver radar */}
        <Radar
          dataKey="value"
          stroke="#EF4444"
          fill="#EF4444"
          fillOpacity={0.32}
          strokeWidth={2}
          isAnimationActive={false}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
