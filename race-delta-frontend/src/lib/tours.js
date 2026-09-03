import { matchPath } from "react-router-dom";

/* Per-page guided tours. Targets are data-tour="id" attributes on the page. A step with no
   target is shown centred. Steps whose target is missing on the page are skipped at runtime. */

const step = (target, title, body) => ({ target, title, body });

const TOURS = [
  {
    path: "/", key: "home", steps: [
      step(null, "Welcome to the pit wall",
        "RaceDelta turns Formula 1 timing data into explainable analysis. This dashboard is the overview: standings, the race calendar and quick access to every tool. Each page has its own guide; the Guide button in the header replays it any time."),
      step("season", "Choose a season",
        "Every page follows this season. Pick a past season to explore its races, or stay on the current one for live standings."),
      step("calendar", "Race calendar",
        "Completed rounds show the winner. Click any race for full results, weather, tyre stints and the position chart."),
      step("tower", "Championship tower",
        "Live driver standings in timing-tower form. Click a driver to open their season analysis: radar, points trend and qualifying-versus-race deltas."),
      step("compare", "Compare two drivers",
        "Pick any two drivers to run a head-to-head on lap pace, sectors, consistency, tyre management, pit stops and more."),
      step("nav", "The analysis tools",
        "AI Lab rates drivers and clusters driving styles. Strategy Lab replays races and simulates pit strategies. Analyst answers questions in plain language. All of it comes from RaceDelta's own telemetry."),
    ],
  },
  {
    path: "/drivers", key: "drivers", steps: [
      step(null, "Driver lineup", "Every driver in the selected season, colour-coded by team."),
      step("driver-grid", "Open a driver", "Click a card to see their season: form, consistency, qualifying-versus-race and points progression."),
    ],
  },
  {
    path: "/driver/:code/season/:season", key: "driver-season", steps: [
      step("driver-card", "Season snapshot", "Wins, podiums and points for this driver in the selected season."),
      step("radar", "Performance radar", "Five normalised scores out of 100: points efficiency, consistency, racecraft, reliability and winning impact. The teammate overlay uses the same scale."),
      step("points-trend", "Points trend", "Points earned at each round through the season."),
      step("quali-delta", "Qualifying versus race", "Places gained (green) or lost (red) between the grid and the chequered flag, round by round."),
    ],
  },
  {
    path: "/teams", key: "teams", steps: [
      step(null, "Constructors", "Every team in the standings with position, points and wins."),
      step("team-grid", "Open a team", "Click a team for its driver lineup, team principal, engine and car."),
    ],
  },
  {
    path: "/teams/:constructorId", key: "team-detail", steps: [
      step("team-header", "Team profile", "Championship position, points, wins and the current driver lineup."),
    ],
  },
  {
    path: "/race/:season/:round", key: "race", steps: [
      step("race-header", "Race overview", "Circuit, date and the headline result for this Grand Prix."),
      step("race-weather", "Track conditions", "Average air and track temperature, humidity and whether it rained."),
      step("race-cards", "Winner and best climber", "Who won, and who gained the most places from their grid slot."),
      step("position-chart", "Position chart", "How the running order changed through the race."),
      step("stints", "Tyre strategies", "Each driver's compounds and stint lengths."),
      step("results", "Classification", "Full results with grid positions, gaps to the leader and the fastest lap."),
    ],
  },
  {
    path: "/compare/drivers", key: "compare", steps: [
      step("compare-select", "Pick two drivers", "Choose two drivers first. Every section below compares the same pair."),
      step("compare-sections", "Four ways to compare",
        "Season: the latest race plus the points timeline. Race: any single Grand Prix, lap by lap. Track: every visit to one circuit across seasons. Conditions: only wet, dry, safety-car, hot or cool races."),
      step("compare-controls", "Narrow it down", "Each section has its own picker: a season, a race, a track, or a condition chip. Deep links keep your choice in the URL."),
      step("compare-track-map", "Sector map", "The circuit traced from telemetry and cut at the official sector timing points. Each sector takes the colour of the driver with the faster average sector time; grey means level within two hundredths."),
      step("compare-verdict", "AI verdict", "Who is better on this set and in which areas. Nine areas are scored by fixed rules from the telemetry features; when a language model is configured it writes the prose, using only those numbers."),
      step("compare-graphs", "Profile and gaps", "The radar scores each area between the two drivers. The bars show the pace gap race by race, or sector by sector for a single race: red means Driver A was faster, blue Driver B."),
      step("compare-table", "Head-to-head", "Average and best laps plus telemetry features: consistency, pace trend, tyre degradation, pit stops, overtakes and penalties. Green marks the better value. In Track and Conditions the numbers are averages over every matching race."),
      step("compare-breakdown", "Race by race", "Where the averages come from: finish, pace delta and the winner of each race in the set, with wet and safety-car flags."),
    ],
  },
  {
    path: "/ai", key: "ai-lab", steps: [
      step(null, "AI Lab", "Machine-learning views of the season, built from lap-level telemetry features rather than championship points."),
      step("rating", "AI Driver Rating", "Drivers scored 0 to 100 on nine telemetry-derived dimensions. Every feature is compared within its own race first, so Monaco and Monza are comparable. Click a driver to load their DNA."),
      step("clusters", "Driving-style clusters", "A map of driver DNA vectors, grouped by K-Means, DBSCAN or hierarchical clustering and labelled by their dominant trait."),
      step("dna", "Driver DNA", "The selected driver's profile as a radar, with the most similar drivers by cosine similarity."),
    ],
  },
  {
    path: "/strategy", key: "strategy", steps: [
      step("strategy-select", "Pick a race and driver", "Rounds not yet loaded are ingested the first time you open them, which takes up to a minute."),
      step("lap-slider", "Scrub through the race", "Drag to any lap to reconstruct the race state at that moment."),
      step("state", "Race state", "Position, tyre compound and age, gaps to the cars around, track status and laps remaining."),
      step("decisions", "Team versus AI", "What the team actually did on this lap, next to what RaceDelta's strategist recommends, with its reasons and confidence. Purple always marks AI output."),
      step("lap-chart", "Lap-time trace", "Real pit stops in red against the AI's suggested stops in green."),
      step("simulator", "Simulate a what-if", "Change pit laps and compounds, add a Safety Car or rain, then get the predicted finish, race time, podium probability and time saved from a per-race pace model."),
    ],
  },
  {
    path: "/analyst", key: "analyst", steps: [
      step("analyst-mode", "Live or offline", "Green means Claude answers using data tools. Amber means offline intent mode: your question is routed to the same tools without an API key."),
      step("analyst-race", "Set the context", "Pick a race for race-specific questions, or Season-wide for ratings and driver DNA."),
      step("analyst-suggest", "Start from a question", "Use a suggestion or type your own. Every answer lists its sources: the data tools that produced it."),
      step("analyst-input", "Ask anything about the race", "Pace, sectors, stints, pit stops, strategy calls, or why a team lost."),
    ],
  },
  {
    path: "/stats", key: "stats", steps: [
      step("standings", "Standings", "Switch between drivers and constructors. Click a name to open its page."),
    ],
  },
];

export function getTour(pathname) {
  for (const t of TOURS) {
    if (matchPath({ path: t.path, end: true }, pathname)) return t;
  }
  return null;
}
