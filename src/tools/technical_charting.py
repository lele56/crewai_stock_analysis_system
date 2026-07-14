# src/tools/technical_charting.py
"""
技术图表生成模块
提供K线图、价格走势图、成交量图、综合指标图的生成功能
"""
from typing import Optional
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import logging
import os

from src.tools.reporting_tools import BaseTool
from src.tools.technical_indicators import calculate_rsi, calculate_macd

logger = logging.getLogger(__name__)


class ChartingTool(BaseTool):
    """图表生成工具"""

    name: str = "Charting Tool"
    description: str = "生成技术分析图表和可视化"

    def _run(self, price_data: str, chart_type: str = "candlestick") -> str:
        """生成技术分析图表"""
        try:
            import json
            data = json.loads(price_data)
            logger.info(f"生成图表，类型: {chart_type}")

            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)

            os.makedirs('reports/charts', exist_ok=True)

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

    def _generate_candlestick_chart(self, df: pd.DataFrame) -> str:
        """生成K线图"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})

        from mplfinance.original_flavor import candlestick_ohlc
        ohlc = df[['Open', 'High', 'Low', 'Close']].copy()
        ohlc['Date'] = range(len(ohlc))
        candlestick_ohlc(ax1, ohlc.values, width=0.6, colorup='g', colordown='r')
        ax1.set_title('K线图')
        ax1.set_ylabel('价格')
        ax1.grid(True)

        ax2.bar(df.index, df['Volume'], color='blue', alpha=0.6)
        ax2.set_title('成交量')
        ax2.set_ylabel('成交量')
        ax2.grid(True)

        plt.tight_layout()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f'reports/charts/candlestick_{timestamp}.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        return filepath

    def _generate_line_chart(self, df: pd.DataFrame) -> str:
        """生成价格走势图"""
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(df.index, df['Close'], label='收盘价', color='blue', linewidth=2)
        ax.plot(df.index, df['Close'].rolling(window=20).mean(), label='MA20', color='orange', linewidth=1)
        ax.plot(df.index, df['Close'].rolling(window=50).mean(), label='MA50', color='red', linewidth=1)

        ax.set_title('价格走势图')
        ax.set_xlabel('日期')
        ax.set_ylabel('价格')
        ax.legend()
        ax.grid(True)

        plt.tight_layout()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f'reports/charts/line_{timestamp}.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        return filepath

    def _generate_volume_chart(self, df: pd.DataFrame) -> str:
        """生成成交量图"""
        fig, ax = plt.subplots(figsize=(12, 6))

        colors = ['green' if close >= open else 'red' for close, open in zip(df['Close'], df['Open'])]
        ax.bar(df.index, df['Volume'], color=colors, alpha=0.6)
        ax.plot(df.index, df['Volume'].rolling(window=20).mean(), label='成交量MA20', color='blue', linewidth=2)

        ax.set_title('成交量分析图')
        ax.set_xlabel('日期')
        ax.set_ylabel('成交量')
        ax.legend()
        ax.grid(True)

        plt.tight_layout()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f'reports/charts/volume_{timestamp}.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        return filepath

    def _generate_indicators_chart(self, df: pd.DataFrame) -> str:
        """生成技术指标图"""
        fig, axes = plt.subplots(4, 1, figsize=(12, 12))

        axes[0].plot(df.index, df['Close'], label='收盘价', color='black', linewidth=1)
        axes[0].plot(df.index, df['Close'].rolling(window=20).mean(), label='MA20', color='blue', linewidth=1)
        axes[0].plot(df.index, df['Close'].rolling(window=50).mean(), label='MA50', color='red', linewidth=1)
        axes[0].set_title('价格和移动平均线')
        axes[0].legend()
        axes[0].grid(True)

        rsi = calculate_rsi(df['Close'])
        axes[1].plot(df.index, rsi, label='RSI', color='purple', linewidth=1)
        axes[1].axhline(y=70, color='red', linestyle='--', alpha=0.5)
        axes[1].axhline(y=30, color='green', linestyle='--', alpha=0.5)
        axes[1].set_title('RSI指标')
        axes[1].legend()
        axes[1].grid(True)

        macd, signal, histogram = calculate_macd(df['Close'])
        axes[2].plot(df.index, macd, label='MACD', color='blue', linewidth=1)
        axes[2].plot(df.index, signal, label='Signal', color='red', linewidth=1)
        axes[2].bar(df.index, histogram, label='Histogram', color='gray', alpha=0.5)
        axes[2].set_title('MACD指标')
        axes[2].legend()
        axes[2].grid(True)

        axes[3].bar(df.index, df['Volume'], color='blue', alpha=0.6)
        axes[3].set_title('成交量')
        axes[3].grid(True)

        plt.tight_layout()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f'reports/charts/indicators_{timestamp}.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        return filepath