# src/tools/technical_tools.py
"""技术分析工具包
TechnicalAnalysisTool 主类，负责数据解析、指标计算编排和报告生成。
具体指标计算函数见 technical_indicators.py，图表生成见 technical_charting.py。
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

from src.tools.reporting_tools import BaseTool
from src.tools.technical_indicators import (
    calculate_all_momentum_indicators,
    calculate_all_trend_indicators,
    calculate_all_volatility_indicators,
    calculate_all_volume_indicators,
)

logger = logging.getLogger(__name__)

# 工具级缓存：避免同一参数重复计算
_cache: dict[str, str] = {}


def _configure_matplotlib() -> None:
    """延迟配置 matplotlib 后端和字体（首次使用时初始化）"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False


class TechnicalAnalysisTool(BaseTool):
    """技术分析工具"""

    name: str = "Technical Analysis Tool"
    description: str = (
        "计算技术指标并生成分析报告。analysis_type 为: comprehensive(综合), trend(趋势), "
        "momentum(动量), volatility(波动率), volume(成交量)。price_data 传股票代码(如600519)或JSON价格数据。"
    )

    def _run(self, price_data: str, analysis_type: str = "comprehensive") -> str:
        """执行技术分析"""
        cache_key = f"{price_data[:50]}|{analysis_type}"
        if cache_key in _cache:
            logger.debug(f"技术分析命中缓存: {price_data[:30]}...")
            return _cache[cache_key]

        try:
            logger.debug(f"[技术分析] 开始分析，分析类型: {analysis_type}")
            df = self._parse_price_data(price_data)
            if df is None or df.empty:
                raise ValueError("价格数据为空或无效")
            df = self._ensure_required_columns(df)

            results = {}
            if analysis_type in ["comprehensive", "trend"]:
                results["trend_indicators"] = self._calculate_trend_indicators(df)
            if analysis_type in ["comprehensive", "momentum"]:
                results["momentum_indicators"] = self._calculate_momentum_indicators(df)
            if analysis_type in ["comprehensive", "volatility"]:
                results["volatility_indicators"] = self._calculate_volatility_indicators(df)
            if analysis_type in ["comprehensive", "volume"]:
                results["volume_indicators"] = self._calculate_volume_indicators(df)

            report = self._generate_technical_report(df, results, analysis_type)
            _cache[cache_key] = report
            logger.info("技术分析完成")
            return report

        except Exception as e:
            error_msg = f"技术分析失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _parse_price_data(self, price_data: str) -> pd.DataFrame | None:
        """解析价格数据，支持多种JSON格式和股票代码"""
        import json

        logger.debug(f"技术分析输入: {price_data[:200]}...")

        try:
            data = json.loads(price_data)
        except (json.JSONDecodeError, TypeError):
            return self._try_fetch_stock_data(price_data)

        try:
            # 格式1: {"Close": [100,101,...], "Open": [...], ...}  → 列式dict
            if isinstance(data, dict) and any(isinstance(v, list) for v in data.values()):
                return pd.DataFrame(data)
            # 格式2: [{"Close":100,...}, {"Close":101,...}]  → 记录列表
            if isinstance(data, list) and all(isinstance(row, dict) for row in data):
                df = pd.DataFrame(data)
                if "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"])
                    df.set_index("Date", inplace=True)
                return df
            # 格式3: 纯文本/数字可能是股票代码
            if isinstance(data, str) and len(data) <= 10:
                return self._try_fetch_stock_data(data)
            if isinstance(data, (int, float)):
                return self._try_fetch_stock_data(str(int(data)))
            # 格式4: LLM包装的JSON → 提取股票代码
            if isinstance(data, dict):
                ticker = data.get("price_data", "") or data.get("ticker", "") or data.get("symbol", "")
                if ticker and isinstance(ticker, str) and len(ticker) <= 10:
                    return self._try_fetch_stock_data(ticker)
            return None
        except Exception:
            return self._try_fetch_stock_data(price_data)

    def _try_fetch_stock_data(self, stock_code: str) -> pd.DataFrame | None:
        """尝试通过缓存或 API 获取K线数据"""
        import time
        code = stock_code.strip()
        try:
            if len(code) > 10:
                import re
                match = re.search(r'(?:sh|sz|SH|SZ)(\d{6})\b', code)
                if not match:
                    match = re.search(r'(?<!\d)(\d{6})(?!\d)', code)
                if match:
                    code = match.group(1)
                else:
                    logger.info(f"无法从文本中提取股票代码: {code[:100]}")
                    return None

            # 优先读缓存
            from src.tools.akshare_data_cache import load_kline_from_cache
            df = load_kline_from_cache(code)
            if df is not None and not df.empty:
                logger.debug(f"从缓存加载K线数据: {code} ({len(df)} 条)")
                return df

            logger.info(f"缓存未命中，API 获取: {code}")
            from src.tools.akshare_data_parser import get_stock_history_data
            for _attempt in range(3):
                result = get_stock_history_data(code, "1y")
                if result is not None and not result.empty:
                    return result
                time.sleep(1)
            logger.warning(f"获取股票数据失败: {code}，3次尝试均返回空")
            return None
        except Exception as e:
            logger.warning(f"获取股票数据异常: {code}，错误: {e}")
            return None

    def _ensure_required_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """确保DataFrame包含所有必要列"""
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        for col in required_columns:
            if col not in df.columns:
                df[col] = (
                    df["Close"]
                    if "Close" in df.columns
                    else pd.Series(np.random.normal(100, 2, len(df)), index=df.index)
                )
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].ffill().bfill()
        return df

    def _calculate_trend_indicators(self, df: pd.DataFrame) -> dict[str, Any]:
        """计算趋势指标"""
        return calculate_all_trend_indicators(df)

    def _calculate_momentum_indicators(self, df: pd.DataFrame) -> dict[str, Any]:
        """计算动量指标"""
        return calculate_all_momentum_indicators(df)

    def _calculate_volatility_indicators(self, df: pd.DataFrame) -> dict[str, Any]:
        """计算波动率指标"""
        return calculate_all_volatility_indicators(df)

    def _calculate_volume_indicators(self, df: pd.DataFrame) -> dict[str, Any]:
        """计算成交量指标"""
        return calculate_all_volume_indicators(df)

    def _generate_technical_report(self, df: pd.DataFrame, results: dict, analysis_type: str) -> str:
        """生成技术分析报告（精简版，适配所有模型）"""
        lines = [
            f"技术分析: {analysis_type}",
            f"数据期间: {df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}, 当前价格: ¥{df['Close'].iloc[-1]:.2f}",
        ]

        if "trend_indicators" in results:
            lines.append(self._generate_trend_analysis(df, results["trend_indicators"]))
        if "momentum_indicators" in results:
            lines.append(self._generate_momentum_analysis(results["momentum_indicators"]))
        if "volatility_indicators" in results:
            lines.append(self._generate_volatility_analysis(results["volatility_indicators"]))
        if "volume_indicators" in results:
            lines.append(self._generate_volume_analysis(df, results["volume_indicators"]))
        if "trading_signals" in results:
            signals = results["trading_signals"]
            lines.append(f"交易信号: {signals}")

        return "\n".join(lines)

    def _generate_trend_analysis(self, df: pd.DataFrame, indicators: dict) -> str:
        """生成趋势分析（精简版）"""
        current_price = df["Close"].iloc[-1]
        ma_20 = indicators["ma_20"].iloc[-1]
        ma_50 = indicators["ma_50"].iloc[-1]

        if current_price > ma_20 > ma_50:
            trend = "强势上涨"
        elif current_price > ma_20 and ma_20 < ma_50:
            trend = "短期反弹"
        elif current_price < ma_20 < ma_50:
            trend = "弱势下跌"
        else:
            trend = "震荡整理"

        macd_data = indicators["macd"]
        macd_signal = "看涨" if macd_data["macd_line"].iloc[-1] > macd_data["signal_line"].iloc[-1] else "看跌"

        return f"趋势: {trend}, 价格: ¥{current_price:.2f}, MA20: ¥{ma_20:.2f}, MA50: ¥{ma_50:.2f}, MACD: {macd_signal}"

    def _generate_momentum_analysis(self, indicators: dict) -> str:
        """生成动量分析（精简版）"""
        rsi_current = indicators["rsi"].iloc[-1]
        if rsi_current > 70:
            rsi_state = "超买"
        elif rsi_current < 30:
            rsi_state = "超卖"
        else:
            rsi_state = "正常"

        stochastic_data = indicators["stochastic"]
        k_val = stochastic_data["k_percent"].iloc[-1]
        if k_val > 80:
            stoch_signal = "超买"
        elif k_val < 20:
            stoch_signal = "超卖"
        else:
            stoch_signal = "正常"

        return f"动量: RSI={rsi_current:.1f}({rsi_state}), K%={k_val:.1f}, D%={stochastic_data['d_percent'].iloc[-1]:.1f}({stoch_signal})"

    def _generate_volatility_analysis(self, indicators: dict) -> str:
        """生成波动率分析（精简版）"""
        atr_current = indicators["atr"].iloc[-1]
        bb_width = indicators["bollinger_bandwidth"].iloc[-1]
        if bb_width > 20:
            vol_state = "高波动"
        elif bb_width < 10:
            vol_state = "低波动"
        else:
            vol_state = "正常"
        return f"波动率: ATR={atr_current:.2f}, 布林带宽={bb_width:.1f}%({vol_state})"

    def _generate_volume_analysis(self, df: pd.DataFrame, indicators: dict) -> str:
        """生成成交量分析（精简版）"""
        volume_change = indicators["volume_change"].iloc[-1]
        if volume_change > 50:
            vol_status = "显著放量"
        elif volume_change < -30:
            vol_status = "明显缩量"
        else:
            vol_status = "正常"

        obv_current = indicators["obv"].iloc[-1]
        obv_prev = indicators["obv"].iloc[-2]
        flow = "流入" if obv_current > obv_prev else "流出"

        return f"成交量: 变化率={volume_change:+.1f}%({vol_status}), 资金{flow}"

    def _generate_trading_recommendations(self, results: dict) -> str:
        """生成交易建议"""
        recommendations = "\n## 综合交易建议\n\n"
        signals = []
        if "trend_indicators" in results:
            macd_data = results["trend_indicators"]["macd"]
            if macd_data["macd_line"].iloc[-1] > macd_data["signal_line"].iloc[-1]:
                signals.append("MACD看涨信号")
            else:
                signals.append("MACD看跌信号")
        if "momentum_indicators" in results:
            rsi = results["momentum_indicators"]["rsi"].iloc[-1]
            if rsi > 70:
                signals.append("RSI超买警告")
            elif rsi < 30:
                signals.append("RSI超卖机会")

        buy_signals = len([s for s in signals if "看涨" in s or "机会" in s])
        sell_signals = len([s for s in signals if "看跌" in s or "警告" in s])

        recommendations += "### 信号汇总\n"
        for signal in signals:
            recommendations += f"- {signal}\n"
        recommendations += "\n### 投资建议\n"
        if buy_signals > sell_signals:
            recommendations += "- **建议**: 适度看涨，可考虑逢低买入\n"
        elif sell_signals > buy_signals:
            recommendations += "- **建议**: 谨慎观望，注意风险控制\n"
        else:
            recommendations += "- **建议**: 中性观望，等待更明确信号\n"
        return recommendations