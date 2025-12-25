export default function HeadToHeadBar({
  headToHead,
  driver1,
  driver2
}) {
  const total =
    headToHead[driver1] + headToHead[driver2];

  const p1 =
    (headToHead[driver1] / total) * 100;
  const p2 =
    (headToHead[driver2] / total) * 100;

  return (
    <div className="bg-[#0f172a] rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-4">
        Season Head-to-Head
      </h3>

      <div className="space-y-4">
        <div>
          <div className="flex justify-between mb-1">
            <span>{driver1}</span>
            <span>{headToHead[driver1]}</span>
          </div>
          <div className="h-3 bg-[#020617] rounded-full overflow-hidden">
            <div
              className="h-full bg-red-500 transition-all duration-700"
              style={{ width: `${p1}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between mb-1">
            <span>{driver2}</span>
            <span>{headToHead[driver2]}</span>
          </div>
          <div className="h-3 bg-[#020617] rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 transition-all duration-700"
              style={{ width: `${p2}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
