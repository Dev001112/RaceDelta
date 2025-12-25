// src/api/client.js
// Single source of truth for RaceDelta frontend API access

const base = "http://127.0.0.1:8000";

/* --------------------------------------------------
   INTERNAL HELPERS
-------------------------------------------------- */

function _log(...args) {
  if (typeof console !== "undefined" && console.debug) {
    console.debug("[client]", ...args);
  }
}

async function _parseErrorResponse(res) {
  const text = await res.text().catch(() => "");
  try {
    const json = text ? JSON.parse(text) : null;
    if (json && typeof json === "object") {
      return json.error || json.message || json.detail || JSON.stringify(json);
    }
    return `${res.status} ${res.statusText}`;
  } catch {
    return `${res.status} ${res.statusText}: ${text}`;
  }
}

export async function safeFetch(path, opts = {}) {
  const url = `${base}${path}`;
  _log("fetch ->", url, opts.method || "GET");

  const fetchOpts = {
    method: opts.method || "GET",
    mode: "cors",
    credentials: "omit",
    headers: {
      Accept: "application/json",
      ...(opts.body && !(opts.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...(opts.headers || {})
    },
    ...opts
  };

  let res;
  try {
    res = await fetch(url, fetchOpts);
  } catch (err) {
    throw new Error(`Network error: ${err.message || err}`);
  }

  if (!res.ok) {
    const errMsg = await _parseErrorResponse(res);
    throw new Error(errMsg);
  }

  try {
    return await res.json();
  } catch {
    throw new Error("Invalid JSON response from server");
  }
}

/* --------------------------------------------------
   CORE DATA
-------------------------------------------------- */

// -----------------------------
// DRIVERS (FIXED)
// -----------------------------

// -----------------------------
// DRIVERS (FIXED FOR ALL CASES)
// -----------------------------

let _driversCache = null;

export async function fetchDrivers() {
  if (_driversCache) {
    return _driversCache;
  }

  const res = await safeFetch("/api/drivers");

  // ✅ Accept BOTH backend formats
  const raw = Array.isArray(res)
    ? res
    : Array.isArray(res?.drivers)
      ? res.drivers
      : [];

  if (raw.length === 0) {
    console.error("Invalid drivers response:", res);
    return [];
  }

  // Normalize ONCE — frontend contract
  const cleaned = raw
    .filter(
      (d) =>
        d.driver_code &&
        d.driver_name &&
        d.team &&
        d.driver_number !== null
    )
    .map((d) => ({
      code: d.driver_code,
      name: d.driver_name,
      number: d.driver_number,
      team: d.team,
      country: d.country_code || "",
      photo: d.headshot_url || null
    }));

  _driversCache = cleaned;
  return cleaned;
}

export function fetchRaces(year) {
  const q = year ? `?year=${encodeURIComponent(year)}` : "";
  return safeFetch(`/api/meetings${q}`);
}

export function fetchSessions(meetingKey) {
  const q = meetingKey
    ? `?meeting_key=${encodeURIComponent(meetingKey)}`
    : "";
  return safeFetch(`/api/sessions${q}`);
}

export function fetchLaps(sessionKey, driverNumber) {
  const params = [];
  if (sessionKey) params.push(`session_key=${encodeURIComponent(sessionKey)}`);
  if (driverNumber)
    params.push(`driver_number=${encodeURIComponent(driverNumber)}`);
  const q = params.length ? `?${params.join("&")}` : "";
  return safeFetch(`/api/laps${q}`);
}

export function fetchPosition(sessionKey, driverNumber) {
  const params = [];
  if (sessionKey) params.push(`session_key=${encodeURIComponent(sessionKey)}`);
  if (driverNumber)
    params.push(`driver_number=${encodeURIComponent(driverNumber)}`);
  const q = params.length ? `?${params.join("&")}` : "";
  return safeFetch(`/api/position${q}`);
}

/* --------------------------------------------------
   TEAMS
-------------------------------------------------- */

export function fetchTeams() {
  return safeFetch("/api/teams");
}

export function fetchTeamDetail(constructorId) {
  return safeFetch(`/api/teams/${constructorId}`);
}

/* --------------------------------------------------
   STANDINGS
-------------------------------------------------- */

export function fetchStandingsLatest(year) {
  const q = year ? `?year=${encodeURIComponent(year)}` : "";
  return safeFetch(`/api/standings/latest${q}`);
}

export function fetchDriverStandings(year) {
  const q = year ? `?year=${encodeURIComponent(year)}` : "";
  return safeFetch(`/api/standings/drivers${q}`);
}

export function fetchConstructorStandings(year) {
  const q = year ? `?year=${encodeURIComponent(year)}` : "";
  return safeFetch(`/api/standings/constructors${q}`);
}

/* --------------------------------------------------
   ANALYTICS / DRIVER COMPARISON
-------------------------------------------------- */

export function fetchDriverSeason(driverCode, season) {
  if (!driverCode || !season) {
    throw new Error("driverCode and season are required");
  }
  return safeFetch(
    `/api/l1/season?driver_code=${driverCode}&season=${season}`
  );
}

export function fetchDriverTimeline({ driver1, driver2, season }) {
  return safeFetch(
    `/api/compare/drivers/timeline?driver1=${driver1}&driver2=${driver2}&season=${season}`
  );
}

export function fetchDriverComparison({ driver1, driver2, season }) {
  return safeFetch(
    `/api/compare/drivers?driver1=${driver1}&driver2=${driver2}&season=${season}`
  );
}

/* --------------------------------------------------
   HEALTH
-------------------------------------------------- */

export function ping() {
  return safeFetch("/");
}

/* --------------------------------------------------
   DEFAULT EXPORT
-------------------------------------------------- */

const client = {
  safeFetch,
  fetchDrivers,
  fetchRaces,
  fetchSessions,
  fetchLaps,
  fetchPosition,
  fetchTeams,
  fetchTeamDetail,
  fetchStandingsLatest,
  fetchDriverStandings,
  fetchConstructorStandings,
  fetchDriverSeason,
  fetchDriverComparison,
  fetchDriverTimeline,
  ping
};

export default client;
