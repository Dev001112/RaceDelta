from datetime import datetime
from app.extensions import db

class Season(db.Model):
    __tablename__ = 'seasons'
    year = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    constructor_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    color = db.Column(db.String(16))
    nationality = db.Column(db.String(64))
    
    # Metadata
    principal = db.Column(db.String(128))
    base = db.Column(db.String(128))
    
    # Relationships
    drivers = db.relationship('Driver', backref='team_ref', lazy=True)

class Driver(db.Model):
    __tablename__ = 'drivers'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), unique=True, nullable=False) # VER, HAM
    number = db.Column(db.Integer)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    dob = db.Column(db.Date)
    nationality = db.Column(db.String(64))
    headshot_url = db.Column(db.String(512))
    
    # Current team link
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Race(db.Model):
    __tablename__ = 'races'
    id = db.Column(db.Integer, primary_key=True)
    season = db.Column(db.Integer, nullable=False)
    round = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(128))
    circuit_name = db.Column(db.String(128))
    date = db.Column(db.DateTime)
    
    # Constraints
    __table_args__ = (db.UniqueConstraint('season', 'round', name='_season_round_uc'),)

class RaceResult(db.Model):
    __tablename__ = 'race_results'
    id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.Integer, db.ForeignKey('races.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    constructor_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    
    position = db.Column(db.Integer)
    points = db.Column(db.Float)
    grid = db.Column(db.Integer)
    status = db.Column(db.String(64)) # "Finished", "DNF"
    
    # Telemetry Summary
    fastest_lap_time = db.Column(db.Float) # Seconds
    fastest_lap_rank = db.Column(db.Integer)
    
    driver = db.relationship('Driver', backref='results')
    race = db.relationship('Race', backref='results')
