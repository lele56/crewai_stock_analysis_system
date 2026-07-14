# src/tools/technical_tools.py
"""
技术分析工具包
TechnicalAnalysisTool 主类，负责数据解析、指标计算编排和报告生成。
具体指标计算函数见 technical_indicators.py，图表生成见 technical_charting.py。
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import logging

from src.tools.reporting_tools import BaseTool
from src.tools.technical_indicators import (
    calculate_all_trend_indicators,
    calculate_all_momentum_indicators,
    calculate_all_volatility_indicators,
    calculate_all_volume_indicators,
)
from src.tools.technical_charting import ChartingTool

logger = logging.getLogger(__name__)

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class TechnicalAnalysisTool(BaseTool):
    """技术分析工具"""

    name: str = "Technical Analysis Tool"
    description: str = "计算各种技术指标并生成技术分析报告"

    def _run(self, price_data: str, analysis_type: str = "comprehensive") -> str:
        """执行技术分析"""
        try:
            logger.debug(f"[技术分析] 开始分析，分析类型: {analysis_type}")
            df = self._parse_price_data(price_data)
            if df is None or df.empty:
                raise ValueError("价格数据为空或无效")
            df = self._ensure_required_columns(df)

            results = {}
            if analysis_type in ["comprehensive", "trend"]:
                results['trend_indicators'] = self._calculate_trend_indicators(df)
            if analysis_type in ["comprehensive", "momentum"]:
                results['momentum_indicators'] = self._calculate_momentum_indicators(df)
            if analysis_type in ["comprehensive", "volatility"]:
                results['volatility_indicators'] = self._calculate_volatility_indicators(df)
            if analysis_type in ["comprehensive", "volume"]:
                results['volume_indicators'] = self._calculate_volume_indicators(df)

            report = self._generate_technical_report(df, results, analysis_type)
            logger.info("技术分析完成")
            return report

        except Exception as e:
            error_msg = f"技术分析失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _parse_price_data(self, price_data: str) -> Optional[pd.DataFrame]:
        """解析价格数据，支持JSON和股票代码"""
        import json
        try:
            data = json.loads(price_data)
            df = pd.DataFrame(data)
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
            return df
        except json.JSONDecodeError:
            return self._try_fetch_stock_data(price_data)

    def _try_fetch_stock_data(self, stock_code: str) -> Optional[pd.DataFrame]:
        """尝试通过AkShare获取股票数据"""
        try:
            from src.tools.akshare_tools import AkShareTool
            ak_tool = AkShareTool()
            stock_data = ak_tool._get_stock_history_data(stock_code)
            return stock_data if stock_data is not None and not stock_data.empty else None
        except Exception:
            return None

    def _ensure_required_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """确保DataFrame包含所有必要列"""
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            if col not in df.columns:
                df[col] = df['Close'] if 'Close' in df.columns else pd.Series(np.random.normal(100, 2, len(df)), index=df.index)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
        return df

    def _calculate_trend_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算趋势指标"""
        return calculate_all_trend_indicators(df)

    def _calculate_momentum_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算动量指标"""
        return calculate_all_momentum_indicators(df)

    def _calculate_volatility_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算波动率指标"""
        return calculate_all_volatility_indicators(df)

    def _calculate_volume_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算成交量指标"""
        return calculate_all_volume_indicators(df)

    def _generate_technical_report(self, df: pd.DataFrame, results: Dict, analysis_type: str) -> str:
        """生成技术分析报告"""
        report = f"# 技术分析报告\n\n"
        report += f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"**数据期间**: {df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}\n"
        report += f"**当前价格**: ${df['Close'].iloc[-1]:.2f}\n\n"

        if 'trend_indicators' in results:
            report += self._generate_trend_analysis(df, results['trend_indicators'])
        if 'momentum_indicators' in results:
            report += self._generate_momentum_analysis(results['momentum_indicators'])
        if 'volatility_indicators' in results:
            report += self._generate_volatility_analysis(results['volatility_indicators'])
        if 'volume_indicators' in results:
            report += self._generate_volume_analysis(df, results['volume_indicators'])

        report += self._generate_trading_recommendations(results)
        return report

    def _generate_trend_analysis(self, df: pd.DataFrame, indicators: Dict) -> str:
        """生成趋势分析"""
        current_price = df['Close'].iloc[-1]
        ma_20 = indicators['ma_20'].iloc[-1]
        ma_50 = indicators['ma_50'].iloc[-1]

        analysis = "## 趋势分析\n\n### 移动平均线\n"
        analysis += f"- 当前价格: ${current_price:.2f}\n- MA20: ${ma_20:.2f}\n- MA50: ${ma_50:.2f}\n"
        if current_price > ma_20 > ma_50:
            analysis += "- **趋势判断**: 强势上涨\n"
        elif current_price > ma_20 and ma_20 < ma_50:
            analysis += "- **趋势判断**: 短期反弹\n"
        elif current_price < ma_20 < ma_50:
            analysis += "- **趋势判断**: 弱势下跌\n"
        else:
            analysis += "- **趋势判断**: 震荡整理\n"

        macd_data = indicators['macd']
        analysis += "\n### MACD指标\n"
        analysis += f"- MACD线: {macd_data['macd_line'].iloc[-1]:.3f}\n"
        analysis += f"- 信号线: {macd_data['signal_line'].iloc[-1]:.3f}\n"
        analysis += "- **信号**: 看涨信号\n" if macd_data['macd_line'].iloc[-1] > macd_data['signal_line'].iloc[-1] else "- **信号**: 看跌信号\n"
        return analysis

    def _generate_momentum_analysis(self, indicators: Dict) -> str:
        """生成动量分析"""
        rsi_current = indicators['rsi'].iloc[-1]
        analysis = "\n## 动量分析\n\n### RSI指标\n"
        analysis += f"- RSI(14): {rsi_current:.1f}\n"
        if rsi_current > 70:
            analysis += "- **状态**: 超买区域\n"
        elif rsi_current < 30:
            analysis += "- **状态**: 超卖区域\n"
        else:
            analysis += "- **状态**: 正常区域\n"

        stochastic_data = indicators['stochastic']
        analysis += "\n### 随机指标\n"
        analysis += f"- %K: {stochastic_data['k_percent'].iloc[-1]:.1f}\n"
        analysis += f"- %D: {stochastic_data['d_percent'].iloc[-1]:.1f}\n"
        if stochastic_data['k_percent'].iloc[-1] > 80:
            analysis += "- **信号**: 超买信号\n"
        elif stochastic_data['k_percent'].iloc[-1] < 20:
            analysis += "- **信号**: 超卖信号\n"
        return analysis

    def _generate_volatility_analysis(self, indicators: Dict) -> str:
        """生成波动率分析"""
        atr_current = indicators['atr'].iloc[-1]
        bb_width = indicators['bollinger_bandwidth'].iloc[-1]
        analysis = "\n## 波动率分析\n\n### 平均真实范围 (ATR)\n"
        analysis += f"- ATR(14): {atr_current:.2f}\n"
        analysis += "\n### 布林带\n"
        analysis += f"- 带宽: {bb_width:.1f}%\n"
        if bb_width > 20:
            analysis += "- **波动状态**: 高波动\n"
        elif bb_width < 10:
            analysis += "- **波动状态**: 低波动\n"
        else:
            analysis += "- **波动状态**: 正常波动\n"
        return analysis

    def _generate_volume_analysis(self, df: pd.DataFrame, indicators: Dict) -> str:
        """生成成交量分析"""
        volume_change = indicators['volume_change'].iloc[-1]
        analysis = "\n## 成交量分析\n\n### 成交量变化\n"
        analysis += f"- 成交量变化率: {volume_change:+.1f}%\n"
        if volume_change > 50:
            analysis += "- **成交量状态**: 显著放量\n"
        elif volume_change < -30:
            analysis += "- **成交量状态**: 明显缩量\n"
        else:
            analysis += "- **成交量状态**: 正常水平\n"

        obv_current = indicators['obv'].iloc[-1]
        obv_prev = indicators['obv'].iloc[-2]
        analysis += "\n### 能量潮指标\n"
        analysis += "- **资金流向**: 资金流入\n" if obv_current > obv_prev else "- **资金流向**: 资金流出\n"
        return analysis

    def _generate_trading_recommendations(self, results: Dict) -> str:
        """生成交易建议"""
        recommendations = "\n## 综合交易建议\n\n"
        signals = []
        if 'trend_indicators' in results:
            macd_data = results['trend_indicators']['macd']
            if macd_data['macd_line'].iloc[-1] > macd_data['signal_line'].iloc[-1]:
                signals.append("MACD看涨信号")
            else:
                signals.append("MACD看跌信号")
        if 'momentum_indicators' in results:
            rsi = results['momentum_indicators']['rsi'].iloc[-1]
            if rsi > 70:
                signals.append("RSI超买警告")
            elif rsi < 30:
                signals.append("RSI超卖机会")

        buy_signals = len([s for s in signals if '看涨' in s or '机会' in s])
        sell_signals = len([s for s in signals if '看跌' in s or '警告' in s])

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