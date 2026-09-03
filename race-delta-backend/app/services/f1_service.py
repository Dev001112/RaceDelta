# app/services/f1_service.py
import os
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from flask import current_app
from cachetools import TTLCache, LRUCache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import fastf1
from app.services import cache_store

# Import models
try:
    from models import db, Driver, Constructor, Race, RaceResult
    from app.services.ingestor import DataIngestor
except ImportError:
    # Fallback for when running scripts outside app context
    from app.models import db, Driver, Constructor, Race, RaceResult
    from app.services.ingestor import DataIngestor

logger = logging.getLogger(__name__)

# F1 Points
F1_POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}

def get_season_drivers(year: Optional[int] = None) -> Dict:
    """
    Get drivers for a season from DB.
    If DB is empty for this season, trigger ingestion of the schedule and initial data.
    """
    if year is None:
        year = datetime.now().year
        
    try:
        # 1. Check DB for drivers who have results in this season
        # We join RaceResult -> Race to filter by season
        results = db.session.query(Driver, Constructor)\
            .join(RaceResult, Driver.driver_id == RaceResult.driver_id)\
            .join(Race, RaceResult.race_id == Race.race_id)\
            .join(Constructor, RaceResult.constructor_id == Constructor.constructor_id)\
            .filter(Race.season == year)\
            .group_by(Driver.driver_id, Constructor.constructor_id)\
            .all()
            
        drivers_list = []
        if results:
            seen_drivers = set()
            for driver, constructor in results:
                if driver.driver_code in seen_drivers:
                    continue
                seen_drivers.add(driver.driver_code)
                
                drivers_list.append({
                    "driver_code": driver.driver_code,
                    "driver_name": driver.full_name,
                    "driver_number": 0, # We might not store number on driver, but in result or lookup
                    "team": constructor.name,
                    "country_code": driver.nationality,
                    "headshot_url": driver.photo_url
                })
            
            # Sort
            drivers_list.sort(key=lambda x: x["driver_name"])
            
            return {
                "source": "database",
                "season": year,
                "count": len(drivers_list),
                "drivers": drivers_list
            }
            
        else:
            # DB Empty? Trigger Ingestion
            logger.info(f"No drivers found in DB for {year}. Triggering ingestion.")
            DataIngestor.ingest_season_schedule(year)
            # Maybe ingest first race results to get drivers?
            # Find first completed race
            race = Race.query.filter_by(season=year).order_by(Race.round).first()
            if race and race.race_date < datetime.utcnow():
                logger.info(f"Ingesting results for Round {race.round} to populate drivers.")
                DataIngestor.ingest_race_results(year, race.round)
                # Recursion to fetch again
                return get_season_drivers(year)
                
            return {"source": "empty", "drivers": []}

    except Exception as e:
        logger.error(f"Error fetching season drivers: {e}")
        return {"source": "error", "drivers": [], "error": str(e)}

def get_race_schedule(year: Optional[int] = None) -> Dict:
    """Get race calendar from DB"""
    if not year:
        year = datetime.now().year
        
    try:
        races = Race.query.filter_by(season=year).order_by(Race.round).all()
        
        if not races:
            # Trigger ingestion
            DataIngestor.ingest_season_schedule(year)
            races = Race.query.filter_by(season=year).order_by(Race.round).all()
            
        race_list = []
        for r in races:
            race_list.append({
                "round": r.round,
                "name": r.name,
                "location": r.circuit, # We stored location in circuit column
                "circuit": r.circuit,
                "date": r.race_date.isoformat() if r.race_date else None,
                "status": r.status
            })
            
        return {
            "races": race_list,
            "season": year,
            "source": "database"
        }
    except Exception as e:
        logger.error(f"Error fetching schedule: {e}")
        return {"races": [], "season": year, "error": str(e)}

# Stub other functions to use legacy or simple DB
def get_driver_standings(season="current"):
    # ... (Keep logic but allow DB query if needed)
    # For now, return empty to not break app, or generic
    return {"standings": [], "source": "todo_db"} 
    
def get_constructor_standings(season="current"):
    return {"standings": [], "source": "todo_db"} 

def get_driver_laps(driver_code):
    return {"laps": []}




# Configuration
OPENF1_BASE = os.getenv("OPENF1_BASE", "https://api.openf1.org/v1")
HTTP_TIMEOUT = float(os.getenv("OPENF1_TIMEOUT", "10"))
CACHE_TTL = int(os.getenv("OPENF1_CACHE_TTL", "300"))  # 5 minutes
PERSISTENT_CACHE_TTL = int(os.getenv("OPENF1_PERSISTENT_CACHE_TTL", "21600"))  # 6 hours

# Cache setup
cache = TTLCache(maxsize=512, ttl=CACHE_TTL)

# Failed OpenF1 calls are not retried for a while (rate limits, outages)
fail_cache = TTLCache(maxsize=512, ttl=int(os.getenv("OPENF1_FAIL_TTL", "120")))

# Session with retry logic
session = requests.Session()
retries = Retry(total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504))
session.mount("https://", HTTPAdapter(max_retries=retries))
session.mount("http://", HTTPAdapter(max_retries=retries))

# F1 Points system
F1_POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}

# TEAM NORMALIZATION
TEAM_ALIASES = {
    "red bull": "Red Bull Racing",
    "oracle red bull racing": "Red Bull Racing",
    "mercedes": "Mercedes",
    "ferrari": "Ferrari",
    "mclaren": "McLaren",
    "aston martin": "Aston Martin",
    "alpine": "Alpine",
    "haas": "Haas",
    "haas f1 team": "Haas",
    "williams": "Williams",
    "sauber": "Sauber",
    "kick sauber": "Sauber",
    "rb": "RB",
    "alphatauri": "RB",
}

def normalize_team(name: str) -> str:
    if not name:
        return "Unknown"
    key = name.lower().strip()
    return TEAM_ALIASES.get(key, name)


def _fetch_openf1(url: str, params: Optional[Dict]) -> Any:
    print(f"Fetching from OpenF1: {url} with params: {params}")
    response = session.get(url, params=params, timeout=HTTP_TIMEOUT)   # retries with backoff on 429/5xx
    response.raise_for_status()
    return response.json()


def _api_request(endpoint: str, params: Optional[Dict] = None, use_cache: bool = True, ttl: Optional[int] = None) -> Any:
    """OpenF1 GET: in-memory layer, persistent stale-while-revalidate layer, negative cache for failures."""
    url = f"{OPENF1_BASE.rstrip('/')}/{endpoint.lstrip('/')}"
    normalized_params = dict(sorted((params or {}).items()))
    cache_key = f"{url}:{normalized_params}"

    if not use_cache:
        try:
            return _fetch_openf1(url, params)
        except Exception as e:
            print(f"OpenF1 API Error: {e}")
            return None
    if cache_key in cache:
        return cache[cache_key]
    if cache_key in fail_cache:
        return None
    try:
        data, fresh = cache_store.cached_entry("openf1", cache_key, ttl or PERSISTENT_CACHE_TTL,
                                               lambda: _fetch_openf1(url, params))
    except Exception as e:
        print(f"OpenF1 API Error: {e}")
        fail_cache[cache_key] = True
        return None
    if fresh:
        cache[cache_key] = data   # stale values stay out of memory so the next call sees the refresh
    return data


#  DRIVERS ....

def _build_roster(year: int) -> List[Dict]:
    """Drivers who raced in the latest completed round of `year` (FastF1)."""
    # Get season schedule
    schedule = fastf1.get_event_schedule(year)

    # Keep only completed races
    completed = schedule[schedule["EventDate"] < datetime.utcnow()]

    if completed.empty:
        raise RuntimeError("No completed races found")

    # Use latest completed race
    latest_event = completed.iloc[-1]["EventName"]

    session = fastf1.get_session(year, latest_event, "RACE")
    session.load(laps=False, telemetry=False, weather=False, messages=False)

    # Drivers who actually raced. Results are much lighter than loading all laps.
    raced_numbers = set(str(n) for n in session.results["DriverNumber"].dropna().unique())

    drivers = []

    for drv in session.drivers:
        info = session.get_driver(drv)

        number = info.get("DriverNumber")
        code = info.get("Abbreviation")
        name = info.get("FullName")

        if not number or not code or not name:
            continue
        if str(number) not in raced_numbers:
            continue

        drivers.append({
            "driver_code": code,
            "driver_name": name,
            "driver_number": int(number),
            "team": normalize_team(info.get("TeamName")),
            "country_code": info.get("CountryCode"),
            "headshot_url": info.get("HeadshotUrl"),
        })

    drivers.sort(key=lambda d: d["driver_number"])
    return drivers


