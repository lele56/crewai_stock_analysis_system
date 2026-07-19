# src/tools/akshare_data_cache.py
"""股票数据缓存层 — 三层缓存（内存 → Redis → 文件）+ 数据校验 + 共享工具函数"""

from datetime import datetime
import json
import logging
import os
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ── 共享 key map：东方财富列名 → 标准英文 key ─────────────────

_FINANCIAL_KEY_MAP: dict[str, str] = {
    "TOTAL_OPERATE_INCOME": "revenue", "OPERATE_INCOME": "revenue",
    "NETPROFIT": "net_income", "PARENT_NETPROFIT": "net_income",
    "OPERATE_PROFIT": "operating_profit",
    "OPERATE_COST": "operating_cost",
    "SALE_EXPENSE": "sale_expense",
    "MANAGE_EXPENSE": "manage_expense",
    "FINANCE_EXPENSE": "finance_expense",
    "RESEARCH_EXPENSE": "research_expense",
    "INTEREST_EXPENSE": "interest_expense",
    "INCOME_TAX": "income_tax",
    "TOTAL_OPERATE_COST": "total_operating_cost",
    "TOTAL_ASSETS": "total_assets",
    "TOTAL_EQUITY": "equity",
    "TOTAL_CURRENT_ASSETS": "current_assets",
    "TOTAL_CURRENT_LIAB": "current_liabilities",
    "INVENTORY": "inventory",
    "MONETARYFUNDS": "cash",
    "TOTAL_LIABILITIES": "total_debt",
    "ACCOUNTS_RECE": "accounts_receivable",
    "ACCOUNTS_PAYABLE": "accounts_payable",
    "FIXED_ASSET": "fixed_assets",
    "GOODWILL": "goodwill",
    "SHORT_LOAN": "short_loan",
    "LONG_LOAN": "long_loan",
    "BORROW_FUND": "borrow_fund",
    "TOTAL_PARENT_EQUITY": "parent_equity",
    "TOTAL_NONCURRENT_ASSETS": "noncurrent_assets",
    "TOTAL_NONCURRENT_LIAB": "noncurrent_liabilities",
    "NETCASH_OPERATE": "operating_cashflow",
    "NETCASH_INVEST": "investing_cashflow",
    "NETCASH_FINANCE": "financing_cashflow",
    "TOTAL_OPERATE_INFLOW": "total_operating_inflow",
    "TOTAL_OPERATE_OUTFLOW": "total_operating_outflow",
    "EPSJB": "eps",
    "BPS": "bps",
}

_FINANCIAL_PREV_MAP: dict[str, str] = {
    "TOTAL_OPERATE_INCOME": "previous_revenue",
    "OPERATE_INCOME": "previous_revenue",
    "NETPROFIT": "previous_net_income",
    "PARENT_NETPROFIT": "previous_net_income",
    "TOTAL_ASSETS": "previous_total_assets",
}


