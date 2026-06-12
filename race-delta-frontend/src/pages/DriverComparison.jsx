import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import client from "../api/client";

import DriverSelect from "../components/DriverSelect";
import CompareHeader from "../components/CompareHeader";
import CompareCharts from "../components/CompareCharts";
import DriverCompareTable from "../components/DriverCompareTable";

/* -------------------------------
   Normalize comparison response
-------------------------------- */
function normalizeComparison(res, driver1, driver2) {
  if (res?.data?.driverA && res?.data?.driverB) {
    return {
      source: res.source,
      drivers: {
        [driver1]: res.data.driverA,
        [driver2]: res.data.driverB
      }
    };
  }

  return res;
}

import { useSeason } from "../context/SeasonContext";

export default function DriverComparison() {
  const { seasonOptions, displaySeason } = useSeason();
  const [searchParams, setSearchParams] = useSearchParams();
  const [drivers, setDrivers] = useState([]);

  const paramD1 = searchParams.get("d1") || "";
  const paramD2 = searchParams.get("d2") || "";
  const paramSeason = searchParams.get("season") || "";

  const [driver1, setDriver1] = useState(paramD1);
  const [driver2, setDriver2] = useState(paramD2);
  const [season, setSeason] = useState(paramSeason || displaySeason || "current");

  // Sync state with URL parameter updates
  useEffect(() => {
    if (paramD1) setDriver1(paramD1);
    if (paramD2) setDriver2(paramD2);
    if (paramSeason) setSeason(paramSeason);
  }, [paramD1, paramD2, paramSeason]);

  // Sync season with displaySeason if no custom season param exists
  useEffect(() => {
    if (displaySeason && !paramSeason) {
      setSeason(displaySeason);
    }
  }, [displaySeason, paramSeason]);

  const [comparison, setComparison] = useState(null);
  const [timeline, setTimeline] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  /* -------------------------------
     Load drivers when season changes
-------------------------------- */
  useEffect(() => {
    client.fetchDrivers(season)
      .then(setDrivers)
      .catch((err) => {
        console.error(err);
        setError("Failed to load drivers");
      });
  }, [season]);

  const d1 = drivers.find(d => d.code === driver1);
  const d2 = drivers.find(d => d.code === driver2);

  // Core comparison fetcher
  async function runComparison(d1Code, d2Code, seasonYear) {
    try {
      setLoading(true);
      setError("");
      setComparison(null);
      setTimeline(null);

      const statsRes = await client.fetchDriverComparison({
        driver1: d1Code,
        driver2: d2Code,
        season: seasonYear
      });

      setComparison(normalizeComparison(statsRes, d1Code, d2Code));

      const timelineRes = await client.fetchDriverTimeline({
        driver1: d1Code,
        driver2: d2Code,
        season: seasonYear
      });

      setTimeline(timelineRes);

    } catch (err) {
      console.error(err);
      setError("Failed to compare drivers");
    } finally {
      setLoading(false);
    }
  }

  // Auto-trigger comparison when drivers list is loaded and we have deep-linked params
  useEffect(() => {
    if (drivers.length > 0 && driver1 && driver2 && !comparison && !loading) {
      runComparison(driver1, driver2, season);
    }
  }, [drivers, driver1, driver2, season]);

  /* -------------------------------
     Compare action from manual click
-------------------------------- */
  async function handleCompare() {
    if (!driver1 || !driver2) {
      setError("Please select two drivers");
      return;
    }

    if (driver1 === driver2) {
      setError("Please select two different drivers");
      return;
    }

    // Update URL params
    setSearchParams({ d1: driver1, d2: driver2, season });
    
    // Run comparison
    await runComparison(driver1, driver2, season);
  }

  /* -------------------------------
     UI
-------------------------------- */
  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-10 text-white">

      <h1 className="text-3xl font-bold">Driver Comparison</h1>

      {/* Selectors */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

        <DriverSelect
          label="Driver 1"
          drivers={drivers}
          value={driver1}
          onChange={setDriver1}
        />

        {/* ✅ FIXED SEASON SELECT */}
        <div className="flex flex-col gap-2">
          <label className="text-sm text-gray-400">
            Season
          </label>

          <select
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            className="bg-[#0f172a] border border-gray-700 rounded-lg p-3 text-white h-[52px]"
          >
            {seasonOptions.length > 0 ? (
              seasonOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))
            ) : (
              <option value="current">Current Season</option>
            )}
          </select>
        </div>

        <DriverSelect
          label="Driver 2"
          drivers={drivers}
          value={driver2}
          onChange={setDriver2}
        />
      </div>

      {/* Compare header */}
      {d1 && d2 && (
        <CompareHeader
          leftDriver={d1}
          rightDriver={d2}
          onCompare={handleCompare}
          disabled={loading}
        />
      )}

      {loading && (
        <div className="text-gray-400 animate-pulse">
          Loading comparison…
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 p-4 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {comparison?.drivers && (
        <DriverCompareTable
          aCode={driver1}
          bCode={driver2}
          a={comparison.drivers[driver1]}
          b={comparison.drivers[driver2]}
        />
      )}

      {timeline?.rounds?.length > 0 && (
        <CompareCharts
          data={timeline}
          driver1={driver1}
          driver2={driver2}
        />
      )}
    </div>
  );
}
