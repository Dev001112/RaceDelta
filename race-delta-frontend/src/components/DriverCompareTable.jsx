function better(a, b, lowerIsBetter = false) {
  if (a == null || b == null) return null;
  return lowerIsBetter ? (a < b ? "A" : "B") : (a > b ? "A" : "B");
}

function format(val) {
  if (val == null) return "–";
  if (typeof val === "number") return val.toFixed(3);
  return val;
}

export default function DriverCompareTable({ aCode, bCode, a, b }) {
  if (!a || !b) return null;

  const rows = [
    ["Avg Lap (s)", a.avg_lap_time, b.avg_lap_time, true],
    ["Best Lap (s)", a.best_lap_time, b.best_lap_time, true],
    ["Laps", a.laps, b.laps, false],
  ];

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
        {rows.map(([label, av, bv, lib]) => {
          const win = better(av, bv, lib);
          return (
            <tr key={label} className="border-t border-gray-700">
              <td className="p-3">{label}</td>
              <td className={`p-3 text-center ${win === "A" ? "text-green-400" : ""}`}>
                {format(av)}
              </td>
              <td className={`p-3 text-center ${win === "B" ? "text-green-400" : ""}`}>
                {format(bv)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
