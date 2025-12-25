import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.f1_service import (
    get_sample_drivers,
    get_driver_standings,
    get_constructor_standings,
    get_race_schedule,
)
from datetime import datetime

def warm_cache():
    """Warm up the cache by fetching all major endpoints"""
    print("🔥 Warming up cache...")
    print("="*60)
    
    # 1. Drivers
    print("\n1. Fetching drivers...")
    try:
        drivers = get_sample_drivers()
        print(f"   ✓ Cached {len(drivers)} drivers")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 2. Race schedule
    print("\n2. Fetching race schedule...")
    try:
        schedule = get_race_schedule(datetime.now().year)
        races = schedule.get("races", [])
        print(f"   ✓ Cached {len(races)} races")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 3. Driver standings
    print("\n3. Computing driver standings...")
    print("   (This may take 20-30 seconds...)")
    try:
        standings = get_driver_standings("current")
        drivers_count = len(standings.get("standings", []))
        source = standings.get("source", "unknown")
        print(f"   ✓ Cached {drivers_count} driver standings (source: {source})")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 4. Constructor standings
    print("\n4. Computing constructor standings...")
    try:
        standings = get_constructor_standings("current")
        teams_count = len(standings.get("standings", []))
        source = standings.get("source", "unknown")
        print(f"   ✓ Cached {teams_count} team standings (source: {source})")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n" + "="*60)
    print("✅ Cache warming completed!")
    print("="*60)
    print("\n💡 The cache will stay warm for 5 minutes")
    print("   Run this script again if cache expires")


if __name__ == "__main__":
    warm_cache()