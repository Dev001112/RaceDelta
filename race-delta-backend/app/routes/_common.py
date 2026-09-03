# app/routes/_common.py
"""Helpers shared by the route modules."""
import functools
import hmac
import os

from flask import jsonify, request

from app.services import cache_store
from app.services.f1_service import _api_request as openf1_request
from app.utils.season_resolver import resolve_seasons


def cached_openf1_get(path, params=None, ttl=None):
    """OpenF1 GET via the shared fetcher (retries, stale-while-revalidate, negative cache).
    Data of a finished season (params carry `year`) never expires."""
    return openf1_request(path, params, ttl=ttl or cache_store.season_ttl((params or {}).get("year")))


def resolve_request_season(raw_season):
    if not raw_season or raw_season == "current":
        return resolve_seasons()["display_season"]
    return int(raw_season)


def admin_only(fn):
    """Admin endpoints trigger FastF1 downloads and DB writes: require ADMIN_TOKEN via X-Admin-Token.
    With no ADMIN_TOKEN configured they are disabled outright rather than open."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        expected = os.getenv("ADMIN_TOKEN") or ""
        if not expected:
            return jsonify({"error": "Admin endpoints are disabled: set ADMIN_TOKEN to enable them"}), 403
        if not hmac.compare_digest(request.headers.get("X-Admin-Token", ""), expected):
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper
