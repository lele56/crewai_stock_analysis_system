# src/tools/schemas.py
"""数据源 Schema 定义 — 将各数据源原始字段映射到统一字段名

接口变更时只需修改此文件，下游代码不受影响。
"""

from datetime import datetime
from typing import Any

import pandas as pd

# ═══════════════════════════════════════════════════════════════════
# 腾讯行情 API (qt.gtimg.cn) — 响应以 ~ 分隔
# 接口变更时：修改此字典的索引值即可
# ═══════════════════════════════════════════════════════════════════

TENCENT_QUOTE_SCHEMA = {
    "name": 0,
    "code": 1,
    "current_price": 3,
    "yesterday_close": 4,
    "open": 5,
    "volume": 6,
    "high": 33,
    "low": 34,
    "pe": 39,
    "market_cap": 44,          # 需要 * 1e8 转为元
    "pb": 46,
    "week52_high": 47,
    "week52_low": 48,
}

# ═══════════════════════════════════════════════════════════════════
# 新浪个股行情 (hq.sinajs.cn) — 响应以 , 分隔
# ═══════════════════════════════════════════════════════════════════

SINA_SPOT_SCHEMA = {
    "name": 0,
    "open": 1,
    "yesterday_close": 2,
    "current_price": 3,
    "high": 4,
    "low": 5,
    "volume": 8,
    "amount": 9,
}

# ═══════════════════════════════════════════════════════════════════
# 腾讯 K 线 (web.ifzq.gtimg.cn) — JSON 响应
# ═══════════════════════════════════════════════════════════════════

TENCENT_KLINE_SCHEMA = {
    "date": 0,
    "open": 1,
    "close": 2,
    "high": 3,
    "low": 4,
    "volume": 5,
}

# ═══════════════════════════════════════════════════════════════════
# akshare K 线 — DataFrame 列名映射
# ═══════════════════════════════════════════════════════════════════

AKSHARE_KLINE_RENAME = {
    "开盘": "Open",
    "收盘": "Close",
    "最高": "High",
    "最低": "Low",
    "成交量": "Volume",
    "日期": "Date",
    "date": "Date",
}

# ═══════════════════════════════════════════════════════════════════
# TickFlow K 线 — DataFrame 列名映射
# ═══════════════════════════════════════════════════════════════════

TICKFLOW_KLINE_RENAME = {
    "open": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "volume": "Volume",
}


# ═══════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════

def field(schema: dict[str, int], fields: list[str], key: str, default: Any = None) -> Any:
    """按 schema 安全读取字段，越界返回 default"""
    idx = schema.get(key, -1)
    if 0 <= idx < len(fields):
        return fields[idx]
    return default


def rename_df(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """安全重命名 DataFrame 列，仅重命名存在的列"""
    existing = {k: v for k, v in mapping.items() if k in df.columns}
    return df.rename(columns=existing) if existing else df


def normalize_kline_df(df: pd.DataFrame, required_cols: list[str] | None = None) -> pd.DataFrame:
    """标准化 K 线 DataFrame：确保包含 Open/High/Low/Close/Volume 列"""
    if df.empty:
        return df
    cols = required_cols or ["Open", "High", "Low", "Close", "Volume"]
    for col in cols:
        if col not in df.columns:
            df[col] = 0.0
    if "Date" not in df.columns and df.index.name != "Date":
        if isinstance(df.index, pd.DatetimeIndex):
            df["Date"] = df.index
        else:
            df["Date"] = pd.date_range(end=datetime.now(), periods=len(df), freq="D")
    if df.index.name != "Date" and "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
    return df[cols]