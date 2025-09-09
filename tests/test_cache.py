import time
from app.cache import MemoryCache, cache_daily_board, get_cached_daily_board, cache_leaderboard, get_cached_leaderboard, invalidate_leaderboard_cache


def test_memory_cache_set_get_and_expire():
    c = MemoryCache()
    c.set('k', 'v', ttl_seconds=1)
    assert c.get('k') == 'v'
    # expire
    time.sleep(1.1)
    assert c.get('k') is None
    # cleanup reports evictions
    removed = c.cleanup_expired()
    assert removed >= 0
    stats = c.get_stats()
    assert 'hits' in stats and 'misses' in stats and 'cache_size' in stats


def test_cache_helpers_leaderboard_and_board():
    date = '2099-01-01'
    board = [[0,0,0,0]] * 12
    cache_daily_board(date, board)
    assert get_cached_daily_board(date) == board

    lb = [{"username": "alice", "best": 42, "completed_at": None}]
    cache_leaderboard(date, lb)
    assert get_cached_leaderboard(date) == lb
    invalidate_leaderboard_cache(date)
    assert get_cached_leaderboard(date) is None
