# src/tools/akshare_tools.py
"""使用多数据源获取股票数据的工具类（腾讯/新浪/TickFlow/akshare）"""

import logging
import time

from src.tools.akshare_data_parser import (
    generate_stock_report,
    get_financial_statements,
    get_stock_basic_info,
    get_stock_history_data,
)
from src.tools.reporting_tools import BaseTool

logger = logging.getLogger(__name__)


# ── 模块级报告缓存，避免同一 ticker 被多次生成报告 ─
_report_cache: dict[str, str] = {}


class AkShareTool(BaseTool):
    """多数据源股票数据工具"""

    name: str = "AkShare Data Tool"
    description: str = "获取股票的财务数据、价格数据和市场信息（多数据源）"

    def _run(self, ticker: str, period: str = "1y") -> str:
        cache_key = f"{ticker}:{period}"
        if cache_key in _report_cache:
            logger.info(f"使用缓存报告: {ticker}")
            return _report_cache[cache_key]

        try:
            time.sleep(1)
            logger.info(f"获取 {ticker} 的数据，周期: {period}")
            time.sleep(0.5)
            info = get_stock_basic_info(ticker)
            time.sleep(0.5)
            hist = get_stock_history_data(ticker, period)
            time.sleep(0.5)
            financials = get_financial_statements(ticker, "利润表")
            time.sleep(0.3)
            balance_sheet = get_financial_statements(ticker, "资产负债表")
            time.sleep(0.3)
            cashflow = get_financial_statements(ticker, "现金流量表")
            report = generate_stock_report(ticker, info, hist, financials, balance_sheet, cashflow)
            _report_cache[cache_key] = report
            logger.info(f"成功获取 {ticker} 的数据")
            return report
        except Exception as e:
            error_msg = f"获取 {ticker} 数据失败: {str(e)}"
            logger.error(error_msg)
            return error_msg