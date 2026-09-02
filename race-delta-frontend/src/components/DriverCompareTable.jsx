function better(a, b, lowerIsBetter = false) {
  if (a == null || b == null || a === b) return null;
  return lowerIsBetter ? (a < b ? "A" : "B") : (a > b ? "A" : "B");
}

function format(val, digits = 3) {
  if (val == null) return "–";
  if (typeof val === "number") return Number.isInteger(val) ? String(val) : val.toFixed(digits);
  return val;
}

/* Phase 2: telemetry-derived features arrive under driver.features (see /api/compare/drivers) */
const FEATURE_ROWS = [
  ["Consistency σ (s)", "lap_consistency_s", true],
  ["Race Pace Trend (s/lap)", "race_pace_trend_s_per_lap", true],
  ["Tyre Degradation (s/lap)", "tyre_degradation_s_per_lap", true],
  ["Avg Stint Length (laps)", "avg_stint_length", false],
  ["Pit Stops", "pit_stop_count", true],
  ["Overtakes", "overtake_count", false],
  ["Positions Gained", "position_changes", false],
  ["Penalties", "penalties", true],
];

export default function DriverCompareTable({ aCode, bCode, a, b }) {
  if (!a || !b) return null;

  const rows = [
    ["Avg Lap (s)", a.avg_lap_time, b.avg_lap_time, true],
    ["Best Lap (s)", a.best_lap_time, b.best_lap_time, true],
    ["Laps", a.laps, b.laps, false],
  ];

  const hasFeatures = Boolean(a.features && b.features);
  const featureRows = hasFeatures
    ? FEATURE_ROWS.map(([label, key, lib]) => [label, a.features[key], b.features[key], lib])
    : [];

  const renderRow = ([label, av, bv, lib]) => {
    const win = better(av, bv, lib);
    return (
      <tr key={label} className="border-t border-gray-700">
        <td className="p-3">{label}</td>
        <td className={`p-3 text-center ${win === "A" ? "text-green-400" : ""}`}>{format(av)}</td>
        <td className={`p-3 text-center ${win === "B" ? "text-green-400" : ""}`}>{format(bv)}</td>
      </tr>
    );
  };

  return (
    <table className="w-full text-sm border border-gray-700 rounded-lg overflow-hidden">
      <thead className="bg-gray-800">
        <tr>
          <th className="p-3 text-left">Metric</th>
          <th className="p-3 text-center">{aCode}</th>
          <th className="p-3 text-center">{bCode}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(renderRow)}
        {hasFeatures && (
          <tr className="border-t border-gray-700 bg-gray-800/60">
            <td colSpan={3} className="p-2 text-xs uppercase tracking-wide text-gray-400">
              Telemetry features · {a.features.event || "latest race"}
            </td>
          </tr>
        )}
        {featureRows.map(renderRow)}
      </tbody>
    </table>
  );
}
