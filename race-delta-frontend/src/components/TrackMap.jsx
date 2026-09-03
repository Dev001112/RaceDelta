import { useEffect, useState } from "react";
import { fetchTrackMap } from "../api/client";

/*
  Circuit outline cut into its three timing sectors, each coloured by the driver with the faster
  average sector time (a/b are feature dicts with s1_avg_s..s3_avg_s: one race, or averages over a set).
  The outline is built from telemetry on first request, so the panel polls while it is pending.
*/
const COLORS = { a: "#ff1801", b: "#38bdf8", level: "#6b7280" };
const LEVEL_S = 0.02;
const fmt = (v) => (v == null ? "–" : Number(v).toFixed(3));
const path = (pts) => pts.map(([x, y], i) => `${i ? "L" : "M"}${x} ${y}`).join(" ");

export default function TrackMap({ candidates = [], event, codes, a, b, perRace = [] }) {
  const key = candidates.map((r) => `${r.season}-${r.round}`).join(",");
  const [map, setMap] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!key) return undefined;
    let live = true;
    let timer = null;
    let tries = 0;
    setMap(null); setError("");
    const load = () => fetchTrackMap({ candidates })
      .then((m) => {
        if (!live) return;
        setMap(m);
        if (m.pending && tries++ < 40) timer = setTimeout(load, 5000);   // first build downloads position data
      })
      .catch((e) => live && setError(e.message));
    load();
    return () => { live = false; if (timer) clearTimeout(timer); };
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  const sectors = [1, 2, 3].map((n) => {
    const va = a?.[`s${n}_avg_s`];
    const vb = b?.[`s${n}_avg_s`];
    const delta = va != null && vb != null ? va - vb : null;
    const leader = delta == null ? null : Math.abs(delta) < LEVEL_S ? "level" : delta < 0 ? "a" : "b";
    return { n, va, vb, delta, leader };
  });
  const colorOf = (n) => {
    const s = sectors[n - 1];
    return s.leader === "a" ? COLORS.a : s.leader === "b" ? COLORS.b : COLORS.level;
  };
  const nameOf = (s) => (s.leader === "a" ? codes.a : s.leader === "b" ? codes.b : s.leader ? "Level" : "–");
  const ready = map && !map.pending && map.sectors;

  return (
    <section className="panel" data-tour="compare-track-map">
      <div className="panel-head">
        <div>
          <h2 className="panel-title">Sector map</h2>
          <p className="panel-subtitle">
            {event} · each sector takes the colour of the driver with the faster average sector time
            {perRace.length > 1 ? ` across ${perRace.length} races` : ""} · grey is level within {LEVEL_S}s
          </p>
        </div>
        <div className="flex gap-2">
          <span className="chip" style={{ borderColor: COLORS.a, color: "#fff" }}>{codes.a}</span>
          <span className="chip" style={{ borderColor: COLORS.b, color: "#fff" }}>{codes.b}</span>
        </div>
      </div>
      <div className="panel-body grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-6 items-center">
        <div>
          {ready ? (
            <svg viewBox={`0 0 ${map.size} ${map.size}`} className="w-full max-h-[480px]" role="img" aria-label={`${event} circuit map`}>
              {map.sectors.map((s) => (
                <path key={`u${s.n}`} d={path(s.points)} fill="none" stroke="#1a1e22" strokeWidth={30} strokeLinecap="round" strokeLinejoin="round" />
              ))}
              {map.sectors.map((s) => (
                <path key={s.n} d={path(s.points)} fill="none" stroke={colorOf(s.n)} strokeWidth={14} strokeLinecap="round" strokeLinejoin="round" />
              ))}
              {map.corners.map((c) => (
                <g key={c.n}>
                  <circle cx={c.x} cy={c.y} r={13} fill="#0d0f11" stroke="#3a4048" />
                  <text x={c.x} y={c.y + 4} textAnchor="middle" fontSize={12} fill="#b4b7bf">{c.n}</text>
                </g>
              ))}
              {map.sectors.map((s) => {
                const m = s.points[Math.floor(s.points.length / 2)];
                return m ? (
                  <text key={`l${s.n}`} x={m[0]} y={m[1] - 24} textAnchor="middle" fontSize={40} fontWeight="900" fontStyle="italic"
                        fill={colorOf(s.n)} stroke="#070809" strokeWidth={6} paintOrder="stroke">
                    S{s.n}
                  </text>
                ) : null;
              })}
              {map.start_finish && (
                <g>
                  <circle cx={map.start_finish[0]} cy={map.start_finish[1]} r={9} fill="#fff" />
                  <text x={map.start_finish[0] + 16} y={map.start_finish[1] + 5} fontSize={14} fontWeight="700" fill="#fff">S/F</text>
                </g>
              )}
            </svg>
          ) : (
            <div className="h-[320px] flex flex-col items-center justify-center text-center text-muted">
              {error ? <span className="text-f1">{error}</span> : map?.unavailable ? <span>{map.reason}</span> : (
                <>
                  <span className="animate-pulse">Drawing the circuit from telemetry…</span>
                  <span className="text-sm mt-1">The first time for a circuit takes a minute or two while the position data downloads.</span>
                </>
              )}
            </div>
          )}
        </div>
        <div className="space-y-3">
          {sectors.map((s) => (
            <div key={s.n} className="stat-tile" style={{ borderLeft: `4px solid ${colorOf(s.n)}` }}>
              <div className="flex items-baseline justify-between">
                <div className="stat-label">Sector {s.n}</div>
                <div className="font-broadcast font-black italic text-lg" style={{ color: colorOf(s.n) }}>{nameOf(s)}</div>
              </div>
              <div className="stat-value text-xl">{s.delta == null ? "–" : `${s.delta > 0 ? "+" : ""}${s.delta.toFixed(3)}s`}</div>
              <div className="stat-sub">{codes.a} {fmt(s.va)}s · {codes.b} {fmt(s.vb)}s · {codes.a} minus {codes.b}</div>
            </div>
          ))}
          {ready && map.lap && (
            <p className="text-muted text-sm">
              Outline traced from {map.lap.driver}'s lap {map.lap.lap_number} of the {map.season} race ({map.lap.lap_time_s}s), cut at the official sector timing points.
              {candidates[0] && map.season !== candidates[0].season ? ` The ${candidates[0].season} telemetry cannot be read yet, so the ${map.season} layout stands in.` : ""}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
