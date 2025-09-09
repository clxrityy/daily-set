import time
from app.cache import get_cache, cache_daily_board, get_cached_daily_board, cleanup_cache_periodically, warm_daily_board_cache, warm_cache_for_today_and_recent


def test_cleanup_cache_periodically_removes_expired(monkeypatch):
    c = get_cache()
    c.clear()
    # Insert an entry with very short TTL via direct set
    cache_daily_board("2099-01-01", [1, 2, 3])
    # Force expire by moving time forward
    orig_time = time.time
    try:
        monkeypatch.setattr(time, "time", lambda: orig_time() + 999999)
        # Should not raise and should evict expired entries
        cleanup_cache_periodically()
        stats = c.get_stats()
        assert stats["evictions"] >= 1
    finally:
        monkeypatch.setattr(time, "time", orig_time)


def test_warm_daily_board_cache_and_recent():
    c = get_cache()
    c.clear()
    # Warm a specific set of dates
    warm_daily_board_cache(["2025-01-01", "2025-01-02"]) 
    assert get_cached_daily_board("2025-01-01") is not None
    assert get_cached_daily_board("2025-01-02") is not None

    # Warm today and recent; just ensure it doesn't crash and populates at least today
    c.clear()
    warm_cache_for_today_and_recent()
    # We can't know today's date here without importing date; just check cache not empty
    assert c.get_stats()["cache_size"] >= 1
