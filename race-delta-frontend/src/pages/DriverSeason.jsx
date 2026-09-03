import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchDriverSeason } from "../api/client";
import { useSeason } from "../context/SeasonContext";
import PageHeader from "../components/PageHeader";
import DriverHeader from "../components/DriverHeader";
import RadarComparison from "../components/RadarComparison";
import PointsTrend from "../components/PointsTrend";
import QualiRaceDelta from "../components/QualiRaceDelta";

function Panel({ title, subtitle, children, tourId, className = "" }) {
  return (
    <section className={`panel ${className}`} data-tour={tourId}>
      {title && (
        <div className="panel-head">
          <div>
            <h2 className="panel-title">{title}</h2>
            {subtitle && <p className="panel-subtitle">{subtitle}</p>}
          </div>
        </div>
      )}
      <div className="panel-body">{children}</div>
    </section>
  );
}

export default function DriverSeason() {
  const { code, season } = useParams();
  const navigate = useNavigate();
  const { seasonOptions } = useSeason();

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const resolvedSeason = season === "current" ? new Date().getFullYear() : Number(season);
  const options = seasonOptions.length
    ? seasonOptions.map((o) => ({ label: o.label, value: String(o.value) }))
    : [{ label: "Current", value: "current" }, { label: String(resolvedSeason - 1), value: String(resolvedSeason - 1) }];

  useEffect(() => {
    setData(null);
    setError(null);
    fetchDriverSeason(code, resolvedSeason).then(setData).catch((e) => setError(e.message));
  }, [code, resolvedSeason]);

  const header = (
    <PageHeader
      kicker="Driver season analysis"
      title={data?.driver?.name || code}
      season={resolvedSeason}
      subtitle="Season form from race results: finishing consistency, qualifying-versus-race deltas and points progression."
      actions={
        <select className="select-broadcast" value={String(season)} onChange={(e) => navigate(`/driver/${code}/season/${e.target.value}`)} aria-label="Season">
          {options.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      }
    />
  );

  if (error) return <div className="py-6">{header}<div className="panel panel-plain border-f1/40 p-4 text-f1">{error}</div></div>;
  if (!data) return <div className="py-6">{header}<p className="text-muted animate-pulse">Loading season analytics…</p></div>;

  const { driver, metrics, radar, teammate } = data;

  return (
    <div className="py-6 space-y-6">
      {header}

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.6fr] gap-6">
        <Panel tourId="driver-card">
          <DriverHeader driver={driver} season={resolvedSeason}
                        points={Number.isFinite(metrics.total_points) ? metrics.total_points : 0}
                        position={metrics.championship_position} />
          <div className="grid grid-cols-3 gap-3 mt-5">
            <div className="stat-tile"><div className="stat-label">Wins</div><div className="stat-value">{metrics.wins ?? 0}</div></div>
            <div className="stat-tile"><div className="stat-label">Podiums</div><div className="stat-value">{metrics.podiums ?? 0}</div></div>
            <div className="stat-tile"><div className="stat-label">Points</div><div className="stat-value">{metrics.total_points ?? 0}</div></div>
          </div>
          <div className="grid grid-cols-3 gap-3 mt-3">
            <div className="stat-tile"><div className="stat-label">Avg finish</div><div className="stat-value">{metrics.avg_finish ?? "–"}</div></div>
            <div className="stat-tile"><div className="stat-label">DNFs</div><div className="stat-value">{metrics.dnf_count ?? 0}</div></div>
            <div className="stat-tile"><div className="stat-label">Pts / race</div><div className="stat-value">{metrics.points_per_race ?? 0}</div></div>
          </div>
        </Panel>

        <Panel tourId="radar" title="Season performance"
               subtitle={teammate?.driver?.code ? `Radar scores out of 100 · teammate ${teammate.driver.code} on the same scale` : "Radar scores out of 100"}>
          <div className="h-[300px]">
            <RadarComparison radar={radar || {}} />
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel tourId="points-trend" title="Points trend" subtitle="Points scored per round">
          <PointsTrend pointsByRace={metrics.points_by_race || []} />
        </Panel>
        <Panel tourId="quali-delta" title="Qualifying vs race" subtitle="Places gained (green) or lost (red) from grid to flag">
          <QualiRaceDelta deltas={metrics.q_vs_race?.by_race || []} />
        </Panel>
      </div>
    </div>
  );
}
