import logging
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from models import db, Race, RaceResult, Driver, Constructor
import fastf1

logger = logging.getLogger(__name__)

class DataIngestor:
    """
    Ingests F1 data from FastF1 into the local Postgres database.
    """
    
    @staticmethod
    def ingest_season_schedule(year: int):
        """
        Loads the schedule for a year and creates Race entries.
        """
        try:
            logger.info(f"Fetching schedule for {year}")
            schedule = fastf1.get_event_schedule(year)
            
            count = 0
            for _, event in schedule.iterrows():
                # Skip pre-season testing
                if "TESTING" in event["EventName"].upper():
                    continue
                    
                # Check if race exists
                existing_race = Race.query.filter_by(season=year, round=int(event["RoundNumber"])).first()
                if existing_race:
                    continue
                
                new_race = Race(
                    season=year,
                    round=int(event["RoundNumber"]),
                    name=event["EventName"],
                    circuit=event["Location"],
                    race_date=event["EventDate"].to_pydatetime(),
                    status="Scheduled"
                )
                db.session.add(new_race)
                count += 1
            
            db.session.commit()
            logger.info(f"Ingested {count} new races for {year}")
            return count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error ingesting schedule: {e}")
            raise

    @staticmethod
    def ingest_race_results(year: int, round_num: int):
        """
        Loads race results for a specific round.
        """
        try:
            # Get the Race object
            race = Race.query.filter_by(season=year, round=round_num).first()
            if not race:
                logger.warning(f"Race {year} Round {round_num} not found in DB. Ingest schedule first.")
                return 0

            session = fastf1.get_session(year, round_num, 'R')
            session.load(laps=False, telemetry=False, weather=False, messages=False)
            
            results_count = 0
            
            for drv in session.drivers:
                drv_info = session.get_driver(drv)
                
                # Upsert Driver
                code = drv_info["Abbreviation"]
                driver = Driver.query.filter_by(driver_code=code).first()
                if not driver:
                    driver = Driver(
                        driver_code=code,
                        full_name=drv_info["FullName"],
                        given_name=drv_info["FirstName"],
                        family_name=drv_info["LastName"],
                        nationality=drv_info["CountryCode"], # Approximate
                        photo_url=drv_info.get("HeadshotUrl")
                    )
                    db.session.add(driver)
                    db.session.flush() # Get ID
                else:
                    # Update photo if missing
                    if not driver.photo_url and drv_info.get("HeadshotUrl"):
                        driver.photo_url = drv_info.get("HeadshotUrl")

                # Upsert Constructor
                team_name = drv_info["TeamName"]
                constructor = Constructor.query.filter_by(name=team_name).first()
                if not constructor and team_name:
                    constructor = Constructor(name=team_name)
                    db.session.add(constructor)
                    db.session.flush()

                # Create Result
                # Check if result exists
                existing_result = RaceResult.query.filter_by(race_id=race.race_id, driver_id=driver.driver_id).first()
                if not existing_result:
                    result = RaceResult(
                        race_id=race.race_id,
                        season=year,
                        driver_id=driver.driver_id,
                        constructor_id=constructor.constructor_id if constructor else None,
                        grid_position=int(drv_info["GridPosition"]),
                        finishing_position=int(drv_info["ClassifiedPosition"]) if str(drv_info["ClassifiedPosition"]).isdigit() else None,
                        status_text=drv_info["Status"],
                        points_awarded=float(drv_info["Points"]),
                    )
                    db.session.add(result)
                    results_count += 1
            
            race.status = "Completed"
            db.session.commit()
            logger.info(f"Ingested {results_count} results for {race.name}")
            return results_count

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error ingesting results: {e}")
            raise
