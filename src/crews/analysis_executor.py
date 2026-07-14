# src/crews/analysis_executor.py
"""
分析团队执行器 - 结果处理、评分计算、协作分析
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def prepare_analysis_inputs(company: str, ticker: str, data_collection_result: Dict) -> Dict:
    return {
        "company": company,
        "ticker": ticker,
        "financial_data": data_collection_result.get("financial_data", {}),
        "market_data": data_collection_result.get("market_data", {}),
        "industry_data": data_collection_result.get("industry_data", {}),
        "news_data": data_collection_result.get("news_data", {}),
    }


def collect_analysis_outputs(tasks_output: List[Any]) -> Dict[str, Any]:
    results = {}
    for i, output in enumerate(tasks_output):
        if hasattr(output, 'raw'):
            results[f"task_{i}"] = str(output.raw)
        elif hasattr(output, 'output'):
            results[f"task_{i}"] = str(output.output)
        else:
            results[f"task_{i}"] = str(output)
    return results


def calculate_collaboration_scores(tasks_outputs: List[Any]) -> Dict[str, Any]:
    scores = {
        "fundamental_score": 0,
        "risk_score": 0,
        "industry_score": 0,
        "quantitative_score": 0,
        "overall_score": 0,
    }
    mapping = [
        "fundamental_score",
        "risk_score",
        "industry_score",
        "quantitative_score",
    ]
    for i, output in enumerate(tasks_outputs):
        if i < len(mapping):
            text = str(output.raw) if hasattr(output, 'raw') else str(output)
            score = _extract_score_from_text(text)
            scores[mapping[i]] = score

    valid_scores = [scores[k] for k in mapping if scores[k] > 0]
    scores["overall_score"] = sum(valid_scores) / len(valid_scores) if valid_scores else 50.0
    return scores


def _extract_score_from_text(text: str) -> float:
    import re
    patterns = [
        r'评分[：:]\s*(\d+(?:\.\d+)?)',
        r'score[：:\s]*(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*分',
        r'(\d+(?:\.\d+)?)\s*/\s*100',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return min(float(match.group(1)), 100.0)
    return 50.0


def generate_final_recommendation(scores: Dict[str, float]) -> Dict[str, Any]:
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


def analyze_collaboration_quality(scores: Dict[str, float]) -> Dict[str, Any]:
    score_values = [
        scores.get("fundamental_score", 0),
        scores.get("risk_score", 0),
        scores.get("industry_score", 0),
        scores.get("quantitative_score", 0),
    ]
    valid = [s for s in score_values if s > 0]
    if len(valid) < 2:
        return {"consistency": "low", "collaboration_level": "minimal"}

    avg = sum(valid) / len(valid)
    variance = sum((s - avg) ** 2 for s in valid) / len(valid)
    std_dev = variance ** 0.5

    if std_dev < 10:
        consistency = "high"
    elif std_dev < 20:
        consistency = "medium"
    else:
        consistency = "low"

    return {
        "consistency": consistency,
        "std_dev": round(std_dev, 2),
        "collaboration_level": "high" if len(valid) >= 4 else "medium",
    }