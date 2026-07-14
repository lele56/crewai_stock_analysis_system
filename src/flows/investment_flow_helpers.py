# src/flows/investment_flow_helpers.py
"""投资流程辅助方法 - 公司特征分析、数据质量评估、状态更新"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def analyze_company_profile(company: str, ticker: str) -> Dict[str, Any]:
    """分析公司特征（规模、行业趋势、复杂度）"""
    return {
        "size": "large" if len(company) > 10 else "medium",
        "trend": "growing" if any(ch.isdigit() for ch in ticker) else "stable",
        "complexity": "high" if len(ticker) <= 4 else "medium"
    }


def determine_analysis_depth(company_profile: Dict[str, Any]) -> str:
    """根据公司特征决定分析深度"""
    if company_profile.get('size') == 'large' and company_profile.get('complexity') == 'high':
        return 'deep'
    elif company_profile.get('size') == 'large':
        return 'comprehensive'
    return 'standard'


def assess_data_quality(data_result: Dict[str, Any]) -> Dict[str, Any]:
    """评估数据质量"""
    metrics = data_result.get('collaboration_metrics', {})
    completeness = metrics.get('collaboration_score', 0)
    if completeness >= 80:
        overall = 'excellent'
    elif completeness >= 60:
        overall = 'good'
    elif completeness >= 40:
        overall = 'acceptable'
    else:
        overall = 'poor'
    return {'completeness': completeness, 'overall_quality': overall}


def update_analysis_state(state, analysis_result: Dict[str, Any]):
    """更新分析状态"""
    try:
        scores = analysis_result.get('collaboration_scores', {})
        metrics = analysis_result.get('collaboration_metrics', {})
        state.financial_score = scores.get('overall_score', 0.0)
        state.analysis_confidence = metrics.get('consensus_level', 0.0)
        state.collaboration_quality = metrics.get('decision_quality', 'medium')
        logger.info("分析状态已更新")
    except Exception as e:
        logger.error(f"更新分析状态失败: {str(e)}")
        state.warnings.append(f"状态更新失败: {str(e)}")


def update_decision_state(state, decision_result: Dict[str, Any]):
    """更新决策状态"""
    try:
        recommendation = decision_result.get('final_recommendation', {})
        metrics = decision_result.get('collective_decision_metrics', {})
        state.final_recommendation = recommendation.get('action', 'hold')
        state.overall_score = recommendation.get('confidence', 0.0) * 100
        state.decision_complexity = metrics.get('decision_quality', 'standard')
        logger.info("决策状态已更新")
    except Exception as e:
        logger.error(f"更新决策状态失败: {str(e)}")
        state.warnings.append(f"状态更新失败: {str(e)}")


def generate_analysis_summary(state) -> Dict[str, Any]:
    """生成分析总结"""
    return {
        "total_stages": len(state.alternative_paths) + 1,
        "primary_path": state.analysis_depth,
        "collaboration_quality": state.collaboration_quality,
        "decision_confidence": state.analysis_confidence,
        "efficiency_metrics": {
            "error_rate": state.error_count,
            "retry_count": sum(state.retry_attempts.values()),
            "alternative_routes": len(state.alternative_paths)
        },
        "recommendation_strength": (
            "high" if state.overall_score >= 80 else
            "medium" if state.overall_score >= 60 else "low"
        )
    }