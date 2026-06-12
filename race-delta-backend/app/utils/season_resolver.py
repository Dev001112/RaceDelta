# app/utils/season_resolver.py
"""
Centralized season resolution utility.
Single source of truth for determining:
- calendar_season (current year)
- active_season (current season if started, else None)
- last_completed_season (previous season)
- is_offseason (boolean)

Transition Logic:
A season becomes "Current" as soon as the first session (Testing or FP1) of the schedule begins.
Before that moment, the previous season is the 'display' season (labeled "Last Season").
"""
from datetime import datetime, timezone
from typing import Dict, Optional, List
import fastf1
import pandas as pd
import logging
import time

logger = logging.getLogger(__name__)
_season_cache = {"expires_at": 0, "value": None}
_SEASON_CACHE_TTL = 60 * 30


def resolve_seasons() -> Dict:
    """
    Resolve all season-related information.
    
    Returns:
        {
            "calendar_season": int,  # Current calendar year
            "display_season": int,   # The season that should be shown by default
            "active_season": Optional[int],  # Current season if started
            "last_completed_season": int,    # The previous season
            "is_offseason": bool,    # True if we are before the start of the current season
            "seasons_dropdown": List[Dict]  # Frontend-ready dropdown options
        }
    """
    now = datetime.now(timezone.utc)
    if _season_cache["value"] is not None and _season_cache["expires_at"] > time.time():
        return _season_cache["value"]

    calendar_season = now.year
    
    # Defaults (assume offseason/pre-season)
    display_season = calendar_season - 1
    active_season = None
    last_completed_season = calendar_season - 1
    is_offseason = True
    
    try:
        # Get race schedule for current calendar year (include testing for earliest date)
        schedule = fastf1.get_event_schedule(calendar_season, include_testing=True)
        
        if not schedule.empty and 'Session1Date' in schedule.columns:
            # Find the earliest session date (Testing or FP1)
            # Filter out NaT and ensure we have dates
            valid_sessions = schedule[schedule['Session1Date'].notna()]
            
            if not valid_sessions.empty:
                first_event_start = valid_sessions['Session1Date'].min()
                
                # Ensure timezone awareness (FastF1 usually returns naive or UTC, assume UTC if naive)
                if first_event_start.tzinfo is None:
                    first_event_start = first_event_start.replace(tzinfo=timezone.utc)
                
                if now >= first_event_start:
                    # Season has started
                    display_season = calendar_season
                    active_season = calendar_season
                    is_offseason = False
                    # Update last completed season? 
                    # If we just started, last completed is still previous year.
                    # Logic holds.
                else:
                    # Before season start
                    logger.info(f"Current time {now} is before season start {first_event_start}")

    except Exception as e:
        logger.error(f"Error resolving season for {calendar_season}: {e}")
        # Build safe fallback based on defaults set above
    
    # Build dropdown
    seasons_dropdown = _build_seasons_dropdown(
        calendar_season=calendar_season,
        display_season=display_season,
        is_offseason=is_offseason
    )
    
    payload = {
        "calendar_season": calendar_season,
        "display_season": display_season,
        "active_season": active_season,
        "last_completed_season": last_completed_season,
        "is_offseason": is_offseason,
        "seasons_dropdown": seasons_dropdown
    }
    _season_cache["value"] = payload
    _season_cache["expires_at"] = time.time() + _SEASON_CACHE_TTL
    return payload


def _build_seasons_dropdown(
    calendar_season: int,
    display_season: int,
    is_offseason: bool
) -> list:
    """
    Build frontend-ready dropdown array.
    """
    dropdown = []
    
    # 1. Primary Option (Display Season)
    if display_season == calendar_season:
        dropdown.append({
            "value": calendar_season,
            "label": f"{calendar_season} (Current)"
        })
    else:
        # Offseason: display season is previous year
        dropdown.append({
            "value": display_season,
            "label": f"{display_season} (Last Season)"
        })
        
        # Optionally add the upcoming season if we are in it but it hasn't started?
        # User requirement says: "never displays an empty 2026 dashboard before the season starts"
        # and "default to 2025".
        # If we just show 2025 as (Last Season), the user can't select 2026.
        # Maybe we should add 2026 as just "2026" or "2026 (Pre-season)"?
        # Requirement: "Use dropdown_options from the backend to populate the selection."
        # If we allow selecting 2026, it might show empty data.
        # "never displays an empty ... dashboard ... DEFAULT to 2025".
        # But if user MANUALLY selects 2026, it's okay?
        # Let's add the calendar season (2026) as an option even if it's not the default?
        # "dropdown_options: A list of objects {'value': int, 'label': 'YYYY (Current/Last Season)'}"
        # Let's simple add the current year if it's not the display season.
        if calendar_season != display_season:
             dropdown.insert(0, {
                 "value": calendar_season,
                 "label": f"{calendar_season} (Upcoming)"
             })

    # 2. Historical Seasons
    # Add context... e.g., last 4 years
    start_history = display_season - 1
    end_history = start_history - 4
    for year in range(start_history, end_history, -1):
        dropdown.append({
            "value": year,
            "label": str(year)
        })
        
    return dropdown


def get_current_season_year() -> int:
    """Convenience: get the year that should be used for queries."""
    r = resolve_seasons()
    return r["display_season"]

def get_active_season() -> Optional[int]:
    """Convenience function to get just the active season."""
    return resolve_seasons()["active_season"]


def get_season_for_drivers() -> int:
    """
    Get the appropriate season to use for driver roster.
    Returns the display_season (Last Season during offseason, Current during active).
    """
    return resolve_seasons()["display_season"]

