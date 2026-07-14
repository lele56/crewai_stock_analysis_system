# src/tools/fundamental_tools.py
"""基本面分析工具 - FundamentalAnalysisTool 主类"""
from typing import Dict, Any, Optional
import json
from datetime import datetime
import logging

from src.tools.reporting_tools import BaseTool
from src.tools.fundamental_calculations import (
    calculate_dcf_valuation,
    analyze_growth_trend,
    calculate_fundamental_score,
    generate_key_findings,
)

logger = logging.getLogger(__name__)


class FundamentalAnalysisTool(BaseTool):
    """基本面分析工具"""

    name: str = "Fundamental Analysis Tool"
    description: str = "进行公司基本面分析和价值评估"

    def _run(self, company_data: str, analysis_type: str = "comprehensive") -> str:
        """执行基本面分析"""
        try:
            logger.info(f"开始基本面分析，类型: {analysis_type}")
            data = json.loads(company_data)

            results = {}
            if analysis_type in ["comprehensive", "valuation"]:
                results['valuation_analysis'] = self._analyze_valuation(data)
            if analysis_type in ["comprehensive", "growth"]:
                results['growth_analysis'] = self._analyze_growth(data)
            if analysis_type in ["comprehensive", "quality"]:
                results['quality_analysis'] = self._analyze_quality(data)
            if analysis_type in ["comprehensive", "financial_health"]:
                results['financial_health'] = self._analyze_financial_health(data)

            report = self._generate_fundamental_report(results, analysis_type)
            logger.info("基本面分析完成")
            return report

        except Exception as e:
            logger.error(f"基本面分析失败: {str(e)}")
            return f"基本面分析失败: {str(e)}"

    def _analyze_valuation(self, data: Dict) -> Dict[str, Any]:
        """分析估值水平"""
        valuation = {}
        try:
            pe_ratio = data.get('pe_ratio', 0)
            industry_pe = data.get('industry_pe', 0)
            if pe_ratio > 0 and industry_pe > 0:
                valuation['pe_analysis'] = {
                    'current_pe': pe_ratio, 'industry_pe': industry_pe,
                    'relative_valuation': '高估' if pe_ratio > industry_pe * 1.2 else '低估' if pe_ratio < industry_pe * 0.8 else '合理'
                }
            pb_ratio = data.get('pb_ratio', 0)
            industry_pb = data.get('industry_pb', 0)
            if pb_ratio > 0 and industry_pb > 0:
                valuation['pb_analysis'] = {
                    'current_pb': pb_ratio, 'industry_pb': industry_pb,
                    'relative_valuation': '高估' if pb_ratio > industry_pb * 1.2 else '低估' if pb_ratio < industry_pb * 0.8 else '合理'
                }
            ps_ratio = data.get('ps_ratio', 0)
            if ps_ratio > 0:
                valuation['ps_analysis'] = {'current_ps': ps_ratio, 'assessment': '较高' if ps_ratio > 5 else '合理' if ps_ratio > 1 else '较低'}
            dcf_value = calculate_dcf_valuation(data)
            if dcf_value:
                valuation['dcf_analysis'] = dcf_value
        except Exception as e:
            logger.error(f"估值分析失败: {str(e)}")
        return valuation

    def _analyze_growth(self, data: Dict) -> Dict[str, Any]:
        """分析成长性"""
        growth = {}
        try:
            revenue_growth = data.get('revenue_growth', 0)
            growth['revenue_growth'] = {'rate': revenue_growth, 'assessment': '高增长' if revenue_growth > 20 else '中等增长' if revenue_growth > 10 else '低增长'}
            net_income_growth = data.get('net_income_growth', 0)
            growth['net_income_growth'] = {'rate': net_income_growth, 'assessment': '高增长' if net_income_growth > 25 else '中等增长' if net_income_growth > 10 else '低增长'}
            eps_growth = data.get('eps_growth', 0)
            growth['eps_growth'] = {'rate': eps_growth, 'assessment': '高增长' if eps_growth > 20 else '中等增长' if eps_growth > 10 else '低增长'}
            growth_trend = analyze_growth_trend(data)
            if growth_trend:
                growth['growth_trend'] = growth_trend
        except Exception as e:
            logger.error(f"成长性分析失败: {str(e)}")
        return growth

    def _analyze_quality(self, data: Dict) -> Dict[str, Any]:
        """分析公司质量"""
        quality = {}
        try:
            roe, roa, gross_margin = data.get('roe', 0), data.get('roa', 0), data.get('gross_margin', 0)
            quality['profitability'] = {
                'roe': roe, 'roe_assessment': '优秀' if roe > 15 else '良好' if roe > 10 else '一般',
                'roa': roa, 'roa_assessment': '优秀' if roa > 8 else '良好' if roa > 5 else '一般',
                'gross_margin': gross_margin, 'margin_assessment': '优秀' if gross_margin > 50 else '良好' if gross_margin > 30 else '一般'
            }
            current_ratio, debt_to_equity = data.get('current_ratio', 0), data.get('debt_to_equity', 0)
            quality['financial_health'] = {
                'current_ratio': current_ratio, 'liquidity_assessment': '优秀' if current_ratio > 2 else '良好' if current_ratio > 1.5 else '一般',
                'debt_to_equity': debt_to_equity, 'leverage_assessment': '保守' if debt_to_equity < 0.5 else '适中' if debt_to_equity < 1 else '激进'
            }
            asset_turnover, inventory_turnover = data.get('asset_turnover', 0), data.get('inventory_turnover', 0)
            quality['efficiency'] = {
                'asset_turnover': asset_turnover, 'efficiency_assessment': '高效' if asset_turnover > 1.5 else '一般' if asset_turnover > 0.8 else '低效',
                'inventory_turnover': inventory_turnover, 'inventory_assessment': '高效' if inventory_turnover > 8 else '一般' if inventory_turnover > 4 else '低效'
            }
        except Exception as e:
            logger.error(f"质量分析失败: {str(e)}")
        return quality

    def _analyze_financial_health(self, data: Dict) -> Dict[str, Any]:
        """分析财务健康度"""
        health = {}
        try:
            current_ratio, quick_ratio, cash_ratio = data.get('current_ratio', 0), data.get('quick_ratio', 0), data.get('cash_ratio', 0)
            health['liquidity'] = {
                'current_ratio': current_ratio, 'quick_ratio': quick_ratio, 'cash_ratio': cash_ratio,
                'overall_liquidity': '优秀' if current_ratio > 2 else '良好' if current_ratio > 1.5 else '一般' if current_ratio > 1 else '较差'
            }
            debt_to_equity, debt_to_assets, interest_coverage = data.get('debt_to_equity', 0), data.get('debt_to_assets', 0), data.get('interest_coverage', 0)
            health['leverage'] = {
                'debt_to_equity': debt_to_equity, 'debt_to_assets': debt_to_assets, 'interest_coverage': interest_coverage,
                'leverage_assessment': '保守' if debt_to_equity < 0.5 else '适中' if debt_to_equity < 1 else '激进'
            }
            operating_margin, net_margin, roe = data.get('operating_margin', 0), data.get('net_margin', 0), data.get('roe', 0)
            health['profitability'] = {
                'operating_margin': operating_margin, 'net_margin': net_margin, 'roe': roe,
                'profitability_assessment': '优秀' if roe > 15 else '良好' if roe > 10 else '一般'
            }
        except Exception as e:
            logger.error(f"财务健康度分析失败: {str(e)}")
        return health

    def _generate_fundamental_report(self, results: Dict, analysis_type: str) -> str:
        """生成基本面分析报告"""
        report = f"# 基本面分析报告\n\n**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n**分析类型**: {analysis_type}\n\n"
        if 'valuation_analysis' in results:
            report += self._generate_valuation_section(results['valuation_analysis'])
        if 'growth_analysis' in results:
            report += self._generate_growth_section(results['growth_analysis'])
        if 'quality_analysis' in results:
            report += self._generate_quality_section(results['quality_analysis'])
        if 'financial_health' in results:
            report += self._generate_financial_health_section(results['financial_health'])
        report += self._generate_overall_assessment(results)
        return report

    def _generate_valuation_section(self, valuation: Dict) -> str:
        section = "## 估值分析\n\n"
        if 'pe_analysis' in valuation:
            pe = valuation['pe_analysis']
            section += f"### 市盈率分析\n- 当前市盈率: {pe['current_pe']}\n- 行业平均: {pe['industry_pe']}\n- 估值状态: {pe['relative_valuation']}\n\n"
        if 'pb_analysis' in valuation:
            pb = valuation['pb_analysis']
            section += f"### 市净率分析\n- 当前市净率: {pb['current_pb']}\n- 行业平均: {pb['industry_pb']}\n- 估值状态: {pb['relative_valuation']}\n\n"
        if 'dcf_analysis' in valuation:
            dcf = valuation['dcf_analysis']
            section += f"### DCF估值\n- 估值结果: ${dcf['total_value']:,.2f}\n- 增长率假设: {dcf['assumptions']['growth_rate']*100:.1f}%\n- 折现率: {dcf['assumptions']['discount_rate']*100:.1f}%\n\n"
        return section

    def _generate_growth_section(self, growth: Dict) -> str:
        section = "## 成长性分析\n\n"
        if 'revenue_growth' in growth:
            section += f"### 营收增长\n- 增长率: {growth['revenue_growth']['rate']:.1f}%\n- 评估: {growth['revenue_growth']['assessment']}\n\n"
        if 'net_income_growth' in growth:
            section += f"### 净利润增长\n- 增长率: {growth['net_income_growth']['rate']:.1f}%\n- 评估: {growth['net_income_growth']['assessment']}\n\n"
        if 'growth_trend' in growth:
            section += f"### 增长趋势\n- 平均增长率: {growth['growth_trend']['average_growth_rate']:.1f}%\n- 趋势特征: {growth['growth_trend']['trend']}\n\n"
        return section

    def _generate_quality_section(self, quality: Dict) -> str:
        section = "## 质量分析\n\n"
        if 'profitability' in quality:
            p = quality['profitability']
            section += f"### 盈利能力\n- 净资产收益率: {p['roe']:.1f}% ({p['roe_assessment']})\n- 总资产收益率: {p['roa']:.1f}% ({p['roa_assessment']})\n- 毛利率: {p['gross_margin']:.1f}% ({p['margin_assessment']})\n\n"
        if 'efficiency' in quality:
            e = quality['efficiency']
            section += f"### 运营效率\n- 资产周转率: {e['asset_turnover']:.2f} ({e['efficiency_assessment']})\n- 库存周转率: {e['inventory_turnover']:.1f} ({e['inventory_assessment']})\n\n"
        return section

    def _generate_financial_health_section(self, health: Dict) -> str:
        section = "## 财务健康度\n\n"
        if 'liquidity' in health:
            l = health['liquidity']
            section += f"### 流动性\n- 流动比率: {l['current_ratio']:.2f}\n- 速动比率: {l['quick_ratio']:.2f}\n- 现金比率: {l['cash_ratio']:.2f}\n- 整体评估: {l['overall_liquidity']}\n\n"
        if 'leverage' in health:
            lev = health['leverage']
            section += f"### 杠杆水平\n- 资产负债率: {lev['debt_to_equity']:.2f}\n- 负债资产比: {lev['debt_to_assets']:.1f}%\n- 利息保障倍数: {lev['interest_coverage']:.1f}\n- 杠杆评估: {lev['leverage_assessment']}\n\n"
        return section

    def _generate_overall_assessment(self, results: Dict) -> str:
        score = calculate_fundamental_score(results)
        assessment = "## 综合评估\n\n### 基本面评分\n"
        assessment += f"- 综合评分: {score:.1f}/100\n"
        if score >= 80:
            grade, outlook = "优秀", "强烈看好"
        elif score >= 70:
            grade, outlook = "良好", "看好"
        elif score >= 60:
            grade, outlook = "一般", "中性"
        else:
            grade, outlook = "较差", "看淡"
        assessment += f"- 评估等级: {grade}\n- 投资展望: {outlook}\n\n"
        assessment += "### 关键发现\n- " + generate_key_findings(results) + "\n"
        assessment += "### 投资建议\n"
        if score >= 70:
            assessment += "- 基于基本面分析，该股票具有良好的投资价值\n- 建议关注估值回调机会进行适当配置\n"
        elif score >= 60:
            assessment += "- 基本面表现一般，需要结合其他因素综合判断\n- 建议观望，等待更好的投资时机\n"
        else:
            assessment += "- 基本面存在明显问题，建议谨慎对待\n- 需要深入分析风险因素\n"
        return assessment