def _safe_float(val: Any) -> float | None:
    """安全地将值转为 float，无法转换时返回 None"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(str(val).replace(",", "").replace("亿", "e8").replace("万", "e4").replace("元", ""))
    except (ValueError, TypeError):
        return None


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """在 DataFrame 中查找第一个存在的列名"""
    for col in candidates:
        if col in df.columns:
            return col
    return None


# ── 三层缓存基础设施 ─────────────────────────────────────────

_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "stock_cache"
)
_FINANCIAL_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "financial_cache"
)
_REDIS_AVAILABLE = False
_REDIS_CLIENT = None
_MEMORY_CACHE: dict[str, dict] = {}

try:
    import redis as _redis

    _redis.Redis(host="localhost", port=6379, socket_connect_timeout=1).ping()
    _REDIS_CLIENT = _redis.Redis(host="localhost", port=6379, socket_connect_timeout=1, decode_responses=True)
    _REDIS_AVAILABLE = True
    logger.info("Redis 缓存已启用")
except Exception:
    logger.info("Redis 未连接，使用文件 + 内存缓存")


# ── 数据校验 ─────────────────────────────────────────────────

def _validate_stock_data(
    name: str, hist: pd.DataFrame, financials: pd.DataFrame,
    balance_sheet: pd.DataFrame, info: dict,
) -> pd.DataFrame | None:
    """校验数据质量，返回清洗后的 hist；不合格返回 None"""
    if hist.empty:
        logger.warning(f"缓存校验 [{name}]: K线为空，跳过缓存")
        return None
    if len(hist) < 10:
        logger.warning(f"缓存校验 [{name}]: K线仅 {len(hist)} 条，数据不足，跳过缓存")
        return None
    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    missing = required_cols - set(hist.columns)
    if missing:
        logger.warning(f"缓存校验 [{name}]: K线缺少列 {missing}，跳过缓存")
        return None
    if hist["Close"].sum() == 0:
        logger.warning(f"缓存校验 [{name}]: K线收盘价全为0，跳过缓存")
        return None
    if pd.isna(hist["Close"].iloc[-1]):
        logger.warning(f"缓存校验 [{name}]: 最新收盘价为NaN，跳过缓存")
        return None
    if (hist["Close"] < 0).any():
        logger.warning(f"缓存校验 [{name}]: K线存在负价格，跳过缓存")
        return None

    bad_rows = hist[
        (hist["High"] < hist["Low"]) |
        (hist["High"] < hist["Open"]) |
        (hist["High"] < hist["Close"]) |
        (hist["Low"] > hist["Open"]) |
        (hist["Low"] > hist["Close"])
    ]
    bad_count = len(bad_rows)
    total = len(hist)
    if bad_count > total * 0.1:
        logger.warning(f"缓存校验 [{name}]: OHLC 逻辑异常 {bad_count}/{total} 行，跳过缓存")
        return None
    if bad_count > 0:
        logger.info(f"缓存校验 [{name}]: OHLC 逻辑异常 {bad_count}/{total} 行（<10%），已剔除异常行")
        hist = hist.drop(bad_rows.index)

    if len(hist) >= 2:
        pct_changes = hist["Close"].pct_change().abs()
        spike_rows = pct_changes[pct_changes > 0.20]
        if len(spike_rows) > 0:
            logger.warning(
                f"缓存校验 [{name}]: 检测到 {len(spike_rows)} 个异常波动日（>20%），"
                f"日期: {list(spike_rows.index[:3])}"
            )

    if hist.index.duplicated().any():
        dup_count = hist.index.duplicated().sum()
        logger.warning(f"缓存校验 [{name}]: K线存在 {dup_count} 个重复日期，跳过缓存")
        return None

    fin_empty = financials.empty and balance_sheet.empty
    if fin_empty:
        logger.info(f"缓存校验 [{name}]: 财务数据为空（非关键），继续缓存")
    else:
        if not financials.empty:
            for col in ["TOTAL_OPERATE_INCOME", "OPERATE_INCOME", "NETPROFIT", "PARENT_NETPROFIT"]:
                if col in financials.columns:
                    val = financials[col].iloc[0] if len(financials) > 0 else 0
                    if val and val != 0:
                        break
            else:
                logger.warning(f"缓存校验 [{name}]: 财务数据营收/净利润全为0，可能异常")

        if not financials.empty and not balance_sheet.empty:
            revenue = 0.0
            for col in ["TOTAL_OPERATE_INCOME", "OPERATE_INCOME"]:
                if col in financials.columns:
                    rv = _safe_float(financials[col].iloc[0])
                    if rv:
                        revenue = rv
                    break
            total_assets = 0.0
            if "TOTAL_ASSETS" in balance_sheet.columns:
                ta = _safe_float(balance_sheet["TOTAL_ASSETS"].iloc[0])
                if ta:
                    total_assets = ta
            if revenue > 0 and total_assets == 0:
                logger.warning(f"缓存校验 [{name}]: 营收={revenue} 但资产总计=0，数据矛盾")

    if not info or len(info) < 2:
        logger.warning(f"缓存校验 [{name}]: 公司信息不足，跳过缓存")
        return None

    return hist


def _is_cache_fresh(cache: dict) -> bool:
    """检查缓存是否新鲜：K线数据的最后一天必须是今天或昨天"""
    kline = cache.get("kline", [])
    if not kline:
        return False
    last_record = kline[-1]
    date_str = last_record.get("Date", "")
    if not date_str:
        return False
    try:
        cache_date = pd.Timestamp(date_str).date()
        today = datetime.now().date()
        diff = (today - cache_date).days
        if diff > 2:
            logger.warning(f"缓存过期: K线最后日期 {cache_date}，距今 {diff} 天")
            return False
        return True
    except Exception:
        return False


# ── 股票缓存写入 ─────────────────────────────────────────────

def _save_financial_fallback(
    ticker: str,
    financials: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> None:
    """将财务数据写入独立缓存（与 K 线校验解耦，确保财务数据不丢失）"""
    try:
        data: dict[str, float] = {}
        for df in [financials, balance_sheet, cashflow]:
            if df.empty:
                continue
            record = df.iloc[0].to_dict()
            for k, v in record.items():
                val = _safe_float(v)
                if val is not None and k in _FINANCIAL_KEY_MAP:
                    data[_FINANCIAL_KEY_MAP[k]] = val
        if data:
            save_financial_cache(ticker, data)
    except Exception as e:
        logger.debug("财务缓存写入失败: %s", str(e)[:50])


def _save_stock_cache(
    ticker: str,
    hist: pd.DataFrame,
    financials: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cashflow: pd.DataFrame,
    info: dict,
) -> None:
    """三层缓存写入：内存 → Redis → 文件。
    财务数据总是写入独立缓存（不依赖K线校验），主缓存仅在校验通过后写入。
    """
    _save_financial_fallback(ticker, financials, balance_sheet, cashflow)

    hist = _validate_stock_data(ticker, hist, financials, balance_sheet, info)
    if hist is None:
        return

    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)

        def _df_to_records(df: pd.DataFrame) -> list[dict]:
            if df.empty:
                return []
            df = df.copy().reset_index()
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].astype(str)
            return df.to_dict(orient="records")

        cache = {
            "ticker": ticker,
            "cached_at": datetime.now().isoformat(),
            "validated": True,
            "info": {k: (v if isinstance(v, (int, float, bool)) or v is None else str(v))
                     for k, v in info.items()},
            "kline": _df_to_records(hist),
            "financials": _df_to_records(financials),
            "balance_sheet": _df_to_records(balance_sheet),
            "cashflow": _df_to_records(cashflow),
        }

        _MEMORY_CACHE[ticker] = cache

        if _REDIS_AVAILABLE:
            try:
                _REDIS_CLIENT.setex(
                    f"stock:{ticker}",
                    3600,
                    json.dumps(cache, ensure_ascii=False),
                )
            except Exception as e:
                logger.debug(f"Redis 写入失败: {e}")

        cache_path = os.path.join(_CACHE_DIR, f"{ticker}.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"缓存已保存: {ticker} (K线{len(cache['kline'])}条, 财务{len(cache['financials'])}条)")
    except Exception as e:
        logger.warning(f"缓存保存失败: {e}")


# ── 股票缓存读取 ─────────────────────────────────────────────

def load_stock_cache(ticker: str, force_refresh: bool = False) -> dict | None:
    """三层缓存读取：内存 → Redis → 文件。force_refresh=True 跳过所有缓存"""
    if force_refresh:
        _MEMORY_CACHE.pop(ticker, None)
        return None

    if ticker in _MEMORY_CACHE:
        if _is_cache_fresh(_MEMORY_CACHE[ticker]):
            return _MEMORY_CACHE[ticker]
        _MEMORY_CACHE.pop(ticker, None)
        return None

    if _REDIS_AVAILABLE:
        try:
            raw = _REDIS_CLIENT.get(f"stock:{ticker}")
            if raw:
                cache = json.loads(raw)
                if _is_cache_fresh(cache):
                    _MEMORY_CACHE[ticker] = cache
                    return cache
                _REDIS_CLIENT.delete(f"stock:{ticker}")
                return None
        except Exception as e:
            logger.debug(f"Redis 读取失败: {e}")

    cache_path = os.path.join(_CACHE_DIR, f"{ticker}.json")
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("validated"):
            if not _is_cache_fresh(cache):
                os.remove(cache_path)
                return None
            _MEMORY_CACHE[ticker] = cache
            logger.info(f"从文件缓存读取: {ticker}")
            return cache
        logger.warning(f"缓存数据未校验: {ticker}，忽略")
        return None
    except Exception as e:
        logger.warning(f"读取缓存失败: {e}")
        return None


def load_kline_from_cache(ticker: str) -> pd.DataFrame | None:
    """从缓存读取 K 线数据为 DataFrame"""
    cache = load_stock_cache(ticker)
    if not cache or not cache.get("kline"):
        return None
    df = pd.DataFrame(cache["kline"])
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
    return df


# ── 财务独立缓存 ─────────────────────────────────────────────

def save_financial_cache(ticker: str, data: dict[str, float]) -> None:
    """保存财务数据到独立文件缓存（仅英文 key，不依赖 K 线）"""
    if not data:
        return
    try:
        os.makedirs(_FINANCIAL_CACHE_DIR, exist_ok=True)
        cache_path = os.path.join(_FINANCIAL_CACHE_DIR, f"{ticker}.json")
        payload = {
            "ticker": ticker,
            "cached_at": datetime.now().isoformat(),
            "data": data,
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"财务缓存已保存: {ticker} ({len(data)} 个字段)")
    except Exception as e:
        logger.warning(f"财务缓存保存失败: {e}")


def load_financial_cache_file(ticker: str) -> dict[str, float] | None:
    """从独立文件缓存读取财务数据，过期时间 24 小时"""
    cache_path = os.path.join(_FINANCIAL_CACHE_DIR, f"{ticker}.json")
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, encoding="utf-8") as f:
            payload = json.load(f)
        cached_at = datetime.fromisoformat(payload.get("cached_at", "2000-01-01"))
        if (datetime.now() - cached_at).total_seconds() > 86400:
            logger.info(f"财务缓存过期: {ticker}")
            return None
        data = payload.get("data", {})
        if data:
            return {k: float(v) for k, v in data.items() if v is not None}
    except Exception as e:
        logger.warning(f"读取财务缓存失败: {e}")
    return None


def load_financial_from_cache(ticker: str) -> dict:
    """从缓存读取财务数据为扁平字典（主缓存 → 财务独立缓存）"""
    cache = load_stock_cache(ticker)
    if cache:
        result: dict[str, float] = {}
        for section in ["financials", "balance_sheet", "cashflow"]:
            records = cache.get(section, [])
            if records:
                row = records[0]
                for k, v in row.items():
                    if v is not None and k not in ("index", "Date"):
                        val = _safe_float(v)
                        if val is not None:
                            result[k] = val

        for cn, en in _FINANCIAL_KEY_MAP.items():
            if cn in result:
                result[en] = result[cn]

        if "gross_profit" not in result and result.get("revenue", 0) > 0 and result.get("operating_cost", 0) > 0:
            result["gross_profit"] = result["revenue"] - result["operating_cost"]

        logger.info(
            "从主缓存读取财务: revenue=%s, net_income=%s, total_assets=%s, equity=%s",
            result.get("revenue", 0), result.get("net_income", 0),
            result.get("total_assets", 0), result.get("equity", 0),
        )
        return result

    fallback = load_financial_cache_file(ticker)
    if fallback:
        if "gross_profit" not in fallback and fallback.get("revenue", 0) > 0 and fallback.get("operating_cost", 0) > 0:
            fallback["gross_profit"] = fallback["revenue"] - fallback["operating_cost"]
        logger.info("从财务独立缓存读取: %s", ticker)
        return fallback

    return {}