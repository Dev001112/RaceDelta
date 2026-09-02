import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, Cell,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
} from "recharts";
import { fetchAiRating, fetchAiDna, fetchAiClusters } from "../api/client";
import { useSeason } from "../context/SeasonContext";

/* Phase 3 — AI Driver Rating · Driver DNA · Style Clustering (all served from the feature store) */

const DIM_LABELS = {
  race_pace: "Race Pace", qualifying_pace: "Quali", consistency: "Consistency",
  tyre_management: "Tyres", overtaking: "Overtaking", defence: "Defence",
  position_gain: "Pos. Gain", wet_performance: "Wet", discipline: "Discipline",
};
const CLUSTER_COLORS = ["#ef4444", "#22c55e", "#38bdf8", "#f59e0b", "#a855f7", "#14b8a6", "#f472b6", "#9ca3af"];
const colorFor = (cluster) => (cluster < 0 ? "#6b7280" : CLUSTER_COLORS[cluster % CLUSTER_COLORS.length]);

function Panel({ title, subtitle, children, right }) {
  return (
    <section className="bg-[#0b1220] rounded-xl p-6 shadow-lg">
      <div className="flex items-start justify-between gap-4 mb-4">
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

function RatingTable({ rating, selected, onSelect }) {
  if (!rating?.drivers?.length) return <p className="text-gray-400">No feature data for this season yet.</p>;
  return (
    <table className="w-full text-sm">
      <thead className="text-gray-400 border-b border-gray-800">
        <tr><th className="py-2 text-left">#</th><th className="text-left">Driver</th><th className="text-left">Team</th>
            <th className="text-right">Races</th><th className="text-left pl-4 w-[38%]">Rating</th><th className="text-left">Strength</th></tr>
      </thead>
      <tbody>
        {rating.drivers.map((d) => (
          <tr key={d.driver_code} onClick={() => onSelect(d.driver_code)}
              className={`border-b border-gray-800/60 cursor-pointer hover:bg-white/5 ${selected === d.driver_code ? "bg-white/10" : ""}`}>
            <td className="py-2 text-gray-400">{d.rank}</td>
            <td className="font-semibold">{d.driver_code} <span className="font-normal text-gray-400">{d.name}</span></td>
            <td className="text-gray-300">{d.team || "–"}</td>
            <td className="text-right text-gray-300">{d.races}{d.low_sample && <span title="fewer than 3 races" className="text-amber-400"> *</span>}</td>
            <td className="pl-4">
              <div className="flex items-center gap-2">
                <div className="h-2 flex-1 bg-[#020617] rounded-full overflow-hidden">
                  <div className="h-full bg-red-500" style={{ width: `${d.rating}%` }} />
                </div>
                <span className="w-12 text-right tabular-nums">{d.rating.toFixed(1)}</span>
              </div>
            </td>
            <td className="text-gray-300">{DIM_LABELS[d.strongest]}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ClusterMap({ clusters, selected, onSelect }) {
  if (!clusters?.points?.length) return <p className="text-gray-400">No clusters yet.</p>;
  const [evx, evy] = clusters.explained_variance || [0, 0];
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 16, right: 16, bottom: 16, left: 0 }}>
            <XAxis dataKey="x" type="number" name={`PC1 (${(evx * 100).toFixed(0)}%)`} tick={{ fill: "#9CA3AF", fontSize: 11 }} />
            <YAxis dataKey="y" type="number" name={`PC2 (${(evy * 100).toFixed(0)}%)`} tick={{ fill: "#9CA3AF", fontSize: 11 }} />
            <ZAxis range={[90, 90]} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }}
              content={({ payload }) => payload?.length ? (
                <div className="bg-[#0f172a] border border-gray-700 rounded p-2 text-xs">
                  <div className="font-semibold">{payload[0].payload.driver_code} · {payload[0].payload.name}</div>
                  <div className="text-gray-400">{payload[0].payload.team} · cluster {payload[0].payload.cluster}</div>
                </div>) : null} />
            <Scatter data={clusters.points} onClick={(p) => onSelect(p.driver_code)}>
              {clusters.points.map((p) => (
                <Cell key={p.driver_code} fill={colorFor(p.cluster)}
                      stroke={selected === p.driver_code ? "#fff" : "none"} strokeWidth={2} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <ul className="space-y-2 text-sm">
        {clusters.clusters.map((c) => (
          <li key={c.cluster} className="bg-[#0f172a] rounded-lg p-3">
            <div className="flex items-center gap-2 font-semibold">
              <span className="inline-block h-3 w-3 rounded-full" style={{ background: colorFor(c.cluster) }} />
              {c.label} <span className="text-gray-400 font-normal">({c.size})</span>
            </div>
            <div className="text-xs text-gray-400 mt-1">{c.members.join(" · ")}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function DnaPanel({ dna, components }) {
  if (!dna) return <p className="text-gray-400">Select a driver in the table or map.</p>;
  const radar = Object.keys(DIM_LABELS).map((k) => ({ metric: DIM_LABELS[k], value: components?.[k] ?? 50 }));
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radar} outerRadius={95}>
            <PolarGrid stroke="rgba(255,255,255,0.15)" />
            <PolarAngleAxis dataKey="metric" tick={{ fill: "#9CA3AF", fontSize: 11 }} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            <Radar dataKey="value" stroke="#EF4444" fill="#EF4444" fillOpacity={0.32} strokeWidth={2} isAnimationActive={false} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <div className="text-sm">
        <div className="text-lg font-semibold">{dna.driver_code} · {dna.name}</div>
        <div className="text-gray-400 mb-3">{dna.team} · {dna.races} races</div>
        <div className="text-xs uppercase tracking-wide text-gray-400 mb-1">Most similar drivers (cosine)</div>
        <ul className="space-y-1">
          {dna.similar.map((s) => (
            <li key={s.driver_code} className="flex justify-between border-b border-gray-800/60 py-1">
              <span>{s.driver_code} <span className="text-gray-400">{s.name}</span></span>
              <span className="tabular-nums text-gray-300">{(s.cosine_similarity * 100).toFixed(0)}%</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function DriverIntelligence() {
  const { seasonOptions, displaySeason } = useSeason();
  const [season, setSeason] = useState(displaySeason || new Date().getFullYear());
  const [method, setMethod] = useState("kmeans");
  const [k, setK] = useState(4);
  const [rating, setRating] = useState(null);
  const [clusters, setClusters] = useState(null);
  const [selected, setSelected] = useState("");
  const [dna, setDna] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { if (displaySeason) setSeason(displaySeason); }, [displaySeason]);

  useEffect(() => {
    setError(""); setRating(null); setClusters(null); setDna(null);
    fetchAiRating(season).then(setRating).catch((e) => setError(e.message));
  }, [season]);

  useEffect(() => {
    fetchAiClusters(season, method, k).then(setClusters).catch((e) => setError(e.message));
  }, [season, method, k]);

  useEffect(() => {
    if (!selected) return;
    fetchAiDna(season, selected, 5).then(setDna).catch((e) => setError(e.message));
  }, [season, selected]);

  const components = useMemo(
    () => rating?.drivers?.find((d) => d.driver_code === selected)?.components,
    [rating, selected]
  );

  const select = "bg-[#0f172a] border border-gray-700 rounded-lg p-2 text-white text-sm";

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8 text-white">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">AI Lab</h1>
          <p className="text-gray-400 text-sm mt-1">Driver Rating · Driver DNA · Style Clustering — computed from lap-level telemetry features</p>
        </div>
        <label className="text-sm text-gray-400">Season&nbsp;
          <select className={select} value={season} onChange={(e) => setSeason(Number(e.target.value))}>
            {seasonOptions.length ? seasonOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)
                                  : <option value={season}>{season}</option>}
          </select>
        </label>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 p-4 rounded-lg text-red-400">{error}</div>}

      <Panel title="AI Driver Rating" subtitle="Within-race z-scores → 0–100 per dimension → weighted score. Click a driver for their DNA.">
        <RatingTable rating={rating} selected={selected} onSelect={setSelected} />
      </Panel>

      <Panel title="Driving Style Clusters" subtitle="PCA map of the DNA vectors; clusters auto-labelled by their dominant trait."
        right={
          <div className="flex gap-2">
            <select className={select} value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="kmeans">K-Means</option><option value="hierarchical">Hierarchical</option><option value="dbscan">DBSCAN</option>
            </select>
            {method !== "dbscan" && (
              <select className={select} value={k} onChange={(e) => setK(Number(e.target.value))}>
                {[2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>k = {n}</option>)}
              </select>
            )}
          </div>}>
        <ClusterMap clusters={clusters} selected={selected} onSelect={setSelected} />
      </Panel>

      <Panel title="Driver DNA" subtitle="Performance vector with nearest drivers by cosine similarity.">
        <DnaPanel dna={dna} components={components} />
      </Panel>
    </div>
  );
}
