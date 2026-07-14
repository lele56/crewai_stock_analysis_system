# tests/test_cache_manager.py
"""
缓存管理器测试
"""
import pytest
import os
from src.utils.cache_manager import CacheManager


class TestCacheManager:
    """测试缓存管理器"""

    def test_init(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir, ttl=3600)
        assert cache.ttl == 3600
        assert cache.cache_dir == temp_cache_dir
        assert len(cache.cache) == 0

    def test_set_and_check(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir, ttl=3600)
        cache.set("AAPL", {"price": 150.0, "score": 85})
        assert cache.check("AAPL") is True

    def test_get(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir, ttl=3600)
        data = {"price": 150.0, "score": 85}
        cache.set("AAPL", data)
        result = cache.get("AAPL")
        assert result == data

    def test_ttl_expiry(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir, ttl=1)
        cache.set("AAPL", {"price": 150.0})
        assert cache.check("AAPL") is True
        # 直接修改缓存时间戳模拟过期，避免 sleep
        cache.cache["AAPL"]["timestamp"] = 0
        assert cache.check("AAPL") is False

    def test_disk_persistence(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir, ttl=3600)
        cache.set("AAPL", {"price": 150.0})

        cache2 = CacheManager(temp_cache_dir, ttl=3600)
        assert cache2.check("AAPL") is True
        assert cache2.get("AAPL") == {"price": 150.0}

    def test_clear(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir, ttl=3600)
        cache.set("AAPL", {"price": 150.0})
        cache.set("GOOGL", {"price": 2800.0})
        assert len(cache.cache) == 2
        cache.clear()
        assert len(cache.cache) == 0

    def test_stats(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir, ttl=3600)
        cache.set("AAPL", {"price": 150.0})
        stats = cache.stats()
        assert stats['cache_size'] == 1
        assert stats['cache_ttl'] == 3600
        assert stats['cache_dir'] == temp_cache_dir

    def test_miss(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir, ttl=3600)
        assert cache.check("NONEXISTENT") is False
        result = cache.get("NONEXISTENT")
        assert result == {}

    def test_special_chars_ticker(self, temp_cache_dir):
        cache = CacheManager(temp_cache_dir, ttl=3600)
        cache.set("BRK-A", {"price": 500000.0})
        assert cache.check("BRK-A") is True
        assert cache.get("BRK-A") == {"price": 500000.0}