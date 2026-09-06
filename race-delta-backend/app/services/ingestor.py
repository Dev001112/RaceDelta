# app/services/ingestor.py
"""
Ingests F1 data from FastF1 into Postgres.

Phase 1: schedule + race results   (ingest_season_schedule / ingest_race_results)
Phase 2: lap-level telemetry storage + the AI-ready feature store
         (ingest_race_telemetry / ingest_season_telemetry)
"""
import logging
from datetime import datetime

import fastf1
import pandas as pd

import app.fastf1_setup  # noqa: F401  (enables the shared on-disk FastF1 cache)
from models import (db, Race, RaceResult, Driver, Constructor,
                    RaceSession, Lap, Stint, DriverRaceFeature)
from app.services import feature_engineering as fe

logger = logging.getLogger(__name__)


def _s(value):
    """NaN-safe string or None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


class ResultsPending(RuntimeError):
    """FastF1 has laps for the race but no finishing positions yet (results land a few hours after the flag)."""


def classification_published(results) -> bool:
    """True once the official classification is in: some driver has a numeric ClassifiedPosition.
    (FastF1 fills `Position` from the timing order within minutes; ClassifiedPosition and Status,
    which the feature store relies on, arrive with the official results hours later.)"""
    try:
        if results is None or len(results) == 0:
            return False
        classified = results["ClassifiedPosition"].astype(str).str.strip()
        return bool(classified.str.fullmatch(r"\d+").any())
    except (KeyError, TypeError, AttributeError):
        return False


class DataIngestor:
    """Ingests F1 data from FastF1 into the local Postgres database."""

    # ------------------------------------------------------------ shared upserts
    @staticmethod
    def _upsert_driver(info) -> Driver:
        code = _s(info.get("Abbreviation"))
        driver = Driver.query.filter_by(driver_code=code).first()
        if not driver:
            driver = Driver(
                driver_code=code,
                full_name=_s(info.get("FullName")) or code,
                given_name=_s(info.get("FirstName")),
                family_name=_s(info.get("LastName")),
                nationality=_s(info.get("CountryCode")),
                photo_url=_s(info.get("HeadshotUrl")),
            )
            db.session.add(driver)
            db.session.flush()
        elif not driver.photo_url and _s(info.get("HeadshotUrl")):
            driver.photo_url = _s(info.get("HeadshotUrl"))
        return driver

    @staticmethod
    def _upsert_constructor(team_name):
        name = _s(team_name)
        if not name:
            return None
        constructor = Constructor.query.filter_by(name=name).first()
        if not constructor:
            constructor = Constructor(name=name)
            db.session.add(constructor)
            db.session.flush()
        return constructor

    @staticmethod
    def _get_or_create_race(year: int, round_num: int) -> Race:
        race = Race.query.filter_by(season=year, round=round_num).first()
        if not race:
            DataIngestor.ingest_season_schedule(year)
            race = Race.query.filter_by(season=year, round=round_num).first()
        if not race:
            raise ValueError(f"Race {year} round {round_num} not in FastF1 schedule")
        return race

    # ------------------------------------------------------------ phase 1
    @staticmethod
    def ingest_season_schedule(year: int):
        """Create Race rows for a season; refresh name/circuit/date on rows that drifted from FastF1."""
        try:
            logger.info(f"Fetching schedule for {year}")
            schedule = fastf1.get_event_schedule(year)
            created = updated = 0
            for _, event in schedule.iterrows():
                if "TESTING" in str(event["EventName"]).upper():
                    continue
                round_num = int(event["RoundNumber"])
                if round_num <= 0:
                    continue
                name, circuit = str(event["EventName"]), _s(event["Location"])
                race_date = event["EventDate"].to_pydatetime()
                race = Race.query.filter_by(season=year, round=round_num).first()
                if race:
                    if race.name != name or race.circuit != circuit:
                        race.name, race.circuit, race.race_date = name, circuit, race_date
                        updated += 1
                    continue
                db.session.add(Race(season=year, round=round_num, name=name, circuit=circuit,
                                    race_date=race_date, status="Scheduled"))
                created += 1
            db.session.commit()
            logger.info(f"Schedule {year}: {created} created, {updated} refreshed")
            return created
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error ingesting schedule: {e}")
            raise

    @staticmethod
    def ingest_race_results(year: int, round_num: int):
        """Loads race results for a specific round."""
        try:
            race = Race.query.filter_by(season=year, round=round_num).first()
            if not race:
                logger.warning(f"Race {year} Round {round_num} not found in DB. Ingest schedule first.")
                return 0

            session = fastf1.get_session(year, round_num, 'R')
            session.load(laps=False, telemetry=False, weather=False, messages=False)

            results_count = 0
            for drv in session.drivers:
                info = session.get_driver(drv)
                driver = DataIngestor._upsert_driver(info)
                constructor = DataIngestor._upsert_constructor(info.get("TeamName"))
                if RaceResult.query.filter_by(race_id=race.race_id, driver_id=driver.driver_id).first():
                    continue
                classified = str(info["ClassifiedPosition"])
                db.session.add(RaceResult(
                    race_id=race.race_id,
                    season=year,
                    driver_id=driver.driver_id,
                    constructor_id=constructor.constructor_id if constructor else None,
                    grid_position=fe.inum(info["GridPosition"]),
                    finishing_position=int(classified) if classified.isdigit() else None,
                    status_text=_s(info["Status"]),
                    points_awarded=float(info["Points"]),
                ))
                results_count += 1

            race.status = "Completed"
            db.session.commit()
            logger.info(f"Ingested {results_count} results for {race.name}")
            return results_count
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error ingesting results: {e}")
            raise

    # ------------------------------------------------------------ phase 2
    @staticmethod
    def ingest_race_telemetry(year: int, round_num: int, session_type: str = "R") -> dict:
        """
        Load one session from FastF1 and (re)write its laps, stints and per-driver
        feature vectors. Idempotent: re-running replaces that session's rows.
        """
        try:
            race = DataIngestor._get_or_create_race(year, round_num)
            logger.info(f"Loading {year} R{round_num} {session_type} telemetry from FastF1")
            session = fastf1.get_session(year, round_num, session_type)
            session.load(laps=True, telemetry=False, weather=True, messages=True)
            laps = session.laps
            if laps is None or laps.empty:
                raise ValueError(f"No lap data for {year} round {round_num}")

            weather = fe.weather_summary(getattr(session, "weather_data", None))
            gaps = fe.compute_gaps(laps)
            results = session.results
            if not classification_published(results):
                raise ResultsPending(f"{session.event['EventName']} {year}: the official classification is not "
                                     f"published yet, so this race cannot be ingested. Try again in a few hours.")
            try:
                rcm = session.race_control_messages
            except Exception:
                rcm = None

            # Refresh race metadata from the loaded event (self-heals placeholder/stale rows).
            event = session.event
            race.name, race.circuit = _s(event["EventName"]), _s(event["Location"])
            race.race_date = event["EventDate"].to_pydatetime()

            rs = RaceSession.query.filter_by(race_id=race.race_id, session_type=session_type).first()
            if not rs:
                rs = RaceSession(race_id=race.race_id, session_type=session_type)
                db.session.add(rs)
            rs.season, rs.round = year, round_num
            rs.event_name = _s(session.event["EventName"])
            rs.total_laps = fe.inum(laps["LapNumber"].max())
            rs.avg_air_temp, rs.avg_track_temp = weather["avg_air_temp"], weather["avg_track_temp"]
            rs.avg_humidity, rs.rainfall = weather["avg_humidity"], weather["rainfall"]
            db.session.flush()
            for model in (Lap, Stint, DriverRaceFeature):
                model.query.filter_by(session_id=rs.session_id).delete(synchronize_session=False)

            n_laps = n_stints = n_drivers = 0
            for abbr in laps["Driver"].dropna().unique():
                dl = laps[laps["Driver"] == abbr]
                if dl.empty:
                    continue
                try:
                    info = session.get_driver(abbr)
                except Exception:
                    info = pd.Series({"Abbreviation": abbr, "DriverNumber": dl["DriverNumber"].iloc[0],
                                      "TeamName": dl["Team"].iloc[0] if "Team" in dl else None})
                driver = DataIngestor._upsert_driver(info)
                constructor = DataIngestor._upsert_constructor(info.get("TeamName"))

                g = gaps.reindex(dl.index)
                for idx, row in dl.iterrows():
                    db.session.add(Lap(
                        session_id=rs.session_id, driver_id=driver.driver_id,
                        lap_number=int(row["LapNumber"]),
                        lap_time_s=fe.sec(row.get("LapTime")),
                        s1_s=fe.sec(row.get("Sector1Time")),
                        s2_s=fe.sec(row.get("Sector2Time")),
                        s3_s=fe.sec(row.get("Sector3Time")),
                        compound=_s(row.get("Compound")),
                        tyre_life=fe.fnum(row.get("TyreLife"), 1),
                        stint=fe.inum(row.get("Stint")),
                        position=fe.inum(row.get("Position")),
                        is_pit_in=not pd.isna(row.get("PitInTime")),
                        is_pit_out=not pd.isna(row.get("PitOutTime")),
                        track_status=_s(row.get("TrackStatus")),
                        is_accurate=bool(row.get("IsAccurate", False)),
                        gap_ahead_s=fe.fnum(g.loc[idx, "gap_ahead_s"]),
                        gap_behind_s=fe.fnum(g.loc[idx, "gap_behind_s"]),
                    ))
                    n_laps += 1
                for st in fe.stint_features(dl):
                    db.session.add(Stint(session_id=rs.session_id, driver_id=driver.driver_id, **st))
                    n_stints += 1

                result_row = None
                if results is not None and not results.empty and "Abbreviation" in results.columns:
                    match = results[results["Abbreviation"] == abbr]
                    result_row = match.iloc[0] if not match.empty else None
                penalties = fe.count_penalties(rcm, abbr, info.get("DriverNumber"))
                feats = fe.driver_race_features(dl, gaps, result_row, weather, penalties)
                db.session.add(DriverRaceFeature(
                    session_id=rs.session_id, race_id=race.race_id, season=year, round=round_num,
                    driver_id=driver.driver_id, driver_code=str(abbr),
                    constructor_id=constructor.constructor_id if constructor else None,
                    **feats))
                n_drivers += 1

            race.status = "Completed"
            db.session.commit()
            summary = {"season": year, "round": round_num, "session_type": session_type,
                       "event": rs.event_name, "drivers": n_drivers, "laps": n_laps,
                       "stints": n_stints, "weather": weather}
            logger.info(f"Telemetry ingested: {summary}")
            return summary
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error ingesting telemetry {year} R{round_num}: {e}")
            raise

    @staticmethod
    def completed_rounds(year: int) -> list:
        """Round numbers whose race date has passed, excluding testing."""
        schedule = fastf1.get_event_schedule(year)
        schedule = schedule[schedule["RoundNumber"] > 0]
        if "EventFormat" in schedule.columns:
            schedule = schedule[schedule["EventFormat"] != "testing"]
        dates = schedule["EventDate"]
        if dates.dt.tz is not None:
            dates = dates.dt.tz_convert(None)
        return [int(r) for r in schedule.loc[dates < datetime.utcnow(), "RoundNumber"]]

    @staticmethod
    def ingest_season_telemetry(year: int, rounds=None) -> list:
        """Backfill the feature store for every completed round (or the given rounds)."""
        rounds = rounds or DataIngestor.completed_rounds(year)
        report = []
        for round_num in rounds:
            try:
                s = DataIngestor.ingest_race_telemetry(year, round_num)
                report.append({"round": round_num, "ok": True, "event": s["event"],
                               "drivers": s["drivers"], "laps": s["laps"]})
            except Exception as e:
                report.append({"round": round_num, "ok": False, "error": str(e)})
        return report
