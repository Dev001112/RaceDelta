export default function DriverSelect({ label, drivers, value, onChange }) {
  return (
    <div className="flex flex-col gap-2">
      <label className="eyebrow">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="select-broadcast w-full h-[52px]" aria-label={label}>
        <option value="">Select driver</option>
        {drivers.map((d) => (
          <option key={d.code} value={d.code}>
            {d.number ? `${d.number} · ` : ""}{d.name}{d.team ? ` (${d.team})` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
