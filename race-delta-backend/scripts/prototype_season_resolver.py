
import fastf1
import pandas as pd
from datetime import datetime, timezone
import logging

import sys
import os

# Configure basic logging to see output
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Make sure we can see output
sys.stdout.reconfigure(encoding='utf-8')

# Enable cache
cache_dir = os.path.join(os.getcwd(), 'fastf1_cache')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

def resolve_seasons_logic(mock_now=None):
    """
    Prototype of the new season resolution logic.
    """
    # Use real current time if not mocked
    if mock_now is None:
        now = datetime.now(timezone.utc)
    else:
        now = mock_now

    # We assume we are transitioning from 2025 to 2026
    current_year = 2026
    previous_year = 2025
    
    display_season = previous_year
    is_offseason = True
    active_season = None
    
    try:
        # Get 2026 schedule including testing
        try:
            schedule = fastf1.get_event_schedule(current_year, include_testing=True)
        except Exception as e:
            logger.warning(f"Failed to get {current_year} schedule: {e}")
            schedule = pd.DataFrame()

        if not schedule.empty and 'Session1Date' in schedule.columns:
            # We want the earliest session start time.
            # Efficiently find the first valid session date.
            # Session1Date is usually FP1 or Day 1 of testing.
            
            # Ensure dates are UTC
            if schedule['Session1Date'].dt.tz is None:
                 # If naive, fastf1 usually returns utc (or local? need to be careful).
                 # FastF1 docs say dates are timestamp objects.
                 # Let's assume we need to be careful.
                 # For now, let's treat them as they come and ensure we compare correctly.
                 pass

            # Filter out NaT
            valid_sessions = schedule[schedule['Session1Date'].notna()]
            
            if not valid_sessions.empty:
                first_event_start = valid_sessions['Session1Date'].min()
                
                # Check timezone awareness
                if first_event_start.tzinfo is None:
                    # Assume UTC if naive (FastF1 standard)
                    first_event_start = first_event_start.replace(tzinfo=timezone.utc)
                
                logger.info(f"First session of {current_year} starts at: {first_event_start}")
                logger.info(f"Current mocked time: {now}")

                if now >= first_event_start:
                    # Season has started!
                    display_season = current_year
                    active_season = current_year
                    is_offseason = False # Or maybe true if between races, but request says "Current" as soon as it begins.
                                         # Request says "Active Season" based on start.
                                         # Request says "If current time is before first 2026 session... label it 'Last Season'".
                                         # Implies if after, it is 'Current Season'.
                else:
                    logger.info("Current time is BEFORE first session.")

    except Exception as e:
        logger.error(f"Error in checking schedule: {e}")

    # Build dropdown
    dropdown_options = []
    
    # 1. Current/Active entry
    if display_season == current_year:
        dropdown_options.append({"value": current_year, "label": f"{current_year} (Current)"})
    else:
        # If we are in 2026 but it hasn't started, prompt says default to 2025 "Last Season".
        # But maybe we still want to see 2026 in the list? 
        # "all backend queries... must use this resolved season"
        # "App must default to 2025... but label it Last Season".
        # Prompt says: "dropdown_options: A list of objects".
        
        # If we are displaying 2025 as default:
        dropdown_options.append({"value": previous_year, "label": f"{previous_year} (Last Season)"})
        # Should we show 2026? 
        # "The frontend never displays an empty 2026 dashboard before the season starts."
        # So maybe hide 2026 until it starts? Or show it but keep 2025 selected?
        # Prompt says "default to 2025".
        # For now, let's include 2026 as "2026 (Upcoming)" maybe? 
        # Or strictly follow "default to 2025".
        # Let's add older seasons too.

    # Add historical seasons
    start_hist = 2023 # example
    for y in range(previous_year, start_hist - 1, -1):
        # Avoid dupes
        if any(d['value'] == y for d in dropdown_options):
            continue
        dropdown_options.append({"value": y, "label": str(y)})
        
    return {
        "display_season": display_season,
        "is_offseason": is_offseason,
        "dropdown_options": dropdown_options
    }

if __name__ == "__main__":
    print("-" * 50)
    print("Test 1: Pre-season (Before start)")
    # Mock time: Jan 1st 2026
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    res1 = resolve_seasons_logic(mock_now=t1)
    print(res1)
    
    print("-" * 50)
    print("Test 2: In-season (After start)")
    # Mock time: March 1st 2026 (assuming season starts around Feb/March)
    # We'll rely on real FastF1 data to know when it actually starts.
    # If the API call works, we'll see the real start date in logs.
    # We'll make this date far in future to be safe for the test.
    t2 = datetime(2026, 6, 1, tzinfo=timezone.utc)
    res2 = resolve_seasons_logic(mock_now=t2)
    print(res2)
