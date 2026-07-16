# src/tools/report_templates.py
"""报告模板工具 - 预定义报告模板集"""

from datetime import datetime


class ReportTemplates:
    """报告模板集合"""

    @staticmethod
    def standard_template(data: dict) -> str:
        """标准模板"""
        return f"""
{data.get("company", "")} ({data.get("ticker", "")}) 投资分析报告

生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

=== 摘要 ===
{data.get("summary", "")}

=== 详细分析 ===
{data.get("detailed_analysis", "")}

=== 投资建议 ===
{data.get("recommendation", "")}

=== 风险提示 ===
{data.get("risk_warning", "")}

=== 免责声明 ===
本报告仅供参考，不构成投资建议。
"""

    @staticmethod
    def professional_template(data: dict) -> str:
        """专业模板"""
        return f"""
PROFESSIONAL INVESTMENT ANALYSIS REPORT
======================================

Company: {data.get("company", "")}
Ticker: {data.get("ticker", "")}
Date: {datetime.now().strftime("%Y-%m-%d")}

EXECUTIVE SUMMARY: {data.get("executive_summary", "")}
COMPANY OVERVIEW: {data.get("company_overview", "")}
FINANCIAL ANALYSIS: {data.get("financial_analysis", "")}
MARKET ANALYSIS: {data.get("market_analysis", "")}
INVESTMENT RECOMMENDATION: {data.get("investment_recommendation", "")}
RISK FACTORS: {data.get("risk_factors", "")}
DISCLAIMER: This report is for informational purposes only.
"""

    @staticmethod
    def executive_template(data: dict) -> str:
        """执行模板"""
        return f"""
EXECUTIVE BRIEFING
=================

Subject: {data.get("company", "")} Investment Analysis
Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}

KEY TAKEAWAYS: {data.get("key_takeaway_1", "")} | {data.get("key_takeaway_2", "")} | {data.get("key_takeaway_3", "")}
INVESTMENT THESIS: {data.get("investment_thesis", "")}
RECOMMENDATION: {data.get("recommendation", "")}
NEXT STEPS: {data.get("next_steps", "")}
"""

    @staticmethod
    def research_template(data: dict) -> str:
        """研究模板"""
        return f"""
RESEARCH REPORT: {data.get("company", "")} ({data.get("ticker", "")})
===================================================

Publication Date: {datetime.now().strftime("%Y-%m-%d")}
Research Analyst: AI Investment System

ABSTRACT: {data.get("abstract", "")}
1. INTRODUCTION: {data.get("introduction", "")}
2. METHODOLOGY: {data.get("methodology", "")}
3. ANALYSIS: {data.get("analysis", "")}
4. FINDINGS: {data.get("findings", "")}
5. CONCLUSIONS: {data.get("conclusions", "")}
REFERENCES: {data.get("references", "")}
DISCLAIMER: This research report is for informational purposes only.
"""

    @staticmethod
    def investment_analysis_template(data: dict) -> str:
        """投资分析报告完整模板"""
        company = data.get("company", "未知公司")
        ticker = data.get("ticker", "UNKNOWN")
        return f"""
# {company} ({ticker}) 投资分析报告

**报告生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**分析师**: AI投资分析系统
**报告类型**: 综合投资分析

---

## 执行摘要

本报告对{company} ({ticker})进行了全面的投资分析，涵盖市场研究、财务分析、技术分析、基本面评估、风险分析等多个维度。

## 公司概况

- **公司名称**: {company}
- **股票代码**: {ticker}
- **行业**: {data.get("industry", "未知")}
- **市值**: {data.get("market_cap", "N/A")}
- **当前股价**: ${data.get("current_price", "N/A")}
- **业务描述**: {data.get("business_description", "暂无业务描述")}

---

## 市场分析

{data.get("market_analysis", "暂无市场分析数据")}

### 行业地位
{data.get("industry_position", "暂无行业地位分析")}

### 竞争优势
{data.get("competitive_advantages", "暂无竞争优势分析")}

---

## 财务分析

{data.get("financial_metrics", "暂无财务指标数据")}

### 盈利能力
{data.get("profitability_analysis", "暂无盈利能力分析")}

### 财务健康度
{data.get("financial_health", "暂无财务健康度分析")}

---

## 技术分析

{data.get("price_trend", "暂无价格走势分析")}
{data.get("technical_indicators", "暂无技术指标分析")}
{data.get("trading_signals", "暂无交易信号分析")}

---

## 基本面分析

{data.get("valuation_analysis", "暂无估值分析")}
{data.get("growth_analysis", "暂无成长性分析")}
{data.get("quality_assessment", "暂无质量评估")}

---

## 风险评估

### 风险等级
- **整体风险等级**: {data.get("risk_level", "未知")}
- **市场风险**: {data.get("market_risk", "未知")}
- **财务风险**: {data.get("financial_risk", "未知")}
- **运营风险**: {data.get("operational_risk", "未知")}

### 主要风险
{data.get("major_risks", "暂无主要风险分析")}

### 风险控制建议
{data.get("risk_control_recommendations", "暂无风险控制建议")}

---

## 投资建议

- **当前评级**: {data.get("investment_rating", "未评级")}
- **目标价位**: ${data.get("target_price", "N/A")}
- **止损价位**: ${data.get("stop_loss", "N/A")}

### 投资策略
{data.get("investment_strategy", "暂无投资策略建议")}

### 时间框架
- **短期**: {data.get("short_term_outlook", "观望")}
- **中期**: {data.get("medium_term_outlook", "观望")}
- **长期**: {data.get("long_term_outlook", "观望")}

---

## 关键假设

{data.get("key_assumptions", "暂无关键假设说明")}

---

## 免责声明

本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。
- 本报告基于公开信息编制，可能存在信息滞后或不准确的情况
- 市场存在不确定性，过去表现不代表未来结果
- 投资者应根据自身风险承受能力和投资目标做出独立决策

---

**报告由 AI 投资分析系统自动生成**
"""

    @staticmethod
    def summary_template(data: dict) -> str:
        """摘要报告模板"""
        company = data.get("company", "未知公司")
        ticker = data.get("ticker", "UNKNOWN")
        return f"""
# {company} ({ticker}) 分析摘要

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 关键信息
- **投资评级**: {data.get("investment_rating", "未评级")}
- **目标价位**: ${data.get("target_price", "N/A")}
- **风险等级**: {data.get("risk_level", "未知")}
- **综合评分**: {data.get("overall_score", "N/A")}/100

## 核心观点
{data.get("core_viewpoints", "暂无核心观点")}

## 主要亮点
{data.get("key_highlights", "暂无主要亮点")}

## 主要风险
{data.get("key_risks", "暂无主要风险")}

## 投资建议
{data.get("investment_recommendation", "暂无投资建议")}
"""

    @staticmethod
    def executive_brief_template(data: dict) -> str:
        """执行简报模板"""
        company = data.get("company", "未知公司")
        ticker = data.get("ticker", "UNKNOWN")
        return f"""
# {company} ({ticker}) 执行简报

**时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 即时概览
- **当前状态**: {data.get("current_status", "正常")}
- **投资评级**: {data.get("investment_rating", "未评级")}
- **市场情绪**: {data.get("market_sentiment", "中性")}

## 关键指标
{data.get("key_metrics", "暂无关键指标")}

## 重要提醒
{data.get("important_reminders", "暂无重要提醒")}

## 行动建议
{data.get("action_items", "暂无行动建议")}
"""

    @classmethod
    def get_templates(cls) -> dict[str, callable]:
        """获取所有模板"""
        return {
            "standard": cls.standard_template,
            "professional": cls.professional_template,
            "executive": cls.executive_template,
            "research": cls.research_template,
            "investment_analysis": cls.investment_analysis_template,
            "summary": cls.summary_template,
            "executive_brief": cls.executive_brief_template,
        }
