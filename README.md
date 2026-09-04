<p align="center">
  <img src="race-delta-frontend/public/logo.png" alt="RaceDelta" width="380">
</p>

<p align="center">
  <strong>Formula 1 telemetry and analytics.</strong><br>
  Lap-by-lap driver comparison, tyre strategy modelling, ML driver ratings, and an AI race analyst.
</p>

<p align="center">
  <a href="https://race-delta0.vercel.app">Live app</a> ·
  <a href="https://racedelta.onrender.com/api/health">API</a>
</p>

---

## What it does

Most F1 sites give you tables. RaceDelta computes the differences between drivers and explains where they come from.

### Compare

Any two drivers, four ways:

| Mode | What it answers |
|---|---|
| **Season** | Head-to-head on the latest race, plus cumulative points across the year |
| **Race** | One Grand Prix, lap by lap |
| **Track** | Every visit to a single circuit |
| **Conditions** | Wet, dry, safety car, VSC, hot track (≥40 °C), cool track (<25 °C) |

### AI Lab

- **Driver Rating** — a 0–100 season score built from within-race z-scores across race pace, qualifying pace, consistency, tyre management, overtaking, defence and discipline.
- **Driving DNA** — a per-driver strength vector plus the most similar drivers by cosine similarity.
- **Clustering** — k-means, DBSCAN or agglomerative grouping of drivers by driving style, with generated labels ("Qualifying Specialists", etc.).

### Strategy Lab

Tyre degradation per compound, stint analysis, pit-stop timing, and a pace model that predicts lap times from stint state. Uses XGBoost when available and falls back to a linear model when it isn't.

### AI Race Analyst

Ask questions in plain language ("who's the strongest contender", "what's Antonelli's driving style"). The model answers through tool calls against the same endpoints the UI uses, and shows which tools it called. Runs on NVIDIA NIM or the Anthropic API; without a key it degrades to an offline intent mode.

### Dashboard, Drivers, Teams

Live standings, race calendar, session results, per-round analytics with weather telemetry, tyre stint timelines and position-change charts.

---

## Data

| Source | Used for |
|---|---|
| [FastF1](https://github.com/theOehrly/Fast-F1) | Lap timing, telemetry, weather, track status |
| [OpenF1](https://openf1.org) | Live driver roster, sessions, meetings, stints |
| [Jolpica](https://api.jolpi.ca) | Standings and schedule — the successor to the retired Ergast API |

The deployed instance ships with a pre-ingested snapshot of the 2026 season: **12 races, 14,101 laps, 762 stints**.

---

## Running locally

**Backend**

```bash
cd race-delta-backend
python -m venv venv && venv/Scripts/activate     # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                             # then fill in the values you need
python app.py                                    # http://127.0.0.1:8000
```

The schema is created automatically at startup. To populate the database with a season:

```bash
python ingest_local.py
```

**Frontend**

```bash
cd race-delta-frontend
npm install
echo "VITE_API_BASE=http://127.0.0.1:8000" > .env.local
npm run dev                                      # http://localhost:5173
```

---

## Configuration

Backend, all optional except in production:

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///racedelta.db` | Postgres works too |
| `CORS_ORIGINS` | `*` in dev, **empty in production** | Comma-separated, no trailing slashes. Production allows nothing until you set it. |
| `FLASK_ENV` | `development` | `production` turns off debug and shortens standings computation |
| `NVIDIA_API_KEY` / `ANTHROPIC_API_KEY` | — | Enables the AI Analyst; NVIDIA takes precedence |
| `ADMIN_TOKEN` | — | Admin ingestion endpoints stay disabled unless set |
| `RACEDELTA_CACHE_DIR` | `.cache` | Persistent JSON cache with stale-while-revalidate |
| `FASTF1_CACHE_DIR` | `./fastf1_cache` | FastF1's on-disk session cache |

Frontend:

| Variable | Notes |
|---|---|
| `VITE_API_BASE` | Backend origin, no trailing slash. **Baked in at build time** — changing it requires a rebuild. |

---

## Deployment

**Backend** — Docker, on any container host. The included `Dockerfile` is sized for a 512 MB / 0.1 CPU instance: one gunicorn worker with eight threads, and the computed cache plus the season database baked into the image so a cold start serves real data without refetching.

```
Root Directory   race-delta-backend
Dockerfile Path  ./Dockerfile
Health Check     /api/health
```

**Frontend** — any static host. Root directory `race-delta-frontend`, Vite preset. `vercel.json` supplies the SPA rewrite that React Router needs for deep links.

Refresh the shipped season data with:

```bash
cd race-delta-backend && python ingest_local.py
git add -f data/racedelta.db && git commit -m "chore: refresh season data"
```

---

## Tech stack

**Frontend** — React 18, Vite, Tailwind, React Router, Recharts, Plotly, Chart.js, Framer Motion

**Backend** — Flask, SQLAlchemy, FastF1, pandas, NumPy, scikit-learn, XGBoost (optional), gunicorn

---

## Project layout

```
race-delta-backend/
  app/
    routes/          core, compare, lab, admin, openf1
    services/        f1_service, ingestor, feature_store, strategy_lab,
                     driver_intelligence, race_analyst, compare_lab, cache_store
  models.py          10 tables: races, race_sessions, laps, stints,
                     driver_race_features, drivers, constructors, ...
  scripts/           Jolpica/Ergast standings and team lookups
  data/              pre-ingested season database
  .cache/            precomputed API responses shipped with the image

race-delta-frontend/
  src/routes/        Home, Compare, Drivers, Teams, Lab, Strategy, Analyst, Race
  src/components/    Navbar, cards, charts, comparison tables
  src/api/client.js  single source of truth for API access
```

---

## Notes and limits

- The deployed season data is a **snapshot**, not a live feed. Standings and the driver roster are live; Compare, Strategy and AI Lab read the shipped database until it's regenerated.
- Free-tier hosting sleeps after 15 minutes idle, so the first request after a quiet period takes ~50 s.
- `/api/compare/track-map` loads full telemetry and is memory-hungry; it needs more than 512 MB.
