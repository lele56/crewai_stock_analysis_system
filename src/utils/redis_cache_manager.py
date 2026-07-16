# src/utils/redis_cache_manager.py
"""Redis 缓存管理器 — 持久化 LLM 分析结果，支持多进程共享

Redis 不可用时自动降级为内存缓存，接口与 StockCacheManager 兼容。
"""

from datetime import datetime
import json
import logging
from typing import Any

from src.config import Config

logger = logging.getLogger(__name__)

_REDIS_AVAILABLE = False
try:
    import redis as _redis
    _REDIS_AVAILABLE = True
except ImportError:
    logger.warning("redis-py 未安装，使用内存缓存降级模式")


class RedisCacheManager:
    """Redis 缓存管理器（自动降级）"""

    def __init__(self) -> None:
        self._redis: _redis.Redis | None = None
        self._fallback: dict[str, Any] = {}       # 降级内存缓存
        self._history: list[dict[str, Any]] = []
        self._connect()

    # ── 连接管理 ─────────────────────────────────

    def _connect(self) -> None:
        """连接 Redis，失败则降级为内存缓存"""
        if not _REDIS_AVAILABLE or not Config.REDIS_ENABLED:
            logger.info("Redis 未启用，使用内存缓存")
            self._redis = None
            return

        try:
            kwargs = {
                "host": Config.REDIS_HOST,
                "port": Config.REDIS_PORT,
                "db": Config.REDIS_DB,
                "decode_responses": True,
                "socket_connect_timeout": 3,
                "socket_timeout": 3,
            }
            if Config.REDIS_PASSWORD:
                kwargs["password"] = Config.REDIS_PASSWORD
            self._redis = _redis.Redis(**kwargs)
            self._redis.ping()
            logger.info(f"Redis 连接成功: {Config.REDIS_HOST}:{Config.REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Redis 连接失败 ({e})，降级为内存缓存")
            self._redis = None

    @property
    def connected(self) -> bool:
        """Redis 是否已连接"""
        return self._redis is not None

    @property
    def redis_available(self) -> bool:
        """Redis 是否可用（健康检查用）"""
        if not self._redis:
            return False
        try:
            self._redis.ping()
            return True
        except Exception:
            return False

    @property
    def redis_error(self) -> str | None:
        """Redis 不可用时的错误信息"""
        if _REDIS_AVAILABLE and Config.REDIS_ENABLED and self._redis is None:
            return "connection_failed"
        if not _REDIS_AVAILABLE:
            return "redis_py_not_installed"
        if not Config.REDIS_ENABLED:
            return "disabled"
        return None

    # ── 键名工具 ─────────────────────────────────

    def _key(self, *parts: str) -> str:
        """构建 Redis 键名: {prefix}:{part1}:{part2}"""
        return ":".join([Config.REDIS_PREFIX, *parts])

    # ── 缓存读写 ─────────────────────────────────

    def check_cache(self, ticker: str) -> bool:
        """检查缓存是否存在且未过期"""
        if self._redis:
            return bool(self._redis.exists(self._key("analysis", ticker)))
        return ticker in self._fallback

    def get_from_cache(self, ticker: str) -> dict[str, Any]:
        """从缓存中获取分析结果"""
        if self._redis:
            raw = self._redis.get(self._key("analysis", ticker))
            if raw:
                return json.loads(raw)
            return {}
        return self._fallback.get(ticker, {})

    def save_to_cache(self, ticker: str, data: dict[str, Any]) -> None:
        """保存分析结果到缓存"""
        payload = json.dumps(data, ensure_ascii=False, default=str)
        if self._redis:
            self._redis.setex(self._key("analysis", ticker), Config.REDIS_ANALYSIS_TTL, payload)
        else:
            self._fallback[ticker] = data

    def save_collection_data(self, ticker: str, data: dict[str, Any]) -> None:
        """保存采集阶段数据（较短 TTL）"""
        payload = json.dumps(data, ensure_ascii=False, default=str)
        if self._redis:
            self._redis.setex(self._key("collection", ticker), Config.REDIS_COLLECTION_TTL, payload)

    def get_collection_data(self, ticker: str) -> dict[str, Any] | None:
        """获取采集阶段缓存"""
        if self._redis:
            raw = self._redis.get(self._key("collection", ticker))
            return json.loads(raw) if raw else None
        return None

    # ── 历史记录 ─────────────────────────────────

    def add_to_history(self, result: dict[str, Any]) -> None:
        """添加分析结果到历史记录（Redis 用 sorted set，按时间排序）"""
        entry = {
            "company": result.get("company", ""),
            "ticker": result.get("ticker", ""),
            "timestamp": result.get("timestamp", datetime.now().isoformat()),
            "success": result.get("success", False),
            "overall_score": result.get("overall_score", 0),
            "investment_rating": result.get("investment_rating", {}).get("rating", "未评级"),
            "profile": result.get("profile", "standard"),
        }
        if self._redis:
            score = datetime.now().timestamp()
            member = json.dumps(entry, ensure_ascii=False)
            history_key = self._key("history")
            self._redis.zadd(history_key, {member: score})
            self._redis.zremrangebyrank(history_key, 0, -1001)  # 保留最近 1000 条
        else:
            self._history.append(entry)
            if len(self._history) > 1000:
                self._history = self._history[-1000:]

    def get_analysis_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取最近的分析历史"""
        if self._redis:
            raw = self._redis.zrevrange(self._key("history"), 0, limit - 1)
            return [json.loads(item) for item in raw]
        return self._history[-limit:]

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        if self._redis:
            info = self._redis.info("keyspace")
            analysis_count = self._redis.dbsize()
            history_count = self._redis.zcard(self._key("history"))
            return {
                "cache_size": analysis_count,
                "history_size": history_count,
                "redis_connected": True,
                "redis_info": info,
            }
        return {
            "cache_size": len(self._fallback),
            "history_size": len(self._history),
            "redis_connected": False,
        }

    def clear_cache(self) -> None:
        """清空分析缓存（保留历史记录）"""
        if self._redis:
            keys = self._redis.keys(self._key("analysis", "*"))
            if keys:
                self._redis.delete(*keys)
        else:
            self._fallback.clear()
        logger.info("缓存已清空")

    def export_history(self, filepath: str) -> None:
        """导出分析历史到 JSON 文件"""
        try:
            history = self.get_analysis_history(limit=10000)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            logger.info(f"历史记录已导出: {filepath} ({len(history)} 条)")
        except Exception as e:
            logger.error(f"导出历史记录失败: {e}")

    def close(self) -> None:
        """关闭 Redis 连接"""
        if self._redis:
            self._redis.close()
            self._redis = None