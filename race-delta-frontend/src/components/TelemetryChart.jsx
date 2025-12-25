// src/components/TelemetryChart.jsx
import React from "react";

export default function TelemetryChart({ data = { x: [], y: [] }, title = "" }) {
  const w = 600, h = 220, pad = 12;
  const xs = data.x;
  const ys = data.y;
  if (!ys || ys.length === 0) {
    return <div className="text-sm muted">No telemetry</div>;
  }
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const len = ys.length;
  const points = ys.map((v, i) => {
    const x = pad + (i / Math.max(1, len - 1)) * (w - pad * 2);
    const y = pad + ((maxY - v) / Math.max(1, maxY - minY)) * (h - pad * 2);
    return `${x},${y}`;
  }).join(" ");
  return (
    <div>
      <div className="font-medium mb-2">{title}</div>
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="xMidYMid meet">
        <polyline fill="none" stroke="#0ea5a7" strokeWidth="2" points={points} />
      </svg>
      <div className="text-xs muted mt-2">min {minY.toFixed(3)}s • max {maxY.toFixed(3)}s</div>
    </div>
  );
}
