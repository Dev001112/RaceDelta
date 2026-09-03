function better(a, b, lowerIsBetter = false) {
  if (a == null || b == null || a === b) return null;
  return lowerIsBetter ? (a < b ? "A" : "B") : (a > b ? "A" : "B");
}

function format(val, digits = 3) {
  if (val == null) return "–";
  if (typeof val === "number") return Number.isInteger(val) ? String(val) : val.toFixed(digits);
  return val;
}

/* Telemetry-derived features arrive under driver.features (see /api/compare/drivers). Green = better value. */
const FEATURE_ROWS = [
  ["Consistency σ (s)", "lap_consistency_s", true],
  ["Race pace trend (s/lap)", "race_pace_trend_s_per_lap", true],
  ["Tyre degradation (s/lap)", "tyre_degradation_s_per_lap", true],
  ["Avg stint length (laps)", "avg_stint_length", false],
  ["Pit stops", "pit_stop_count", true],
  ["Overtakes", "overtake_count", false],
  ["Positions gained", "position_changes", false],
  ["Penalties", "penalties", true],
];

export default function DriverCompareTable({ aCode, bCode, a, b, title = "Head-to-head", subtitle, tourId = "compare-table" }) {
  if (!a || !b) return null;

  const rows = [
    ["Avg lap (s)", a.avg_lap_time, b.avg_lap_time, true],
    ["Best lap (s)", a.best_lap_time, b.best_lap_time, true],
    ["Laps", a.laps, b.laps, false],
  ];
  const hasFeatures = Boolean(a.features && b.features);
  const featureRows = hasFeatures ? FEATURE_ROWS.map(([label, key, lib]) => [label, a.features[key], b.features[key], lib]) : [];

  const renderRow = ([label, av, bv, lib]) => {
    const win = better(av, bv, lib);
    return (
      <tr key={label}>
        <td>{label}</td>
        <td className={`num font-broadcast font-bold text-lg ${win === "A" ? "text-good" : "text-white"}`}>{format(av)}</td>
        <td className={`num font-broadcast font-bold text-lg ${win === "B" ? "text-good" : "text-white"}`}>{format(bv)}</td>
      </tr>
    );
  };

  return (
    <section className="panel" data-tour={tourId}>
      <div className="panel-head">
        <div>
          <h2 className="panel-title">{title}</h2>
          <p className="panel-subtitle">{subtitle ?? `${a.features?.event ? `${a.features.event} · ` : ""}green marks the better value`}</p>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="timing-table">
          <thead>
            <tr><th>Metric</th><th className="num">{aCode}</th><th className="num">{bCode}</th></tr>
          </thead>
          <tbody>
            {rows.map(renderRow)}
            {hasFeatures && (
              <tr>
                <td colSpan={3} className="bg-raised">
                  <span className="eyebrow eyebrow-ai">Telemetry features · from the feature store</span>
                </td>
              </tr>
            )}
            {featureRows.map(renderRow)}
          </tbody>
        </table>
      </div>
    </section>
  );
}
