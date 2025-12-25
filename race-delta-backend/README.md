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
