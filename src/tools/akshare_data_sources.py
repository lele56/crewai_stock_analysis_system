# src/tools/akshare_data_sources.py
"""多数据源底层实现 - 腾讯/新浪/TickFlow/akshare数据获取

所有字段映射集中在 schemas.py，接口变更只需改一处。
"""

from datetime import datetime, timedelta
import http.client
import json
import logging
import re
import ssl

import pandas as pd

from src.config import Config
from src.tools.circuit_breaker import CircuitBreaker
from src.tools.schemas import (
    AKSHARE_KLINE_RENAME,
    SINA_SPOT_SCHEMA,
    TENCENT_KLINE_SCHEMA,
    TENCENT_QUOTE_SCHEMA,
    TICKFLOW_KLINE_RENAME,
    field,
    normalize_kline_df,
    rename_df,
)

logger = logging.getLogger(__name__)


def _safe_float(val) -> float | None:
    """安全转换数值（支持亿/万/千单位）"""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace(" ", "")
    if not s:
        return None
    units = {"亿": 1e8, "万": 1e4, "千": 1e3, "百": 1e2, "十": 1e1}
    for unit, multiplier in units.items():
        if s.endswith(unit):
            try:
                return float(s[:-1]) * multiplier
            except ValueError:
                continue
    try:
        return float(s)
    except ValueError:
        return None

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE
_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://finance.sina.com.cn/",
}

TICKFLOW_AVAILABLE = False
_tickflow_free = None
try:
    import sys
    import io

    _old_stdout = sys.stdout
    try:
        sys.stdout = io.StringIO()
        import tickflow as tf  # type: ignore[import-untyped]

        _tickflow_free = tf.TickFlow.free()
        TICKFLOW_AVAILABLE = True
    finally:
        sys.stdout = _old_stdout
except Exception:
    pass


def _to_tickflow_symbol(ticker: str) -> str:
    t = ticker.upper().replace("SH", "").replace("SZ", "")
    if t.startswith("6"):
        return f"{t}.SH"
    return f"{t}.SZ"


def _ensure_exchange_prefix(ticker: str) -> str:
    t = ticker.lower().replace("sh", "").replace("sz", "")
    if t.startswith("6"):
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
    return start_date.strftime("%Y%m%d")


# ═══════════════════════════════════════════════════════════════════
# 实时行情
# ═══════════════════════════════════════════════════════════════════


def fill_from_tickflow(ticker: str, info: dict) -> None:
    """从 TickFlow 数据源填充股票信息"""
    cb = CircuitBreaker.get("tickflow_spot")
    if not TICKFLOW_AVAILABLE or not cb.allow_request():
        return
    try:
        tf_symbol = _to_tickflow_symbol(ticker)
        tf_info = _tickflow_free.instruments.get(tf_symbol)
        if tf_info and info.get("longName", "N/A") == "N/A":
            info["longName"] = tf_info.get("name", "N/A")
        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"TickFlow: {str(e)[:50]}")


def fill_from_sina_spot(ticker: str, info: dict) -> None:
    """从新浪个股行情填充股票信息（Schema 驱动）"""
    cb = CircuitBreaker.get("sina_spot")
    if not cb.allow_request():
        return
    try:
        sina_symbol = _ensure_exchange_prefix(ticker)
        conn = http.client.HTTPSConnection("hq.sinajs.cn", timeout=Config.SOURCE_TIMEOUT, context=_SSL_CTX)
        conn.request("GET", f"/list={sina_symbol}", headers=_HTTP_HEADERS)
        resp = conn.getresponse()
        raw = resp.read().decode("gbk", errors="ignore")
        conn.close()
        data = raw.split('"')[1] if '"' in raw else ""
        if not data:
            cb.record_success()
            return
        fields = data.split(",")
        if len(fields) < 10:
            cb.record_success()
            return

        _name = field(SINA_SPOT_SCHEMA, fields, "name")
        if _name and info.get("longName", "N/A") == "N/A":
            info["longName"] = _name

        _price = field(SINA_SPOT_SCHEMA, fields, "current_price")
        if _price:
            info["currentPrice"] = float(_price)

        _high = field(SINA_SPOT_SCHEMA, fields, "high")
        _low = field(SINA_SPOT_SCHEMA, fields, "low")
        if _high:
            info["fiftyTwoWeekHigh"] = info.get("fiftyTwoWeekHigh", 0) or float(_high)
        if _low:
            info["fiftyTwoWeekLow"] = info.get("fiftyTwoWeekLow", 0) or float(_low)

        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"新浪个股行情: {str(e)[:50]}")


