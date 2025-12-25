// src/lib/api.js

// --------------------------------------------------
// API BASE
// --------------------------------------------------
// Keep backend configurable via .env
const API_BASE =
  import.meta.env.VITE_API_BASE ||
  "http://127.0.0.1:8000/api";

// --------------------------------------------------
// GENERIC HELPER
// --------------------------------------------------
async function apiFetch(url, errorMessage) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(errorMessage || "API request failed");
  }
  return res.json();
}

// --------------------------------------------------
// DRIVERS
// --------------------------------------------------
export async function fetchDrivers() {
  return apiFetch(
    `${API_BASE}/drivers`,
    "Failed to fetch drivers"
  );
}

// --------------------------------------------------
// TEAMS
// --------------------------------------------------
export async function fetchTeams() {
  return apiFetch(
    `${API_BASE}/teams`,
    "Failed to fetch teams"
  );
}

export async function fetchTeamDetail(constructorId) {
  return apiFetch(
    `${API_BASE}/teams/${constructorId}`,
    `Failed to fetch team ${constructorId}`
  );
}

// --------------------------------------------------
// STANDINGS
// --------------------------------------------------
export async function fetchDriverStandings() {
  return apiFetch(
    `${API_BASE}/standings/drivers`,
    "Failed to fetch driver standings"
  );
}

export async function fetchConstructorStandings() {
  return apiFetch(
    `${API_BASE}/standings/constructors`,
    "Failed to fetch constructor standings"
  );
}

// --------------------------------------------------
// L1 — SEASON ANALYTICS (FROZEN CONTRACT)
// --------------------------------------------------
/**
 * Fetch season-level analytics for a driver
 * Includes:
 * - metrics
 * - radar normalization
 * - teammate overlay
 */
export async function fetchDriverSeason(driverCode, season) {
  if (!driverCode || !season) {
    throw new Error("driverCode and season are required");
  }

  return apiFetch(
    `${API_BASE}/l1/season?driver_code=${driverCode}&season=${season}`,
    "Failed to fetch L1 season analytics"
  );
}

// --------------------------------------------------
// FUTURE-READY PLACEHOLDERS (DO NOT REMOVE)
// --------------------------------------------------
// export async function fetchL2TrackAnalytics(...) {}
// export async function fetchL3LapAnalytics(...) {}

export async function fetchDriverComparison({ driver1, driver2, season }) {
  const res = await fetch(
    `http://127.0.0.1:8000/api/compare/drivers?driver1=${driver1}&driver2=${driver2}&season=${season}`
  );

  if (!res.ok) {
    throw new Error("Failed to fetch driver comparison");
  }

  return res.json();
}
