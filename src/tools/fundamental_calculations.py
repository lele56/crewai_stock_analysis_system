# src/tools/fundamental_calculations.py
"""
基本面计算模块
包含DCF估值、增长趋势分析、基本面评分等纯计算函数
"""
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def calculate_dcf_valuation(data: Dict) -> Optional[Dict[str, Any]]:
    """计算DCF估值"""
    try:
        current_fcf = data.get('free_cash_flow', 0)
        growth_rate = data.get('growth_rate', 0.05)
        discount_rate = data.get('discount_rate', 0.10)
        terminal_growth_rate = 0.03

        if current_fcf <= 0:
            return None

        fcf_projections = [current_fcf * (1 + growth_rate) ** year for year in range(1, 6)]
        present_values = [fcf / ((1 + discount_rate) ** (i + 1)) for i, fcf in enumerate(fcf_projections)]

        terminal_fcf = fcf_projections[-1] * (1 + terminal_growth_rate)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth_rate)
        terminal_pv = terminal_value / ((1 + discount_rate) ** 5)

        total_value = sum(present_values) + terminal_pv

        return {
            'fcf_projections': fcf_projections,
            'present_values': present_values,
            'terminal_value': terminal_value,
            'total_value': total_value,
            'assumptions': {
                'growth_rate': growth_rate,
                'discount_rate': discount_rate,
                'terminal_growth_rate': terminal_growth_rate
            }
        }

    except Exception as e:
        logger.error(f"DCF估值计算失败: {str(e)}")
        return None


def analyze_growth_trend(data: Dict) -> Optional[Dict[str, Any]]:
    """分析增长趋势"""
    try:
        historical_revenue = data.get('historical_revenue', [])
        if len(historical_revenue) < 3:
            return None

        revenue_growth_rates = []
        for i in range(1, len(historical_revenue)):
            growth_rate = (historical_revenue[i] - historical_revenue[i-1]) / historical_revenue[i-1] * 100
            revenue_growth_rates.append(growth_rate)

        avg_growth_rate = sum(revenue_growth_rates) / len(revenue_growth_rates)
        trend = '稳定增长' if all(g > 0 for g in revenue_growth_rates[-3:]) else '波动增长'

        return {
            'revenue_growth_rates': revenue_growth_rates,
            'average_growth_rate': avg_growth_rate,
            'trend': trend
        }

    except Exception as e:
        logger.error(f"增长趋势分析失败: {str(e)}")
        return None


def calculate_fundamental_score(results: Dict) -> float:
    """计算基本面综合评分"""
    score = 50.0

    if 'valuation_analysis' in results:
        valuation = results['valuation_analysis']
        if 'pe_analysis' in valuation:
            pe_valuation = valuation['pe_analysis']['relative_valuation']
            if pe_valuation == '低估':
                score += 15
            elif pe_valuation == '合理':
                score += 10
            elif pe_valuation == '高估':
                score += 5

    if 'growth_analysis' in results:
        growth = results['growth_analysis']
        if 'revenue_growth' in growth:
            rev_rate = growth['revenue_growth']['rate']
            if rev_rate > 20:
                score += 25
            elif rev_rate > 10:
                score += 20
            elif rev_rate > 5:
                score += 15
            else:
                score += 10

    if 'quality_analysis' in results:
        quality = results['quality_analysis']
        if 'profitability' in quality:
            roe = quality['profitability']['roe']
            if roe > 15:
                score += 25
            elif roe > 10:
                score += 20
            elif roe > 5:
                score += 15
            else:
                score += 10

    if 'financial_health' in results:
        health = results['financial_health']
        if 'liquidity' in health:
            current_ratio = health['liquidity']['current_ratio']
            if current_ratio > 2:
                score += 15
            elif current_ratio > 1.5:
                score += 10
            elif current_ratio > 1:
                score += 5

    return min(100, max(0, score))


def generate_key_findings(results: Dict) -> str:
    """生成关键发现"""
    findings = []
    if 'valuation_analysis' in results:
        pe_analysis = results['valuation_analysis'].get('pe_analysis', {})
        if pe_analysis:
            findings.append(f"估值水平{pe_analysis.get('relative_valuation', '未知')}")
    if 'growth_analysis' in results:
        rev = results['growth_analysis'].get('revenue_growth', {})
        if rev:
            findings.append(f"营收增长{rev.get('assessment', '未知')}")
    if 'quality_analysis' in results:
        roe = results['quality_analysis'].get('profitability', {})
        if roe:
            findings.append(f"盈利能力{roe.get('roe_assessment', '未知')}")
    return "；".join(findings) if findings else "无明显特征"