def fill_industry_from_sina(code: str, info: dict) -> None:
    """从新浪获取行业分类信息"""
    cb = CircuitBreaker.get("sina_industry")
    if not cb.allow_request():
        return
    try:
        conn = http.client.HTTPConnection("vip.stock.finance.sina.com.cn", timeout=Config.SOURCE_TIMEOUT)
        conn.request("GET", f"/corp/go.php/vCI_CorpOtherInfo/stockid/{code}/menu_num/2.phtml", headers=_HTTP_HEADERS)
        resp = conn.getresponse()
        html = resp.read().decode("gbk", errors="ignore")
        conn.close()
        m = re.search(r"所属行业板块</td>\s*</tr>\s*<tr>.*?</tr>\s*<tr>\s*<td[^>]*>(.+?)</td>", html, re.DOTALL)
        if m:
            info["industry"] = m.group(1).strip()
        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"新浪行业分类: {str(e)[:50]}")


def fill_from_tencent_quote(code: str, info: dict) -> None:
    """从腾讯行情API填充股票信息（Schema 驱动）"""
    cb = CircuitBreaker.get("tencent_quote")
    if not cb.allow_request():
        return
    try:
        ticker = f"sh{code}" if code.startswith("6") else f"sz{code}"
        conn = http.client.HTTPSConnection("qt.gtimg.cn", timeout=Config.SOURCE_TIMEOUT, context=_SSL_CTX)
        conn.request("GET", f"/q={ticker}", headers=_HTTP_HEADERS)
        resp = conn.getresponse()
        raw = resp.read().decode("gbk", errors="ignore")
        conn.close()
        data = raw.split('"')[1] if '"' in raw else ""
        if not data:
            cb.record_success()
            return
        fields = data.split("~")
        if len(fields) < 50:
            cb.record_success()
            return

        _price = field(TENCENT_QUOTE_SCHEMA, fields, "current_price")
        if _price and float(_price) > 0:
            info["currentPrice"] = float(_price)

        _pe = field(TENCENT_QUOTE_SCHEMA, fields, "pe", "")
        if _pe and _pe != "0":
            info["trailingPE"] = float(_pe)
            info["forwardPE"] = float(_pe)

        _pb = field(TENCENT_QUOTE_SCHEMA, fields, "pb", "")
        if _pb and _pb != "0":
            info["priceToBook"] = float(_pb)

        _mcap = field(TENCENT_QUOTE_SCHEMA, fields, "market_cap", "")
        if _mcap and _mcap != "0":
            info["marketCap"] = int(float(_mcap) * 1e8)

        _high52 = field(TENCENT_QUOTE_SCHEMA, fields, "week52_high", "")
        if _high52 and _high52 != "0":
            info["fiftyTwoWeekHigh"] = max(info.get("fiftyTwoWeekHigh", 0) or 0, float(_high52))

        _low52 = field(TENCENT_QUOTE_SCHEMA, fields, "week52_low", "")
        if _low52 and _low52 != "0":
            info["fiftyTwoWeekLow"] = info.get("fiftyTwoWeekLow", 0) or float(_low52)

        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"腾讯行情API: {str(e)[:50]}")


def fill_valuation_from_akshare(code: str, info: dict) -> None:
    """从 akshare 东方财富获取估值指标"""
    cb = CircuitBreaker.get("akshare_valuation")
    if not cb.allow_request():
        return
    try:
        import akshare as ak

        symbol = f"{code}.SH" if code.startswith("6") else f"{code}.SZ"
        indicator_df = ak.stock_financial_analysis_indicator_em(symbol=symbol)
        if not indicator_df.empty:
            row = indicator_df.iloc[0]
            if info.get("dividendYield", "N/A") == "N/A" or info.get("dividendYield", 0) == 0:
                dividend = _safe_float(row.get("股息率(%)", 0))
                if dividend:
                    info["dividendYield"] = dividend / 100
            if info.get("beta", "N/A") == "N/A":
                info["beta"] = _safe_float(row.get("贝塔系数", 0)) or "N/A"
            if info.get("trailingPE", "N/A") == "N/A":
                info["trailingPE"] = _safe_float(row.get("市盈率", 0)) or "N/A"
            if info.get("priceToBook", "N/A") == "N/A":
                info["priceToBook"] = _safe_float(row.get("市净率", 0)) or "N/A"
        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug("akshare估值指标获取失败，使用已有数据")


# ═══════════════════════════════════════════════════════════════════
# K 线数据
# ═══════════════════════════════════════════════════════════════════


