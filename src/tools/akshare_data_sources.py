# src/tools/akshare_data_sources.py
"""多数据源底层实现 - 腾讯/新浪/TickFlow/akshare/tushare数据获取"""
import http.client
import json
import re
import ssl
import logging
from typing import Dict
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE
_HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://finance.sina.com.cn/',
}

TICKFLOW_AVAILABLE = False
_tickflow_free = None
try:
    import tickflow as tf  # type: ignore[import-untyped]
    _tickflow_free = tf
    TICKFLOW_AVAILABLE = True
except ImportError:
    pass

TUSHARE_AVAILABLE = False
_ts_api = None
try:
    import tushare as ts  # type: ignore[import-untyped]
    _ts_api = ts
    TUSHARE_AVAILABLE = True
except ImportError:
    pass


def _to_tickflow_symbol(ticker: str) -> str:
    t = ticker.upper().replace('SH', '').replace('SZ', '')
    if t.startswith('6'):
        return f"{t}.SH"
    return f"{t}.SZ"


def _ensure_exchange_prefix(ticker: str) -> str:
    t = ticker.lower().replace('sh', '').replace('sz', '')
    if t.startswith('6'):
        return f"sh{t}"
    return f"sz{t}"


def _calculate_start_date(period: str) -> str:
    today = datetime.now()
    periods = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "10y": 3650}
    if period == "ytd":
        start_date = datetime(today.year, 1, 1)
    elif period == "max":
        start_date = datetime(2000, 1, 1)
    elif period in periods:
        start_date = today - timedelta(days=periods[period])
    else:
        start_date = today - timedelta(days=365)
    return start_date.strftime('%Y%m%d')


# ── 腾讯数据源 ─────────────────────────────────

def fill_from_tickflow(ticker: str, info: dict) -> None:
    if not TICKFLOW_AVAILABLE:
        return
    try:
        tf_symbol = _to_tickflow_symbol(ticker)
        tf_info = _tickflow_free.instruments.get(tf_symbol)
        if tf_info and info.get('longName', 'N/A') == 'N/A':
            info['longName'] = tf_info.get('name', 'N/A')
    except Exception as e:
        logger.debug(f"TickFlow: {str(e)[:50]}")


def fill_from_sina_spot(ticker: str, info: dict) -> None:
    try:
        sina_symbol = _ensure_exchange_prefix(ticker)
        conn = http.client.HTTPSConnection('hq.sinajs.cn', timeout=10, context=_SSL_CTX)
        conn.request('GET', f'/list={sina_symbol}', headers=_HTTP_HEADERS)
        resp = conn.getresponse()
        raw = resp.read().decode('gbk', errors='ignore')
        conn.close()
        data = raw.split('"')[1] if '"' in raw else ''
        if not data:
            return
        fields = data.split(',')
        if len(fields) < 32:
            return
        if info.get('longName', 'N/A') == 'N/A':
            info['longName'] = fields[0] if fields[0] else 'N/A'
        info['currentPrice'] = float(fields[3]) if fields[3] else info['currentPrice']
        high = float(fields[4]) if fields[4] else 0
        low = float(fields[5]) if fields[5] else 0
        info['fiftyTwoWeekHigh'] = info.get('fiftyTwoWeekHigh', 0) or high
        info['fiftyTwoWeekLow'] = info.get('fiftyTwoWeekLow', 0) or low
    except Exception as e:
        logger.debug(f"新浪个股行情: {str(e)[:50]}")


def fill_industry_from_sina(code: str, info: dict) -> None:
    try:
        conn = http.client.HTTPConnection('vip.stock.finance.sina.com.cn', timeout=10)
        conn.request('GET', f'/corp/go.php/vCI_CorpOtherInfo/stockid/{code}/menu_num/2.phtml',
                     headers=_HTTP_HEADERS)
        resp = conn.getresponse()
        html = resp.read().decode('gbk', errors='ignore')
        conn.close()
        m = re.search(r'所属行业板块</td>\s*</tr>\s*<tr>.*?</tr>\s*<tr>\s*<td[^>]*>(.+?)</td>', html, re.DOTALL)
        if m:
            info['industry'] = m.group(1).strip()
    except Exception as e:
        logger.debug(f"新浪行业分类: {str(e)[:50]}")


