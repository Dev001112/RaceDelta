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
