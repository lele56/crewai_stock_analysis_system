# src/crews/decision_executor.py
"""
决策团队执行器 - 结果处理、集体决策投票、报告生成
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os
import logging

from src.tasks.collective_decision_maker import (
    CollectiveDecisionMaker,
    DecisionType,
    get_decision_maker,
    create_investment_decision_vote,
)
from src.tasks.task_dataclasses import VotingRecord
from src.tools.collaboration_optimizer import (
    analyze_collaboration_patterns,
    optimize_workload,
)

logger = logging.getLogger(__name__)


def prepare_decision_inputs(analysis_result: Dict) -> Dict:
    return {
        "company": analysis_result.get("company", ""),
        "ticker": analysis_result.get("ticker", ""),
        "scores": analysis_result.get("collaboration_scores", {}),
        "analysis_recommendations": analysis_result.get("final_recommendation", {}),
        "analysis_outputs": analysis_result.get("analysis_outputs", {}),
    }


def collect_decision_outputs(tasks_output: List[Any]) -> Dict[str, Any]:
    results = {}
    for i, output in enumerate(tasks_output):
        if hasattr(output, 'raw'):
            results[f"task_{i}"] = str(output.raw)
        elif hasattr(output, 'output'):
            results[f"task_{i}"] = str(output.output)
        else:
            results[f"task_{i}"] = str(output)
    return results


def run_collective_decision_vote(company: str, ticker: str,
                                  analysis_scores: Dict[str, float]) -> Dict[str, Any]:
    decision_maker = get_decision_maker()
    decision_maker.clear_history()

    votes = []
    for role, score in analysis_scores.items():
        if role != "overall_score" and score > 0:
            vote = create_investment_decision_vote(role, score, 0.8)
            votes.append(vote)

    if not votes:
        vote = create_investment_decision_vote("default", 50.0, 0.5)
        votes.append(vote)

    result = decision_maker.decide(votes)
    result["company"] = company
    result["ticker"] = ticker
    return result


def _map_score_to_vote(overall_score: float, confidence: float) -> str:
    if overall_score >= 80:
        return "强烈买入"
    elif overall_score >= 50:
        return "买入"
    elif overall_score >= 30:
        return "持有"
    elif overall_score >= 15:
        return "卖出"
    else:
        return "强烈卖出"


def extract_final_recommendation(decision_result: Dict) -> Dict[str, Any]:
    return {
        "action": decision_result.get("result", "持有"),
        "confidence": decision_result.get("confidence", 0.5),
    }


def calculate_decision_metrics(decision_result: Dict) -> Dict[str, Any]:
    return {
        "vote_count": decision_result.get("voter_count", 0),
        "decision_type": decision_result.get("decision_type", "weighted"),
        "confidence": decision_result.get("confidence", 0.0),
    }


def get_investment_rating(action: str) -> Dict:
    mapping = {
        "强烈买入": {"rating": "强烈买入", "score": 90},
        "买入": {"rating": "买入", "score": 70},
        "持有": {"rating": "持有", "score": 50},
        "卖出": {"rating": "卖出", "score": 30},
        "强烈卖出": {"rating": "强烈卖出", "score": 10},
    }
    return mapping.get(action, {"rating": action, "score": 50})


def generate_analysis_summary(
    company: str,
    ticker: str,
    scores: Dict[str, float],
    recommendation: Dict[str, Any],
    decision_metrics: Dict[str, Any],
) -> str:
    lines = [
        f"# 投资分析摘要: {company} ({ticker})",
        "",
        "## 维度评分",
        "",
    ]
    for name, score in scores.items():
        if name != "overall_score":
            lines.append(f"- **{name}**: {score:.1f}/100")
    lines.extend([
        "",
        f"## 综合评分",
        f"- **overall**: {scores.get('overall_score', 0):.1f}/100",
        "",
        f"## 最终建议",
        f"- **操作**: {recommendation.get('action', '持有')}",
        f"- **置信度**: {recommendation.get('confidence', 0):.1%}",
        f"- **投票人数**: {decision_metrics.get('vote_count', 0)}",
        "",
    ])
    return "\n".join(lines)


def generate_investment_report(
    company: str,
    ticker: str,
    data_collection_result: Dict,
    analysis_result: Dict,
    decision_result: Dict,
    summary: str,
) -> str:
    lines = [
        f"# 投资分析报告: {company} ({ticker})",
        "",
        "## 执行时间",
        f"- {datetime.now().isoformat()}",
        "",
        "## 分析摘要",
        summary,
        "",
        "## 数据收集",
        f"- 状态: {'成功' if data_collection_result.get('status') == 'success' else '失败'}",
        "",
        "## 分析评分",
    ]
    scores = analysis_result.get("collaboration_scores", {})
    for k, v in scores.items():
        lines.append(f"- {k}: {v:.1f}")
    lines.extend([
        "",
        "## 集体决策",
        f"- 决策结果: {decision_result.get('result', '未知')}",
        f"- 置信度: {decision_result.get('confidence', 0):.1%}",
        f"- 投票人数: {decision_result.get('voter_count', 0)}",
        "",
    ])
    return "\n".join(lines)


def save_report(report_content: str, company: str, ticker: str) -> str:
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analysis_{ticker}_{timestamp}.md"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_content)
    return filepath


def export_to_json(data: Dict, company: str, ticker: str) -> str:
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data_{ticker}_{timestamp}.json"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


def analyze_collective_decision(decision_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """分析集体决策结果，评估一致性和置信度"""
    outputs = list(decision_outputs.values())
    sentiments = []
    for output in outputs:
        text = str(output) if output else ""
        if "买入" in text and "强烈" in text:
            sentiments.append(("强烈买入", 0.9))
        elif "买入" in text:
            sentiments.append(("买入", 0.7))
        elif "卖出" in text and "强烈" in text:
            sentiments.append(("强烈卖出", 0.9))
        elif "卖出" in text:
            sentiments.append(("卖出", 0.7))
        else:
            sentiments.append(("持有", 0.5))

    if not sentiments:
        return {"consensus": "持有", "confidence": 0.5, "agreement": 0.0, "voter_count": 0}

    from collections import Counter
    vote_counts = Counter(s[0] for s in sentiments)
    total = len(sentiments)
    most_common = vote_counts.most_common(1)[0]
    agreement = most_common[1] / total if total > 0 else 0.0
    avg_confidence = sum(s[1] for s in sentiments) / total

    return {
        "consensus": most_common[0],
        "confidence": round(avg_confidence, 4),
        "agreement": round(agreement, 4),
        "voter_count": total,
        "vote_distribution": dict(vote_counts),
    }


def run_collaboration_optimization() -> Dict[str, Any]:
    from src.tasks.dynamic_task_allocation import get_task_allocator
    from src.tools.communication_tools import global_communication_hub

    allocator = get_task_allocator()
    hub = global_communication_hub

    stats = allocator.get_allocation_statistics()
    messages = hub.get_all_messages()

    analysis = analyze_collaboration_patterns(
        stats.get("allocation_history", []),
        messages,
    )

    actions = optimize_workload(analysis.get("agent_workload", {}))

    return {
        "efficiency": analysis.get("collaboration_efficiency", 0),
        "bottlenecks": analysis.get("bottlenecks", []),
        "recommendations": analysis.get("recommendations", []),
        "optimization_actions": actions,
    }