import { TEAM_LOGOS } from "../lib/teamLogos";

export default function CompareHeader({
  leftDriver,
  rightDriver,
  onCompare,
  disabled
}) {
  return (
    <div className="grid grid-cols-[1fr_auto_1fr] gap-6 items-center">
      
      {/* LEFT DRIVER */}
      <div className="bg-[#0f172a] rounded-xl p-4 flex items-center gap-4">
        <img
          src={leftDriver.photo}
          alt={leftDriver.name}
          className="w-16 h-16 rounded-full object-cover"
        />

        <div>
          <h3 className="font-semibold">
            {leftDriver.name}
          </h3>
          <p className="text-sm text-gray-400">
            {leftDriver.team}
          </p>
        </div>

        {TEAM_LOGOS[leftDriver.team] && (
          <img
            src={TEAM_LOGOS[leftDriver.team]}
            alt={leftDriver.team}
            className="ml-auto h-10"
          />
        )}
      </div>

      {/* COMPARE BUTTON */}
      <button
        onClick={onCompare}
        disabled={disabled}
        className="bg-red-600 hover:bg-red-700 disabled:opacity-50 px-6 py-3 rounded-lg font-semibold"
      >
        COMPARE →
      </button>

      {/* RIGHT DRIVER */}
      <div className="bg-[#0f172a] rounded-xl p-4 flex items-center gap-4">
        <img
          src={rightDriver.photo}
          alt={rightDriver.name}
          className="w-16 h-16 rounded-full object-cover"
        />

        <div>
          <h3 className="font-semibold">
            {rightDriver.name}
          </h3>
          <p className="text-sm text-gray-400">
            {rightDriver.team}
          </p>
        </div>

        {TEAM_LOGOS[rightDriver.team] && (
          <img
            src={TEAM_LOGOS[rightDriver.team]}
            alt={rightDriver.team}
            className="ml-auto h-10"
          />
        )}
      </div>
    </div>
  );
}
