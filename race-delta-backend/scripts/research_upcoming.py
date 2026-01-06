
import fastf1
import requests
import sys
import os

# Enable cache for FastF1
cache_dir = os.path.join(os.getcwd(), 'fastf1_cache')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

def check_fastf1_2026():
    print("--- Checking FastF1 for 2026 ---")
    try:
        # Check schedule
        schedule = fastf1.get_event_schedule(2026, include_testing=True)
        if schedule.empty:
            print("FastF1: No schedule found for 2026.")
        else:
            print(f"FastF1: Found {len(schedule)} events for 2026.")
            print("First 3 events:")
            print(schedule[['EventName', 'EventDate', 'Session1Date']].head(3))
            
            # Try to get valid session
            # Usually upcoming sessions don't have driver lists until entry lists are published/session starts.
            # But let's try accessing a session object.
            try:
                # Pick first event (probably testing)
                first_event = schedule.iloc[0]
                print(f"\nAttempting to load session for: {first_event['EventName']}")
                session = fastf1.get_session(2026, first_event['EventName'], 'Practice 1')
                # session.load() # This usually fails for future sessions as data isn't there.
                # But maybe we can check drivers via Ergast/OpenF1 fallback? 
                
                print("Session object created. Skipping .load() as it will likely raise error for future dates.")
            except Exception as e:
                print(f"FastF1 Session Error: {e}")

    except Exception as e:
        print(f"FastF1 Error: {e}")

def check_openf1_2026():
    print("\n--- Checking OpenF1 for 2026 ---")
    base_url = "https://api.openf1.org/v1"
    
    # 1. Check Sessions
    try:
        url = f"{base_url}/sessions?year=2026"
        print(f"Fetching: {url}")
        resp = requests.get(url, timeout=5)
        if resp.ok:
            data = resp.json()
            print(f"OpenF1 Sessions 2026: Found {len(data)}")
            if len(data) > 0:
                print(data[0])
        else:
            print(f"OpenF1 Sessions Error: {resp.status_code}")
            
    except Exception as e:
        print(f"OpenF1 Sessions Exception: {e}")

    # 2. Check Drivers for 2026? 
    # OpenF1 drivers endpoint usually takes a session_key. 
    # If we found no sessions, we can't get drivers easily by session.
    # But maybe without params?
    try:
        url = f"{base_url}/drivers?session_key=latest" # "latest" might be 2025 until 2026 starts.
        print(f"Fetching: {url}")
        resp = requests.get(url, timeout=5)
        if resp.ok:
            data = resp.json()
            if data:
                print(f"OpenF1 Latest Drivers: Found {len(data)}. Sample: {data[0].get('name_acronym')}")
                # Check if we can infer year from meeting_key or session_key (if connected to 2026)
                # But 'latest' means most recent *completed* or *live*, so likely 2025.
            else:
                print("OpenF1 Latest Drivers: None")
    except Exception as e:
        print(f"OpenF1 Drivers Exception: {e}")

if __name__ == "__main__":
    check_fastf1_2026()
    check_openf1_2026()
