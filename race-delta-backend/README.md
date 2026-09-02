RaceDelta backend (position + standings approx) - v5
---------------------------------------------------
This build includes:
- /api/meetings, /api/sessions, /api/drivers
- /api/position (bulk + per-driver + fallback)
- /api/session_positions (bulk)
- /api/laps
- /api/standings (try OpenF1 standings, fallback to positions-based approx)
- /api/latest_winner and /api/latest_podium (auto-discover latest race and use session_result)
- Simple DB caching via APICache (optional)

Quick run (Windows CMD):
1. python -m venv venv
2. venv\Scripts\activate
3. pip install -r requirements.txt
4. set OPENF1_BASE=https://api.openf1.org/v1
5. set DATABASE_URL=sqlite:///racedelta.db
6. set FLASK_DEBUG=1
7. python app.py

Notes:
- If your OpenF1 instance lacks session_result for the latest race, latest_winner/latest_podium will return 404.
- compute_standings_from_positions uses last position sample per driver per race as a best-effort approximation.

Phase 2 — telemetry storage + feature engineering
------------------------------------------------
New tables (created by `python create_tables.py`): race_sessions, laps, stints, driver_race_features
(the AI-ready feature store: one standardized row per driver per race).

Endpoints
- GET  /api/features/race?season=2025&round=1        per-driver features for a race (ingests from FastF1 on first call)
- GET  /api/features/driver?driver_code=VER&season=2025   all ingested races for a driver + season aggregates
- GET  /api/compare/drivers?driver1=NOR&driver2=VER&season=2025   now returns `features` per driver (from the store)
- POST /api/admin/ingest/telemetry/<year>/<round>    (re)ingest one race
- POST /api/admin/ingest/telemetry/<year>            backfill every completed round

Backfill a whole season from the CLI:
    python scripts/backfill_features.py 2025

Feature math lives in app/services/feature_engineering.py (pure pandas, no DB);
tests: python -m unittest tests.test_feature_engineering

Phase 3 — driver intelligence (rating / DNA / clustering)
---------------------------------------------------------
Built on the feature store; maths in app/services/driver_intelligence.py (scikit-learn).
Every feature is z-scored within its race against the field, then averaged over the season.

- GET /api/ai/rating?season=2025                         AI Driver Rating, ranked 0–100 with component scores
- GET /api/ai/dna?season=2025&driver_code=VER&k=5        Driver DNA vector + most similar drivers (cosine) + PCA coords
- GET /api/ai/clusters?season=2025&method=kmeans&k=4     Style clusters (kmeans | dbscan | hierarchical) on a 2-D PCA map

Frontend: /ai ("AI Lab" in the navbar). Tests: python -m unittest tests.test_driver_intelligence
Results are cached for 1h and keyed by the store's row count, so they refresh after each ingest.

Phase 4 — Strategy Lab (replay / simulator)
-------------------------------------------
app/services/strategy_lab.py (explainable rule-based strategist + what-if simulator) and
app/services/pace_model.py (per-race XGBoost lap-time model, linear fallback). Uses the laps/stints tables.

- GET  /api/strategy/races?season=2025                                  rounds available in the store
- GET  /api/strategy/race?season=2025&round=1                           drivers + real strategies, compounds, pit loss, SC laps, model
- GET  /api/strategy/replay?season=2025&round=1&driver_code=VER&lap=30   race state, team decision vs AI recommendation, full timeline
- POST /api/strategy/simulate  {season, round, driver_code, start_compound?, pit_stops:[{lap, compound}], safety_car?:{lap, laps}, weather?}
       -> predicted finish, estimated race time, position gain, podium probability, time saved, explanation

Frontend: /strategy ("Strategy" in the navbar). Tests: python -m unittest tests.test_strategy_lab

Phase 5 — AI Race Analyst (conversational, tool-grounded)
--------------------------------------------------------
app/services/race_analyst.py (Claude tool-calling loop, claude-opus-5 with server-side refusal fallbacks)
+ app/services/race_analyst_tools.py (9 tools over the feature store, laps/stints, Strategy Lab and driver
intelligence). The model may only answer from tool results. Set ANTHROPIC_API_KEY (and optionally
ANALYST_MODEL) in .env; without a key the analyst runs in offline intent mode (rule-based routing to the
same tools) so demos work without an LLM.

- GET  /api/analyst/status                       mode (claude | offline), model, tools, suggested questions
- POST /api/analyst/ask  {question, season, round?, history?:[{role, content}]}
       -> {answer, mode, model, tools_used:[{name, input, summary}], usage}

Frontend: /analyst ("Analyst" in the navbar). Tests: python -m unittest tests.test_race_analyst
