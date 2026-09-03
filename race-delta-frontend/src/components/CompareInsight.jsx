import { useEffect, useState } from "react";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ReferenceLine, Legend,
} from "recharts";
import { fetchCompareVerdict } from "../api/client";

/*
  AI verdict + graphs for one comparison set. The verdict endpoint scores nine areas by fixed rules
  (and lets a language model write the prose when configured); the radar plots those area scores.
  The bar chart shows the pace gap race by race, or sector by sector when the set is a single race.
*/
const COLORS = { a: "#ff1801", b: "#38bdf8" };
const AXIS = { fontSize: 12, fill: "#b4b7bf" };
const TIP = { background: "#0d0f11", border: "1px solid #22272c" };
const shortEvent = (r) => `${(r.event || "").replace(" Grand Prix", "")} '${String(r.season).slice(2)}`;

function Panel({ title, subtitle, children, tourId }) {
  return (
    <section className="panel" data-tour={tourId}>
      <div className="panel-head"><div><h2 className="panel-title">{title}</h2><p className="panel-subtitle">{subtitle}</p></div></div>
      <div className="panel-body h-[320px]">{children}</div>
    </section>
  );
}

export default function CompareInsight({ driver1, driver2, races, context, a, b, perRace = [] }) {
  const [state, setState] = useState({ v: null, loading: false, error: "" });
  const key = races.map((r) => `${r.season}-${r.round}`).join(",");

  // The rules verdict arrives at once; when the model prose is still being written (`pending`)
  // poll a few times so the panel upgrades without a reload.
  useEffect(() => {
    if (!driver1 || !driver2 || !key) { setState({ v: null, loading: false, error: "" }); return undefined; }
    let live = true;
    let timer = null;
    const delays = [3000, 5000, 8000, 12000, 15000, 20000, 30000];   // ~90 s: covers a stalled model call
    const load = (attempt) => fetchCompareVerdict({ driver1, driver2, races, context })
      .then((v) => {
        if (!live) return;
        setState({ v, loading: false, error: "" });
        if (v.pending && attempt < delays.length) timer = setTimeout(() => load(attempt + 1), delays[attempt]);
      })
      .catch((e) => live && attempt === 0 && setState({ v: null, loading: false, error: e.message }));
    setState({ v: null, loading: true, error: "" });
    load(0);
    return () => { live = false; if (timer) clearTimeout(timer); };
  }, [driver1, driver2, key, context]); // eslint-disable-line react-hooks/exhaustive-deps

  const v = state.v;
  const codes = v?.codes || { a: driver1, b: driver2 };
  const radar = (v?.areas || []).filter((x) => x.score_a != null).map((x) => ({ area: x.label, [codes.a]: x.score_a, [codes.b]: x.score_b }));

  // pace gap per race, or per sector for a single race (A minus B: negative = A faster)
  const multi = perRace.filter((r) => r.pace_delta_s != null);
  const bars = multi.length > 1
    ? multi.map((r) => ({ name: shortEvent(r), delta: r.pace_delta_s }))
    : a && b && a.s1_avg_s != null && b.s1_avg_s != null
      ? ["s1_avg_s", "s2_avg_s", "s3_avg_s"].map((k, i) => ({ name: `Sector ${i + 1}`, delta: a[k] != null && b[k] != null ? Number((a[k] - b[k]).toFixed(3)) : null }))
      : [];
  const barsTitle = multi.length > 1 ? "Pace gap by race" : "Sector gaps";
  const barsSub = `${codes.a} minus ${codes.b}, average lap · red bars mean ${codes.a} was faster, blue ${codes.b}`;

  return (
    <div className="space-y-6">
      <section className="panel panel-ai" data-tour="compare-verdict">
        <div className="panel-head">
          <div>
            <h2 className="panel-title">AI verdict</h2>
            <p className="panel-subtitle">
              Who is better here and how · scored from the telemetry features
              {v?.source?.startsWith("llm") ? ` · written by ${v.model}` : v?.pending ? " · rule-based summary, model prose on its way" : v ? " · rule-based summary" : ""}
            </p>
          </div>
          {v && v.areas.length > 0 && (
            <span className={`chip ${v.winner ? "chip-ai" : ""}`}>
              {v.winner ? `${v.winner} ahead · ${Math.round(v.confidence * 100)}% margin` : "Too close to call"}
            </span>
          )}
        </div>
        <div className="panel-body space-y-3">
          {state.loading && <p className="text-muted animate-pulse">Weighing up the numbers…</p>}
          {state.error && <p className="text-f1">{state.error}</p>}
          {v && (
            <>
              <p className="font-broadcast font-black italic uppercase text-white text-2xl leading-tight">{v.headline}</p>
              <p className="text-white/90 leading-relaxed">{v.summary}</p>
              {v.caveats?.length > 0 && <p className="text-muted text-sm">{v.caveats.join(" ")}</p>}
              {v.areas.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {v.areas.map((x) => (
                    <span key={x.key} className="chip" style={x.leader ? { borderColor: x.leader === "A" ? COLORS.a : COLORS.b, color: "#fff" } : undefined}>
                      {x.label}: {x.leader ? `${x.leader === "A" ? codes.a : codes.b} · ${x.detail}` : x.detail}
                    </span>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </section>

      {v && v.areas.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6" data-tour="compare-graphs">
          <Panel title="Performance profile" subtitle="Each area scored between the two drivers · further out is better">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radar} outerRadius="72%">
                <PolarGrid stroke="rgba(255,255,255,0.12)" />
                <PolarAngleAxis dataKey="area" tick={{ ...AXIS, fontSize: 11 }} />
                <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                <Radar name={codes.a} dataKey={codes.a} stroke={COLORS.a} fill={COLORS.a} fillOpacity={0.22} strokeWidth={2} isAnimationActive={false} />
                <Radar name={codes.b} dataKey={codes.b} stroke={COLORS.b} fill={COLORS.b} fillOpacity={0.22} strokeWidth={2} isAnimationActive={false} />
                <Legend />
                <Tooltip contentStyle={TIP} formatter={(val) => `${val} / 100`} />
              </RadarChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title={barsTitle} subtitle={barsSub}>
            {bars.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={bars} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                  <XAxis dataKey="name" tick={{ ...AXIS, fontSize: 11 }} stroke="#22272c" interval={0} angle={bars.length > 6 ? -30 : 0} textAnchor={bars.length > 6 ? "end" : "middle"} height={bars.length > 6 ? 64 : 30} />
                  <YAxis tick={AXIS} stroke="#22272c" width={52} tickFormatter={(val) => `${val > 0 ? "+" : ""}${val}`} />
                  <Tooltip contentStyle={TIP} formatter={(val) => (val == null ? "–" : `${val > 0 ? "+" : ""}${Number(val).toFixed(3)}s`)} />
                  <ReferenceLine y={0} stroke="rgba(255,255,255,0.4)" />
                  <Bar dataKey="delta" isAnimationActive={false} maxBarSize={42}>
                    {bars.map((d, i) => <Cell key={i} fill={d.delta != null && d.delta < 0 ? COLORS.a : COLORS.b} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted">No pace or sector data to chart for this set.</p>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}
