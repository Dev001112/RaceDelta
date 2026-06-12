# RaceDelta

Making Formula 1 data easier to explore, compare, and understand.

RaceDelta is a Formula 1 data analysis and visualization platform designed for fans who want more than just standings and headlines.

Instead of only showing what happened in a race or season, RaceDelta focuses on how drivers and teams compare, where performance differences come from, and how form changes over time.

---

## What is RaceDelta?

RaceDelta turns raw Formula 1 data into clear, visual, and comparable insights.

Most F1 websites give you tables and numbers. RaceDelta connects those numbers and tells a story:
- How drivers perform across different tracks  
- How teammates compare under the same car  
- How form evolves through a season  

The platform uses modern F1 data sources like **OpenF1** and **FastF1**, with custom logic on top to compute meaningful comparisons.

---

## Core Features

### 📺 F1 Broadcast Aesthetic Design (New)
The platform is styled to mimic official Formula 1 TV broadcast graphics:
- **Leaderboard Timing Towers**: Standing towers styled like the live timing tower with flat, team-color left borders.
- **Condensed Sports Typography**: Modern fonts (`Barlow Condensed` and `Titillium Web`) used for racing codes, positions, and labels.
- **Spotlight Cards**: Premium cards spotlighting the race winner and the climber (Driver of the Day/Best Driver) with official high-resolution driver headshots.

---

### 📊 Dynamic Race Analytics Dashboard (New)
A comprehensive telemetry and analytics dashboard for each round:
- **Dynamic Calendar Strip**: Displays all GP races dynamically ordered with the latest completed race first, followed by previous races (reverse chronological order), and then upcoming races (chronological order).
- **Weather Telemetry Strip**: A horizontal panel showing average air temperature, track temperature, humidity, and rainfall flags.
- **Interactive Tyre Stints Timeline**: Visualized timeline showing each driver's tire stint compounds (Soft, Medium, Hard, Inter, Wet) and lap ranges.
- **Position Change Chart**: A Recharts line chart illustrating lap-by-lap position developments for the top 8 runners with an inverted Y-axis.
- **Enriched Classification Table**: Timing-tower style list showing final positions, starting grid (`GRID`), position delta differences (`▲` for gains, `▼` for losses, `-` for no change), elapsed durations, fastest lap badges, and full DNF/DNS/DSQ status rendering.

---

### 👥 Head-to-Head Driver Comparison
Compare any two drivers directly and objectively:
- Side-by-side performance comparison
- Points progression comparison across a season or selected races
- Qualifying vs race performance differences
- Average finishing positions, wins, podiums, and consistency statistics
- Track-by-track comparison

---

### 🏎️ Team & Constructor Analysis
- Team branding and overview
- Dynamic driver lineup with resolved headshots
- Constructor standings and points
- Driver contribution delta within the same team
- Performance trends across the season

---

## Setup

1. **Frontend**:
   ```bash
   cd race-delta-frontend
   npm install
   npm run dev
   ```
   *Note: If you encounter missing package errors, run `fix_frontend_errors.bat` in the root directory.*

2. **Backend**:
   ```bash
   cd race-delta-backend
   pip install -r requirements.txt
   python create_tables.py
   python app.py
   ```

---

## Tech Stack

RaceDelta is built with a modern, scalable setup:
- **Backend:** Flask (Python)
- **Data Sources:** OpenF1 API, FastF1
- **Frontend:** React, Recharts
- **Styling:** Vanilla CSS & TailwindCSS (hybrid)
