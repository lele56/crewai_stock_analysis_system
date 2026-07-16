# src/tools/technical_indicators.py
"""技术指标计算模块
包含各类技术指标的纯计算函数：趋势指标、动量指标、波动率指标、成交量指标
"""

from typing import Any

import numpy as np
import pandas as pd


def calculate_ma(prices: pd.Series, period: int) -> pd.Series:
    """计算移动平均线"""
    return prices.rolling(window=period).mean()


def calculate_macd(
    prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """计算MACD指标"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    prices: pd.Series, period: int = 20, std_dev: float = 2
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """计算布林带"""
    ma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    return upper, ma, lower


def calculate_sar(
    high: pd.Series, low: pd.Series, close: pd.Series, acceleration: float = 0.02, maximum: float = 0.2
) -> pd.Series:
    """计算抛物线SAR"""
    sar = pd.Series(index=close.index, dtype=float)
    sar.iloc[0] = low.iloc[0]
    ep = low.iloc[0]
    af = acceleration
    pos_trend = True

    for i in range(1, len(close)):
        if pos_trend:
            sar.iloc[i] = sar.iloc[i - 1] + af * (ep - sar.iloc[i - 1])
            if low.iloc[i] < sar.iloc[i]:
                pos_trend = False
                sar.iloc[i] = ep
                ep = high.iloc[i]
                af = acceleration
            else:
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + acceleration, maximum)
        else:
            sar.iloc[i] = sar.iloc[i - 1] + af * (ep - sar.iloc[i - 1])
            if high.iloc[i] > sar.iloc[i]:
                pos_trend = True
                sar.iloc[i] = ep
                ep = low.iloc[i]
                af = acceleration
            else:
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + acceleration, maximum)

    return sar


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """计算RSI指标"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_stochastic(
    high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3
) -> tuple[pd.Series, pd.Series]:
    """计算随机指标"""
    lowest_low = high.rolling(window=k_period).min()
    highest_high = low.rolling(window=k_period).max()
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=d_period).mean()
    return k_percent, d_percent


def calculate_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """计算威廉指标"""
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    return -100 * ((highest_high - close) / (highest_high - lowest_low))


def calculate_cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """计算商品通道指标"""
    tp = (high + low + close) / 3
    sma_tp = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.fabs(x - x.mean()).mean())
    return (tp - sma_tp) / (0.015 * mad)


def calculate_momentum(prices: pd.Series, period: int = 10) -> pd.Series:
    """计算动量指标"""
    return prices.diff(period)


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """计算平均真实范围"""
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    tr = np.maximum(high_low, np.maximum(high_close, low_close))
    return tr.rolling(window=period).mean()


def calculate_historical_volatility(prices: pd.Series, period: int = 20) -> pd.Series:
    """计算历史波动率"""
    returns = np.log(prices / prices.shift(1))
    volatility = returns.rolling(window=period).std() * np.sqrt(252)
    return volatility * 100


def calculate_volume_change(volume: pd.Series) -> pd.Series:
    """计算成交量变化率"""
    return volume.pct_change() * 100


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """计算能量潮指标"""
    obv = np.where(close > close.shift(), volume, np.where(close < close.shift(), -volume, 0))
    return pd.Series(obv, index=close.index).cumsum()


def calculate_accumulation_distribution(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
) -> pd.Series:
    """计算累积/派发线"""
    clv = ((close - low) - (high - close)) / (high - low)
    clv = clv.fillna(0)
    ad = clv * volume
    return ad.cumsum()


def calculate_all_trend_indicators(df: pd.DataFrame) -> dict[str, Any]:
    """计算所有趋势指标"""
    indicators = {}
    indicators["ma_5"] = calculate_ma(df["Close"], 5)
    indicators["ma_10"] = calculate_ma(df["Close"], 10)
    indicators["ma_20"] = calculate_ma(df["Close"], 20)
    indicators["ma_50"] = calculate_ma(df["Close"], 50)
    indicators["ma_200"] = calculate_ma(df["Close"], 200)
    macd, signal, histogram = calculate_macd(df["Close"])
    indicators["macd"] = {"macd_line": macd, "signal_line": signal, "histogram": histogram}
    upper, middle, lower = calculate_bollinger_bands(df["Close"])
    indicators["bollinger_bands"] = {"upper": upper, "middle": middle, "lower": lower}
    indicators["sar"] = calculate_sar(df["High"], df["Low"], df["Close"])
    return indicators


def calculate_all_momentum_indicators(df: pd.DataFrame) -> dict[str, Any]:
    """计算所有动量指标"""
    indicators = {}
    indicators["rsi"] = calculate_rsi(df["Close"])
    k, d = calculate_stochastic(df["High"], df["Low"], df["Close"])
    indicators["stochastic"] = {"k_percent": k, "d_percent": d}
    indicators["williams_r"] = calculate_williams_r(df["High"], df["Low"], df["Close"])
    indicators["cci"] = calculate_cci(df["High"], df["Low"], df["Close"])
    indicators["momentum"] = calculate_momentum(df["Close"])
    return indicators


def calculate_all_volatility_indicators(df: pd.DataFrame) -> dict[str, Any]:
    """计算所有波动率指标"""
    indicators = {}
    indicators["atr"] = calculate_atr(df["High"], df["Low"], df["Close"])
    upper, middle, lower = calculate_bollinger_bands(df["Close"])
    indicators["bollinger_bandwidth"] = ((upper - lower) / middle) * 100
    indicators["historical_volatility"] = calculate_historical_volatility(df["Close"])
    return indicators


def calculate_all_volume_indicators(df: pd.DataFrame) -> dict[str, Any]:
    """计算所有成交量指标"""
    indicators = {}
    indicators["volume_ma_20"] = calculate_ma(df["Volume"], 20)
    indicators["volume_change"] = calculate_volume_change(df["Volume"])
    indicators["obv"] = calculate_obv(df["Close"], df["Volume"])
    indicators["accumulation_distribution"] = calculate_accumulation_distribution(
        df["High"], df["Low"], df["Close"], df["Volume"]
    )
    return indicators
