export default function DriverSelect({
  label,
  drivers,
  value,
  onChange
}) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm text-gray-400">
        {label}
      </label>

      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-[#0f172a] border border-gray-700 rounded-lg p-3 text-white"
      >
        <option value="">Select driver</option>

        {drivers.map((d) => (
          <option key={d.code} value={d.code}>
            {d.name}
          </option>
        ))}
      </select>
    </div>
  );
}
