import { useEffect, useMemo, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer } from "recharts";
import { fetchStrategyRaces, fetchStrategyRace, fetchStrategyReplay, postStrategySimulate } from "../api/client";
import { useSeason } from "../context/SeasonContext";

/* Phase 4 — Strategy Lab: lap-by-lap replay (actual vs AI) and what-if strategy simulation */

const COMPOUNDS = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"];
const COMPOUND_COLORS = { SOFT: "#ef4444", MEDIUM: "#facc15", HARD: "#e5e7eb", INTERMEDIATE: "#22c55e", WET: "#3b82f6" };
const FLAG_COLORS = { GREEN: "#22c55e", YELLOW: "#facc15", VSC: "#f59e0b", SC: "#f97316", RED: "#ef4444" };
const select = "bg-[#0f172a] border border-gray-700 rounded-lg p-2 text-white text-sm";
const input = "bg-[#0f172a] border border-gray-700 rounded-lg p-2 text-white text-sm w-20";

function Panel({ title, subtitle, children, right }) {
  return (
    <section className="bg-[#0b1220] rounded-xl p-6 shadow-lg">
      <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

function Stat({ label, value, sub, accent }) {
  return (
    <div className="bg-[#0f172a] rounded-lg p-3">
      <div className="text-[11px] uppercase tracking-wide text-gray-400">{label}</div>
      <div className={`text-xl font-semibold ${accent || ""}`}>{value ?? "–"}</div>
      {sub && <div className="text-xs text-gray-400">{sub}</div>}
    </div>
  );
}

function Compound({ c }) {
  if (!c) return <span className="text-gray-400">–</span>;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: COMPOUND_COLORS[c] || "#9ca3af" }} />
      {c}
    </span>
  );
}

function DecisionCard({ title, action, compound, confidence, reasons, tone }) {
  const isPit = action === "PIT";
  return (
    <div className={`rounded-lg p-4 border ${tone === "ai" ? "border-red-500/40 bg-red-500/5" : "border-gray-700 bg-[#0f172a]"}`}>
      <div className="text-[11px] uppercase tracking-wide text-gray-400 mb-1">{title}</div>
      <div className={`text-2xl font-bold ${isPit ? "text-red-400" : "text-green-400"}`}>
        {isPit ? "PIT" : "STAY OUT"}{compound && <span className="text-base font-medium text-gray-200 ml-2">→ <Compound c={compound} /></span>}
      </div>
      {confidence != null && (
        <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
          <span>confidence</span>
          <div className="h-1.5 flex-1 bg-[#020617] rounded-full overflow-hidden"><div className="h-full bg-red-500" style={{ width: `${confidence * 100}%` }} /></div>
          <span className="tabular-nums">{Math.round(confidence * 100)}%</span>
        </div>
      )}
      {reasons?.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs text-gray-300 list-disc pl-4">{reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
      )}
    </div>
  );
}

