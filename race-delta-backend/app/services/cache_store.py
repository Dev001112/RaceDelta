import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Optional


BASE_DIR = Path(os.getenv("RACEDELTA_CACHE_DIR", ".cache"))


def _path(namespace: str, key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return BASE_DIR / namespace / f"{digest}.json"


def get(namespace: str, key: str) -> Optional[Any]:
    path = _path(namespace, key)
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if payload.get("expires_at", 0) < time.time():
            try:
                path.unlink()
            except OSError:
                pass
            return None
        return payload.get("value")
    except (OSError, json.JSONDecodeError):
        return None


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
