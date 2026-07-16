# src/crews/analysis_executor.py
"""分析团队执行器 - 结果处理、评分计算、协作分析"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def prepare_analysis_inputs(company: str, ticker: str, data_collection_result: Any) -> dict:
    """准备分析输入数据"""
    if hasattr(data_collection_result, "raw"):
        raw_text = str(data_collection_result.raw)
    elif isinstance(data_collection_result, str):
        raw_text = data_collection_result
    else:
        raw_text = str(data_collection_result)

    return {
        "company": company,
        "ticker": ticker,
        "raw_data": raw_text,
    }


def collect_analysis_outputs(tasks_output: list[Any]) -> dict[str, Any]:
    """收集各分析任务的输出结果"""
    results: dict[str, Any] = {}
    for i, output in enumerate(tasks_output):
        if hasattr(output, "raw"):
            results[f"task_{i}"] = str(output.raw)
        elif hasattr(output, "output"):
            results[f"task_{i}"] = str(output.output)
        else:
            results[f"task_{i}"] = str(output)
    return results


def calculate_collaboration_scores(tasks_outputs: list[Any]) -> dict[str, Any]:
    """计算协作评分"""
    scores: dict[str, Any] = {
        "fundamental_score": 0,
        "risk_score": 0,
        "industry_score": 0,
        "overall_score": 0,
    }
    mapping = [
        "fundamental_score",
        "risk_score",
        "industry_score",
    ]
    for i, output in enumerate(tasks_outputs):
        if i < len(mapping):
            text = str(output.raw) if hasattr(output, "raw") else str(output)
            score = _extract_score_from_text(text)
            scores[mapping[i]] = score

    valid_scores = [scores[k] for k in mapping if scores[k] > 0]
    scores["overall_score"] = sum(valid_scores) / len(valid_scores) if valid_scores else 50.0
    return scores


def _extract_score_from_text(text: str) -> float:
    import re

    patterns = [
        r"评分[：:]\s*(\d+(?:\.\d+)?)",
        r"score[：:\s]*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*分",
        r"(\d+(?:\.\d+)?)\s*/\s*100",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return min(float(match.group(1)), 100.0)
    return 50.0


def generate_final_recommendation(scores: dict[str, float]) -> dict[str, Any]:
    """根据评分生成最终投资建议"""
    overall = scores.get("overall_score", 50.0)
    if overall >= 80:
        action = "强烈买入"
        confidence = min(overall / 100, 0.95)
    elif overall >= 65:
        action = "买入"
        confidence = min(overall / 100, 0.85)
    elif overall >= 45:
        action = "持有"
        confidence = 0.6
    elif overall >= 30:
        action = "卖出"
        confidence = 0.7
    else:
        action = "强烈卖出"
        confidence = min((100 - overall) / 100, 0.9)
    return {
        "action": action,
        "confidence": round(confidence, 4),
        "overall_score": overall,
    }


def analyze_collaboration_quality(scores: dict[str, float]) -> dict[str, Any]:
    """分析协作质量"""
    score_values = [
        scores.get("fundamental_score", 0),
        scores.get("risk_score", 0),
        scores.get("industry_score", 0),
    ]
    valid = [s for s in score_values if s > 0]
    if len(valid) < 2:
        return {"consistency": "low", "collaboration_level": "minimal"}

    avg = sum(valid) / len(valid)
    variance = sum((s - avg) ** 2 for s in valid) / len(valid)
    std_dev = variance**0.5

    if std_dev < 10:
        consistency = "high"
    elif std_dev < 20:
        consistency = "medium"
    else:
        consistency = "low"

    return {
        "consistency": consistency,
        "std_dev": round(std_dev, 2),
        "collaboration_level": "high" if len(valid) >= 3 else "medium",
    }