export default function StrategyLab() {
  const { seasonOptions, displaySeason } = useSeason();
  const [season, setSeason] = useState(displaySeason || new Date().getFullYear());
  const [races, setRaces] = useState([]);
  const [round, setRound] = useState(null);
  const [race, setRace] = useState(null);
  const [driver, setDriver] = useState("");
  const [lap, setLap] = useState(1);
  const [replay, setReplay] = useState(null);
  const [stops, setStops] = useState([]);
  const [startCompound, setStartCompound] = useState("MEDIUM");
  const [scLap, setScLap] = useState("");
  const [weather, setWeather] = useState("");
  const [sim, setSim] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { if (displaySeason) setSeason(displaySeason); }, [displaySeason]);

  useEffect(() => {
    setError(""); setRaces([]); setRace(null); setReplay(null); setSim(null);
    fetchStrategyRaces(season).then((r) => { setRaces(r.races); setRound(r.races[0]?.round ?? null); })
      .catch((e) => setError(e.message));
  }, [season]);

  useEffect(() => {
    if (!round) return;
    setRace(null); setReplay(null); setSim(null);
    fetchStrategyRace(season, round).then((r) => {
      setRace(r);
      const first = r.drivers[0];
      if (first) { setDriver(first.driver_code); setLap(Math.max(1, Math.round(r.total_laps / 2))); }
    }).catch((e) => setError(e.message));
  }, [season, round]);

  // seed the simulator with the driver's real strategy
  useEffect(() => {
    const d = race?.drivers.find((x) => x.driver_code === driver);
    if (!d) return;
    setStops(d.stops.map((s) => ({ ...s })));
    setStartCompound(d.start_compound || "MEDIUM");
    setSim(null);
  }, [race, driver]);

  useEffect(() => {
    if (!race || !driver || !lap) return;
    const t = setTimeout(() => {
      fetchStrategyReplay(season, round, driver, lap).then(setReplay).catch((e) => setError(e.message));
    }, 200);
    return () => clearTimeout(t);
  }, [season, round, driver, lap, race]);

  const maxLap = replay?.actual_strategy?.laps_completed || race?.total_laps || 1;
  const chart = useMemo(() => (replay?.timeline || []).map((t) => ({ ...t, lap_time_s: t.lap_time_s ?? null })), [replay]);

  async function runSim() {
    setBusy(true); setError("");
    try {
      const payload = { season, round, driver_code: driver, start_compound: startCompound, pit_stops: stops };
      if (scLap) payload.safety_car = { lap: Number(scLap), laps: 3 };
      if (weather) payload.weather = weather;
      setSim(await postStrategySimulate(payload));
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  const st = replay?.state; const rec = replay?.recommendation; const act = replay?.actual_decision;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8 text-white">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Strategy Lab</h1>
          <p className="text-gray-400 text-sm mt-1">Replay any race lap by lap against an explainable AI strategist, then simulate what-if strategies with a per-race XGBoost pace model.</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <select className={select} value={season} onChange={(e) => setSeason(Number(e.target.value))}>
            {seasonOptions.length ? seasonOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>) : <option value={season}>{season}</option>}
          </select>
          <select className={select} value={round ?? ""} onChange={(e) => setRound(Number(e.target.value))}>
            {races.map((r) => <option key={r.round} value={r.round}>R{r.round} · {r.event}{r.rainfall ? " ☔" : ""}{r.ingested === false ? " (loads on select)" : ""}</option>)}
          </select>
          <select className={select} value={driver} onChange={(e) => setDriver(e.target.value)}>
            {(race?.drivers || []).map((d) => <option key={d.driver_code} value={d.driver_code}>{d.driver_code} · {d.name} (P{d.finish_position ?? "–"})</option>)}
          </select>
        </div>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 p-4 rounded-lg text-red-400">{error}</div>}
      {!races.length && !error && <p className="text-gray-400">No completed races found for {season}.</p>}
      {round && !race && !error && (
        <p className="text-gray-400 animate-pulse">Loading race data… first open of a race ingests its telemetry from FastF1 and can take up to a minute.</p>
      )}

      {/* ---------------- Component A: Replay ---------------- */}
      {race && (
        <Panel title="Strategy Replay" subtitle={`${race.event} · ${race.total_laps} laps · pit loss ≈ ${race.pit_loss_s}s · ${race.sc_laps.length ? `SC laps ${race.sc_laps.join(", ")}` : "no Safety Car"}`}
          right={replay && <div className="text-xs text-gray-400">AI agreed with the team on <span className="text-white font-semibold">{replay.agreement_pct}%</span> of laps</div>}>
          <div className="flex items-center gap-4 mb-4">
            <span className="text-sm text-gray-400 w-16">Lap {lap}</span>
            <input type="range" min={1} max={maxLap} value={Math.min(lap, maxLap)} onChange={(e) => setLap(Number(e.target.value))} className="flex-1 accent-red-500" />
            <span className="text-sm text-gray-400">/ {maxLap}</span>
          </div>

          {st && (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-4">
              <Stat label="Position" value={st.position ? `P${st.position}` : "–"} />
              <Stat label="Tyre" value={<Compound c={st.compound} />} sub={st.tyre_life != null ? `${st.tyre_life} laps old` : ""} />
              <Stat label="Lap time" value={st.lap_time_s ? `${st.lap_time_s.toFixed(3)}s` : "–"} sub={st.delta_to_median_s != null ? `${st.delta_to_median_s > 0 ? "+" : ""}${st.delta_to_median_s.toFixed(2)}s vs median` : ""} />
              <Stat label="Gap ahead" value={st.gap_ahead_s != null ? `${st.gap_ahead_s}s` : "–"} sub={st.ahead ? `${st.ahead.driver_code} · ${st.ahead.compound || ""} ${st.ahead.tyre_life ?? ""}L` : "leader"} />
              <Stat label="Gap behind" value={st.gap_behind_s != null ? `${st.gap_behind_s}s` : "–"} sub={st.behind ? `${st.behind.driver_code}` : ""} />
              <Stat label="Track" value={<span style={{ color: FLAG_COLORS[st.flag] }}>{st.flag}</span>} sub={`pit loss now ${st.effective_pit_loss_s}s`} />
              <Stat label="Remaining" value={`${st.laps_remaining} laps`} sub={`${st.stops_so_far} stop${st.stops_so_far === 1 ? "" : "s"} so far`} />
            </div>
          )}

          {rec && act && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <DecisionCard title={`Team decision · lap ${lap}`} action={act.action} compound={act.new_compound}
                reasons={act.next_pit_lap && !act.pitted_this_lap ? [`Next real stop: lap ${act.next_pit_lap}`] : []} />
              <DecisionCard title={`RaceDelta AI · ${rec.headline}`} action={rec.action} compound={rec.compound} confidence={rec.confidence}
                reasons={[...rec.reasons, rec.expected_outcome ? `Pitting now vs staying out over the next ${rec.expected_outcome.horizon_laps} laps: ${rec.expected_outcome.net_gain_s > 0 ? "+" : ""}${rec.expected_outcome.net_gain_s}s` : null,
                  `Pit window: laps ${rec.pit_window.from}–${rec.pit_window.to}`].filter(Boolean)} tone="ai" />
            </div>
          )}

          {chart.length > 0 && (
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chart} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                  <XAxis dataKey="lap" tick={{ fill: "#9CA3AF", fontSize: 11 }} />
                  <YAxis domain={["auto", "auto"]} tick={{ fill: "#9CA3AF", fontSize: 11 }} width={50} />
                  <Tooltip content={({ payload }) => payload?.length ? (
                    <div className="bg-[#0f172a] border border-gray-700 rounded p-2 text-xs">
                      <div>Lap {payload[0].payload.lap} · P{payload[0].payload.position} · {payload[0].payload.compound} {payload[0].payload.tyre_life}L</div>
                      <div>{payload[0].payload.lap_time_s?.toFixed(3)}s · {payload[0].payload.flag} · AI: {payload[0].payload.ai_action}</div>
                    </div>) : null} />
                  {replay.actual_pit_laps.map((L) => <ReferenceLine key={`a${L}`} x={L} stroke="#ef4444" strokeDasharray="4 2" label={{ value: "team pit", fill: "#ef4444", fontSize: 10, position: "top" }} />)}
                  {replay.ai_pit_laps.map((L) => <ReferenceLine key={`ai${L}`} x={L} stroke="#22c55e" strokeDasharray="2 2" label={{ value: "AI pit", fill: "#22c55e", fontSize: 10, position: "insideTop" }} />)}
                  <ReferenceLine x={lap} stroke="#ffffff55" />
                  <Line type="monotone" dataKey="lap_time_s" stroke="#38bdf8" strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>
      )}

      {/* ---------------- Component B: Simulator ---------------- */}
      {race && driver && (
        <Panel title="Strategy Simulator" subtitle={`What if ${driver} had raced differently? Pace model: ${race.model.kind} (RMSE ${race.model.rmse_s}s on ${race.model.n_train_laps} clean laps).`}>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-3">
                <span className="w-28 text-gray-400">Start tyre</span>
                <select className={select} value={startCompound} onChange={(e) => setStartCompound(e.target.value)}>
                  {COMPOUNDS.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              {stops.map((s, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="w-28 text-gray-400">Stop {i + 1}: lap</span>
                  <input type="number" min={1} max={race.total_laps - 1} className={input} value={s.lap}
                    onChange={(e) => setStops(stops.map((x, j) => j === i ? { ...x, lap: Number(e.target.value) } : x))} />
                  <select className={select} value={s.compound} onChange={(e) => setStops(stops.map((x, j) => j === i ? { ...x, compound: e.target.value } : x))}>
                    {COMPOUNDS.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  <button className="text-gray-400 hover:text-red-400" onClick={() => setStops(stops.filter((_, j) => j !== i))}>remove</button>
                </div>
              ))}
              <button className="text-xs text-red-400 hover:text-red-300" onClick={() => setStops([...stops, { lap: Math.min(race.total_laps - 1, (stops[stops.length - 1]?.lap || 0) + 15), compound: "HARD" }])}>+ add pit stop</button>
              <div className="flex items-center gap-3 pt-2">
                <span className="w-28 text-gray-400">Safety car at lap</span>
                <input type="number" min={1} max={race.total_laps} className={input} value={scLap} placeholder="none" onChange={(e) => setScLap(e.target.value)} />
                <span className="w-16 text-gray-400">Weather</span>
                <select className={select} value={weather} onChange={(e) => setWeather(e.target.value)}>
                  <option value="">as raced</option><option value="dry">dry</option><option value="wet">wet</option>
                </select>
              </div>
              <button onClick={runSim} disabled={busy} className="mt-2 bg-[#ff1801] hover:bg-red-600 disabled:opacity-50 text-white font-semibold px-5 py-2 rounded-lg">
                {busy ? "Simulating…" : "Simulate"}
              </button>
            </div>

            <div>
              {sim ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <Stat label="Predicted finish" value={`P${sim.alternative.predicted_finish_position}`} sub={`actual P${sim.actual.finish_position ?? "–"}`} accent={sim.alternative.position_gain > 0 ? "text-green-400" : sim.alternative.position_gain < 0 ? "text-red-400" : ""} />
                    <Stat label="Position gain" value={sim.alternative.position_gain == null ? "–" : `${sim.alternative.position_gain > 0 ? "+" : ""}${sim.alternative.position_gain}`} />
                    <Stat label="Podium probability" value={`${Math.round(sim.alternative.podium_probability * 100)}%`} />
                    <Stat label="Est. race time" value={`${(sim.alternative.estimated_race_time_s / 60).toFixed(2)} min`} sub={sim.actual.race_time_s ? `actual ${(sim.actual.race_time_s / 60).toFixed(2)} min` : ""} />
                    <Stat label="Time saved" value={`${sim.alternative.time_saved_s > 0 ? "+" : ""}${sim.alternative.time_saved_s}s`} accent={sim.alternative.time_saved_s > 0 ? "text-green-400" : "text-red-400"} sub="vs actual strategy" />
                    <Stat label="Model σ" value={`±${sim.sigma_s}s`} sub={sim.model.kind} />
                  </div>
                  <table className="w-full text-xs">
                    <thead className="text-gray-400"><tr><th className="text-left py-1">Stint</th><th className="text-left">Laps</th><th className="text-right">Avg lap</th><th className="text-right">Pit loss</th></tr></thead>
                    <tbody>{sim.alternative.stints.map((s, i) => (
                      <tr key={i} className="border-t border-gray-800"><td className="py-1"><Compound c={s.compound} /></td><td>{s.laps}</td><td className="text-right tabular-nums">{s.avg_lap_s.toFixed(3)}s</td><td className="text-right tabular-nums">{s.pit_loss_s ? `${s.pit_loss_s}s` : "–"}</td></tr>
                    ))}</tbody>
                  </table>
                  <ul className="text-xs text-gray-300 space-y-1 list-disc pl-4">{sim.explanation.map((e, i) => <li key={i}>{e}</li>)}</ul>
                  {sim.warnings.length > 0 && <ul className="text-xs text-amber-400 space-y-1 list-disc pl-4">{sim.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
                </div>
              ) : <p className="text-gray-400 text-sm">Adjust the strategy and press Simulate.</p>}
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}
