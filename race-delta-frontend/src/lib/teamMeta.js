// src/lib/teamMeta.js
// Centralized mapping of F1 teams to official HEX colors and display configurations.

export const TEAM_COLORS = {
  red_bull: "#3671C6",
  ferrari: "#F91536",
  mercedes: "#27F4D2",
  mclaren: "#FF8000",
  aston_martin: "#229971",
  alpine: "#0093CC",
  williams: "#37BEDD",
  haas: "#B6BABD",
  rb: "#6692FF",
  sauber: "#52E252",
  audi: "#F50A25",
  unknown: "#7F8C8D"
};

export const TEAM_ALIASES = {
  "red_bull_racing": "red_bull",
  "scuderia_ferrari": "ferrari",
  "mercedes_amg_petronas_f1_team": "mercedes",
  "mclaren_racing": "mclaren",
  "aston_martin_aramco_cognizant_f1_team": "aston_martin",
  "alpine_f1_team": "alpine",
  "williams_racing": "williams",
  "haas_f1_team": "haas",
  "scuderia_alphatauri": "rb",
  "alphatauri": "rb",
  "racing_bulls": "rb",
  "rb": "rb",
  "alfa_romeo": "sauber",
  "alfa_romeo_racing": "sauber",
  "kick_sauber": "sauber",
  "stake_f1_team_kick_sauber": "sauber",
  "audi": "sauber",
  "mclaren": "mclaren",
  "mercedes": "mercedes",
  "ferrari": "ferrari",
  "williams": "williams",
  "alpine": "alpine",
  "aston_martin": "aston_martin",
  "haas": "haas"
};

export function getTeamKey(teamNameOrId) {
  if (!teamNameOrId) return "unknown";
  
  // Normalize string for key matching
  const normalized = teamNameOrId.toLowerCase().replace(/[\s-]/g, "_");
  
  if (TEAM_ALIASES[normalized]) return TEAM_ALIASES[normalized];
  
  // Try substring checks for loose matching
  if (normalized.includes("red_bull") || normalized.includes("redbull")) return "red_bull";
  if (normalized.includes("ferrari")) return "ferrari";
  if (normalized.includes("mercedes")) return "mercedes";
  if (normalized.includes("mclaren")) return "mclaren";
  if (normalized.includes("aston_martin") || normalized.includes("aston")) return "aston_martin";
  if (normalized.includes("alpine")) return "alpine";
  if (normalized.includes("williams")) return "williams";
  if (normalized.includes("haas")) return "haas";
  if (normalized.includes("racing_bulls") || normalized.includes("alphatauri") || normalized.includes("vcarb") || normalized.includes("rb")) return "rb";
  if (normalized.includes("sauber") || normalized.includes("alfa_romeo")) return "sauber";
  if (normalized.includes("audi")) return "audi";
  
  return "unknown";
}

export function getTeamColor(teamNameOrId) {
  const key = getTeamKey(teamNameOrId);
  return TEAM_COLORS[key] || TEAM_COLORS.unknown;
}

export function getDriverAbbreviation(driverName, driverCode) {
  if (driverCode) return driverCode.toUpperCase();
  if (!driverName) return "DRV";
  const parts = driverName.trim().split(" ");
  if (parts.length === 1) return parts[0].slice(0, 3).toUpperCase();
  return parts[parts.length - 1].slice(0, 3).toUpperCase();
}
