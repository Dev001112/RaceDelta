export default function DriverCompareCard({ code, data, highlight }) {
  return (
    <div
      className={`rounded-xl p-4 border ${
        highlight ? "border-green-500" : "border-gray-700"
      } bg-[#0f172a]`}
    >
      <h2 className="text-xl font-bold mb-2">{code}</h2>

      <ul className="space-y-1 text-sm">
        <li>Points: <strong>{data.points}</strong></li>
        <li>Wins: <strong>{data.wins}</strong></li>
        <li>Podiums: <strong>{data.podiums}</strong></li>
        <li>Avg Finish: <strong>{data.avg_finish}</strong></li>
        <li>DNFs: <strong>{data.dnf}</strong></li>
        <li>Avg Lap Time: <strong>{data.avg_lap_time}s</strong></li>
      </ul>
    </div>
  );
}