def fill_from_tencent_quote(code: str, info: dict) -> None:
    try:
        ticker = f"sh{code}" if code.startswith('6') else f"sz{code}"
        conn = http.client.HTTPSConnection('qt.gtimg.cn', timeout=10, context=_SSL_CTX)
        conn.request('GET', f'/q={ticker}', headers=_HTTP_HEADERS)
        resp = conn.getresponse()
        raw = resp.read().decode('gbk', errors='ignore')
        conn.close()
        data = raw.split('"')[1] if '"' in raw else ''
        if not data:
            return
        fields = data.split('~')
        if len(fields) < 50:
            return
        if fields[3] and float(fields[3]) > 0:
            info['currentPrice'] = float(fields[3])
        pe = fields[39] if fields[39] else ''
        if pe and pe != '0':
            info['trailingPE'] = float(pe)
            info['forwardPE'] = float(pe)
        pb = fields[46] if fields[46] else ''
        if pb and pb != '0':
            info['priceToBook'] = float(pb)
        mcap = fields[44] if fields[44] else ''
        if mcap and mcap != '0':
            info['marketCap'] = int(float(mcap) * 1e8)
        high52 = fields[47] if fields[47] else ''
        if high52 and high52 != '0':
            info['fiftyTwoWeekHigh'] = max(info.get('fiftyTwoWeekHigh', 0) or 0, float(high52))
        low52 = fields[48] if fields[48] else ''
        if low52 and low52 != '0':
            info['fiftyTwoWeekLow'] = info.get('fiftyTwoWeekLow', 0) or float(low52)
    except Exception as e:
        logger.debug(f"腾讯行情API: {str(e)[:50]}")


def fill_valuation_from_akshare(code: str, info: dict) -> None:
    try:
        import akshare as ak
        indicator_df = ak.stock_financial_analysis_indicator(symbol=code)
        if not indicator_df.empty:
            ind = indicator_df.set_index('指标名称')['最新'].to_dict()
            info['dividendYield'] = float(ind.get('股息率', 0)) / 100 if ind.get('股息率', 0) else info.get('dividendYield', 0)
            info['beta'] = float(ind.get('贝塔系数', 0)) if ind.get('贝塔系数', 0) else 'N/A'
            if info.get('trailingPE', 'N/A') == 'N/A':
                info['trailingPE'] = float(ind.get('市盈率', 0)) if ind.get('市盈率', 0) else 'N/A'
            if info.get('priceToBook', 'N/A') == 'N/A':
                info['priceToBook'] = float(ind.get('市净率', 0)) if ind.get('市净率', 0) else 'N/A'
    except Exception:
        logger.debug("akshare估值指标获取失败，使用已有数据")


# ── K线数据 ─────────────────────────────────────

def get_tencent_kline(code: str, period: str) -> pd.DataFrame:
    try:
        start_date = pd.to_datetime(_calculate_start_date(period))
        tk_code = f"sh{code}" if code.startswith('6') else f"sz{code}"
        conn = http.client.HTTPSConnection('web.ifzq.gtimg.cn', timeout=10, context=_SSL_CTX)
        url = f'/appstock/app/fqkline/get?param={tk_code},day,,,640,qfq'
        conn.request('GET', url, headers=_HTTP_HEADERS)
        resp = conn.getresponse()
        raw = resp.read().decode('utf-8', errors='ignore')
        conn.close()
        data = json.loads(raw)
        klines = data.get('data', {}).get(tk_code, {}).get('qfqday', []) or \
                 data.get('data', {}).get(tk_code, {}).get('day', [])
        if not klines:
            return pd.DataFrame()
        rows = [{'Date': pd.to_datetime(k[0]), 'Open': float(k[1]), 'Close': float(k[2]),
                 'High': float(k[3]), 'Low': float(k[4]), 'Volume': float(k[5])} for k in klines]
        df = pd.DataFrame(rows).set_index('Date')
        return df[df.index >= start_date]
    except Exception as e:
        logger.debug(f"腾讯K线: {str(e)[:50]}")
        return pd.DataFrame()


