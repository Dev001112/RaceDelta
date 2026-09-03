# app/routes/__init__.py
"""The /api blueprint. Each module below registers its routes on `api_bp` when imported."""
from flask import Blueprint

api_bp = Blueprint("api", __name__)

from . import core, compare, openf1, admin, lab  # noqa: E402,F401  (import for side effects)
