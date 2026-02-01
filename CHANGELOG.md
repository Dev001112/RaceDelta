# Changelog - 2026 Season Update

## 1. Fixed Season Logic in `DriverComparison.jsx`
- **Issue**: The page had hardcoded options (Current, 2024, 2023) and wasn't aware of the new 2026 context.
- **Fix**: Connected the page to the global `SeasonContext`. It now dynamically populates the season dropdown with the correct options from the backend (e.g., "2026 (Upcoming)", "2025 (Last Season)").
- **Result**: The "Current season" default now correctly respects the backend's logic, defaulting to the last completed season (2025) during the pre-season, while allowing you to select 2026.

## 2. UI Modernization (Tailwind CSS)
- **`Teams.jsx`**: Replaced inline styles with a responsive Tailwind grid layout.
- **`TeamDetail.jsx`**: Completely redesigned with a modern, "premium" look using Tailwind. Features include:
    -   Hero section with car image and team logo.
    -   Glassmorphism effects for stats cards.
    -   Improved driver cards with headshots.
    -   Responsive layout for mobile and desktop.

## 3. Data Infrastructure for 2025/2026
- **`team_meta.py`**: Refactored the metadata system to be season-aware.
    -   Added support for **2025** and **2026** car models (e.g., RB21, RB22, Audi F1 for Sauber in 2026).
    -   The system defaults to 2024 images if newer ones aren't available yet, preventing blank comparisons.
    -   Updated `routes.py` to pass the selected season to the metadata engine, so viewing a team in 2026 shows the correct car name (e.g., "RB22").

## 4. Cleanup
- Attempted to remove temporary debugging scripts to keep the codebase clean.
