# src/crews/data_collection_executor.py
"""数据采集执行器 — 直接调用工具，不再经过 Agent 层

Profile 分层:
  RAPID:    纯函数调用，无 LLM 参与
  STANDARD: 函数调用 + 1 质检员 Agent 检查完整性
  DEEP:    函数调用 + 1 质检员 Agent 检查 + 补漏建议
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any

from src.config import AnalysisProfile
from src.crews.data_schemas import (
    CollectionData,
    FinancialMetrics,
    IndustryData,
    MarketData,
    TechnicalData,
)

logger = logging.getLogger(__name__)


def collect_data_direct(company: str, ticker: str) -> CollectionData:
    """直接调用底层函数获取数据，零 LLM 参与

    Returns:
        CollectionData 结构化数据，可直接传给分析阶段
    """
    logger.info(f"[数据采集-直接] 开始: {company} ({ticker})")

    result = CollectionData(company=company, ticker=ticker)

    result.market = _fetch_market_data(ticker)
    result.financial = _fetch_financial_data(ticker)
    result.technical = _fetch_technical_data(ticker)
    result.industry = _fetch_industry_data(ticker, company)

    logger.info(
        f"[数据采集-直接] 完成: market={not result.market.is_empty()}, "
        f"financial={not result.financial.is_empty()}, "
        f"technical={not result.technical.is_empty()}, "
        f"industry={not result.industry.is_empty()}"
    )
    return result


def _fetch_market_data(ticker: str) -> MarketData:
    """从缓存/API 获取市场数据"""
    try:
        from src.tools.akshare_data_cache import load_stock_cache

        _hist, _fin, _bs, _cf, info = load_stock_cache(ticker)
        if not info:
            return MarketData()

        return MarketData(
            price=_safe_float(info.get("price", 0)),
            change_pct=_safe_float(info.get("change_pct", 0)),
            volume=_safe_float(info.get("volume", 0)),
            avg_volume_20d=_safe_float(info.get("avg_volume_20d", 0)),
            high_52w=_safe_float(info.get("high_52w", 0)),
            low_52w=_safe_float(info.get("low_52w", 0)),
            beta=_safe_float(info.get("beta", 0)),
            volatility_30d=_safe_float(info.get("volatility_30d", 0)),
        )
    except Exception as e:
        logger.warning(f"获取市场数据失败: {e}")
        return MarketData()


def _fetch_financial_data(ticker: str) -> FinancialMetrics:
    """从 FinancialCalculatorTool 获取财务数据 dict，转为 FinancialMetrics"""
    try:
        from src.tools.financial_tools import FinancialCalculatorTool

        data = FinancialCalculatorTool._fetch_financial_from_api(ticker)
        if not data:
            return FinancialMetrics()

        return FinancialMetrics(
            revenue=_safe_list(data.get("revenue")),
            net_profit=_safe_list(data.get("net_profit")),
            total_assets=_safe_float(data.get("total_assets", 0)),
            total_liabilities=_safe_float(data.get("total_liabilities", 0)),
            operating_cash_flow=_safe_float(data.get("operating_cash_flow", 0)),
            gross_margin=_safe_float(data.get("gross_margin", 0)),
            net_margin=_safe_float(data.get("net_margin", 0)),
            roe=_safe_float(data.get("roe", 0)),
            roa=_safe_float(data.get("roa", 0)),
            debt_ratio=_safe_float(data.get("debt_ratio", 0)),
            current_ratio=_safe_float(data.get("current_ratio", 0)),
            quick_ratio=_safe_float(data.get("quick_ratio", 0)),
            revenue_growth=_safe_float(data.get("revenue_growth", 0)),
            profit_growth=_safe_float(data.get("profit_growth", 0)),
            pe=_safe_float(data.get("pe", 0)),
            pb=_safe_float(data.get("pb", 0)),
            ps=_safe_float(data.get("ps", 0)),
            market_cap=_safe_float(data.get("market_cap", 0)),
            dividend_yield=_safe_float(data.get("dividend_yield", 0)),
        )
    except Exception as e:
        logger.warning(f"获取财务数据失败: {e}")
        return FinancialMetrics()


def _fetch_technical_data(ticker: str) -> TechnicalData:
    """从缓存获取K线数据，计算技术指标"""
    try:
        from src.tools.technical_tools import TechnicalAnalysisTool

        tool = TechnicalAnalysisTool()
        df = tool._try_fetch_stock_data(ticker)
        if df is None or df.empty:
            return TechnicalData()

        df = tool._ensure_required_columns(df)
        indicators = tool._calculate_all_indicators(df)

        return TechnicalData(
            ma_5=_safe_float(indicators.get("ma_5", 0)),
            ma_20=_safe_float(indicators.get("ma_20", 0)),
            ma_50=_safe_float(indicators.get("ma_50", 0)),
            ma_200=_safe_float(indicators.get("ma_200", 0)),
            rsi_14=_safe_float(indicators.get("rsi_14", 0)),
            macd=_safe_float(indicators.get("macd", 0)),
            macd_signal=_safe_float(indicators.get("macd_signal", 0)),
            macd_histogram=_safe_float(indicators.get("macd_histogram", 0)),
            bollinger_upper=_safe_float(indicators.get("bollinger_upper", 0)),
            bollinger_middle=_safe_float(indicators.get("bollinger_middle", 0)),
            bollinger_lower=_safe_float(indicators.get("bollinger_lower", 0)),
            atr_14=_safe_float(indicators.get("atr_14", 0)),
        )
    except Exception as e:
        logger.warning(f"获取技术数据失败: {e}")
        return TechnicalData()


def _fetch_industry_data(ticker: str, company: str) -> IndustryData:
    """从缓存获取行业数据"""
    try:
        from src.tools.akshare_data_cache import load_stock_cache

        _hist, _fin, _bs, _cf, info = load_stock_cache(ticker)
        if not info:
            return IndustryData()

        sector = str(info.get("sector", "") or info.get("industry", ""))
        industry = str(info.get("industry", "") or info.get("sector", ""))

        return IndustryData(
            sector=sector,
            industry=industry,
            market_position=str(info.get("market_position", "") or _guess_position(info)),
            market_share=_safe_float(info.get("market_share", 0)),
            competitors=list(info.get("competitors", [])) if info.get("competitors") else [],
            industry_growth=_safe_float(info.get("industry_growth", 0)),
            industry_size=_safe_float(info.get("industry_size", 0)),
            trends=str(info.get("trends", "") or info.get("development", "")),
            opportunities=str(info.get("opportunities", "")),
            threats=str(info.get("threats", "")),
        )
    except Exception as e:
        logger.warning(f"获取行业数据失败: {e}")
        return IndustryData()


def _guess_position(info: dict) -> str:
    """根据市值/PE 粗略判断行业地位"""
    mc = _safe_float(info.get("market_cap", 0))
    if mc > 5000:
        return "龙头"
    if mc > 1000:
        return "领先"
    if mc > 100:
        return "跟随"
    return "挑战者"


def _safe_float(val: Any) -> float:
    """安全转换为 float，不抛出异常"""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return float(val)
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _safe_list(val: Any) -> list[float]:
    """安全转换为 float 列表"""
    if val is None:
        return []
    if isinstance(val, list):
        return [_safe_float(v) for v in val]
    try:
        return [_safe_float(val)]
    except (ValueError, TypeError):
        return []


# ── 质检 Agent ──────────────────────────────────

def _build_quality_check_input(company: str, ticker: str, data: CollectionData) -> str:
    """构建质检 Agent 的输入 prompt"""
    parts = [
        f"请检查以下 {company}（{ticker}）的数据采集结果是否完整、准确。",
        "",
        data.to_financial_prompt(),
        "",
        data.to_market_prompt(),
        "",
        data.to_technical_prompt(),
        "",
        data.to_industry_prompt(),
        "",
        "请输出 JSON 格式的检查结果：",
        '{',
        '  "completeness": "high|medium|low",',
        '  "issues": ["问题描述1", "问题描述2"],',
        '  "summary": "一句话总结数据质量"',
        '}',
    ]
    return "\n".join(parts)


def run_quality_check(
    company: str,
    ticker: str,
    data: CollectionData,
    profile: AnalysisProfile,
) -> dict[str, Any]:
    """运行数据质检 Agent（仅 STANDARD/DEEP）

    Returns:
        {"quality": "high"|"medium"|"low", "issues": [...], "summary": "..."}
    """
    if profile == AnalysisProfile.RAPID:
        return {"quality": "high", "issues": [], "summary": "RAPID 模式跳过质检"}

    try:
        from crewai import Agent, Crew, Process, Task

        from src.utils.llm_factory import get_llm

        prompt = _build_quality_check_input(company, ticker, data)

        agent = Agent(
            role="数据质检员",
            goal="检查数据采集结果的完整性和准确性，发现缺失或异常数据",
            backstory="你是一位严谨的数据质量检查员，擅长发现数据缺失和异常值。",
            llm=get_llm(),
            verbose=False,
            allow_delegation=False,
            max_iter=1,
        )

        task = Task(
            description=prompt,
            expected_output="数据质量检查结果的 JSON",
            agent=agent,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
            memory=False,
            cache=False,
        )

        result = crew.kickoff()
        raw = str(result.raw) if hasattr(result, "raw") else str(result)

        parsed = _parse_quality_result(raw)

        if profile == AnalysisProfile.DEEP and parsed["quality"] != "high":
            logger.info(f"[质检] 发现 {len(parsed['issues'])} 个问题，DEEP 模式将补充数据")
            data = _fill_missing_data(ticker, data, parsed["issues"])
            parsed["summary"] += " (已尝试补漏)"

        logger.info(f"[质检] 完成: quality={parsed['quality']}, issues={len(parsed['issues'])}")
        return parsed

    except Exception as e:
        logger.warning(f"质检失败: {e}，跳过质检")
        return {"quality": "high", "issues": [], "summary": "质检跳过（异常）"}


def _parse_quality_result(raw: str) -> dict[str, Any]:
    """解析质检 Agent 的 JSON 输出"""
    try:
        if "{" in raw and "}" in raw:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return {"quality": "medium", "issues": ["无法解析质检结果"], "summary": raw[:200]}


def _fill_missing_data(ticker: str, data: CollectionData, issues: list[str]) -> None:
    """DEEP 模式：根据质检问题尝试补漏"""
    for issue in issues:
        il = issue.lower()
        if ("市场" in issue or "market" in il or "价格" in issue or "price" in il) and data.market.is_empty():
            data.market = _fetch_market_data(ticker)
        if ("财务" in issue or "financial" in il or "利润" in issue or "revenue" in il) and data.financial.is_empty():
            data.financial = _fetch_financial_data(ticker)
        if ("技术" in issue or "technical" in il or "指标" in issue or "indicator" in il) and data.technical.is_empty():
            data.technical = _fetch_technical_data(ticker)
        if ("行业" in issue or "industry" in il or "板块" in issue or "sector" in il) and data.industry.is_empty():
            data.industry = _fetch_industry_data(ticker, data.company)