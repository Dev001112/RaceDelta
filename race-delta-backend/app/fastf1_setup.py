"""
Single place that enables the FastF1 on-disk cache. Import for its side effect.

Points at <backend>/fastf1_cache, which already holds the cached seasons.
Override with FASTF1_CACHE_DIR if needed.
"""
import os
import fastf1

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.getenv("FASTF1_CACHE_DIR", os.path.join(BACKEND_ROOT, "fastf1_cache"))
os.makedirs(CACHE_DIR, exist_ok=True)

try:
    fastf1.Cache.enable_cache(CACHE_DIR)
except Exception:  # already enabled elsewhere / read-only filesystem
    pass