def get_season_drivers(year: Optional[int] = None) -> Dict:
    """
    Clean, race-only F1 drivers for a season. Cached per season; finished seasons never expire.
    """
    if year is None:
        year = datetime.now().year
    try:
        drivers = cache_store.cached("derived", f"roster:v1:{year}", cache_store.season_ttl(year),
                                     lambda: _build_roster(year))
        return {"source": "fastf1", "season": year, "count": len(drivers), "drivers": drivers}

    except Exception as e:
        # Silent fallback during offseason - not an error condition
        # Log only if it's unexpected (not offseason-related)
        import logging
        logger = logging.getLogger(__name__)
        if "No completed races" not in str(e):
            logger.debug(f"Driver fetch fallback: {e}")
        return {
            "source": "fallback",
            "drivers": _get_fallback_drivers()
        }


def _get_fallback_drivers() -> List[Dict]:
    """Fallback driver data - Simplified"""
    return []


#LAP DATA 
def get_driver_laps(driver_code: str) -> Dict:
    """Get lap times for a specific driver from latest session"""
    try:
        derived_cache_key = f"driver_laps:{driver_code.upper()}"
        cached = cache_store.get("derived", derived_cache_key)
        if cached is not None:
            return cached

        print(f"Fetching laps for driver: {driver_code}")
        
        # Get latest race session
        sessions = _api_request("sessions", params={"session_name": "Race"})
        if not sessions:
            return {"driver": driver_code, "laps": [], "source": "fallback", "error": "No sessions found"}
        
        # Filter for race sessions and get most recent
        race_sessions = [s for s in sessions if (s.get("session_name") or "").lower() == "race"]
        if not race_sessions:
            return {"driver": driver_code, "laps": [], "source": "fallback", "error": "No race sessions found"}
        
        latest_session = sorted(race_sessions, key=lambda x: x.get("date_start", ""), reverse=True)[0]
        session_key = latest_session.get("session_key")
        
        print(f"Using session_key: {session_key} for laps")
        
        # Find driver number from code
        drivers = _api_request("drivers", params={"session_key": session_key})
        driver_number = None
        for d in drivers:
            if d.get("name_acronym") == driver_code.upper():
                driver_number = d.get("driver_number")
                break
        
        if not driver_number:
            return {"driver": driver_code, "laps": [], "source": "fallback", "error": "Driver not found"}
        
        # Get lap data
        laps = _api_request("laps", params={
            "session_key": session_key,
            "driver_number": driver_number
        })
        
        if not laps:
            return {"driver": driver_code, "laps": [], "source": "fallback", "error": "No lap data"}
        
        # Transform lap data
        lap_data = []
        for lap in laps:
            lap_time = lap.get("lap_duration")
            if lap_time:
                lap_data.append({
                    "lap": lap.get("lap_number"),
                    "time": lap_time,
                    "sector1": lap.get("duration_sector_1"),
                    "sector2": lap.get("duration_sector_2"),
                    "sector3": lap.get("duration_sector_3"),
                })
        
        payload = {
            "driver": driver_code,
            "laps": lap_data,
            "source": "openf1",
            "session": latest_session.get("session_name")
        }
        cache_store.set("derived", derived_cache_key, payload, PERSISTENT_CACHE_TTL)
        return payload
    
    except Exception as e:
        print(f"Error fetching laps for {driver_code}: {e}")
        import traceback
        traceback.print_exc()
        return {"driver": driver_code, "laps": [], "source": "error", "error": str(e)}


# STANDINGS 

def _classification_from_session_result(session_key):
    rows = _api_request("session_result", params={"session_key": session_key}, use_cache=True)
    if not rows:
        return None

    normalized = []
    for row in rows:
        try:
            position = int(row.get("position") or row.get("classified_position") or row.get("pos"))
        except Exception:
            continue

        driver_number = row.get("driver_number")
        if driver_number is None:
            continue

        normalized.append({
            "driver_number": driver_number,
            "position": position,
        })

    return normalized or None


def _classification_from_driver_laps(session_key, drivers):
    normalized = []
    for driver in drivers:
        driver_number = driver.get("driver_number")
        if not driver_number:
            continue

        laps = _api_request(
            "laps",
            params={"session_key": session_key, "driver_number": driver_number},
            use_cache=True,
        )
        if not laps:
            continue

        final_lap = max(laps, key=lambda x: x.get("lap_number", 0))
        try:
            position = int(final_lap.get("position"))
        except Exception:
            continue

        normalized.append({
            "driver_number": driver_number,
            "position": position,
        })

    return normalized


