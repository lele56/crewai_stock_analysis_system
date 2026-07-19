# src/tools/akshare_data_parser.py
"""股票数据获取与解析 — 多数据源架构（腾讯/新浪/TickFlow/akshare）"""

import logging

import pandas as pd

from src.tools.akshare_data_cache import (
    _find_column,
    _safe_float,
    _save_stock_cache,
)
from src.tools.akshare_data_sources import (
    fill_business_ths,
    fill_company_info_cninfo,
    fill_from_sina_spot,
    fill_from_tencent_quote,
    fill_from_tickflow,
    fill_industry_from_sina,
    fill_valuation_from_akshare,
    get_akshare_kline,
    get_financial_data_em,
    get_tencent_akshare_kline,
    get_tencent_kline,
    get_tickflow_kline,
    get_valuation_baidu,
)
from src.tools.circuit_breaker import CircuitBreaker
from src.tools.technical_indicators import calculate_macd, calculate_rsi

logger = logging.getLogger(__name__)

# ── 模块级请求缓存（避免同一 ticker 被多次获取）─────────────
_basic_info_cache: dict[str, dict] = {}
_history_cache: dict[str, pd.DataFrame] = {}
_financial_cache: dict[str, pd.DataFrame] = {}


def get_stock_basic_info(ticker: str) -> dict:
    """获取股票基本信息（多数据源合并，带模块级缓存）"""
    if ticker in _basic_info_cache:
        return _basic_info_cache[ticker]

    info = {
        "longName": "N/A",
        "industry": "N/A",
        "marketCap": 0,
        "currentPrice": 0,
        "fiftyTwoWeekHigh": 0,
        "fiftyTwoWeekLow": 0,
        "trailingPE": "N/A",
        "forwardPE": "N/A",
        "priceToBook": "N/A",
        "dividendYield": 0,
        "beta": "N/A",
    }
    code = ticker.replace("sh", "").replace("sz", "").replace("SH", "").replace("SZ", "")
    fill_from_tickflow(ticker, info)
    fill_from_sina_spot(ticker, info)
    fill_industry_from_sina(code, info)
    fill_from_tencent_quote(code, info)
    fill_valuation_from_akshare(code, info)
    fill_company_info_cninfo(code, info)
    fill_business_ths(code, info)
    if not info.get("marketCap"):
        baidu_val = get_valuation_baidu(code)
        if baidu_val:
            info.update(baidu_val)
    _basic_info_cache[ticker] = info
    return info


def get_stock_history_data(ticker: str, period: str) -> pd.DataFrame:
    """获取历史K线数据（带缓存，断路器自动跳过故障源）"""
    cache_key = f"{ticker}:{period}"
    if cache_key in _history_cache:
        return _history_cache[cache_key]

    try:
        code = ticker.replace("sh", "").replace("sz", "").replace("SH", "").replace("SZ", "")

        if CircuitBreaker.get("tencent_kline").allow_request():
            df = get_tencent_kline(code, period)
            if not df.empty:
                _history_cache[cache_key] = df
                return df

        if CircuitBreaker.get("tencent_ak_kline").allow_request():
            df = get_tencent_akshare_kline(ticker, period)
            if not df.empty:
                _history_cache[cache_key] = df
                return df

        if CircuitBreaker.get("tickflow_kline").allow_request():
            df = get_tickflow_kline(ticker, period)
            if not df.empty:
                _history_cache[cache_key] = df
                return df

        df = get_akshare_kline(ticker, period)
        if not df.empty:
            _history_cache[cache_key] = df
        return df
    except Exception as e:
        logger.error(f"获取股票历史数据失败: {str(e)}")
        return pd.DataFrame()


def get_financial_statements(ticker: str, statement_type: str) -> pd.DataFrame:
    """获取财务报表（带缓存，东方财富 → 纯HTTP）"""
    cache_key = f"{ticker}:{statement_type}"
    if cache_key in _financial_cache:
        return _financial_cache[cache_key]

    try:
        code = ticker.replace("sh", "").replace("sz", "").replace("SH", "").replace("SZ", "")

        if CircuitBreaker.get("em_financial").allow_request():
            df = get_financial_data_em(code, statement_type)
            if not df.empty:
                _financial_cache[cache_key] = df
                return df

        return pd.DataFrame()
    except Exception as e:
        logger.error(f"获取{statement_type}失败: {str(e)}")
        return pd.DataFrame()


