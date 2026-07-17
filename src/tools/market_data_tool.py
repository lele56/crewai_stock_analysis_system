# src/tools/market_data_tool.py
"""市场数据工具 - 获取实时市场概览、行业表现、市场情绪
通过 akshare 获取真实 A 股市场数据，数据源不可用时降级为通用描述
"""

from datetime import datetime
import logging

from src.tools.reporting_tools import BaseTool

logger = logging.getLogger(__name__)

_AKSHARE_AVAILABLE = False
try:
    import akshare as ak  # type: ignore[import-untyped]
    _AKSHARE_AVAILABLE = True
except ImportError:
    pass

# A 股主要指数代码
_A_INDEX_MAP = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "科创50": "sh000688",
    "沪深300": "sh000300",
    "中证500": "sh000905",
}

_INDEX_CACHE: dict[str, dict] = {}
_INDEX_CACHE_TS = 0.0
_INDEX_CACHE_TTL = 300  # 5 分钟


def _fetch_index_data() -> dict[str, dict]:
    """获取 A 股主要指数最新行情（5 分钟缓存）
    主源: stock_zh_index_daily_tx (腾讯，纯HTTP，不依赖 py_mini_racer)
    """
    global _INDEX_CACHE, _INDEX_CACHE_TS

    now = datetime.now().timestamp()
    if _INDEX_CACHE and (now - _INDEX_CACHE_TS) < _INDEX_CACHE_TTL:
        return _INDEX_CACHE

    if not _AKSHARE_AVAILABLE:
        return {}
    from src.tools.akshare_data_sources import get_index_daily_tx

    try:
        result = {}
        for name, code in _A_INDEX_MAP.items():
            try:
                df = get_index_daily_tx(code)
                if not df.empty:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) >= 2 else latest
                    close_col = latest.get("close", latest.get("收盘", 0))
                    prev_col = prev.get("close", prev.get("收盘", close_col))
                    result[name] = {
                        "price": float(close_col),
                        "change_pct": float((close_col - prev_col) / prev_col * 100) if prev_col else 0,
                        "volume": int(latest.get("volume", latest.get("成交量", 0))),
                        "amount": float(latest.get("amount", latest.get("成交额", 0)) if ("amount" in latest or "成交额" in latest) else 0),
                    }
            except Exception:
                continue
        _INDEX_CACHE = result
        _INDEX_CACHE_TS = now
        return result
    except Exception as e:
        logger.debug(f"获取指数行情失败: {str(e)[:80]}")
        return _INDEX_CACHE or {}


def _fetch_sector_data() -> list[dict]:
    """通过 akshare 获取行业板块涨跌排行"""
    if not _AKSHARE_AVAILABLE:
        return []
    try:
        df = ak.stock_sector_fund_flow_rank(indicator="今日")
        if df.empty:
            return []
        sectors = []
        for _, row in df.head(10).iterrows():
            sectors.append({
                "name": str(row.get("名称", "")),
                "change_pct": float(row.get("涨跌幅", 0)),
            })
        return sectors
    except Exception as e:
        logger.debug(f"获取板块资金流失败: {str(e)[:80]}")
        return []


def _format_amount(amount: float) -> str:
    """格式化成交额"""
    if amount >= 1e8:
        return f"{amount / 1e8:.1f}亿"
    if amount >= 1e4:
        return f"{amount / 1e4:.1f}万"
    return f"{amount:.0f}"


class MarketDataTool(BaseTool):
    """市场数据工具"""

    name: str = "Market Data Tool"
    description: str = "获取实时市场数据和行业信息"

    def _run(self, query: str, data_type: str = "market_overview") -> str:
        """获取市场数据"""
        try:
            logger.info(f"获取市场数据: {query}, 类型: {data_type}")
            dt = data_type.lower()
            if dt in ("market_overview", "market_data", "market_summary", "stock_market_data",
                      "china_a_share_market_data", "stock_daily_history", "index_daily_history",
                      "fund_flow_and_sentiment", "index_constituents",
                      "income_statement_balance_sheet_cashflow", "competitor_financial_performance",
                      "financial_data", "industry_analysis", "stock_analysis", "company_analysis",
                      "valutation_and_context", "price_data", "market_research", "sector_analysis"):
                return self._get_market_overview()
            if dt in ("sector_performance", "sector_performance_data", "sector_analysis"):
                return self._get_sector_performance()
            if dt in ("market_sentiment", "sentiment_analysis", "market_mood"):
                return self._get_market_sentiment()
            return self._get_market_overview()
        except Exception as e:
            error_msg = f"获取市场数据失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _get_market_overview(self) -> str:
        """获取市场概览 - 优先使用 akshare 真实数据（精简版）"""
        index_data = _fetch_index_data()
        if index_data:
            parts = []
            for name, data in index_data.items():
                sign = "+" if data["change_pct"] >= 0 else ""
                parts.append(f"{name}: {data['price']:.2f}({sign}{data['change_pct']:.2f}%)")
            return "市场概览: " + ", ".join(parts)
        return "市场概览: 数据源不可用"

    def _get_sector_performance(self) -> str:
        """获取行业表现 - 优先使用 akshare 真实数据（精简版）"""
        sectors = _fetch_sector_data()
        if sectors:
            parts = []
            for s in sectors:
                sign = "+" if s["change_pct"] >= 0 else ""
                parts.append(f"{s['name']}: {sign}{s['change_pct']:.2f}%")
            return "行业表现: " + ", ".join(parts)
        return "行业表现: 数据源不可用"

    def _get_market_sentiment(self) -> str:
        """获取市场情绪（精简版）"""
        return "市场情绪: 请结合指数涨跌、成交量变化、北向资金流向、融资融券余额、涨跌停家数等维度综合判断"