def get_driver_standings(season: str = "current") -> Dict:
    """Get driver championship standings - OPTIMIZED VERSION"""
    try:
        year = datetime.now().year if season == "current" else int(season)
        derived_cache_key = f"driver_standings:{year}"
        cached = cache_store.get("derived", derived_cache_key)
        if cached is not None:
            return cached

        print(f"Computing standings for season: {year}")
        
        # Get all race sessions for the season (more efficient query)
        print(f"Fetching sessions for year {year}...")
        sessions = _api_request("sessions", params={"year": year}, use_cache=True)
        
        if not sessions or len(sessions) == 0:
            print("No sessions found, trying alternative approach...")
            # Try getting sessions without year filter
            all_sessions = _api_request("sessions", use_cache=True)
            if all_sessions:
                # Filter for race sessions manually
                sessions = [s for s in all_sessions 
                           if (s.get("session_name") or "").lower() == "race" 
                           and str(year) in str(s.get("date_start", ""))]
        
        if not sessions or len(sessions) == 0:
            print("Still no sessions found, using fallback")
            return {"standings": _get_fallback_standings(), "season": year, "source": "fallback"}
        
        # Filter for race sessions
        race_sessions = [s for s in sessions if (s.get("session_name") or "").lower() == "race"]
        print(f"Found {len(race_sessions)} race sessions")
        
        if not race_sessions:
            print("No race sessions found, using fallback")
            return {"standings": _get_fallback_standings(), "season": year, "source": "fallback"}
        
        # Sort by date and get completed races
        completed_sessions = sorted(
            [s for s in race_sessions if s.get("date_end")],
            key=lambda x: x.get("date_start", ""),
            reverse=True
        )
        
        if not completed_sessions:
            print("No completed races, using fallback")
            return {"standings": _get_fallback_standings(), "season": year, "source": "fallback"}
        
        # Limit processing
        max_races = int(os.getenv("STANDINGS_MAX_RACES", "10"))
        races_to_process = completed_sessions[:max_races]
        print(f"Processing {len(races_to_process)} most recent completed races")
        
        driver_points = {}
        driver_info = {}
        races_processed = 0
        
        # Process only completed race sessions
        for i, session in enumerate(races_to_process):
            session_key = session.get("session_key")
            session_name = session.get("meeting_name") or session.get("session_name")
            print(f"  [{i+1}/{len(races_to_process)}] Processing {session_name} (session: {session_key})")
            
            try:
                # Get all drivers for this session
                drivers = _api_request("drivers", params={"session_key": session_key}, use_cache=True)
                if not drivers:
                    print(f"    ⚠ No drivers found")
                    continue
                
                print(f"    Found {len(drivers)} drivers")
                
                classification = (
                    _classification_from_session_result(session_key)
                    or _classification_from_driver_laps(session_key, drivers)
                )
                if not classification:
                    print("    No classification found")
                    continue

                classification_by_driver = {
                    str(row["driver_number"]): row
                    for row in classification
                }
                
                # Process each driver
                for driver in drivers:
                    driver_number = driver.get("driver_number")
                    if not driver_number:
                        continue
                    
                    name = driver.get("full_name") or driver.get("name_acronym", "Unknown")
                    team = driver.get("team_name", "Unknown")
                    code = driver.get("name_acronym", "UNK")
                    
                    # Store driver info
                    if driver_number not in driver_info:
                        driver_info[driver_number] = {
                            "name": name,
                            "code": code,
                            "team": team,
                        }
                    
                    result = classification_by_driver.get(str(driver_number))
                    if not result:
                        continue
                    
                    position = result.get("position")
                    
                    if position and isinstance(position, (int, float)) and position in F1_POINTS:
                        points = F1_POINTS[int(position)]
                        if driver_number not in driver_points:
                            driver_points[driver_number] = {"points": 0, "wins": 0, "podiums": 0}
                        
                        driver_points[driver_number]["points"] += points
                        if position == 1:
                            driver_points[driver_number]["wins"] += 1
                        if position <= 3:
                            driver_points[driver_number]["podiums"] += 1
                
                races_processed += 1
                print(f"    ✓ Processed successfully")
                
            except Exception as e:
                print(f"    ✗ Error processing race: {e}")
                continue
        
        print(f"\nTotal races processed: {races_processed}")
        print(f"Total drivers found: {len(driver_info)}")
        
        # Build standings
        standings = []
        for driver_num, info in driver_info.items():
            points_data = driver_points.get(driver_num, {"points": 0, "wins": 0, "podiums": 0})
            if points_data["points"] > 0:  # Only include drivers with points
                standings.append({
                    "position": 0,
                    "driver": info["name"],
                    "code": info["code"],
                    "team": info["team"],
                    "points": points_data["points"],
                    "wins": points_data["wins"],
                    "podiums": points_data["podiums"],
                })
        
        # Sort by points, then wins
        standings.sort(key=lambda x: (-x["points"], -x["wins"]))
        
        # Set positions
        for i, standing in enumerate(standings, 1):
            standing["position"] = i
        
        if not standings or races_processed == 0:
            print("No standings computed, using fallback")
            standings = _get_fallback_standings()
            source = "fallback"
        else:
            source = "openf1"
            print(f"✓ Successfully computed standings for {len(standings)} drivers")
        
        payload = {
            "standings": standings,
            "season": year,
            "source": source,
            "races_processed": races_processed,
            "last_updated": datetime.now().isoformat()
        }
        cache_store.set("derived", derived_cache_key, payload, PERSISTENT_CACHE_TTL)
        return payload
    
    except Exception as e:
        print(f"ERROR in get_driver_standings: {e}")
        import traceback
        traceback.print_exc()
        return {"standings": _get_fallback_standings(), "season": season, "source": "error", "error": str(e)}


