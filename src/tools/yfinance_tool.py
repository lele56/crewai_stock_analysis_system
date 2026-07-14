# src/tools/yfinance_tool.py
"""兼容数据工具 - 内部使用AkShare实现股票数据获取"""
from typing import Dict
import pandas as pd
import logging
from datetime import datetime

from src.tools.reporting_tools import BaseTool
from src.tools.akshare_tools import AkShareTool

logger = logging.getLogger(__name__)


class YFinanceTool(BaseTool):
    """兼容工具 - 内部使用AkShare实现"""

    name: str = "兼容数据工具"
    description: str = "兼容工具 - 获取股票的财务数据、价格数据和市场信息（内部使用AkShare实现）"

    def _run(self, ticker: str, period: str = "1y") -> str:
        """获取股票数据（内部使用AkShareTool实现）"""
        try:
            logger.info(f"YFinanceTool已迁移至AkShareTool，正在使用AkShare获取 {ticker} 的数据")
            ak_tool = AkShareTool()
            if not (ticker.startswith('sh') or ticker.startswith('sz')):
                adjusted_ticker = f'sh{ticker}'
                logger.warning(f"股票代码格式非A股标准格式，尝试添加前缀: {ticker} -> {adjusted_ticker}")
            else:
                adjusted_ticker = ticker
            result = ak_tool._run(adjusted_ticker, period)
            return result
        except Exception as e:
            error_msg = f"获取 {ticker} 数据失败: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"[API错误] {ticker}, {period}, {type(e).__name__}: {str(e)}")
            return error_msg

    def _generate_stock_report(self, ticker: str, info: Dict, hist: pd.DataFrame,
                             financials: pd.DataFrame, balance_sheet: pd.DataFrame,
                             cashflow: pd.DataFrame) -> str:
        """生成股票数据报告"""
        report = f"# {ticker} 股票数据报告\n\n"
        report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += "## 基本信息\n\n"
        report += f"- **公司名称**: {info.get('longName', 'N/A')}\n"
        report += f"- **行业**: {info.get('industry', 'N/A')}\n"
        report += f"- **市值**: ${info.get('marketCap', 0):,.0f}\n"
        report += f"- **当前价格**: ${info.get('currentPrice', 0):.2f}\n"
        report += f"- **52周最高**: ${info.get('fiftyTwoWeekHigh', 0):.2f}\n"
        report += f"- **52周最低**: ${info.get('fiftyTwoWeekLow', 0):.2f}\n\n"
        if not hist.empty:
            report += "## 价格统计\n\n"
            current_price = hist['Close'].iloc[-1]
            period_return = ((current_price - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
            report += f"- **当前价格**: ${current_price:.2f}\n"
            report += f"- **期间涨幅**: {period_return:.2f}%\n"
            report += f"- **期间最高**: ${hist['High'].max():.2f}\n"
            report += f"- **期间最低**: ${hist['Low'].min():.2f}\n"
            report += f"- **平均成交额**: ${hist['Volume'].mean():,.0f}\n\n"
        report += "## 关键财务指标\n\n"
        financial_metrics = self._extract_financial_metrics(info, financials)
        for metric, value in financial_metrics.items():
            report += f"- **{metric}**: {value}\n"
        if not hist.empty:
            report += "\n## 技术指标\n\n"
            tech_indicators = self._calculate_technical_indicators(hist)
            for indicator, value in tech_indicators.items():
                report += f"- **{indicator}**: {value}\n"
        return report

    def _extract_financial_metrics(self, info: Dict, financials: pd.DataFrame) -> Dict[str, str]:
        """提取关键财务指标"""
        metrics = {}
        metrics['市盈率'] = f"{info.get('trailingPE', 'N/A')}"
        metrics['前瞻市盈率'] = f"{info.get('forwardPE', 'N/A')}"
        metrics['市净率'] = f"{info.get('priceToBook', 'N/A')}"
        metrics['股息率'] = f"{info.get('dividendYield', 0) * 100:.2f}%"
        metrics['Beta'] = f"{info.get('beta', 'N/A')}"
        if not financials.empty:
            latest_revenue = financials.iloc[0].get('Total Revenue', 0)
            if latest_revenue:
                metrics['最新营收'] = f"${latest_revenue:,.0f}"
            latest_net_income = financials.iloc[0].get('Net Income', 0)
            if latest_net_income:
                metrics['最新净利润'] = f"${latest_net_income:,.0f}"
        return metrics

    def _calculate_technical_indicators(self, hist: pd.DataFrame) -> Dict[str, str]:
        """计算技术指标"""
        indicators = {}
        if len(hist) < 20:
            return indicators
        close_prices = hist['Close']
        ma5 = close_prices.rolling(window=5).mean().iloc[-1]
        ma20 = close_prices.rolling(window=20).mean().iloc[-1]
        ma50 = close_prices.rolling(window=50).mean().iloc[-1]
        indicators['MA5'] = f"${ma5:.2f}"
        indicators['MA20'] = f"${ma20:.2f}"
        indicators['MA50'] = f"${ma50:.2f}"
        if len(hist) >= 14:
            rsi = self._calculate_rsi(close_prices)
            indicators['RSI(14)'] = f"{rsi:.1f}"
        if len(hist) >= 26:
            macd, signal = self._calculate_macd(close_prices)
            indicators['MACD'] = f"{macd:.3f}"
            indicators['Signal'] = f"{signal:.3f}"
        return indicators

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        return macd.iloc[-1], signal_line.iloc[-1]