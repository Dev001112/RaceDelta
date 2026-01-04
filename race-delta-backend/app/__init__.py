# D:\RaceDelta\race-delta-backend\app\__init__.py
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Import the single shared SQLAlchemy instance from models (where migrations & models live)
# This ensures there is only one SQLAlchemy object in the project.
from models import db
from config import get_config

def create_app(config_name=None):
    """
    Application factory pattern.
    Loads configuration from config.py based on FLASK_ENV environment variable.
    """
    load_dotenv()

    app = Flask(__name__)
    
    # Load configuration from config.py
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Validate required configuration
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is not set. Set it in the shell or in a .env file.")

    CORS(app)

    # Initialize the shared db instance with this Flask app
    db.init_app(app)

    # Register error handlers
    from .middleware.error_handler import register_error_handlers
    register_error_handlers(app)

    # Register routes inside factory to avoid top-level circular imports
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
