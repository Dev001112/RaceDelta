# config.py
import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # OpenF1 API Configuration
    OPENF1_BASE = os.getenv("OPENF1_BASE", "https://api.openf1.org/v1")
    OPENF1_TIMEOUT = int(os.getenv("OPENF1_TIMEOUT", "10"))
    OPENF1_CACHE_TTL = int(os.getenv("OPENF1_CACHE_TTL", "300"))  # 5 minutes
    
    # Performance Settings
    STANDINGS_MAX_RACES = int(os.getenv("STANDINGS_MAX_RACES", "10"))  # Limit races processed
    ENABLE_STANDINGS_CACHE = os.getenv("ENABLE_STANDINGS_CACHE", "true").lower() == "true"
    
    # Request timeouts
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))  # seconds


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///racedelta.db"
    )
    SQLALCHEMY_ECHO = False  # Set to True to see SQL queries


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/racedelta"
    )
    SQLALCHEMY_ECHO = False
    
    # Production settings
    OPENF1_CACHE_TTL = 600  # 10 minutes in production
    STANDINGS_MAX_RACES = 5  # Process fewer races in production for speed


class TestConfig(Config):
    """Test configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestConfig,
    "default": DevelopmentConfig,
}


def get_config(env=None):
    """Get configuration based on environment"""
    if env is None:
        env = os.getenv("FLASK_ENV", "development")
    return config.get(env, config["default"])