"""
Simple in-memory caching system for Daily Set application.
Provides caching for daily boards and other frequently accessed data.
"""

import time
from typing import Any, Optional, Dict, Tuple
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """A single cache entry with value and expiration"""
    value: Any
    expires_at: float
    created_at: float


class MemoryCache:
    """Thread-safe in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache, return None if not found or expired"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats['misses'] += 1
                return None
            
            # Check if expired
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._stats['misses'] += 1
                self._stats['evictions'] += 1
                return None
            
            self._stats['hits'] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set a value in cache with TTL in seconds"""
        with self._lock:
            now = time.time()
            expires_at = now + ttl_seconds
            
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=expires_at,
                created_at=now
            )
            self._stats['sets'] += 1
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache, return True if existed"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            evicted = len(self._cache)
            self._cache.clear()
            self._stats['evictions'] += evicted
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries, return count of removed entries"""
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry.expires_at
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            self._stats['evictions'] += len(expired_keys)
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                **self._stats,
                'total_requests': total_requests,
                'hit_rate_percent': round(hit_rate, 2),
                'cache_size': len(self._cache),
                'cache_memory_estimate_kb': self._estimate_memory_usage()
            }
    
    def _estimate_memory_usage(self) -> int:
        """Rough estimate of memory usage in KB"""
        # Very rough estimate: 1KB per entry on average
        return len(self._cache)


# Global cache instance
_cache = MemoryCache()


def get_cache() -> MemoryCache:
    """Get the global cache instance"""
    return _cache


def cache_daily_board(date: str, board: list, ttl_hours: int = 24) -> None:
    """Cache a daily board for the given date"""
    cache_key = f"daily_board:{date}"
    _cache.set(cache_key, board, ttl_hours * 3600)


def get_cached_daily_board(date: str) -> Optional[list]:
    """Get cached daily board for the given date"""
    cache_key = f"daily_board:{date}"
    return _cache.get(cache_key)


def cache_leaderboard(date: str, leaderboard: list, ttl_minutes: int = 5) -> None:
    """Cache leaderboard data with shorter TTL since it changes frequently"""
    cache_key = f"leaderboard:{date}"
    _cache.set(cache_key, leaderboard, ttl_minutes * 60)


def get_cached_leaderboard(date: str) -> Optional[list]:
    """Get cached leaderboard for the given date"""
    cache_key = f"leaderboard:{date}"
    return _cache.get(cache_key)


def invalidate_leaderboard_cache(date: str) -> None:
    """Invalidate leaderboard cache when new completions are added"""
    cache_key = f"leaderboard:{date}"
    _cache.delete(cache_key)


def cleanup_cache_periodically():
    """Cleanup function that can be called periodically"""
    expired_count = _cache.cleanup_expired()
    if expired_count > 0:
        print(f"Cache cleanup: removed {expired_count} expired entries")


# Cache warming functions
def warm_daily_board_cache(dates: list[str]) -> None:
    """Pre-populate cache with daily boards for given dates"""
    from . import game
    
    for date in dates:
        if get_cached_daily_board(date) is None:
            board = game.daily_board(date)
            cache_daily_board(date, board)


def warm_cache_for_today_and_recent():
    """Warm cache with today's board and recent dates"""
    from . import game
    from datetime import date, timedelta
    
    today = date.today()
    dates_to_warm = []
    
    # Add today and next few days
    for i in range(7):
        date_str = (today + timedelta(days=i)).isoformat()
        dates_to_warm.append(date_str)
    
    # Add previous few days  
    for i in range(1, 4):
        date_str = (today - timedelta(days=i)).isoformat()
        dates_to_warm.append(date_str)
    
    warm_daily_board_cache(dates_to_warm)