def get_tencent_kline(code: str, period: str) -> pd.DataFrame:
    """从腾讯获取K线数据（Schema 驱动）"""
    cb = CircuitBreaker.get("tencent_kline")
    if not cb.allow_request():
        return pd.DataFrame()
    try:
        start_date = pd.to_datetime(_calculate_start_date(period))
        tk_code = f"sh{code}" if code.startswith("6") else f"sz{code}"
        conn = http.client.HTTPSConnection("web.ifzq.gtimg.cn", timeout=Config.SOURCE_TIMEOUT, context=_SSL_CTX)
        url = f"/appstock/app/fqkline/get?param={tk_code},day,,,640,qfq"
        conn.request("GET", url, headers=_HTTP_HEADERS)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8", errors="ignore")
        conn.close()
        data = json.loads(raw)
        klines = data.get("data", {}).get(tk_code, {}).get("qfqday", []) or data.get("data", {}).get(tk_code, {}).get(
            "day", []
        )
        if not klines:
            cb.record_success()
            return pd.DataFrame()

        rows = [
            {
                "Date": pd.to_datetime(field(TENCENT_KLINE_SCHEMA, k, "date", "")),
                "Open": float(field(TENCENT_KLINE_SCHEMA, k, "open", 0)),
                "Close": float(field(TENCENT_KLINE_SCHEMA, k, "close", 0)),
                "High": float(field(TENCENT_KLINE_SCHEMA, k, "high", 0)),
                "Low": float(field(TENCENT_KLINE_SCHEMA, k, "low", 0)),
                "Volume": float(field(TENCENT_KLINE_SCHEMA, k, "volume", 0)),
            }
            for k in klines
        ]
        df = pd.DataFrame(rows).set_index("Date")
        df = df[df.index >= start_date]
        cb.record_success()
        return df
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"腾讯K线: {str(e)[:50]}")
        return pd.DataFrame()


def get_tickflow_kline(ticker: str, period: str) -> pd.DataFrame:
    """从 TickFlow 获取K线数据"""
    cb = CircuitBreaker.get("tickflow_kline")
    if not TICKFLOW_AVAILABLE or not cb.allow_request():
        return pd.DataFrame()
    try:
        tf_symbol = _to_tickflow_symbol(ticker)
        start = _calculate_start_date(period)
        end = datetime.now().strftime("%Y%m%d")
        start_ts = int(datetime.strptime(start, "%Y%m%d").timestamp())
        end_ts = int(datetime.strptime(end, "%Y%m%d").timestamp())
        df = _tickflow_free.klines.get(tf_symbol, start_time=start_ts, end_time=end_ts, as_dataframe=True)
        if df is not None and not df.empty:
            df = rename_df(df, TICKFLOW_KLINE_RENAME)
            df.index = pd.to_datetime(df.index)
            df = normalize_kline_df(df)
            cb.record_success()
            return df
        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"TickFlow K线: {str(e)[:50]}")
    return pd.DataFrame()


def get_akshare_kline(ticker: str, period: str) -> pd.DataFrame:
    """从腾讯（akshare封装）获取K线数据（纯HTTP，不依赖 py_mini_racer）"""
    cb = CircuitBreaker.get("akshare_kline")
    if not cb.allow_request():
        return pd.DataFrame()
    try:
        import akshare as ak

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = _calculate_start_date(period)
        symbol = _ensure_exchange_prefix(ticker)
        df = ak.stock_zh_a_hist_tx(symbol=symbol, start_date=start_date, end_date=end_date, adjust="qfq")
        if not df.empty:
            df = df.rename(columns={"date": "Date", "open": "Open", "close": "Close", "high": "High", "low": "Low", "amount": "Volume"})
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]]
            cb.record_success()
            return df
        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"akshare K线: {str(e)[:50]}")
    return pd.DataFrame()


def get_tencent_akshare_kline(ticker: str, period: str) -> pd.DataFrame:
    """从腾讯（akshare封装）获取K线数据，作为腾讯HTTP的替补"""
    cb = CircuitBreaker.get("tencent_ak_kline")
    if not cb.allow_request():
        return pd.DataFrame()
    try:
        import akshare as ak

        symbol = _ensure_exchange_prefix(ticker)
        start = _calculate_start_date(period)
        end = datetime.now().strftime("%Y%m%d")
        df = ak.stock_zh_a_hist_tx(symbol=symbol, start_date=start, end_date=end, adjust="qfq")
        if not df.empty:
            df = df.rename(columns={"date": "Date", "open": "Open", "close": "Close", "high": "High", "low": "Low", "amount": "Volume"})
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]]
            cb.record_success()
            return df
        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"腾讯akshare K线: {str(e)[:50]}")
    return pd.DataFrame()


