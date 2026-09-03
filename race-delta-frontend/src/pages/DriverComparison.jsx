import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import client, { fetchCompareRaces, fetchCompareOnRaces, fetchCompareLaps } from "../api/client";
import { useSeason } from "../context/SeasonContext";
import DriverSelect from "../components/DriverSelect";
import CompareHeader from "../components/CompareHeader";
import CompareCharts from "../components/CompareCharts";
import DriverCompareTable from "../components/DriverCompareTable";
import PageHeader from "../components/PageHeader";
import RaceSetComparison, { ConditionChips, Tile, finishLabel, tableSide } from "../components/RaceSetComparison";
import CompareLapChart from "../components/CompareLapChart";
import CompareInsight from "../components/CompareInsight";
import TrackMap from "../components/TrackMap";

/*
  Compare lab. The pair of drivers lives in the URL (d1, d2) and four sections look at it differently:
  season (latest race + points timeline), race (one Grand Prix, lap by lap), track (every visit to a circuit)
  and conditions (only wet / dry / safety-car / hot / cool races). Each section keeps its pick in the URL too.
*/

const SECTIONS = [
  { key: "season", label: "Season", hint: "Latest race + points timeline" },
  { key: "race", label: "Race", hint: "Any single Grand Prix, lap by lap" },
  { key: "track", label: "Track", hint: "Every visit to one circuit" },
  { key: "conditions", label: "Conditions", hint: "Wet, safety car, hot or cool" },
];

const CONDITIONS = [
  { key: "wet", label: "Wet race", test: (r) => r.wet },
  { key: "dry", label: "Dry race", test: (r) => !r.wet },
  { key: "sc", label: "Safety car", test: (r) => r.safety_car },
  { key: "nosc", label: "No safety car", test: (r) => !r.safety_car },
  { key: "vsc", label: "Virtual safety car", test: (r) => r.virtual_safety_car },
  { key: "hot", label: "Hot track ≥ 40°C", test: (r) => r.hot },
  { key: "cool", label: "Cool track < 25°C", test: (r) => r.cool },
];

const raceKey = (r) => `${r.season}-${r.round}`;
const seasonsOf = (races) => [...new Set(races.map((r) => r.season))].sort((a, b) => b - a);

function normalizeComparison(res, driver1, driver2) {
  if (res?.data?.driverA && res?.data?.driverB) {
    return { source: res.source, drivers: { [driver1]: res.data.driverA, [driver2]: res.data.driverB } };
  }
  return res;
}

/* Both drivers over a set of races; re-runs whenever the set changes. */
function useRaceSet(driver1, driver2, races) {
  const [state, setState] = useState({ data: null, loading: false, error: "" });
  const key = races.map(raceKey).join(",");
  useEffect(() => {
    if (!driver1 || !driver2 || !key) { setState({ data: null, loading: false, error: "" }); return undefined; }
    let live = true;
    setState({ data: null, loading: true, error: "" });
    fetchCompareOnRaces({ driver1, driver2, races })
      .then((d) => live && setState({ data: d, loading: false, error: "" }))
      .catch((e) => live && setState({ data: null, loading: false, error: e.message }));
    return () => { live = false; };
  }, [driver1, driver2, key]); // eslint-disable-line react-hooks/exhaustive-deps
  return state;
}

function Prompt({ eyebrow = "Compare lab", children }) {
  return (
    <div className="panel panel-plain p-8 text-center">
      <div className="eyebrow eyebrow-red">{eyebrow}</div>
      <p className="text-white text-lg mt-2">{children}</p>
    </div>
  );
}

function Status({ loading, error }) {
  return (
    <>
      {loading && <div className="text-muted animate-pulse">Loading comparison…</div>}
      {error && <div className="panel panel-plain border-f1/40 p-4 text-f1">{error}</div>}
    </>
  );
}

