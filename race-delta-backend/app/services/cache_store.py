"""
Persistent JSON cache with stale-while-revalidate.

- get/set: plain TTL cache (unchanged API).
- cached(): return a fresh value; if the entry is expired but inside STALE_GRACE, return it immediately and
  rebuild it on a single background worker; build synchronously only when nothing is cached at all.
- season_ttl(): finished seasons never change, so their data gets LONG_TTL.
"""
import hashlib
import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional, Tuple


BASE_DIR = Path(os.getenv("RACEDELTA_CACHE_DIR", ".cache"))
DEFAULT_TTL = int(os.getenv("RACEDELTA_CACHE_TTL", str(6 * 3600)))
LONG_TTL = 365 * 24 * 3600
STALE_GRACE = int(os.getenv("RACEDELTA_CACHE_STALE_GRACE", str(30 * 24 * 3600)))

_MISSING = object()
_refreshing: dict = {}          # keys with a refresh queued or running
_lock = threading.Lock()
_queue: "queue.Queue" = queue.Queue()
_worker: Optional[threading.Thread] = None


def _path(namespace: str, key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return BASE_DIR / namespace / f"{digest}.json"


def get_entry(namespace: str, key: str) -> Tuple[Any, bool]:
    """(value, fresh). value is _MISSING when absent or older than the stale grace."""
    path = _path(namespace, key)
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return _MISSING, False
    expires_at = payload.get("expires_at", 0)
    now = time.time()
    if expires_at >= now:
        return payload.get("value"), True
    if expires_at + STALE_GRACE >= now:
        return payload.get("value"), False
    try:
        path.unlink()
    except OSError:
        pass
    return _MISSING, False


def get(namespace: str, key: str) -> Optional[Any]:
    value, fresh = get_entry(namespace, key)
    return value if fresh else None


def set(namespace: str, key: str, value: Any, ttl: int) -> None:
    path = _path(namespace, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "expires_at": time.time() + ttl,
        "value": value,
    }
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"), default=str)
    os.replace(tmp_path, path)


def cached_entry(namespace: str, key: str, ttl: int, build: Callable[[], Any]) -> Tuple[Any, bool]:
    """(value, fresh). Fresh hit -> value. Stale hit -> value now, refresh in the background. Miss -> build now."""
    value, fresh = get_entry(namespace, key)
    if fresh and value is not None:
        return value, True
    if value is _MISSING or value is None:
        value = build()
        set(namespace, key, value, ttl)
        return value, True
    _refresh_async(namespace, key, ttl, build)
    return value, False


def cached(namespace: str, key: str, ttl: int, build: Callable[[], Any]) -> Any:
    return cached_entry(namespace, key, ttl, build)[0]


def season_ttl(season, default: int = DEFAULT_TTL) -> int:
    """LONG_TTL for a season older than the one currently displayed; `default` otherwise."""
    try:
        from app.utils.season_resolver import resolve_seasons
        if season is not None and int(season) < int(resolve_seasons()["display_season"]):
            return LONG_TTL
    except Exception:
        pass
    return default


def enqueue(namespace: str, key: str, ttl: int, build: Callable[[], Any]) -> None:
    """Build `key` on the background worker and store it; a None result is not stored. Deduped per key."""
    _refresh_async(namespace, key, ttl, build)


def _refresh_async(namespace: str, key: str, ttl: int, build: Callable[[], Any]) -> None:
    with _lock:
        if key in _refreshing:
            return
        _refreshing[key] = True
    app = None
    try:
        from flask import current_app, has_app_context
        if has_app_context():
            app = current_app._get_current_object()
    except Exception:
        pass
    _queue.put((namespace, key, ttl, build, app))
    _ensure_worker()


def _ensure_worker() -> None:
    global _worker
    with _lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_drain, daemon=True, name="cache-refresh")
            _worker.start()


def _drain() -> None:
    # ponytail: one worker, so background FastF1 loads never overlap each other
    while True:
        namespace, key, ttl, build, app = _queue.get()
        try:
            if app is not None:
                with app.app_context():
                    value = build()
            else:
                value = build()
            if value is not None:
                set(namespace, key, value, ttl)
        except Exception:
            pass  # keep serving the stale copy; the next stale hit queues a retry
        finally:
            with _lock:
                _refreshing.pop(key, None)
            _queue.task_done()