def generate_stock_report(
    ticker: str,
    info: dict,
    hist: pd.DataFrame,
    financials: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> str:
    """生成股票数据报告（精简版，适配所有模型）"""
    lines = [f"{ticker} 股票数据:"]
    company = info.get('longName', 'N/A')
    industry = info.get('industry', 'N/A')
    mcap = info.get("marketCap", 0)
    price = info.get("currentPrice", 0)
    high52 = info.get("fiftyTwoWeekHigh", 0)
    low52 = info.get("fiftyTwoWeekLow", 0)

    basic = f"公司: {company}, 行业: {industry}"
    if mcap and price:
        basic += f", 市值: ¥{mcap:,.0f}, 价格: ¥{price:.2f}"
    if high52 and low52:
        basic += f", 52周区间: ¥{low52:.2f}-¥{high52:.2f}"
    lines.append(basic)

    if not hist.empty:
        current_price = hist["Close"].iloc[-1]
        period_return = (
            (current_price - hist["Close"].iloc[0]) / hist["Close"].iloc[0] * 100
        )
        lines.append(
            f"价格: ¥{current_price:.2f}, 涨幅: {period_return:.2f}%, "
            f"最高: ¥{hist['High'].max():.2f}, 最低: ¥{hist['Low'].min():.2f}"
        )

    financial_metrics = _extract_financial_metrics(info, financials)
    fm_items = [f"{k}: {v}" for k, v in financial_metrics.items()]
    if fm_items:
        lines.append("财务: " + ", ".join(fm_items))

    balance_metrics = _extract_balance_sheet_metrics(balance_sheet)
    if balance_metrics:
        bm_items = [f"{k}: {v}" for k, v in balance_metrics.items()]
        lines.append("资产负债表: " + ", ".join(bm_items))

    cashflow_metrics = _extract_cashflow_metrics(cashflow)
    if cashflow_metrics:
        cm_items = [f"{k}: {v}" for k, v in cashflow_metrics.items()]
        lines.append("现金流: " + ", ".join(cm_items))

    _save_stock_cache(ticker, hist, financials, balance_sheet, cashflow, info)

    return "\n".join(lines)


def _extract_financial_metrics(info: dict, financials: pd.DataFrame) -> dict[str, str]:
    """从基本信息和利润表提取关键财务指标"""
    metrics = {
        "市盈率": f"{info.get('trailingPE', 'N/A')}",
        "前瞻市盈率": f"{info.get('forwardPE', 'N/A')}",
        "市净率": f"{info.get('priceToBook', 'N/A')}",
        "股息率": f"{info.get('dividendYield', 0) * 100:.2f}%",
        "Beta": f"{info.get('beta', 'N/A')}",
    }
    if not financials.empty:
        try:
            rev_col = _find_column(financials, ["TOTAL_OPERATE_INCOME", "OPERATE_INCOME"])
            if rev_col and len(financials) > 0:
                rev = _safe_float(financials[rev_col].iloc[0])
                metrics["最新营收"] = f"{rev:,.2f} 元" if rev else "N/A"

            np_col = _find_column(financials, ["NETPROFIT", "PARENT_NETPROFIT"])
            if np_col and len(financials) > 0:
                np_val = _safe_float(financials[np_col].iloc[0])
                metrics["最新净利润"] = f"{np_val:,.2f} 元" if np_val else "N/A"

            op_col = _find_column(financials, ["OPERATE_PROFIT"])
            if op_col and len(financials) > 0:
                op_val = _safe_float(financials[op_col].iloc[0])
                metrics["营业利润"] = f"{op_val:,.2f} 元" if op_val else "N/A"

            cost_col = _find_column(financials, ["OPERATE_COST"])
            if rev_col and cost_col and len(financials) > 0:
                revenue = _safe_float(financials[rev_col].iloc[0])
                cost = _safe_float(financials[cost_col].iloc[0])
                if revenue and cost and revenue > 0:
                    metrics["毛利率"] = f"{((revenue - cost) / revenue) * 100:.2f}%"
        except Exception as e:
            logger.debug(f"提取财务指标时出错: {str(e)[:50]}")
    return metrics


def _extract_balance_sheet_metrics(balance_sheet: pd.DataFrame) -> dict[str, str]:
    """从资产负债表提取关键指标"""
    metrics = {}
    if balance_sheet.empty:
        return metrics
    try:
        col_map = {
            "流动资产": ["TOTAL_CURRENT_ASSETS"],
            "流动负债": ["TOTAL_CURRENT_LIAB"],
            "资产总计": ["TOTAL_ASSETS"],
            "负债合计": ["TOTAL_LIABILITIES"],
            "存货": ["INVENTORY"],
            "货币资金": ["MONETARYFUNDS"],
            "股东权益": ["TOTAL_EQUITY"],
        }
        for metric_name, col_names in col_map.items():
            col = _find_column(balance_sheet, col_names)
            if col and len(balance_sheet) > 0:
                val = _safe_float(balance_sheet[col].iloc[0])
                metrics[metric_name] = f"{val:,.2f} 元" if val else "N/A"
    except Exception as e:
        logger.debug(f"提取资产负债表指标时出错: {str(e)[:50]}")
    return metrics


def _extract_cashflow_metrics(cashflow: pd.DataFrame) -> dict[str, str]:
    """从现金流量表提取关键指标"""
    metrics = {}
    if cashflow.empty:
        return metrics
    try:
        col_map = {
            "经营活动现金流量净额": ["NETCASH_OPERATE"],
            "投资活动现金流量净额": ["NETCASH_INVEST"],
            "筹资活动现金流量净额": ["NETCASH_FINANCE"],
        }
        for metric_name, col_names in col_map.items():
            col = _find_column(cashflow, col_names)
            if col and len(cashflow) > 0:
                val = _safe_float(cashflow[col].iloc[0])
                metrics[metric_name] = f"{val:,.2f} 元" if val else "N/A"
    except Exception as e:
        logger.debug(f"提取现金流量表指标时出错: {str(e)[:50]}")
    return metrics


def _calculate_technical_indicators(hist: pd.DataFrame) -> dict[str, str]:
    """计算技术指标（MA5/MA20/MA50/RSI/MACD）"""
    indicators = {}
    if len(hist) < 20:
        return indicators
    close_prices = hist["Close"]
    indicators["MA5"] = f"${close_prices.rolling(window=5).mean().iloc[-1]:.2f}"
    indicators["MA20"] = f"${close_prices.rolling(window=20).mean().iloc[-1]:.2f}"
    indicators["MA50"] = f"${close_prices.rolling(window=50).mean().iloc[-1]:.2f}"
    if len(hist) >= 14:
        indicators["RSI(14)"] = f"{calculate_rsi(close_prices).iloc[-1]:.1f}"
    if len(hist) >= 26:
        macd, signal, histogram = calculate_macd(close_prices)
        indicators["MACD"] = f"{macd.iloc[-1]:.3f}"
        indicators["Signal"] = f"{signal.iloc[-1]:.3f}"
    return indicators