def get_index_daily_tx(symbol: str) -> pd.DataFrame:
    """从腾讯获取指数日线数据，作为主指数接口的替补"""
    cb = CircuitBreaker.get("index_tx")
    if not cb.allow_request():
        return pd.DataFrame()
    try:
        import akshare as ak

        df = ak.stock_zh_index_daily_tx(symbol=symbol)
        if not df.empty:
            df = df.rename(columns={"date": "Date", "open": "open", "close": "close", "high": "high", "low": "low", "amount": "amount"})
            cb.record_success()
            return df
        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"腾讯指数日线: {str(e)[:50]}")
    return pd.DataFrame()


def get_index_spot_sina() -> pd.DataFrame:
    """从新浪获取指数实时行情"""
    cb = CircuitBreaker.get("index_sina")
    if not cb.allow_request():
        return pd.DataFrame()
    try:
        import akshare as ak

        df = ak.stock_zh_index_spot_sina()
        cb.record_success()
        return df
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"新浪指数行情: {str(e)[:50]}")
    return pd.DataFrame()


def get_valuation_baidu(code: str) -> dict:
    """从百度获取估值数据（总市值），作为 stock_value_em 的替补"""
    cb = CircuitBreaker.get("baidu_valuation")
    if not cb.allow_request():
        return {}
    try:
        import akshare as ak

        df = ak.stock_zh_valuation_baidu(symbol=code, indicator="总市值")
        if not df.empty:
            cb.record_success()
            return {"marketCap": float(df["value"].iloc[-1]) * 1e8, "source": "baidu"}
        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"百度估值: {str(e)[:50]}")
    return {}


def fill_company_info_cninfo(code: str, info: dict) -> None:
    """从巨潮资讯网补充公司基本信息"""
    cb = CircuitBreaker.get("cninfo_profile")
    if not cb.allow_request():
        return
    try:
        import akshare as ak

        df = ak.stock_profile_cninfo(symbol=code)
        if not df.empty:
            row = df.iloc[0]
            if info.get("longName", "N/A") == "N/A":
                info["longName"] = row.get("公司名称", "N/A")
            if info.get("industry", "N/A") == "N/A":
                info["industry"] = row.get("所属行业", "N/A")
            info["website"] = row.get("官方网站", "N/A")
            info["listedDate"] = row.get("上市日期", "N/A")
            info["registeredCapital"] = row.get("注册资金", "N/A")
        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"巨潮公司信息: {str(e)[:50]}")


def fill_business_ths(code: str, info: dict) -> None:
    """从同花顺补充主营业务信息"""
    cb = CircuitBreaker.get("ths_business")
    if not cb.allow_request():
        return
    try:
        import akshare as ak

        df = ak.stock_zyjs_ths(symbol=code)
        if not df.empty:
            row = df.iloc[0]
            info["mainBusiness"] = row.get("主营业务", "N/A")
            info["productType"] = row.get("产品类型", "N/A")
            info["productName"] = row.get("产品名称", "N/A")
        cb.record_success()
    except Exception as e:
        cb.record_failure(str(e))
        logger.debug(f"同花顺主营业务: {str(e)[:50]}")


# ═══════════════════════════════════════════════════════════════════
# 财务报表
# ═══════════════════════════════════════════════════════════════════


def get_financial_data_em(code: str, statement_type: str = "all") -> pd.DataFrame:
    """从东方财富获取财务报表（纯HTTP，不依赖 py_mini_racer）。
    注：东方财富 API 返回全部历史数据，akshare 不支持日期过滤，
    这里拉取后只保留最近 8 个季度（2 年），减少后续处理开销。
    """
    cb = CircuitBreaker.get("em_financial")
    if not cb.allow_request():
        return pd.DataFrame()

    symbol = f"{code}.{'SH' if code.startswith('6') else 'SZ'}"

    try:
        import akshare as ak

        df = pd.DataFrame()
        if "资产负债" in statement_type:
            df = ak.stock_balance_sheet_by_report_em(symbol=symbol)
        elif "现金流" in statement_type:
            df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
        elif "利润" in statement_type:
            df = ak.stock_profit_sheet_by_report_em(symbol=symbol)
        else:
            df = ak.stock_financial_analysis_indicator_em(symbol=symbol, indicator="按报告期")

        if not df.empty:
            cb.record_success()
            return df.head(8)
    except Exception as e:
        cb.record_failure(str(e))
        return pd.DataFrame()