def _get_fallback_standings():
    """Fallback driver standings - Simplified"""
    return []


def _get_fallback_constructor_standings():
    """2025 F1 Constructor Championship - Live Season (Updated Dec 2025)"""
    return [
        {"position": 1, "team": "McLaren", "points": 729, "wins": 9},
        {"position": 2, "team": "Ferrari", "points": 600, "wins": 6},
        {"position": 3, "team": "Red Bull Racing", "points": 581, "wins": 9},
        {"position": 4, "team": "Mercedes", "points": 425, "wins": 4},
        {"position": 5, "team": "Aston Martin", "points": 92, "wins": 0},
        {"position": 6, "team": "Alpine", "points": 54, "wins": 0},
        {"position": 7, "team": "Haas", "points": 46, "wins": 0},
        {"position": 8, "team": "RB", "points": 42, "wins": 0},
        {"position": 9, "team": "Sauber", "points": 37, "wins": 0},
        {"position": 10, "team": "Williams", "points": 16, "wins": 0},
    ]


def get_constructor_standings(season: str = "current") -> Dict:
    """Get constructor championship standings - OPTIMIZED"""
    try:
        year = datetime.now().year if season == "current" else int(season)
        derived_cache_key = f"constructor_standings:{year}"
        cached = cache_store.get("derived", derived_cache_key)
        if cached is not None:
            return cached

        print(f"Computing constructor standings for season: {year}")
        
        # Get race sessions directly (more efficient)
        sessions = _api_request("sessions", params={"session_name": "Race", "year": year}, use_cache=True)
        
        if not sessions:
            return {"standings": _get_fallback_constructor_standings(), "season": year, "source": "fallback"}
        
        # Filter completed races
        completed_sessions = [s for s in sessions if s.get("date_end")]
        print(f"Processing {len(completed_sessions)} completed races")
        
        team_points = {}
        
        # Process only recent races (limit to 10 for speed)
        for i, session in enumerate(completed_sessions[:10]):
            session_key = session.get("session_key")
            print(f"Processing race {i+1}/{min(len(completed_sessions), 10)}")
            
            drivers = _api_request("drivers", params={"session_key": session_key}, use_cache=True)
            if not drivers:
                continue
            
            classification = (
                _classification_from_session_result(session_key)
                or _classification_from_driver_laps(session_key, drivers)
            )
            if not classification:
                continue

            classification_by_driver = {
                str(row["driver_number"]): row
                for row in classification
            }
            
            for driver in drivers:
                driver_number = driver.get("driver_number")
                team = driver.get("team_name", "Unknown")
                
                result = classification_by_driver.get(str(driver_number))
                if not result:
                    continue
                
                position = result.get("position")
                
                if position and position in F1_POINTS:
                    points = F1_POINTS[position]
                    if team not in team_points:
                        team_points[team] = {"points": 0, "wins": 0}
                    
                    team_points[team]["points"] += points
                    if position == 1:
                        team_points[team]["wins"] += 1
        
        # Build standings
        standings = []
        for team, data in team_points.items():
            standings.append({
                "position": 0,
                "team": team,
                "points": data["points"],
                "wins": data["wins"],
            })
        
        standings.sort(key=lambda x: (-x["points"], -x["wins"]))
        
        for i, standing in enumerate(standings, 1):
            standing["position"] = i
        
        if not standings:
            standings = _get_fallback_constructor_standings()
            source = "fallback"
        else:
            source = "openf1"
        
        payload = {
            "standings": standings,
            "season": year,
            "source": source,
            "races_processed": min(len(completed_sessions), 10),
            "last_updated": datetime.now().isoformat()
        }
        cache_store.set("derived", derived_cache_key, payload, PERSISTENT_CACHE_TTL)
        return payload
    
    except Exception as e:
        print(f"Error computing constructor standings: {e}")
        import traceback
        traceback.print_exc()
        return {"standings": _get_fallback_constructor_standings(), "season": season, "source": "error", "error": str(e)}


