import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, Cell,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
} from "recharts";
import { fetchAiRating, fetchAiDna, fetchAiClusters } from "../api/client";
import { useSeason } from "../context/SeasonContext";
import PageHeader from "../components/PageHeader";

/* Phase 3 — AI Driver Rating · Driver DNA · Style Clustering (purple = AI output) */

const SECTOR = "#b26bff";
const DIM_LABELS = {
  race_pace: "Race pace", qualifying_pace: "Qualifying", consistency: "Consistency",
  tyre_management: "Tyres", overtaking: "Overtaking", defence: "Defence",
  position_gain: "Positions gained", wet_performance: "Wet weather", discipline: "Discipline",
};
const CLUSTER_COLORS = ["#ff1801", "#22c55e", "#38bdf8", "#facc15", "#b26bff", "#14b8a6", "#f472b6", "#9ca3af"];
const colorFor = (cluster) => (cluster < 0 ? "#6b7280" : CLUSTER_COLORS[cluster % CLUSTER_COLORS.length]);

function Panel({ title, subtitle, children, right, tourId, ai }) {
  return (
    <section className={`panel ${ai ? "panel-ai" : ""}`} data-tour={tourId}>
      <div className="panel-head">
        <div>
          <h2 className="panel-title">{title}</h2>
          {subtitle && <p className="panel-subtitle">{subtitle}</p>}
        </div>
        {right}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}

function RatingTable({ rating, selected, onSelect }) {
  if (!rating?.drivers?.length) return <p className="text-muted">No feature data for this season yet.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="timing-table">
        <thead>
          <tr><th>#</th><th>Driver</th><th>Team</th><th className="num">Races</th><th style={{ width: "34%" }}>Rating</th><th>Strength</th></tr>
        </thead>
        <tbody>
          {rating.drivers.map((d) => (
            <tr key={d.driver_code} onClick={() => onSelect(d.driver_code)}
                className={`cursor-pointer ${selected === d.driver_code ? "bg-white/5" : ""}`}>
              <td className="pos">{String(d.rank).padStart(2, "0")}</td>
              <td>
                <span className="font-broadcast font-black uppercase text-white text-lg">{d.driver_code}</span>
                <span className="text-muted ml-2">{d.name}</span>
              </td>
              <td className="text-muted">{d.team || "–"}</td>
              <td className="num">{d.races}{d.low_sample && <span title="Fewer than 3 races" className="text-flag"> *</span>}</td>
              <td>
                <div className="flex items-center gap-3">
                  <div className="h-2.5 flex-1 bg-carbon border border-line"><div className="h-full ai-bar" style={{ width: `${d.rating}%` }} /></div>
                  <span className="font-broadcast font-black italic text-lg tabular w-12 text-right">{d.rating.toFixed(1)}</span>
                </div>
              </td>
              <td className="text-muted">{DIM_LABELS[d.strongest]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ClusterMap({ clusters, selected, onSelect }) {
  if (!clusters?.points?.length) return <p className="text-muted">No clusters yet.</p>;
  const [evx, evy] = clusters.explained_variance || [0, 0];
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <div className="lg:col-span-2 h-[380px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 16, right: 16, bottom: 16, left: 0 }}>
            <XAxis dataKey="x" type="number" name={`PC1 (${(evx * 100).toFixed(0)}%)`} tick={{ fill: "#b4b7bf", fontSize: 12 }} />
            <YAxis dataKey="y" type="number" name={`PC2 (${(evy * 100).toFixed(0)}%)`} tick={{ fill: "#b4b7bf", fontSize: 12 }} />
            <ZAxis range={[110, 110]} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }}
              content={({ payload }) => payload?.length ? (
                <div className="panel panel-plain p-3 text-sm">
                  <div className="font-broadcast font-black uppercase text-white">{payload[0].payload.driver_code} · {payload[0].payload.name}</div>
                  <div className="text-muted">{payload[0].payload.team} · cluster {payload[0].payload.cluster}</div>
                </div>) : null} />
            <Scatter data={clusters.points} onClick={(p) => onSelect(p.driver_code)}>
              {clusters.points.map((p) => (
                <Cell key={p.driver_code} fill={colorFor(p.cluster)} stroke={selected === p.driver_code ? "#fff" : "none"} strokeWidth={2} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <ul className="space-y-2">
        {clusters.clusters.map((c) => (
          <li key={c.cluster} className="stat-tile">
            <div className="flex items-center gap-2 font-broadcast font-black uppercase text-white">
              <span className="inline-block h-3 w-3" style={{ background: colorFor(c.cluster) }} />
              {c.label} <span className="text-muted font-bold">({c.size})</span>
            </div>
            <div className="stat-sub">{c.members.join(" · ")}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function DnaPanel({ dna, components }) {
  if (!dna) return <p className="text-muted">Select a driver in the rating table or on the map.</p>;
  const radar = Object.keys(DIM_LABELS).map((k) => ({ metric: DIM_LABELS[k], value: components?.[k] ?? 50 }));
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radar} outerRadius={105}>
            <PolarGrid stroke="rgba(255,255,255,0.15)" />
            <PolarAngleAxis dataKey="metric" tick={{ fill: "#b4b7bf", fontSize: 12 }} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            <Radar dataKey="value" stroke={SECTOR} fill={SECTOR} fillOpacity={0.3} strokeWidth={2} isAnimationActive={false} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <div>
        <div className="font-broadcast font-black italic uppercase text-white text-2xl">{dna.driver_code} <span className="not-italic font-bold text-muted text-lg">{dna.name}</span></div>
        <div className="text-muted mb-4">{dna.team} · {dna.races} races</div>
        <div className="eyebrow eyebrow-ai mb-2">Most similar drivers · cosine similarity</div>
        <ul>
          {dna.similar.map((s) => (
            <li key={s.driver_code} className="flex justify-between border-b border-line py-2">
              <span><span className="font-broadcast font-black text-white">{s.driver_code}</span> <span className="text-muted">{s.name}</span></span>
              <span className="tabular text-white">{(s.cosine_similarity * 100).toFixed(0)}%</span>
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

  return (
    <div className="py-6 space-y-6">
      <PageHeader
        kicker="AI Lab · driver intelligence"
        title="AI Lab"
        season={season}
        subtitle="Driver rating, driver DNA and driving-style clusters, computed from lap-level telemetry features rather than championship points."
        actions={
          <select className="select-broadcast" value={season} onChange={(e) => setSeason(Number(e.target.value))} aria-label="Season">
            {seasonOptions.length ? seasonOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>) : <option value={season}>{season}</option>}
          </select>
        }
      />

      {error && <div className="panel panel-plain border-f1/40 p-4 text-f1">{error}</div>}

      <Panel ai tourId="rating" title="AI Driver Rating"
             subtitle="Within-race z-scores, then 0–100 per dimension, then a weighted score. Click a driver to load their DNA.">
        <RatingTable rating={rating} selected={selected} onSelect={setSelected} />
      </Panel>

      <Panel ai tourId="clusters" title="Driving-style clusters"
             subtitle="PCA map of the DNA vectors; clusters are labelled by their dominant trait."
             right={
               <div className="flex gap-2">
                 <select className="select-broadcast" value={method} onChange={(e) => setMethod(e.target.value)} aria-label="Clustering method">
                   <option value="kmeans">K-Means</option><option value="hierarchical">Hierarchical</option><option value="dbscan">DBSCAN</option>
                 </select>
                 {method !== "dbscan" && (
                   <select className="select-broadcast" value={k} onChange={(e) => setK(Number(e.target.value))} aria-label="Number of clusters">
                     {[2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>k = {n}</option>)}
                   </select>
                 )}
               </div>}>
        <ClusterMap clusters={clusters} selected={selected} onSelect={setSelected} />
      </Panel>

      <Panel ai tourId="dna" title="Driver DNA" subtitle="Performance vector with the nearest drivers by cosine similarity.">
        <DnaPanel dna={dna} components={components} />
      </Panel>
    </div>
  );
}
