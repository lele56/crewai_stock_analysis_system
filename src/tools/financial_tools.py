# src/tools/financial_tools.py
"""金融数据工具包 - 包含财务计算等工具"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import logging

from src.tools.reporting_tools import BaseTool
from src.tools.yfinance_tool import YFinanceTool

logger = logging.getLogger(__name__)


class FinancialCalculatorTool(BaseTool):
    """金融计算器工具"""

    name: str = "Financial Calculator Tool"
    description: str = "计算各种财务指标和比率"

    def _run(self, financial_data: str, calculation_type: str = "all") -> str:
        """
        计算财务指标

        Args:
            financial_data: 财务数据（JSON格式）
            calculation_type: 计算类型 (liquidity, profitability, leverage, growth, all)

        Returns:
            财务指标计算结果
        """
        try:
            import json
            data = json.loads(financial_data)
            logger.info(f"开始计算财务指标，类型: {calculation_type}")

            results = {}

            if calculation_type in ["liquidity", "all"]:
                results['liquidity_ratios'] = self._calculate_liquidity_ratios(data)

            if calculation_type in ["profitability", "all"]:
                results['profitability_ratios'] = self._calculate_profitability_ratios(data)

            if calculation_type in ["leverage", "all"]:
                results['leverage_ratios'] = self._calculate_leverage_ratios(data)

            if calculation_type in ["growth", "all"]:
                results['growth_rates'] = self._calculate_growth_rates(data)

            report = self._generate_financial_report(results)
            logger.info("财务指标计算完成")
            return report

        except Exception as e:
            error_msg = f"财务指标计算失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _calculate_liquidity_ratios(self, data: Dict) -> Dict[str, float]:
        """计算流动性比率"""
        ratios = {}

        try:
            # 流动比率
            current_assets = data.get('current_assets', 0)
            current_liabilities = data.get('current_liabilities', 0)
            if current_liabilities > 0:
                ratios['current_ratio'] = current_assets / current_liabilities

            # 速动比率
            inventory = data.get('inventory', 0)
            quick_assets = current_assets - inventory
            if current_liabilities > 0:
                ratios['quick_ratio'] = quick_assets / current_liabilities

            # 现金比率
            cash = data.get('cash', 0)
            if current_liabilities > 0:
                ratios['cash_ratio'] = cash / current_liabilities

        except Exception as e:
            logger.error(f"计算流动性比率失败: {str(e)}")

        return ratios

    def _calculate_profitability_ratios(self, data: Dict) -> Dict[str, float]:
        """计算盈利能力比率"""
        ratios = {}

        try:
            # 毛利率
            revenue = data.get('revenue', 0)
            gross_profit = data.get('gross_profit', 0)
            if revenue > 0:
                ratios['gross_margin'] = (gross_profit / revenue) * 100

            # 净利率
            net_income = data.get('net_income', 0)
            if revenue > 0:
                ratios['net_margin'] = (net_income / revenue) * 100

            # 资产收益率
            total_assets = data.get('total_assets', 0)
            if total_assets > 0:
                ratios['roa'] = (net_income / total_assets) * 100

            # 净资产收益率
            equity = data.get('equity', 0)
            if equity > 0:
                ratios['roe'] = (net_income / equity) * 100

        except Exception as e:
            logger.error(f"计算盈利能力比率失败: {str(e)}")

        return ratios

    def _calculate_leverage_ratios(self, data: Dict) -> Dict[str, float]:
        """计算杠杆比率"""
        ratios = {}

        try:
            # 资产负债率
            total_assets = data.get('total_assets', 0)
            total_debt = data.get('total_debt', 0)
            if total_assets > 0:
                ratios['debt_to_assets'] = (total_debt / total_assets) * 100

            # 权益乘数
            equity = data.get('equity', 0)
            if equity > 0:
                ratios['equity_multiplier'] = total_assets / equity

            # 利息保障倍数
            ebit = data.get('ebit', 0)
            interest_expense = data.get('interest_expense', 0)
            if interest_expense > 0:
                ratios['interest_coverage'] = ebit / interest_expense

        except Exception as e:
            logger.error(f"计算杠杆比率失败: {str(e)}")

        return ratios

    def _calculate_growth_rates(self, data: Dict) -> Dict[str, float]:
        """计算增长率"""
        rates = {}

        try:
            # 营收增长率
            current_revenue = data.get('current_revenue', 0)
            previous_revenue = data.get('previous_revenue', 0)
            if previous_revenue > 0:
                rates['revenue_growth'] = ((current_revenue - previous_revenue) / previous_revenue) * 100

            # 净利润增长率
            current_net_income = data.get('current_net_income', 0)
            previous_net_income = data.get('previous_net_income', 0)
            if previous_net_income > 0:
                rates['net_income_growth'] = ((current_net_income - previous_net_income) / previous_net_income) * 100

            # 资产增长率
            current_assets = data.get('current_assets', 0)
            previous_assets = data.get('previous_assets', 0)
            if previous_assets > 0:
                rates['asset_growth'] = ((current_assets - previous_assets) / previous_assets) * 100

        except Exception as e:
            logger.error(f"计算增长率失败: {str(e)}")

        return rates

    def _generate_financial_report(self, results: Dict) -> str:
        """生成财务指标报告"""
        report = "# 财务指标分析报告\n\n"
        report += f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        for category, ratios in results.items():
            report += f"## {category.replace('_', ' ').title()}\n\n"

            if not ratios:
                report += "无可用数据\n\n"
                continue

            for ratio_name, value in ratios.items():
                ratio_name_chinese = self._translate_ratio_name(ratio_name)
                if 'growth' in ratio_name or 'margin' in ratio_name or ratio_name in ['roa', 'roe']:
                    report += f"- **{ratio_name_chinese}**: {value:.2f}%\n"
                else:
                    report += f"- **{ratio_name_chinese}**: {value:.2f}\n"

            report += "\n"

        # 添加分析建议
        report += self._generate_analysis_suggestions(results)

        return report

    def _translate_ratio_name(self, ratio_name: str) -> str:
        """翻译财务指标名称"""
        translations = {
            'current_ratio': '流动比率',
            'quick_ratio': '速动比率',
            'cash_ratio': '现金比率',
            'gross_margin': '毛利率',
            'net_margin': '净利率',
            'roa': '资产收益率',
            'roe': '净资产收益率',
            'debt_to_assets': '资产负债率',
            'equity_multiplier': '权益乘数',
            'interest_coverage': '利息保障倍数',
            'revenue_growth': '营收增长率',
            'net_income_growth': '净利润增长率',
            'asset_growth': '资产增长率'
        }
        return translations.get(ratio_name, ratio_name)

    def _generate_analysis_suggestions(self, results: Dict) -> str:
        """生成分析建议"""
        suggestions = "## 分析建议\n\n"

        # 流动性分析
        liquidity = results.get('liquidity_ratios', {})
        current_ratio = liquidity.get('current_ratio', 0)
        if current_ratio < 1:
            suggestions += "- **流动性风险**: 流动比率低于1，可能存在短期偿债压力\n"
        elif current_ratio > 2:
            suggestions += "- **资金利用**: 流动比率较高，可考虑提高资金使用效率\n"

        # 盈利能力分析
        profitability = results.get('profitability_ratios', {})
        net_margin = profitability.get('net_margin', 0)
        if net_margin < 5:
            suggestions += "- **盈利能力**: 净利率较低，需要提高盈利能力\n"
        elif net_margin > 20:
            suggestions += "- **盈利能力**: 净利率表现优秀，具有较强的竞争优势\n"

        # 杠杆分析
        leverage = results.get('leverage_ratios', {})
        debt_to_assets = leverage.get('debt_to_assets', 0)
        if debt_to_assets > 70:
            suggestions += "- **财务风险**: 资产负债率较高，财务风险需要关注\n"
        elif debt_to_assets < 30:
            suggestions += "- **财务保守**: 资产负债率较低，可考虑适度增加财务杠杆\n"

        # 增长分析
        growth = results.get('growth_rates', {})
        revenue_growth = growth.get('revenue_growth', 0)
        if revenue_growth > 20:
            suggestions += "- **增长强劲**: 营收增长率较高，业务发展良好\n"
        elif revenue_growth < 0:
            suggestions += "- **增长停滞**: 营收出现负增长，需要关注业务发展\n"

        return suggestions


# 使用示例
if __name__ == "__main__":
    from src.tools.akshare_tools import AkShareTool
    ak_tool = AkShareTool()
    logger.info("=== 测试AkShare工具 ===")
    result = ak_tool._run("sh600000", "6mo")
    logger.info(result[:500] + "...")

    calc_tool = FinancialCalculatorTool()
    logger.info("=== 测试金融计算器工具 ===")
    test_data = {
        "current_assets": 1000000, "current_liabilities": 500000, "inventory": 200000,
        "cash": 300000, "revenue": 2000000, "gross_profit": 800000,
        "net_income": 400000, "total_assets": 3000000, "equity": 1500000, "total_debt": 1000000
    }
    import json
    calc_result = calc_tool._run(json.dumps(test_data))
    logger.info(calc_result)