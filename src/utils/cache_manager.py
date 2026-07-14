# src/utils/cache_manager.py
"""
磁盘缓存管理器 - 带TTL过期，持久化存储
缓存LLM调用结果、数据采集结果，避免重复请求
"""
import os
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from src.config import Config


class CacheManager:
    """磁盘缓存管理器"""

    def __init__(self, cache_dir: Path = None, ttl: int = None):
        self.cache_dir = cache_dir or Config.CACHE_DIR
        self.ttl = ttl or Config.CACHE_TTL
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.cache_dir / "cache_index.json"
        self.cache: Dict[str, Dict] = self._load_index()

    def _load_index(self) -> Dict[str, Dict]:
        """加载缓存索引"""
        if not self.index_path.exists():
            return {}
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_index(self):
        """保存缓存索引"""
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.cache_dir / f"{safe_key}.json"

    def check(self, key: str) -> bool:
        """检查key是否存在且未过期"""
        if key not in self.cache:
            return False
        entry = self.cache[key]
        if time.time() - entry["timestamp"] > self.ttl:
            self.delete(key)
            return False
        if not self._get_cache_path(key).exists():
            self.delete(key)
            return False
        return True

    def get(self, key: str) -> Dict[str, Any]:
        """获取缓存数据"""
        if not self.check(key):
            return {}
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            self.delete(key)
            return {}

    def set(self, key: str, data: Dict[str, Any]):
        """设置缓存数据"""
        cache_path = self._get_cache_path(key)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.cache[key] = {
            "timestamp": time.time(),
            "size": len(json.dumps(data)),
        }
        self._save_index()

    def delete(self, key: str):
        """删除指定缓存"""
        if key in self.cache:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
            del self.cache[key]
            self._save_index()

    def clear(self):
        """清空所有缓存"""
        for key in list(self.cache.keys()):
            self.delete(key)
        self.cache = {}
        self._save_index()

    def cleanup_expired(self) -> int:
        """清理过期缓存，返回清理数量"""
        deleted = 0
        for key in list(self.cache.keys()):
            if not self.check(key):
                deleted += 1
        return deleted

    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_files = len(list(self.cache_dir.glob("*.json"))) - 1  # minus index
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))
        return {
            "cache_size": len(self.cache),
            "cache_ttl": self.ttl,
            "cache_dir": str(self.cache_dir),
            "total_files": total_files,
            "total_bytes": total_size,
        }


# 全局单例
_cache_instance: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器单例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance