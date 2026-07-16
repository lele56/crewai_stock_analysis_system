# src/tools/akshare_data_parser.py
"""股票数据获取与解析 - 多数据源架构（腾讯/新浪/TickFlow/akshare）"""

from datetime import datetime
import json
import logging
import os

import pandas as pd

from src.tools.akshare_data_sources import (
    fill_business_ths,
    fill_company_info_cninfo,
    fill_from_sina_spot,
    fill_from_tencent_quote,
    fill_from_tickflow,
    fill_industry_from_sina,
    fill_valuation_from_akshare,
    get_akshare_kline,
    get_financial_data_ths,
    get_tencent_akshare_kline,
    get_tencent_kline,
    get_tickflow_kline,
    get_valuation_baidu,
)
from src.tools.circuit_breaker import CircuitBreaker
from src.tools.technical_indicators import calculate_macd, calculate_rsi

logger = logging.getLogger(__name__)


def get_stock_basic_info(ticker: str) -> dict:
    """获取股票基本信息（多数据源合并）"""
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
    return info


def get_stock_history_data(ticker: str, period: str) -> pd.DataFrame:
    """获取历史K线数据（腾讯HTTP → 腾讯akshare → TickFlow → 新浪akshare，断路器自动跳过故障源）"""
    try:
        code = ticker.replace("sh", "").replace("sz", "").replace("SH", "").replace("SZ", "")

        if CircuitBreaker.get("tencent_kline").allow_request():
            df = get_tencent_kline(code, period)
            if not df.empty:
                return df

        if CircuitBreaker.get("tencent_ak_kline").allow_request():
            df = get_tencent_akshare_kline(ticker, period)
            if not df.empty:
                return df

        if CircuitBreaker.get("tickflow_kline").allow_request():
            df = get_tickflow_kline(ticker, period)
            if not df.empty:
                return df

        return get_akshare_kline(ticker, period)
    except Exception as e:
        logger.error(f"获取股票历史数据失败: {str(e)}")
        return pd.DataFrame()


def get_financial_statements(ticker: str, statement_type: str) -> pd.DataFrame:
    """获取财务报表（同花顺 → 断路器自动跳过故障源）"""
    try:
        code = ticker.replace("sh", "").replace("sz", "").replace("SH", "").replace("SZ", "")

        if CircuitBreaker.get("ths_financial").allow_request():
            df = get_financial_data_ths(code, statement_type)
            if not df.empty:
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
    """生成股票数据报告"""
    report = f"# {ticker} 股票数据报告\n\n"
    report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += "## 基本信息\n\n"
    report += f"- **公司名称**: {info.get('longName', 'N/A')}\n"
    report += f"- **行业**: {info.get('industry', 'N/A')}\n"
    mcap = info.get("marketCap", 0)
    report += f"- **市值**: ¥{mcap:,.0f}\n" if mcap else "- **市值**: N/A\n"
    price = info.get("currentPrice", 0)
    report += f"- **当前价格**: ¥{price:.2f}\n" if price else "- **当前价格**: N/A\n"
    high52 = info.get("fiftyTwoWeekHigh", 0)
    low52 = info.get("fiftyTwoWeekLow", 0)
    report += f"- **52周最高**: ¥{high52:.2f}\n" if high52 else "- **52周最高**: N/A\n"
    report += f"- **52周最低**: ¥{low52:.2f}\n\n" if low52 else "- **52周最低**: N/A\n\n"
    if not hist.empty:
        report += "## 价格统计\n\n"
        current_price = hist["Close"].iloc[-1]
        period_return = ((current_price - hist["Close"].iloc[0]) / hist["Close"].iloc[0]) * 100
        report += f"- **当前价格**: ¥{current_price:.2f}\n"
        report += f"- **期间涨幅**: {period_return:.2f}%\n"
        report += f"- **期间最高**: ¥{hist['High'].max():.2f}\n"
        report += f"- **期间最低**: ¥{hist['Low'].min():.2f}\n"
        report += f"- **平均成交额**: {hist['Volume'].mean():,.0f} 股\n\n"
    report += "## 关键财务指标\n\n"
    financial_metrics = _extract_financial_metrics(info, financials)
    for metric, value in financial_metrics.items():
        report += f"- **{metric}**: {value}\n"
    balance_metrics = _extract_balance_sheet_metrics(balance_sheet)
    if balance_metrics:
        report += "\n### 资产负债表摘要\n\n"
        for metric, value in balance_metrics.items():
            report += f"- **{metric}**: {value}\n"
    cashflow_metrics = _extract_cashflow_metrics(cashflow)
    if cashflow_metrics:
        report += "\n### 现金流量表摘要\n\n"
        for metric, value in cashflow_metrics.items():
            report += f"- **{metric}**: {value}\n"
    if not hist.empty:
        report += "\n## 技术指标\n\n"
        tech_indicators = _calculate_technical_indicators(hist)
        for indicator, value in tech_indicators.items():
            report += f"- **{indicator}**: {value}\n"

    # 缓存原始财务数据，后续工具可直接读取，无需重复调用 API
    _save_stock_cache(ticker, hist, financials, balance_sheet, cashflow, info)

    return report


# ── 股票数据缓存（三层：内存 → Redis → 文件）─────────────────

_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "stock_cache")
_REDIS_AVAILABLE = False
_REDIS_CLIENT = None
_MEMORY_CACHE: dict[str, dict] = {}  # L0: 进程内存

try:
    import redis as _redis

    _redis.Redis(host="localhost", port=6379, socket_connect_timeout=1).ping()
    _REDIS_CLIENT = _redis.Redis(host="localhost", port=6379, socket_connect_timeout=1, decode_responses=True)
    _REDIS_AVAILABLE = True
    logger.info("Redis 缓存已启用")
except Exception:
    logger.info("Redis 未连接，使用文件 + 内存缓存")


def _validate_stock_data(
    name: str, hist: pd.DataFrame, financials: pd.DataFrame,
    balance_sheet: pd.DataFrame, info: dict,
) -> bool:
    """校验数据质量，拒绝缓存垃圾数据"""
    # K线检查
    if hist.empty:
        logger.warning(f"缓存校验 [{name}]: K线为空，跳过缓存")
        return False
    if len(hist) < 10:
        logger.warning(f"缓存校验 [{name}]: K线仅 {len(hist)} 条，数据不足，跳过缓存")
        return False
    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    missing = required_cols - set(hist.columns)
    if missing:
        logger.warning(f"缓存校验 [{name}]: K线缺少列 {missing}，跳过缓存")
        return False
    if hist["Close"].sum() == 0:
        logger.warning(f"缓存校验 [{name}]: K线收盘价全为0，跳过缓存")
        return False
    if pd.isna(hist["Close"].iloc[-1]):
        logger.warning(f"缓存校验 [{name}]: 最新收盘价为NaN，跳过缓存")
        return False
    if (hist["Close"] < 0).any():
        logger.warning(f"缓存校验 [{name}]: K线存在负价格，跳过缓存")
        return False

    # OHLC 逻辑一致性：High >= Low, High >= Open/Close, Low <= Open/Close
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
        logger.warning(
            f"缓存校验 [{name}]: OHLC 逻辑异常 {bad_count}/{total} 行，"
            f"跳过缓存"
        )
        return False
    elif bad_count > 0:
        logger.info(
            f"缓存校验 [{name}]: OHLC 逻辑异常 {bad_count}/{total} 行（<10%），"
            f"已剔除异常行"
        )
        hist = hist.drop(bad_rows.index)

    # 异常波动检测：单日涨跌幅 > 20%（A股涨跌停 ±10%，留余量）
    if len(hist) >= 2:
        pct_changes = hist["Close"].pct_change().abs()
        spike_rows = pct_changes[pct_changes > 0.20]
        if len(spike_rows) > 0:
            logger.warning(
                f"缓存校验 [{name}]: 检测到 {len(spike_rows)} 个异常波动日（>20%），"
                f"日期: {list(spike_rows.index[:3])}"
            )
            # 不拒绝，但警告。可能是除权除息日

    # 日期连续性：不能有重复日期，日期必须递增
    if hist.index.duplicated().any():
        dup_count = hist.index.duplicated().sum()
        logger.warning(f"缓存校验 [{name}]: K线存在 {dup_count} 个重复日期，跳过缓存")
        return False

    # 财务检查
    fin_empty = financials.empty and balance_sheet.empty
    if fin_empty:
        logger.info(f"缓存校验 [{name}]: 财务数据为空（非关键），继续缓存")
    else:
        if not financials.empty:
            for col in ["营业总收入", "营业收入", "净利润"]:
                if col in financials.columns:
                    val = financials[col].iloc[0] if len(financials) > 0 else 0
                    if val and val != 0:
                        break
            else:
                logger.warning(f"缓存校验 [{name}]: 财务数据营收/净利润全为0，可能异常")

        # 财务逻辑一致性：营收 > 0 但资产总计 = 0 不合理
        if not financials.empty and not balance_sheet.empty:
            revenue = 0.0
            for col in ["营业总收入", "营业收入"]:
                if col in financials.columns:
                    revenue = financials[col].iloc[0] or 0
                    break
            total_assets = 0.0
            if "资产总计" in balance_sheet.columns:
                total_assets = balance_sheet["资产总计"].iloc[0] or 0
            if revenue > 0 and total_assets == 0:
                logger.warning(
                    f"缓存校验 [{name}]: 营收={revenue} 但资产总计=0，数据矛盾"
                )

    # 公司信息检查
    if not info or len(info) < 2:
        logger.warning(f"缓存校验 [{name}]: 公司信息不足，跳过缓存")
        return False

    return True


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


def _save_stock_cache(
    ticker: str,
    hist: pd.DataFrame,
    financials: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cashflow: pd.DataFrame,
    info: dict,
) -> None:
    """三层缓存写入：内存 → Redis → 文件"""
    if not _validate_stock_data(ticker, hist, financials, balance_sheet, info):
        return

    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)

        def _df_to_records(df: pd.DataFrame) -> list[dict]:
            if df.empty:
                return []
            return df.reset_index().to_dict(orient="records")

        cache = {
            "ticker": ticker,
            "cached_at": datetime.now().isoformat(),
            "validated": True,
            "info": {k: str(v) for k, v in info.items()},
            "kline": _df_to_records(hist),
            "financials": _df_to_records(financials),
            "balance_sheet": _df_to_records(balance_sheet),
            "cashflow": _df_to_records(cashflow),
        }

        # L0: 内存缓存
        _MEMORY_CACHE[ticker] = cache

        # L1: Redis（可选）
        if _REDIS_AVAILABLE:
            try:
                _REDIS_CLIENT.setex(
                    f"stock:{ticker}",
                    3600,  # 1小时过期
                    json.dumps(cache, ensure_ascii=False),
                )
            except Exception as e:
                logger.debug(f"Redis 写入失败: {e}")

        # L2: 文件持久化
        cache_path = os.path.join(_CACHE_DIR, f"{ticker}.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(
            f"缓存已保存: {ticker} (K线{len(cache['kline'])}条, 财务{len(cache['financials'])}条)"
        )
    except Exception as e:
        logger.warning(f"缓存保存失败: {e}")


def load_stock_cache(ticker: str, force_refresh: bool = False) -> dict | None:
    """三层缓存读取：内存 → Redis → 文件。force_refresh=True 跳过所有缓存"""
    if force_refresh:
        _MEMORY_CACHE.pop(ticker, None)
        return None

    # L0: 内存
    if ticker in _MEMORY_CACHE:
        if _is_cache_fresh(_MEMORY_CACHE[ticker]):
            return _MEMORY_CACHE[ticker]
        else:
            _MEMORY_CACHE.pop(ticker, None)  # 过期，清除
            return None

    # L1: Redis
    if _REDIS_AVAILABLE:
        try:
            raw = _REDIS_CLIENT.get(f"stock:{ticker}")
            if raw:
                cache = json.loads(raw)
                if _is_cache_fresh(cache):
                    _MEMORY_CACHE[ticker] = cache
                    return cache
                else:
                    _REDIS_CLIENT.delete(f"stock:{ticker}")  # 过期，清除
                    return None
        except Exception as e:
            logger.debug(f"Redis 读取失败: {e}")

    # L2: 文件
    cache_path = os.path.join(_CACHE_DIR, f"{ticker}.json")
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("validated"):
            if not _is_cache_fresh(cache):
                os.remove(cache_path)  # 过期，删除文件
                return None
            _MEMORY_CACHE[ticker] = cache
            logger.info(f"从文件缓存读取: {ticker}")
            return cache
        else:
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


def load_financial_from_cache(ticker: str) -> dict:
    """从缓存读取财务数据为扁平字典"""
    cache = load_stock_cache(ticker)
    if not cache:
        return {}

    result: dict[str, float] = {}
    for section in ["financials", "balance_sheet", "cashflow"]:
        records = cache.get(section, [])
        if records:
            row = records[0]
            for k, v in row.items():
                if v is not None and k not in ("index", "Date"):
                    try:
                        result[k] = float(v)
                    except (ValueError, TypeError):
                        pass

    # 映射为标准 key
    _key_map = {
        "营业总收入": "revenue", "营业收入": "revenue",
        "净利润": "net_income",
        "资产总计": "total_assets",
        "股东权益": "equity",
        "流动资产": "current_assets",
        "流动负债": "current_liabilities",
        "存货": "inventory",
        "货币资金": "cash",
        "负债合计": "total_debt",
        "经营活动现金流量净额": "operating_cashflow",
    }
    for cn, en in _key_map.items():
        if cn in result:
            result[en] = result[cn]

    logger.info(
        "从缓存读取财务: revenue=%s, net_income=%s, total_assets=%s, equity=%s",
        result.get("revenue", 0), result.get("net_income", 0),
        result.get("total_assets", 0), result.get("equity", 0),
    )
    return result


def _extract_financial_metrics(info: dict, financials: pd.DataFrame) -> dict[str, str]:
    metrics = {
        "市盈率": f"{info.get('trailingPE', 'N/A')}",
        "前瞻市盈率": f"{info.get('forwardPE', 'N/A')}",
        "市净率": f"{info.get('priceToBook', 'N/A')}",
        "股息率": f"{info.get('dividendYield', 0) * 100:.2f}%",
        "Beta": f"{info.get('beta', 'N/A')}",
    }
    if not financials.empty:
        try:
            _rev_col = None
            for _col in ["营业总收入", "营业收入"]:
                if _col in financials.columns:
                    _rev_col = _col
                    break
            if _rev_col and len(financials) > 0:
                metrics["最新营收"] = f"{financials[_rev_col].iloc[0]:,.2f} 元"
            if "净利润" in financials.columns and len(financials) > 0:
                metrics["最新净利润"] = f"{financials['净利润'].iloc[0]:,.2f} 元"
            for _col in ["营业利润", "营业总收入", "营业收入"]:
                if _col in financials.columns and len(financials) > 0:
                    metrics["营业利润"] = f"{financials[_col].iloc[0]:,.2f} 元"
                    break
            if _rev_col and "营业成本" in financials.columns and len(financials) > 0:
                revenue, cost = financials[_rev_col].iloc[0], financials["营业成本"].iloc[0]
                if revenue > 0:
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
        for col in ["流动资产", "流动负债", "资产总计", "负债合计", "存货", "货币资金", "股东权益"]:
            if col in balance_sheet.columns and len(balance_sheet) > 0:
                val = balance_sheet[col].iloc[0]
                metrics[col] = f"{val:,.2f} 元" if pd.notna(val) else "N/A"
    except Exception as e:
        logger.debug(f"提取资产负债表指标时出错: {str(e)[:50]}")
    return metrics


def _extract_cashflow_metrics(cashflow: pd.DataFrame) -> dict[str, str]:
    """从现金流量表提取关键指标"""
    metrics = {}
    if cashflow.empty:
        return metrics
    try:
        for col in ["经营活动现金流量净额", "投资活动现金流量净额", "筹资活动现金流量净额"]:
            if col in cashflow.columns and len(cashflow) > 0:
                val = cashflow[col].iloc[0]
                metrics[col] = f"{val:,.2f} 元" if pd.notna(val) else "N/A"
    except Exception as e:
        logger.debug(f"提取现金流量表指标时出错: {str(e)[:50]}")
    return metrics


def _calculate_technical_indicators(hist: pd.DataFrame) -> dict[str, str]:
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