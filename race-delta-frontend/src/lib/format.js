// Race classification time column: P1 shows the race time (h:mm:ss.sss), everyone else the gap.
export function formatDuration(seconds, position, gap) {
  if (position === 1) {
    if (!seconds) return "FINISHED";
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = (seconds % 60).toFixed(3);
    return hrs > 0 ? `${hrs}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(6, "0")}` : `${mins}:${secs.toString().padStart(6, "0")}`;
  }
  if (gap === 0 || gap === "0") return "FINISHED";
  if (typeof gap === "number") return `+${gap.toFixed(3)}s`;
  if (String(gap).includes("Lap")) return gap;
  return gap ? (String(gap).startsWith("+") ? gap : `+${gap}`) : "FINISHED";
}
