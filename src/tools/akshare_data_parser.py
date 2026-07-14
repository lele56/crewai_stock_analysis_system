# src/tools/akshare_data_parser.py
"""股票数据获取与解析 - 多数据源架构（腾讯/新浪/TickFlow/akshare/tushare）"""
import logging
from typing import Dict
from datetime import datetime
import pandas as pd

from src.config import Config
from src.tools.technical_indicators import calculate_rsi, calculate_macd
from src.tools.akshare_data_sources import (
    fill_from_tickflow, fill_from_sina_spot, fill_industry_from_sina,
    fill_from_tencent_quote, fill_valuation_from_akshare,
    get_tencent_kline, get_tickflow_kline, get_tushare_kline, get_akshare_kline,
    get_sina_financial, get_akshare_financial, get_tushare_financial,
    _calculate_start_date,
)

logger = logging.getLogger(__name__)


def get_stock_basic_info(ticker: str) -> Dict:
    """获取股票基本信息（多数据源合并）"""
    info = {
        'longName': 'N/A', 'industry': 'N/A', 'marketCap': 0,
        'currentPrice': 0, 'fiftyTwoWeekHigh': 0, 'fiftyTwoWeekLow': 0,
        'trailingPE': 'N/A', 'forwardPE': 'N/A', 'priceToBook': 'N/A',
        'dividendYield': 0, 'beta': 'N/A',
    }
    code = ticker.replace('sh', '').replace('sz', '').replace('SH', '').replace('SZ', '')
    fill_from_tickflow(ticker, info)
    fill_from_sina_spot(ticker, info)
    fill_industry_from_sina(code, info)
    fill_from_tencent_quote(code, info)
    fill_valuation_from_akshare(code, info)
    return info


def get_stock_history_data(ticker: str, period: str) -> pd.DataFrame:
    """获取历史K线数据（腾讯K线 → TickFlow → tushare保底）"""
    try:
        code = ticker.replace('sh', '').replace('sz', '').replace('SH', '').replace('SZ', '')
        df = get_tencent_kline(code, period)
        if not df.empty:
            return df
        df = get_tickflow_kline(ticker, period)
        if not df.empty:
            return df
        df = get_tushare_kline(code, period)
        if not df.empty:
            return df
        return get_akshare_kline(ticker, period)
    except Exception as e:
        logger.error(f"获取股票历史数据失败: {str(e)}")
        return pd.DataFrame()


def get_financial_statements(ticker: str, statement_type: str) -> pd.DataFrame:
    """获取财务报表（新浪 → akshare → tushare保底）"""
    try:
        code = ticker.replace('sh', '').replace('sz', '').replace('SH', '').replace('SZ', '')
        df = get_sina_financial(code, statement_type)
        if not df.empty:
            return df
        df = get_akshare_financial(code, statement_type)
        if not df.empty:
            return df
        return get_tushare_financial(code, statement_type)
    except Exception as e:
        logger.error(f"获取{statement_type}失败: {str(e)}")
        return pd.DataFrame()


def generate_stock_report(ticker: str, info: Dict, hist: pd.DataFrame,
                         financials: pd.DataFrame, balance_sheet: pd.DataFrame,
                         cashflow: pd.DataFrame) -> str:
    """生成股票数据报告"""
    report = f"# {ticker} 股票数据报告\n\n"
    report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += "## 基本信息\n\n"
    report += f"- **公司名称**: {info.get('longName', 'N/A')}\n"
    report += f"- **行业**: {info.get('industry', 'N/A')}\n"
    mcap = info.get('marketCap', 0)
    report += f"- **市值**: ¥{mcap:,.0f}\n" if mcap else f"- **市值**: N/A\n"
    price = info.get('currentPrice', 0)
    report += f"- **当前价格**: ¥{price:.2f}\n" if price else f"- **当前价格**: N/A\n"
    high52 = info.get('fiftyTwoWeekHigh', 0)
    low52 = info.get('fiftyTwoWeekLow', 0)
    report += f"- **52周最高**: ¥{high52:.2f}\n" if high52 else f"- **52周最高**: N/A\n"
    report += f"- **52周最低**: ¥{low52:.2f}\n\n" if low52 else f"- **52周最低**: N/A\n\n"
    if not hist.empty:
        report += "## 价格统计\n\n"
        current_price = hist['Close'].iloc[-1]
        period_return = ((current_price - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        report += f"- **当前价格**: ¥{current_price:.2f}\n"
        report += f"- **期间涨幅**: {period_return:.2f}%\n"
        report += f"- **期间最高**: ¥{hist['High'].max():.2f}\n"
        report += f"- **期间最低**: ¥{hist['Low'].min():.2f}\n"
        report += f"- **平均成交额**: {hist['Volume'].mean():,.0f} 股\n\n"
    report += "## 关键财务指标\n\n"
    financial_metrics = _extract_financial_metrics(info, financials)
    for metric, value in financial_metrics.items():
        report += f"- **{metric}**: {value}\n"
    if not hist.empty:
        report += "\n## 技术指标\n\n"
        tech_indicators = _calculate_technical_indicators(hist)
        for indicator, value in tech_indicators.items():
            report += f"- **{indicator}**: {value}\n"
    return report


def _extract_financial_metrics(info: Dict, financials: pd.DataFrame) -> Dict[str, str]:
    metrics = {
        '市盈率': f"{info.get('trailingPE', 'N/A')}",
        '前瞻市盈率': f"{info.get('forwardPE', 'N/A')}",
        '市净率': f"{info.get('priceToBook', 'N/A')}",
        '股息率': f"{info.get('dividendYield', 0) * 100:.2f}%",
        'Beta': f"{info.get('beta', 'N/A')}",
    }
    if not financials.empty:
        try:
            if '营业收入' in financials.columns and len(financials) > 0:
                metrics['最新营收'] = f"{financials['营业收入'].iloc[0]:,.2f} 元"
            if '净利润' in financials.columns and len(financials) > 0:
                metrics['最新净利润'] = f"{financials['净利润'].iloc[0]:,.2f} 元"
            if '营业收入' in financials.columns and '营业成本' in financials.columns and len(financials) > 0:
                revenue, cost = financials['营业收入'].iloc[0], financials['营业成本'].iloc[0]
                if revenue > 0:
                    metrics['毛利率'] = f"{((revenue - cost) / revenue) * 100:.2f}%"
        except Exception as e:
            logger.debug(f"提取财务指标时出错: {str(e)[:50]}")
    return metrics


def _calculate_technical_indicators(hist: pd.DataFrame) -> Dict[str, str]:
    indicators = {}
    if len(hist) < 20:
        return indicators
    close_prices = hist['Close']
    indicators['MA5'] = f"${close_prices.rolling(window=5).mean().iloc[-1]:.2f}"
    indicators['MA20'] = f"${close_prices.rolling(window=20).mean().iloc[-1]:.2f}"
    indicators['MA50'] = f"${close_prices.rolling(window=50).mean().iloc[-1]:.2f}"
    if len(hist) >= 14:
        indicators['RSI(14)'] = f"{calculate_rsi(close_prices).iloc[-1]:.1f}"
    if len(hist) >= 26:
        macd, signal = calculate_macd(close_prices)
        indicators['MACD'] = f"{macd.iloc[-1]:.3f}"
        indicators['Signal'] = f"{signal.iloc[-1]:.3f}"
    return indicators