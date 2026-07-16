# src/utils/stock_cache_manager.py
"""股票分析缓存管理器"""

from datetime import datetime
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class StockCacheManager:
    """缓存管理"""

    def __init__(self) -> None:
        """初始化缓存管理器"""
        self.cache = {}
        self.cache_ttl = 3600
        self.analysis_history = []

    def check_cache(self, ticker: str) -> bool:
        """检查缓存是否存在且未过期"""
        if ticker in self.cache:
            cache_time = self.cache[ticker].get("timestamp", 0)
            return (datetime.now().timestamp() - cache_time) < self.cache_ttl
        return False

    def get_from_cache(self, ticker: str) -> dict[str, Any]:
        """从缓存中获取数据"""
        return self.cache.get(ticker, {})

    def save_to_cache(self, ticker: str, data: dict[str, Any]) -> None:
        """保存数据到缓存"""
        self.cache[ticker] = {"data": data, "timestamp": datetime.now().timestamp()}

    def add_to_history(self, result: dict[str, Any]) -> None:
        """添加分析结果到历史记录"""
        self.analysis_history.append(
            {
                "company": result["company"],
                "ticker": result["ticker"],
                "timestamp": result["timestamp"],
                "success": result["success"],
                "overall_score": result.get("overall_score", 0),
                "investment_rating": result.get("investment_rating", {}).get("rating", "未评级"),
            }
        )
        if len(self.analysis_history) > 1000:
            self.analysis_history = self.analysis_history[-1000:]

    def get_analysis_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取最近的分析历史记录"""
        return self.analysis_history[-limit:]

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        return {"cache_size": len(self.cache), "history_size": len(self.analysis_history), "cache_ttl": self.cache_ttl}

    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")

    def export_history(self, filepath: str) -> None:
        """导出分析历史到 JSON 文件"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.analysis_history, f, ensure_ascii=False, indent=2)
            logger.info(f"历史记录已导出: {filepath}")
        except Exception as e:
            logger.error(f"导出历史记录失败: {str(e)}")