/* ---------------- Season: the original comparison ---------------- */
function SeasonSection({ driver1, driver2, season, onSeason, seasonOptions }) {
  const [comparison, setComparison] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setComparison(null); setTimeline(null); setError("");
    if (!driver1 || !driver2) return undefined;
    if (driver1 === driver2) { setError("Pick two different drivers."); return undefined; }
    let live = true;
    setLoading(true);
    (async () => {
      try {
        const stats = await client.fetchDriverComparison({ driver1, driver2, season });
        if (!live) return;
        setComparison(normalizeComparison(stats, driver1, driver2));
        const tl = await client.fetchDriverTimeline({ driver1, driver2, season });
        if (live) setTimeline(tl);
      } catch (e) {
        if (live) setError(e.message || "Failed to compare drivers");
      } finally {
        if (live) setLoading(false);
      }
    })();
    return () => { live = false; };
  }, [driver1, driver2, season]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4" data-tour="compare-controls">
        <div className="flex flex-col gap-2">
          <label className="eyebrow">Season</label>
          <select className="select-broadcast" value={season} onChange={(e) => onSeason(e.target.value)} aria-label="Season">
            {seasonOptions.length ? seasonOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>) : <option value="current">Current season</option>}
          </select>
        </div>
        <p className="text-muted text-sm pb-3">Head-to-head on the season's latest race, plus cumulative points across the year.</p>
      </div>
      <Status loading={loading} error={error} />
      {comparison?.drivers && comparison.round && (
        <CompareInsight driver1={driver1} driver2={driver2} races={[{ season: comparison.season, round: comparison.round }]}
                        context={`${comparison.event || "latest race"} ${comparison.season}`}
                        a={comparison.drivers[driver1]?.features} b={comparison.drivers[driver2]?.features} />
      )}
      {comparison?.drivers && <DriverCompareTable aCode={driver1} bCode={driver2} a={comparison.drivers[driver1]} b={comparison.drivers[driver2]} />}
      {timeline?.rounds?.length > 0 && <CompareCharts data={timeline} driver1={driver1} driver2={driver2} />}
    </div>
  );
}

/* ---------------- Race: one Grand Prix, lap by lap ---------------- */
function RaceSection({ driver1, driver2, races, selected, onSelect }) {
  const race = races.find((r) => raceKey(r) === selected) || null;
  const set = useMemo(() => (race ? [race] : []), [race]);
  const { data, loading, error } = useRaceSet(driver1, driver2, set);
  const [laps, setLaps] = useState(null);

  useEffect(() => {
    setLaps(null);
    if (!race || !driver1 || !driver2) return undefined;
    let live = true;
    fetchCompareLaps({ driver1, driver2, season: race.season, round: race.round })
      .then((d) => live && setLaps(d))
      .catch(() => live && setLaps(null));
    return () => { live = false; };
  }, [race, driver1, driver2]);

  const line = data?.races?.[0];
  const codes = data?.codes;
  const delta = line?.pace_delta_s;
  const paceLeader = delta == null || delta === 0 ? null : delta < 0 ? codes.a : codes.b;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4" data-tour="compare-controls">
        <div className="flex flex-col gap-2 min-w-[320px]">
          <label className="eyebrow">Grand Prix</label>
          <select className="select-broadcast" value={selected} onChange={(e) => onSelect(e.target.value)} aria-label="Race">
            <option value="">Select a race</option>
            {seasonsOf(races).map((s) => (
              <optgroup key={s} label={String(s)}>
                {races.filter((r) => r.season === s).map((r) => (
                  <option key={raceKey(r)} value={raceKey(r)}>
                    R{r.round} · {r.event}{r.wet ? " · wet" : ""}{r.safety_car ? " · SC" : ""}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
        {race && (
          <div className="flex flex-wrap items-center gap-3 pb-3">
            <ConditionChips r={race} />
            {race.avg_track_temp != null && (
              <span className="text-muted text-sm">track {race.avg_track_temp.toFixed(0)}°C · air {race.avg_air_temp?.toFixed(0) ?? "–"}°C · {race.total_laps} laps</span>
            )}
          </div>
        )}
      </div>

      {!race && <Prompt>Pick a Grand Prix to compare the pair on that race alone.</Prompt>}
      <Status loading={loading} error={error} />

      {line && (line.a && line.b ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Tile label={`${codes.a} finish`} value={finishLabel(line.a)} sub={`grid ${line.a.grid_position ?? "–"} · ${line.a.points ?? 0} pts`} good={line.winner === "A"} />
            <Tile label={`${codes.b} finish`} value={finishLabel(line.b)} sub={`grid ${line.b.grid_position ?? "–"} · ${line.b.points ?? 0} pts`} good={line.winner === "B"} />
            <Tile label="Pace delta" value={delta == null ? "–" : `${delta > 0 ? "+" : ""}${delta.toFixed(3)}s`} sub={paceLeader ? `${paceLeader} faster per lap` : "average lap, A minus B"} good={Boolean(paceLeader)} />
            <Tile label="Pit stops" value={`${line.a.pit_stop_count ?? "–"} · ${line.b.pit_stop_count ?? "–"}`} sub={`laps ${(line.a.pit_laps || []).join(", ") || "–"} · ${(line.b.pit_laps || []).join(", ") || "–"}`} />
          </div>
          <TrackMap candidates={races.filter((r) => r.track === race.track).sort((x, y) => y.season - x.season)} event={`${race.event} ${race.season}`} codes={codes} a={line.a} b={line.b} />
          <CompareInsight driver1={codes.a} driver2={codes.b} races={set} context={`${race.event} ${race.season}`} a={line.a} b={line.b} perRace={[line]} />
          <DriverCompareTable aCode={codes.a} bCode={codes.b} a={tableSide(line.a)} b={tableSide(line.b)}
                              title={`${race.event} ${race.season}`} subtitle="Telemetry from this race only · green marks the better value" />
          <CompareLapChart laps={laps?.laps} codes={codes} event={`${race.event} ${race.season}`} />
        </>
      ) : (
        <Prompt>
          {line.a || line.b
            ? `Only ${line.a ? codes.a : codes.b} has telemetry for this race.`
            : "Neither driver has telemetry for this race."}
        </Prompt>
      ))}
    </div>
  );
}

/* ---------------- Track: every visit to one circuit ---------------- */
function TrackSection({ driver1, driver2, races, selected, onSelect }) {
  const tracks = useMemo(() => {
    const m = new Map();
    races.forEach((r) => m.set(r.track, [...(m.get(r.track) || []), r]));
    return [...m.entries()].sort((x, y) => x[0].localeCompare(y[0]));
  }, [races]);
  const set = useMemo(() => tracks.find(([t]) => t === selected)?.[1] || [], [tracks, selected]);
  const { data, loading, error } = useRaceSet(driver1, driver2, set);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4" data-tour="compare-controls">
        <div className="flex flex-col gap-2 min-w-[320px]">
          <label className="eyebrow">Circuit</label>
          <select className="select-broadcast" value={selected} onChange={(e) => onSelect(e.target.value)} aria-label="Track">
            <option value="">Select a track</option>
            {tracks.map(([t, rs]) => (
              <option key={t} value={t}>{t} · {rs.length} race{rs.length === 1 ? "" : "s"} ({rs.map((r) => r.season).join(", ")})</option>
            ))}
          </select>
        </div>
        {selected && <p className="text-muted text-sm pb-3">Every visit to {selected} with stored telemetry, averaged.</p>}
      </div>
      {!selected && <Prompt>Pick a circuit to compare the pair across every visit we have telemetry for.</Prompt>}
      <Status loading={loading} error={error} />
      {data && (
        <RaceSetComparison data={data} mapCandidates={[...set].reverse()}
                           title={`${selected} · averages over ${data.aggregate.races_compared} race${data.aggregate.races_compared === 1 ? "" : "s"}`}
                           subtitle="Each race's telemetry features, averaged · green marks the better value" />
      )}
    </div>
  );
}

/* ---------------- Conditions: only races that match ---------------- */
function ConditionsSection({ driver1, driver2, races, condition, onCondition, seasonFilter, onSeasonFilter }) {
  const cond = CONDITIONS.find((c) => c.key === condition) || null;
  const inSeason = (r) => seasonFilter === "all" || r.season === Number(seasonFilter);
  const set = useMemo(() => (cond ? races.filter((r) => cond.test(r) && inSeason(r)) : []), [races, cond, seasonFilter]); // eslint-disable-line react-hooks/exhaustive-deps
  const { data, loading, error } = useRaceSet(driver1, driver2, set);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-6" data-tour="compare-controls">
        <div className="flex flex-col gap-2">
          <label className="eyebrow">Condition</label>
          <div className="flex flex-wrap gap-2">
            {CONDITIONS.map((c) => {
              const n = races.filter((r) => c.test(r) && inSeason(r)).length;
              return (
                <button key={c.key} type="button" onClick={() => onCondition(c.key)} aria-pressed={condition === c.key}
                        className={`chip chip-button ${condition === c.key ? "chip-live" : ""}`}>
                  {c.label} · {n}
                </button>
              );
            })}
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <label className="eyebrow">Seasons</label>
          <select className="select-broadcast" value={seasonFilter} onChange={(e) => onSeasonFilter(e.target.value)} aria-label="Season filter">
            <option value="all">All seasons</option>
            {seasonsOf(races).map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>
      {!cond && <Prompt>Pick a condition to compare the pair only on the races that match it.</Prompt>}
      {cond && set.length === 0 && <Prompt>No stored race matches that condition.</Prompt>}
      <Status loading={loading} error={error} />
      {data && cond && (
        <RaceSetComparison data={data} title={`${cond.label} · averages over ${data.aggregate.races_compared} race${data.aggregate.races_compared === 1 ? "" : "s"}`}
                           subtitle="Each matching race's telemetry features, averaged · green marks the better value" />
      )}
    </div>
  );
}

/* ---------------- Page ---------------- */
export default function DriverComparison() {
  const { seasonOptions, displaySeason } = useSeason();
  const [searchParams, setSearchParams] = useSearchParams();
  const get = (k, fallback = "") => searchParams.get(k) || fallback;
  const patch = useCallback((changes) => {
    const next = new URLSearchParams(searchParams);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  const driver1 = get("d1");
  const driver2 = get("d2");
  const section = SECTIONS.some((s) => s.key === get("mode")) ? get("mode") : "season";
  const season = get("season") || (displaySeason ? String(displaySeason) : "current");

  const [drivers, setDrivers] = useState([]);
  const [races, setRaces] = useState([]);
  useEffect(() => { client.fetchDrivers(season).then(setDrivers).catch(() => setDrivers([])); }, [season]);
  useEffect(() => { fetchCompareRaces().then((r) => setRaces(r.races || [])).catch(() => setRaces([])); }, []);

  const d1 = drivers.find((d) => d.code === driver1);
  const d2 = drivers.find((d) => d.code === driver2);
  const ready = Boolean(driver1 && driver2);

  return (
    <div className="py-6 space-y-8">
      <PageHeader kicker="Compare lab" title="Driver Comparison" season={Number(season) || null}
        subtitle="Two drivers, four lenses: the season, a single Grand Prix, one circuit across seasons, or only the races run under a chosen condition." />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6" data-tour="compare-select">
        <DriverSelect label="Driver A" drivers={drivers} value={driver1} onChange={(v) => patch({ d1: v })} />
        <DriverSelect label="Driver B" drivers={drivers} value={driver2} onChange={(v) => patch({ d2: v })} />
      </div>
      {d1 && d2 && <CompareHeader leftDriver={d1} rightDriver={d2} />}

      <div className="flex flex-wrap gap-2 border-b border-line pb-4" data-tour="compare-sections" role="tablist" aria-label="Comparison sections">
        {SECTIONS.map((s) => (
          <button key={s.key} type="button" role="tab" aria-selected={section === s.key} onClick={() => patch({ mode: s.key })}
                  className={`text-left px-4 py-2.5 border transition-colors ${section === s.key ? "bg-f1 border-f1 text-white" : "border-line text-muted hover:text-white hover:border-[#3a4048]"}`}>
            <span className="block font-broadcast font-black uppercase italic tracking-wider text-sm">{s.label}</span>
            <span className={`block text-xs ${section === s.key ? "text-white/85" : "text-muted"}`}>{s.hint}</span>
          </button>
        ))}
      </div>

      {!ready && <Prompt eyebrow="Ready to compare">Pick two drivers above. Every section compares the same pair.</Prompt>}
      {ready && section === "season" && (
        <SeasonSection driver1={driver1} driver2={driver2} season={season} onSeason={(v) => patch({ season: v })} seasonOptions={seasonOptions} />
      )}
      {ready && section === "race" && (
        <RaceSection driver1={driver1} driver2={driver2} races={races} selected={get("race")} onSelect={(v) => patch({ race: v })} />
      )}
      {ready && section === "track" && (
        <TrackSection driver1={driver1} driver2={driver2} races={races} selected={get("track")} onSelect={(v) => patch({ track: v })} />
      )}
      {ready && section === "conditions" && (
        <ConditionsSection driver1={driver1} driver2={driver2} races={races} condition={get("cond")} onCondition={(v) => patch({ cond: v })}
                           seasonFilter={get("cs", "all")} onSeasonFilter={(v) => patch({ cs: v === "all" ? "" : v })} />
      )}
    </div>
  );
}