def _get_fallback_constructor_standings():
    """Fallback constructor standings - Simplified"""
    return []


# TYRE & TELEMETRY DATA 

def get_tyre_data(session_key: Optional[str] = None, driver_number: Optional[int] = None) -> Dict:
    """Get tyre compound and stint data"""
    try:
        if not session_key:
            sessions = _api_request("sessions")
            if sessions:
                race_sessions = [s for s in sessions if (s.get("session_name") or "").lower() == "race"]
                if race_sessions:
                    latest = sorted(race_sessions, key=lambda x: x.get("date_start", ""), reverse=True)[0]
                    session_key = latest.get("session_key")
        
        if not session_key:
            return {"error": "No session found", "stints": []}
        
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        
        stints = _api_request("stints", params=params)
        
        if not stints:
            return {"error": "No stint data", "stints": []}
        
        stint_data = []
        for stint in stints:
            stint_data.append({
                "driver_number": stint.get("driver_number"),
                "stint_number": stint.get("stint_number"),
                "compound": stint.get("compound"),
                "tyre_age_at_start": stint.get("tyre_age_at_start"),
                "lap_start": stint.get("lap_start"),
                "lap_end": stint.get("lap_end"),
            })
        
        return {
            "stints": stint_data,
            "session_key": session_key,
            "source": "openf1"
        }
    
    except Exception as e:
        print(f"Error fetching tyre data: {e}")
        return {"error": str(e), "stints": []}


def get_car_telemetry(session_key: str, driver_number: int) -> Dict:
    """Get car telemetry data"""
    try:
        derived_cache_key = f"telemetry:{session_key}:{driver_number}"
        cached = cache_store.get("derived", derived_cache_key)
        if cached is not None:
            return cached

        car_data = _api_request("car_data", params={
            "session_key": session_key,
            "driver_number": driver_number
        }, use_cache=True)
        
        if not car_data:
            return {"error": "No telemetry data", "data": []}
        
        sampled = car_data[::10] if len(car_data) > 100 else car_data
        
        telemetry = []
        for point in sampled:
            telemetry.append({
                "date": point.get("date"),
                "speed": point.get("speed"),
                "rpm": point.get("rpm"),
                "throttle": point.get("throttle"),
                "brake": point.get("brake"),
                "drs": point.get("drs"),
                "gear": point.get("n_gear"),
            })
        
        payload = {
            "data": telemetry,
            "driver_number": driver_number,
            "session_key": session_key,
            "source": "openf1"
        }
        cache_store.set("derived", derived_cache_key, payload, PERSISTENT_CACHE_TTL)
        return payload
    
    except Exception as e:
        print(f"Error fetching telemetry: {e}")
        return {"error": str(e), "data": []}


def get_race_schedule(year: Optional[int] = None) -> Dict:
    """Get race calendar for a season"""
    try:
        if not year:
            year = datetime.now().year
        
        meetings = _api_request("meetings", params={"year": year})
        
        if not meetings:
            return {"races": [], "season": year}
        
        races = []
        for meeting in sorted(meetings, key=lambda x: x.get("date_start", "")):
            races.append({
                "round": meeting.get("meeting_key"),
                "name": meeting.get("meeting_name"),
                "location": meeting.get("location"),
                "country": meeting.get("country_name"),
                "circuit": meeting.get("circuit_short_name"),
                "date": meeting.get("date_start"),
            })
        
        return {
            "races": races,
            "season": year,
            "source": "openf1"
        }
    
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return {"races": [], "season": year, "error": str(e)}
    
