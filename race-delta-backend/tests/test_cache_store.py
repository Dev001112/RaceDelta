import time

from app.services import cache_store


def test_cached_serves_stale_and_refreshes_in_background(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_store, "BASE_DIR", tmp_path)
    calls = []

    def build():
        calls.append(1)
        return {"n": len(calls)}

    assert cache_store.cached("t", "k", 60, build) == {"n": 1}      # miss -> synchronous build
    assert cache_store.cached("t", "k", 60, build) == {"n": 1}      # fresh hit, no rebuild
    cache_store.set("t", "k", {"n": "old"}, ttl=-1)                  # expired, inside the stale grace
    assert cache_store.cached("t", "k", 60, build) == {"n": "old"}  # stale served immediately
    deadline = time.time() + 5
    while cache_store.get("t", "k") != {"n": 2} and time.time() < deadline:
        time.sleep(0.05)
    assert cache_store.get("t", "k") == {"n": 2}                    # refreshed in the background


def test_season_ttl_is_long_only_for_finished_seasons(monkeypatch):
    import app.utils.season_resolver as sr
    monkeypatch.setattr(sr, "resolve_seasons", lambda: {"display_season": 2026})
    assert cache_store.season_ttl(2023) == cache_store.LONG_TTL
    assert cache_store.season_ttl(2026) == cache_store.DEFAULT_TTL
    assert cache_store.season_ttl(None) == cache_store.DEFAULT_TTL
