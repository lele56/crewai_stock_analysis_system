# src/flows/investment_flow_helpers.py
"""投资流程辅助方法 — 公司特征分析、数据质量评估、状态更新"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.flows.investment_flow import AnalysisState

logger = logging.getLogger(__name__)

# ── 质量等级阈值 ─────────────────────────────────
_QUALITY_THRESHOLDS = (
    (80, "excellent"),
    (60, "good"),
    (40, "acceptable"),
)

# ── 分析深度查表 ─────────────────────────────────
_DEPTH_LOOKUP = {
    ("large", "high"): "deep",
    ("large", "medium"): "comprehensive",
    ("large", "low"): "comprehensive",
}

# ── 建议强度阈值 ─────────────────────────────────
_STRENGTH_THRESHOLDS = (
    (80, "high"),
    (60, "medium"),
)


def analyze_company_profile(company: str, ticker: str) -> dict[str, Any]:
    """分析公司特征（规模、行业趋势、复杂度）— 基于真实市值和行业数据。

    通过 get_stock_basic_info 获取实际市值和行业分类来判断规模与复杂度，
    避免使用公司名长度等不靠谱的启发式规则。
    """
    from src.tools.akshare_data_parser import get_stock_basic_info

    try:
        info = get_stock_basic_info(ticker)
    except Exception:
        logger.warning("获取公司基本信息失败，使用默认值")
        info = {}

    market_cap = info.get("marketCap", 0)
    industry = info.get("industry", "N/A")

    # 规模：基于市值（单位：元）
    if market_cap > 1000e8:       # > 1000亿 → 大盘
        size = "large"
    elif market_cap > 100e8:      # > 100亿 → 中盘
        size = "medium"
    else:
        size = "small"

    # 复杂度：大盘股或特定行业视为高复杂度
    high_complexity_industries = {"金融", "科技", "医药", "电子", "半导体"}
    is_high = size == "large" or industry in high_complexity_industries
    complexity = "high" if is_high else "medium"

    return {"size": size, "trend": "stable", "complexity": complexity}


def determine_analysis_depth(company_profile: dict[str, Any]) -> str:
    """根据公司特征决定分析深度 — 查表"""
    size = company_profile.get("size", "medium")
    complexity = company_profile.get("complexity", "medium")
    key = (size, complexity)
    return _DEPTH_LOOKUP.get(key, "standard")


def assess_data_quality(data_result: dict[str, Any]) -> dict[str, Any]:
    """评估数据质量 — 基于 agents 数量和执行时间"""
    if not (data_result.get("success") or data_result.get("status") == "success"):
        return {"completeness": 0, "overall_quality": "poor"}

    agents_count = data_result.get("agents_count", 0)
    execution_time = data_result.get("execution_time", 999)

    completeness = _calc_completeness(agents_count, execution_time)
    overall = _threshold_lookup(completeness, _QUALITY_THRESHOLDS, "poor")
    return {"completeness": completeness, "overall_quality": overall}


# ── 完整性得分阈值（agents_count, execution_time）→ 得分 ─
_COMPLETENESS_THRESHOLDS = (
    (3, 300, 85),
    (2, 600, 70),
    (1, 1800, 55),
)


def _calc_completeness(agents_count: int, execution_time: float) -> int:
    """计算数据完整性得分 — 阈值查表"""
    for min_agents, max_time, score in _COMPLETENESS_THRESHOLDS:
        if agents_count >= min_agents and execution_time <= max_time:
            return score
    return 50


def _threshold_lookup(value: float, thresholds: tuple[tuple[float, str], ...], default: str) -> str:
    """按阈值查表，返回第一个匹配的标签"""
    for threshold, label in thresholds:
        if value >= threshold:
            return label
    return default


def update_analysis_state(state: "AnalysisState", analysis_result: dict[str, Any]) -> None:
    """更新分析状态"""
    try:
        scores = analysis_result.get("collaboration_scores", {})
        metrics = analysis_result.get("collaboration_metrics", {})
        state.financial_score = scores.get("overall_score", 0.0)
        state.analysis_confidence = _consistency_to_confidence(metrics.get("consistency", "medium"))
        state.collaboration_quality = metrics.get("collaboration_level", "medium")
        logger.info("分析状态已更新")
    except Exception as e:
        logger.error(f"更新分析状态失败: {str(e)}")
        state.warnings.append(f"状态更新失败: {str(e)}")


def _consistency_to_confidence(consistency: str) -> float:
    """一致性映射到置信度"""
    return {"high": 0.9, "medium": 0.6}.get(consistency, 0.3)


def update_decision_state(state: "AnalysisState", decision_result: dict[str, Any]) -> None:
    """更新决策状态"""
    try:
        recommendation = decision_result.get("final_recommendation", {})
        metrics = decision_result.get("collective_decision_metrics", {})
        state.final_recommendation = recommendation.get("action", "hold")
        state.overall_score = recommendation.get("confidence", 0.0) * 100
        state.decision_complexity = metrics.get("decision_type", "standard")
        logger.info("决策状态已更新")
    except Exception as e:
        logger.error(f"更新决策状态失败: {str(e)}")
        state.warnings.append(f"状态更新失败: {str(e)}")


def generate_analysis_summary(state: "AnalysisState") -> dict[str, Any]:
    """生成分析总结"""
    strength = _threshold_lookup(state.overall_score, _STRENGTH_THRESHOLDS, "low")

    return {
        "total_stages": len(state.alternative_paths) + 1,
        "primary_path": state.analysis_depth,
        "collaboration_quality": state.collaboration_quality,
        "decision_confidence": state.analysis_confidence,
        "efficiency_metrics": {
            "error_rate": state.error_count,
            "retry_count": sum(state.retry_attempts.values()),
            "alternative_routes": len(state.alternative_paths),
        },
        "recommendation_strength": strength,
    }