def get_tickflow_kline(ticker: str, period: str) -> pd.DataFrame:
    if not TICKFLOW_AVAILABLE:
        return pd.DataFrame()
    try:
        tf_symbol = _to_tickflow_symbol(ticker)
        start = _calculate_start_date(period)
        end = datetime.now().strftime('%Y%m%d')
        df = _tickflow_free.daily(tf_symbol, start_date=start, end_date=end)
        if df is not None and not df.empty:
            df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low',
                                    'close': 'Close', 'volume': 'Volume'})
            df.index = pd.to_datetime(df.index)
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        logger.debug(f"TickFlow K线: {str(e)[:50]}")
    return pd.DataFrame()


def get_tushare_kline(code: str, period: str) -> pd.DataFrame:
    if not TUSHARE_AVAILABLE:
        return pd.DataFrame()
    try:
        start = _calculate_start_date(period)
        end = datetime.now().strftime('%Y%m%d')
        pro = _ts_api.pro_api()
        df = pro.daily(ts_code=f"{code}.SH" if code.startswith('6') else f"{code}.SZ",
                       start_date=start, end_date=end)
        if df is not None and not df.empty:
            df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low',
                                    'close': 'Close', 'vol': 'Volume'})
            df['Date'] = pd.to_datetime(df['trade_date'])
            df = df.set_index('Date').sort_index()
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        logger.debug(f"Tushare K线: {str(e)[:50]}")
    return pd.DataFrame()


def get_akshare_kline(ticker: str, period: str) -> pd.DataFrame:
    try:
        import akshare as ak
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = _calculate_start_date(period)
        df = ak.stock_zh_a_daily(symbol=ticker, start_date=start_date, end_date=end_date, adjust="qfq")
        if not df.empty:
            df = df.rename(columns={'开盘': 'Open', '收盘': 'Close', '最高': 'High', '最低': 'Low', '成交量': 'Volume'})
            if '日期' in df.columns:
                df['Date'] = pd.to_datetime(df['日期'])
            elif 'date' in df.columns:
                df['Date'] = pd.to_datetime(df['date'])
            else:
                df['Date'] = pd.date_range(end=end_date, periods=len(df), freq='D')
            df = df.set_index('Date')
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col not in df.columns:
                    df[col] = 0
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        logger.debug(f"akshare K线: {str(e)[:50]}")
    return pd.DataFrame()


# ── 财务报表 ────────────────────────────────────

def get_sina_financial(code: str, statement_type: str) -> pd.DataFrame:
    try:
        import akshare as ak
        return ak.stock_financial_report_sina(stock=f"sh{code}" if code.startswith('6') else f"sz{code}",
                                              symbol=statement_type)
    except Exception:
        return pd.DataFrame()


def get_akshare_financial(code: str, statement_type: str) -> pd.DataFrame:
    try:
        import akshare as ak
        return ak.stock_financial_report_sina(symbol=code, report_type=statement_type)
    except Exception:
        return pd.DataFrame()


def get_tushare_financial(code: str, statement_type: str) -> pd.DataFrame:
    if not TUSHARE_AVAILABLE:
        return pd.DataFrame()
    try:
        ts_code = f"{code}.SH" if code.startswith('6') else f"{code}.SZ"
        pro = _ts_api.pro_api()
        if statement_type == "利润表":
            return pro.income(ts_code=ts_code)
        elif statement_type == "资产负债表":
            return pro.balancesheet(ts_code=ts_code)
        elif statement_type == "现金流量表":
            return pro.cashflow(ts_code=ts_code)
    except Exception:
        return pd.DataFrame()