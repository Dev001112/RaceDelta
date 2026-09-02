# D:\RaceDelta\race-delta-backend\models.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Driver(db.Model):
    __tablename__ = "drivers"
    driver_id = db.Column(db.Integer, primary_key=True)
    driver_code = db.Column(db.String(8), unique=True)
    full_name = db.Column(db.Text, nullable=False)
    given_name = db.Column(db.Text)
    family_name = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    nationality = db.Column(db.Text)
    photo_url = db.Column(db.Text)
    last_updated = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class Constructor(db.Model):
    __tablename__ = "constructors"
    constructor_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    short_name = db.Column(db.String(64))
    nationality = db.Column(db.Text)
    logo_url = db.Column(db.Text)
    last_updated = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class Race(db.Model):
    __tablename__ = "races"
    race_id = db.Column(db.Integer, primary_key=True)
    season = db.Column(db.Integer, nullable=False, index=True)
    round = db.Column(db.Integer)
    name = db.Column(db.Text)
    circuit = db.Column(db.Text)
    race_date = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(32))
    last_updated = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class RaceResult(db.Model):
    __tablename__ = "race_results"
    id = db.Column(db.BigInteger, primary_key=True)
    race_id = db.Column(db.Integer, db.ForeignKey('races.race_id', ondelete='CASCADE'), nullable=False, index=True)
    season = db.Column(db.Integer, nullable=False, index=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.driver_id'), nullable=False)
    constructor_id = db.Column(db.Integer, db.ForeignKey('constructors.constructor_id'))
    grid_position = db.Column(db.Integer)
    finishing_position = db.Column(db.Integer)
    laps = db.Column(db.Integer)
    status_text = db.Column(db.Text)
    time_text = db.Column(db.Text)
    fastest_lap = db.Column(db.Boolean, default=False)
    points_awarded = db.Column(db.Numeric(6,2), default=0)
    last_updated = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('race_id', 'driver_id', name='uq_race_driver'),)

class StandingsCache(db.Model):
    __tablename__ = "standings_cache"
    season = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum('drivers', 'constructors', name='scoring_type'), primary_key=True)
    payload = db.Column(db.JSON, nullable=False)
    computed_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

class IngestionMeta(db.Model):
    __tablename__ = "ingestion_meta"
    key = db.Column(db.Text, primary_key=True)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ======================================================================
# PHASE 2 — ENHANCED TELEMETRY STORAGE + AI-READY FEATURE STORE
# ======================================================================

class RaceSession(db.Model):
    """One loaded FastF1 session (normally the Race) for a round, with a weather summary."""
    __tablename__ = "race_sessions"
    session_id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.Integer, db.ForeignKey('races.race_id', ondelete='CASCADE'), nullable=False, index=True)
    season = db.Column(db.Integer, nullable=False, index=True)
    round = db.Column(db.Integer, nullable=False)
    session_type = db.Column(db.String(8), nullable=False, default="R")  # R, Q, S ...
    event_name = db.Column(db.Text)
    total_laps = db.Column(db.Integer)
    avg_air_temp = db.Column(db.Float)
    avg_track_temp = db.Column(db.Float)
    avg_humidity = db.Column(db.Float)
    rainfall = db.Column(db.Boolean, default=False)
    ingested_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('race_id', 'session_type', name='uq_session_race_type'),)


class Lap(db.Model):
    """Per-driver, per-lap timing row (the raw telemetry-derived layer)."""
    __tablename__ = "laps"
    id = db.Column(db.BigInteger, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('race_sessions.session_id', ondelete='CASCADE'), nullable=False, index=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.driver_id'), nullable=False)
    lap_number = db.Column(db.Integer, nullable=False)
    lap_time_s = db.Column(db.Float)
    s1_s = db.Column(db.Float)
    s2_s = db.Column(db.Float)
    s3_s = db.Column(db.Float)
    compound = db.Column(db.String(16))
    tyre_life = db.Column(db.Float)
    stint = db.Column(db.Integer)
    position = db.Column(db.Integer)
    is_pit_in = db.Column(db.Boolean, default=False)
    is_pit_out = db.Column(db.Boolean, default=False)
    track_status = db.Column(db.String(8))
    is_accurate = db.Column(db.Boolean, default=False)
    gap_ahead_s = db.Column(db.Float)
    gap_behind_s = db.Column(db.Float)

    __table_args__ = (
        db.UniqueConstraint('session_id', 'driver_id', 'lap_number', name='uq_lap_session_driver_lap'),
        db.Index('ix_laps_session_driver', 'session_id', 'driver_id'),
    )


class Stint(db.Model):
    """Per-driver tyre stint with its own pace and degradation slope."""
    __tablename__ = "stints"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('race_sessions.session_id', ondelete='CASCADE'), nullable=False, index=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.driver_id'), nullable=False)
    stint_number = db.Column(db.Integer, nullable=False)
    compound = db.Column(db.String(16))
    lap_start = db.Column(db.Integer)
    lap_end = db.Column(db.Integer)
    laps = db.Column(db.Integer)
    avg_lap_time_s = db.Column(db.Float)
    degradation_s_per_lap = db.Column(db.Float)

    __table_args__ = (db.UniqueConstraint('session_id', 'driver_id', 'stint_number', name='uq_stint_session_driver_stint'),)


class DriverRaceFeature(db.Model):
    """
    AI-ready feature store: one row per driver per race with standardized numeric features.
    Every downstream AI module (driver rating, DNA, clustering, strategy) reads from here.
    """
    __tablename__ = "driver_race_features"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('race_sessions.session_id', ondelete='CASCADE'), nullable=False, index=True)
    race_id = db.Column(db.Integer, db.ForeignKey('races.race_id', ondelete='CASCADE'), nullable=False)
    season = db.Column(db.Integer, nullable=False, index=True)
    round = db.Column(db.Integer, nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.driver_id'), nullable=False)
    driver_code = db.Column(db.String(8), nullable=False, index=True)
    constructor_id = db.Column(db.Integer, db.ForeignKey('constructors.constructor_id'))

    # result context
    grid_position = db.Column(db.Integer)
    finish_position = db.Column(db.Integer)
    status = db.Column(db.Text)
    points = db.Column(db.Float)
    total_laps = db.Column(db.Integer)
    clean_laps = db.Column(db.Integer)

    # pace
    avg_pace_s = db.Column(db.Float)
    best_lap_s = db.Column(db.Float)
    s1_avg_s = db.Column(db.Float)
    s2_avg_s = db.Column(db.Float)
    s3_avg_s = db.Column(db.Float)
    lap_consistency_s = db.Column(db.Float)            # std-dev of clean laps
    race_pace_trend_s_per_lap = db.Column(db.Float)    # slope vs lap number

    # tyres / strategy
    tyre_degradation_s_per_lap = db.Column(db.Float)   # mean per-stint slope vs tyre life
    avg_stint_length = db.Column(db.Float)
    pit_stop_count = db.Column(db.Integer)
    pit_laps = db.Column(db.JSON)

    # racecraft
    position_changes = db.Column(db.Integer)           # grid - finish (+ = gained)
    overtake_count = db.Column(db.Integer)
    avg_gap_ahead_s = db.Column(db.Float)
    avg_gap_behind_s = db.Column(db.Float)
    penalties = db.Column(db.Integer)

    # conditions
    avg_air_temp = db.Column(db.Float)
    avg_track_temp = db.Column(db.Float)
    rainfall = db.Column(db.Boolean, default=False)

    computed_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('session_id', 'driver_id', name='uq_feature_session_driver'),)
