# D:\RaceDelta\race-delta-backend\app\__init__.py
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Import the single shared SQLAlchemy instance from models (where migrations & models live)
# This ensures there is only one SQLAlchemy object in the project.
from models import db

def create_app():
    load_dotenv()

    app = Flask(__name__)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set. Set it in the shell or in a .env file.")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key")

    CORS(app)

    # Initialize the shared db instance with this Flask app
    db.init_app(app)

    # Register routes inside factory to avoid top-level circular imports
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
