# src/crews/data_parser.py
"""从 Agent 输出中提取结构化数据

优先级：
  1. CrewAI output_pydantic → 直接取 task.output.pydantic（最可靠）
  2. JSON 文本解析 → 从 task.output.raw 中提取 JSON
  3. 原始文本 → 回退方案
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.crews.data_schemas import (
    CollectionData,
    FinancialDataOutput,
    FinancialMetrics,
    FinancialRatioOutput,
    IndustryData,
    MarketData,
    MarketResearchOutput,
    TechnicalData,
    TechnicalDataOutput,
)

logger = logging.getLogger(__name__)

# ── JSON 提取正则 ────────────────────────────────
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)
_BRACE_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


def _fix_json(text: str) -> str:
    """修复 LLM 常见的 JSON 格式错误"""
    return re.sub(r",\s*(\}|\])", r"\1", text)


def _extract_json(text: str) -> dict[str, Any] | None:
    """从文本中提取并解析 JSON"""
    if not text:
        return None

    matches = _JSON_BLOCK_RE.findall(text)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            try:
                return json.loads(_fix_json(match))
            except json.JSONDecodeError:
                continue

    match = _BRACE_BLOCK_RE.search(text)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            try:
                return json.loads(_fix_json(candidate))
            except json.JSONDecodeError:
                logger.debug("JSON 修复后仍解析失败，继续尝试其他方式")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return json.loads(_fix_json(text))
        except json.JSONDecodeError:
            return None


# ── output_pydantic 模型 → 内部模型转换 ──────────

def _market_output_to_internal(data: MarketResearchOutput) -> tuple[MarketData, IndustryData]:
    """MarketResearchOutput → MarketData + IndustryData"""
    market = MarketData(
        price=data.price,
        change_pct=data.change_pct,
        volume=data.volume,
        avg_volume_20d=data.avg_volume_20d,
        high_52w=data.high_52w,
        low_52w=data.low_52w,
        beta=data.beta,
        volatility_30d=data.volatility_30d,
    )
    industry = IndustryData(
        sector=data.sector,
        industry=data.industry,
        market_position=data.market_position,
        market_share=data.market_share,
        competitors=data.competitors,
        industry_growth=data.industry_growth,
        industry_size=data.industry_size,
        trends=data.trends,
        opportunities=data.opportunities,
        threats=data.threats,
    )
    return market, industry


def _financial_output_to_internal(data: FinancialDataOutput | FinancialRatioOutput | dict) -> FinancialMetrics:
    """FinancialDataOutput/FinancialRatioOutput → FinancialMetrics"""
    if isinstance(data, dict):
        return FinancialMetrics(**data)
    return FinancialMetrics(
        revenue=data.revenue,
        net_profit=data.net_profit,
        total_assets=data.total_assets,
        total_liabilities=data.total_liabilities,
        operating_cash_flow=data.operating_cash_flow,
        gross_margin=data.gross_margin,
        net_margin=data.net_margin,
        roe=data.roe,
        roa=data.roa,
        debt_ratio=data.debt_ratio,
        current_ratio=data.current_ratio,
        quick_ratio=data.quick_ratio,
        revenue_growth=data.revenue_growth,
        profit_growth=data.profit_growth,
        pe=data.pe,
        pb=data.pb,
        ps=data.ps,
        market_cap=data.market_cap,
        dividend_yield=data.dividend_yield,
    )


def _technical_output_to_internal(data: TechnicalDataOutput | dict) -> TechnicalData:
    """TechnicalDataOutput → TechnicalData"""
    if isinstance(data, dict):
        return TechnicalData(**data)
    return TechnicalData(
        ma_5=data.ma_5, ma_20=data.ma_20, ma_50=data.ma_50, ma_200=data.ma_200,
        rsi_14=data.rsi_14, macd=data.macd, macd_signal=data.macd_signal,
        macd_histogram=data.macd_histogram,
        bollinger_upper=data.bollinger_upper, bollinger_middle=data.bollinger_middle,
        bollinger_lower=data.bollinger_lower, atr_14=data.atr_14,
    )


def parse_collection_data(
    task_outputs: list[Any],
    company: str = "",
    ticker: str = "",
) -> CollectionData:
    """从数据收集任务输出中提取完整结构化数据

    优先级：output_pydantic > JSON 文本解析 > 原始文本

    任务索引（按数据收集阶段输出顺序）：
      0: market_research         → MarketResearchOutput → MarketData + IndustryData
      1: financial_data_collection → FinancialDataOutput → FinancialMetrics
      2: financial_ratio_calculation → FinancialRatioOutput → FinancialMetrics（合并）
      3: technical_data_collection  → TechnicalDataOutput → TechnicalData
      4: data_collection_coordination → 汇总（跳过）
    """
    result = CollectionData(company=company, ticker=ticker)

    def _get_pydantic(index: int) -> Any:
        """获取指定索引的 task output 的 pydantic 模型"""
        if index < len(task_outputs):
            to = task_outputs[index]
            if hasattr(to, "pydantic") and to.pydantic is not None:
                return to.pydantic
        return None

    def _get_raw_text(index: int) -> str:
        if index < len(task_outputs):
            to = task_outputs[index]
            if hasattr(to, "raw"):
                return str(to.raw)
            return str(to)
        return ""

    # ── 任务 0: market_research → MarketResearchOutput ──
    pyd = _get_pydantic(0)
    if pyd and isinstance(pyd, MarketResearchOutput):
        result.market, result.industry = _market_output_to_internal(pyd)
        logger.info("从 output_pydantic 提取市场/行业数据成功")
    elif pyd:
        logger.warning(f"任务0 pydantic 类型不匹配: {type(pyd).__name__}，回退 JSON 解析")
        result.market, result.industry = _parse_market_from_text(_get_raw_text(0))
    else:
        logger.debug("任务0 无 pydantic 输出，使用 JSON 文本解析")
        result.market, result.industry = _parse_market_from_text(_get_raw_text(0))

    # ── 任务 1: financial_data_collection → FinancialDataOutput ──
    pyd = _get_pydantic(1)
    if pyd and isinstance(pyd, (FinancialDataOutput, FinancialRatioOutput)):
        fin1 = _financial_output_to_internal(pyd)
        logger.info("从 output_pydantic 提取财务数据(1)成功")
    elif pyd:
        logger.warning(f"任务1 pydantic 类型不匹配: {type(pyd).__name__}，回退 JSON 解析")
        fin1 = _parse_financial_from_text(_get_raw_text(1))
    else:
        fin1 = _parse_financial_from_text(_get_raw_text(1))

    # ── 任务 2: financial_ratio_calculation → FinancialRatioOutput ──
    pyd = _get_pydantic(2)
    if pyd and isinstance(pyd, (FinancialDataOutput, FinancialRatioOutput)):
        fin2 = _financial_output_to_internal(pyd)
        logger.info("从 output_pydantic 提取财务数据(2)成功")
    elif pyd:
        logger.warning(f"任务2 pydantic 类型不匹配: {type(pyd).__name__}，回退 JSON 解析")
        fin2 = _parse_financial_from_text(_get_raw_text(2))
    else:
        fin2 = _parse_financial_from_text(_get_raw_text(2))

    result.financial = _merge_financial(fin1, fin2)

    # ── 任务 3: technical_data_collection → TechnicalDataOutput ──
    pyd = _get_pydantic(3)
    if pyd and isinstance(pyd, TechnicalDataOutput):
        result.technical = _technical_output_to_internal(pyd)
        logger.info("从 output_pydantic 提取技术数据成功")
    elif pyd:
        logger.warning(f"任务3 pydantic 类型不匹配: {type(pyd).__name__}，回退 JSON 解析")
        result.technical = _parse_technical_from_text(_get_raw_text(3))
    else:
        result.technical = _parse_technical_from_text(_get_raw_text(3))

    return result


# ── JSON 文本回退解析 ────────────────────────────

def _parse_market_from_text(text: str) -> tuple[MarketData, IndustryData]:
    """从文本中解析市场 + 行业数据（回退方案）"""
    data = _extract_json(text)
    if data:
        market = MarketData(
            price=data.get("price", 0.0),
            change_pct=data.get("change_pct", 0.0),
            volume=data.get("volume", 0.0),
            avg_volume_20d=data.get("avg_volume_20d", 0.0),
            high_52w=data.get("high_52w", 0.0),
            low_52w=data.get("low_52w", 0.0),
            beta=data.get("beta", 0.0),
            volatility_30d=data.get("volatility_30d", 0.0),
        )
        industry = IndustryData(
            sector=data.get("sector", ""),
            industry=data.get("industry", ""),
            market_position=data.get("market_position", ""),
            market_share=data.get("market_share", 0.0),
            competitors=data.get("competitors", []),
            industry_growth=data.get("industry_growth", 0.0),
            industry_size=data.get("industry_size", 0.0),
            trends=data.get("trends", ""),
            opportunities=data.get("opportunities", ""),
            threats=data.get("threats", ""),
        )
        return market, industry
    return MarketData(), IndustryData()


def _parse_financial_from_text(text: str) -> FinancialMetrics:
    """从文本中解析财务数据（回退方案）"""
    data = _extract_json(text)
    if data:
        return FinancialMetrics(**data)
    return FinancialMetrics()


def _parse_technical_from_text(text: str) -> TechnicalData:
    """从文本中解析技术数据（回退方案）"""
    data = _extract_json(text)
    if data:
        return TechnicalData(**data)
    return TechnicalData()


def _merge_financial(a: FinancialMetrics, b: FinancialMetrics) -> FinancialMetrics:
    """合并两个财务数据源，非零字段优先"""
    merged = a.model_dump()
    for key, val in b.model_dump().items():
        if (val and not merged.get(key) and (
            (isinstance(val, list) and val) or
            (isinstance(val, (int, float)) and val != 0) or
            (isinstance(val, str) and val)
        )):
            merged[key] = val
    return FinancialMetrics(**merged)


def collection_data_to_prompt(data: CollectionData) -> dict[str, str]:
    """将结构化数据转换为分析 Agent 的 prompt 文本

    返回三个独立字段，每个分析 Agent 只取自己需要的。
    """
    financial_text = data.to_financial_prompt()
    risk_text = data.to_risk_prompt()
    industry_text = data.to_industry_prompt()

    if data.is_effectively_empty:
        logger.warning("所有结构化数据均为空，分析 Agent 将缺乏有效输入")

    return {
        "financial_data": financial_text or "（财务数据暂未获取到）",
        "risk_data": risk_text or "（风险数据暂未获取到）",
        "industry_data": industry_text or "（行业数据暂未获取到）",
    }