# D:\RaceDelta\race-delta-backend\app\__init__.py
import os

from flask import Flask, request
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
    load_dotenv(override=os.getenv("FLASK_ENV", "development") != "production")   # see config.py: dev must survive a reloader re-exec

    app = Flask(__name__)
    
    # Load configuration from config.py
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Validate required configuration
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is not set. Set it in the shell or in a .env file.")

    CORS(app, origins=app.config["CORS_ORIGINS"])

    # Initialize the shared db instance with this Flask app
    db.init_app(app)

    # Register error handlers
    from .middleware.error_handler import register_error_handlers
    register_error_handlers(app)

    # Register routes inside factory to avoid top-level circular imports
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.after_request
    def _browser_cache(resp):
        # Data changes once a week, not once a click: let the browser reuse GET responses across navigations.
        path = request.path
        if (request.method == "GET" and resp.status_code == 200 and path.startswith("/api/")
                and not path.startswith(("/api/admin", "/api/analyst", "/api/health"))):
            resp.headers.setdefault("Cache-Control", f"public, max-age={app.config.get('BROWSER_CACHE_MAX_AGE', 300)}")
            resp.add_etag()
            return resp.make_conditional(request)
        return resp

    from app.services.cache_warmer import start as start_cache_warmer
    start_cache_warmer(app)

    return app
