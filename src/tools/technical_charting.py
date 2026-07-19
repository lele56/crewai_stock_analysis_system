# src/tools/technical_charting.py
"""技术图表生成模块
提供K线图、价格走势图、成交量图、综合指标图的生成功能
"""

from datetime import datetime
import logging
import os
from typing import Any

import pandas as pd

from src.tools.reporting_tools import BaseTool
from src.tools.technical_indicators import calculate_macd, calculate_rsi

logger = logging.getLogger(__name__)


def _configure_matplotlib() -> Any:
    """延迟配置 matplotlib 后端和字体（首次图表生成时初始化），返回 pyplot 模块"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False
    return plt

# 模块级单例缓存
_plt: Any = None


def _get_plt() -> Any:
    """获取 matplotlib.pyplot 模块（延迟初始化）"""
    global _plt
    if _plt is None:
        _plt = _configure_matplotlib()
    return _plt


class ChartingTool(BaseTool):
    """图表生成工具"""

    name: str = "Charting Tool"
    description: str = (
        "生成技术分析图表。chart_type 必须为以下之一: candlestick(K线图), line(走势图), "
        "volume(成交量图), indicators(综合指标图)。price_data 传股票代码(如600519)或JSON价格数据。"
    )

    def _run(self, price_data: str, chart_type: str = "candlestick") -> str:
        """生成技术分析图表"""
        try:
            df = self._parse_or_fetch_price_data(price_data)
            if df is None or df.empty:
                return "生成图表失败: 无法获取价格数据"

            logger.info(f"生成图表，类型: {chart_type}")

            # 归一化图表类型（LLM 可能传各种变体）
            _type_aliases = {
                "technical_analysis": "indicators",
                "综合分析": "indicators",
                "kline": "candlestick",
                "k线": "candlestick",
            }
            chart_type = _type_aliases.get(chart_type, chart_type)

            os.makedirs("reports/charts", exist_ok=True)

            if chart_type == "candlestick":
                filepath = self._generate_candlestick_chart(df)
            elif chart_type == "line":
                filepath = self._generate_line_chart(df)
            elif chart_type == "volume":
                filepath = self._generate_volume_chart(df)
            elif chart_type == "indicators":
                filepath = self._generate_indicators_chart(df)
            else:
                raise ValueError("不支持的图表类型")

            logger.info(f"图表生成完成: {filepath}")
            return filepath

        except Exception as e:
            error_msg = f"生成图表失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _parse_or_fetch_price_data(self, price_data: str) -> pd.DataFrame | None:
        """解析价格数据或通过股票代码获取"""
        import json

        try:
            data = json.loads(price_data)
        except (json.JSONDecodeError, TypeError):
            return self._fetch_by_stock_code(price_data)

        if isinstance(data, dict) and any(isinstance(v, list) for v in data.values()):
            return pd.DataFrame(data)
        if isinstance(data, list) and all(isinstance(row, dict) for row in data):
            df = pd.DataFrame(data)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
            return df
        # 数字 → 股票代码
        if isinstance(data, (int, float)):
            return self._fetch_by_stock_code(str(int(data)))
        # LLM包装的JSON → 提取股票代码
        if isinstance(data, dict):
            ticker = data.get("price_data", "") or data.get("ticker", "") or data.get("symbol", "")
            if ticker and isinstance(ticker, str) and len(ticker) <= 10:
                return self._fetch_by_stock_code(ticker)
        return self._fetch_by_stock_code(price_data)

    def _fetch_by_stock_code(self, text: str) -> pd.DataFrame | None:
        """从文本中提取股票代码并获取数据（优先缓存）"""
        import time
        code = text.strip()
        try:
            if len(code) > 10:
                import re
                match = re.search(r'(?:sh|sz|SH|SZ)(\d{6})\b', code)
                if not match:
                    match = re.search(r'(?<!\d)(\d{6})(?!\d)', code)
                if match:
                    code = match.group(1)
                else:
                    logger.warning(f"无法从文本中提取股票代码: {code[:100]}")
                    return None

            # 优先读缓存
            from src.tools.akshare_data_cache import load_kline_from_cache
            df = load_kline_from_cache(code)
            if df is not None and not df.empty:
                logger.info(f"图表工具从缓存加载: {code} ({len(df)} 条)")
                return df

            logger.info(f"图表工具 API 获取: {code}")
            from src.tools.akshare_data_parser import get_stock_history_data
            for _attempt in range(3):
                result = get_stock_history_data(code, "1y")
                if result is not None and not result.empty:
                    return result
                time.sleep(1)
            logger.warning(f"图表工具获取股票数据失败: {code}，3次尝试均返回空")
            return None
        except Exception as e:
            logger.warning(f"图表工具获取股票数据异常: {code}，错误: {e}")
            return None

    def _generate_candlestick_chart(self, df: pd.DataFrame) -> str:
        """生成K线图"""
        plt = _get_plt()
        import matplotlib.dates as mdates
        from mplfinance.original_flavor import candlestick_ohlc

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [3, 1]})

        # 将日期转换为 matplotlib 日期数字格式，candlestick_ohlc 要求 float date
        ohlc = df[["Open", "High", "Low", "Close"]].copy()
        ohlc["Date"] = mdates.date2num(df.index.to_pydatetime())
        quotes = [tuple(row) for row in ohlc[["Date", "Open", "High", "Low", "Close"]].values]

        candlestick_ohlc(ax1, quotes, width=0.6, colorup="g", colordown="r")
        ax1.set_title("K线图")
        ax1.set_ylabel("价格")
        ax1.grid(True)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")

        ax2.bar(df.index, df["Volume"], color="blue", alpha=0.6)
        ax2.set_title("成交量")
        ax2.set_ylabel("成交量")
        ax2.grid(True)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha="right")

        plt.tight_layout()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"reports/charts/candlestick_{timestamp}.png"
        plt.savefig(filepath, dpi=300, bbox_inches="tight")
        plt.close()
        return filepath

    def _generate_line_chart(self, df: pd.DataFrame) -> str:
        """生成价格走势图"""
        plt = _get_plt()
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(df.index, df["Close"], label="收盘价", color="blue", linewidth=2)
        ax.plot(df.index, df["Close"].rolling(window=20).mean(), label="MA20", color="orange", linewidth=1)
        ax.plot(df.index, df["Close"].rolling(window=50).mean(), label="MA50", color="red", linewidth=1)

        ax.set_title("价格走势图")
        ax.set_xlabel("日期")
        ax.set_ylabel("价格")
        ax.legend()
        ax.grid(True)

        plt.tight_layout()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"reports/charts/line_{timestamp}.png"
        plt.savefig(filepath, dpi=300, bbox_inches="tight")
        plt.close()
        return filepath

    def _generate_volume_chart(self, df: pd.DataFrame) -> str:
        """生成成交量图"""
        plt = _get_plt()
        fig, ax = plt.subplots(figsize=(12, 6))

        colors = ["green" if close >= open else "red" for close, open in zip(df["Close"], df["Open"], strict=False)]
        ax.bar(df.index, df["Volume"], color=colors, alpha=0.6)
        ax.plot(df.index, df["Volume"].rolling(window=20).mean(), label="成交量MA20", color="blue", linewidth=2)

        ax.set_title("成交量分析图")
        ax.set_xlabel("日期")
        ax.set_ylabel("成交量")
        ax.legend()
        ax.grid(True)

        plt.tight_layout()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"reports/charts/volume_{timestamp}.png"
        plt.savefig(filepath, dpi=300, bbox_inches="tight")
        plt.close()
        return filepath

    def _generate_indicators_chart(self, df: pd.DataFrame) -> str:
        """生成技术指标图"""
        plt = _get_plt()
        fig, axes = plt.subplots(4, 1, figsize=(12, 12))

        axes[0].plot(df.index, df["Close"], label="收盘价", color="black", linewidth=1)
        axes[0].plot(df.index, df["Close"].rolling(window=20).mean(), label="MA20", color="blue", linewidth=1)
        axes[0].plot(df.index, df["Close"].rolling(window=50).mean(), label="MA50", color="red", linewidth=1)
        axes[0].set_title("价格和移动平均线")
        axes[0].legend()
        axes[0].grid(True)

        rsi = calculate_rsi(df["Close"])
        axes[1].plot(df.index, rsi, label="RSI", color="purple", linewidth=1)
        axes[1].axhline(y=70, color="red", linestyle="--", alpha=0.5)
        axes[1].axhline(y=30, color="green", linestyle="--", alpha=0.5)
        axes[1].set_title("RSI指标")
        axes[1].legend()
        axes[1].grid(True)

        macd, signal, histogram = calculate_macd(df["Close"])
        axes[2].plot(df.index, macd, label="MACD", color="blue", linewidth=1)
        axes[2].plot(df.index, signal, label="Signal", color="red", linewidth=1)
        axes[2].bar(df.index, histogram, label="Histogram", color="gray", alpha=0.5)
        axes[2].set_title("MACD指标")
        axes[2].legend()
        axes[2].grid(True)

        axes[3].bar(df.index, df["Volume"], color="blue", alpha=0.6)
        axes[3].set_title("成交量")
        axes[3].grid(True)

        plt.tight_layout()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"reports/charts/indicators_{timestamp}.png"
        plt.savefig(filepath, dpi=300, bbox_inches="tight")
        plt.close()
        return filepath