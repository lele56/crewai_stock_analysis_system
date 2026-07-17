# src/crews/decision_executor.py
"""决策团队执行器 - 结果处理、集体决策投票、报告生成"""

from datetime import datetime
import json
import logging
import os
from typing import Any

from src.tasks.collective_decision_maker import (
    create_investment_decision_vote,
    get_decision_maker,
)

logger = logging.getLogger(__name__)


def prepare_decision_inputs(analysis_result: dict) -> dict:
    """准备决策输入"""
    return {
        "company": analysis_result.get("company", ""),
        "ticker": analysis_result.get("ticker", ""),
        "scores": analysis_result.get("collaboration_scores", {}),
        "analysis_recommendations": analysis_result.get("final_recommendation", {}),
        "analysis_outputs": analysis_result.get("agent_outputs", {}),
    }


def collect_decision_outputs(tasks_output: list[Any]) -> dict[str, Any]:
    """收集决策输出"""
    results = {}
    for i, output in enumerate(tasks_output):
        if hasattr(output, "raw"):
            results[f"task_{i}"] = str(output.raw)
        elif hasattr(output, "output"):
            results[f"task_{i}"] = str(output.output)
        else:
            results[f"task_{i}"] = str(output)
    return results


def run_collective_decision_vote(company: str, ticker: str, analysis_scores: dict[str, float]) -> dict[str, Any]:
    """运行集体决策投票"""
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
    if overall_score >= 50:
        return "买入"
    if overall_score >= 30:
        return "持有"
    if overall_score >= 15:
        return "卖出"
    return "强烈卖出"


def extract_final_recommendation(decision_result: dict) -> dict[str, Any]:
    """提取最终建议"""
    return {
        "action": decision_result.get("consensus", decision_result.get("result", "持有")),
        "confidence": decision_result.get("confidence", 0.5),
    }


def calculate_decision_metrics(decision_result: dict) -> dict[str, Any]:
    """计算决策指标"""
    return {
        "vote_count": decision_result.get("voter_count", 0),
        "decision_type": decision_result.get("decision_type", "weighted"),
        "confidence": decision_result.get("confidence", 0.0),
    }


def get_investment_rating(action: str) -> dict:
    """获取投资评级"""
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
    scores: dict[str, float],
    recommendation: dict[str, Any],
    decision_metrics: dict[str, Any],
) -> str:
    """生成分析摘要"""
    lines = [
        f"# 投资分析摘要: {company} ({ticker})",
        "",
        "## 维度评分",
        "",
    ]
    for name, score in scores.items():
        if name != "overall_score":
            lines.append(f"- **{name}**: {score:.1f}/100")
    lines.extend(
        [
            "",
            "## 综合评分",
            f"- **overall**: {scores.get('overall_score', 0):.1f}/100",
            "",
            "## 最终建议",
            f"- **操作**: {recommendation.get('action', '持有')}",
            f"- **置信度**: {recommendation.get('confidence', 0):.1%}",
            f"- **投票人数**: {decision_metrics.get('vote_count', 0)}",
            "",
        ]
    )
    return "\n".join(lines)


def generate_investment_report(
    company: str,
    ticker: str,
    data_collection_result: dict,
    analysis_result: dict,
    decision_result: dict,
    summary: str,
) -> str:
    """生成投资报告 — 数据驱动，LLM 分析仅作补充"""
    scores = analysis_result.get("collaboration_scores", {})
    overall = scores.get("overall_score", 0)
    recommendation = decision_result.get("final_recommendation", {})
    action = recommendation.get("action", "持有")
    confidence = recommendation.get("confidence", 0)

    # 评级颜色
    rating_map = {
        "强烈买入": "🟢", "买入": "🟢", "持有": "🟡", "卖出": "🔴", "强烈卖出": "🔴",
    }
    emoji = rating_map.get(action, "⚪")

    def _bar(score: float, width: int = 20) -> str:
        filled = int(score / 100 * width)
        return "█" * filled + "░" * (width - filled)

    lines = [
        f"# 投资分析报告: {company} ({ticker})",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        f"## {emoji} 投资结论: {action}（置信度 {confidence:.0%}）",
        "",
        "---",
        "",
        "## 综合评分",
        "",
        f"| 维度 | 评分 | 评级 |",
        f"|------|------|------|",
    ]
    for name, score in scores.items():
        if name != "overall_score":
            level = "优秀" if score >= 80 else "良好" if score >= 60 else "一般" if score >= 40 else "较差"
            lines.append(f"| {name} | {score:.1f} | {level} |")
    lines.append(f"| **综合** | **{overall:.1f}** | **{_get_rating_label(overall)}** |")

    lines.extend([
        "",
        f"```",
        f"综合评分: {_bar(overall)} {overall:.1f}/100",
        f"```",
        "",
        "---",
        "",
        "## 数据采集状态",
        "",
        f"- 数据采集: {'✅ 成功' if data_collection_result.get('status') == 'success' else '❌ 失败'}",
        f"- 数据时间: {data_collection_result.get('timestamp', 'N/A')}",
        f"- 采集耗时: {data_collection_result.get('execution_time', 0):.1f} 秒",
        "",
        "---",
        "",
        "## 决策详情",
        "",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 最终决策 | **{action}** |",
        f"| 置信度 | {confidence:.1%} |",
        f"| 投票人数 | {decision_result.get('collective_decision_metrics', {}).get('vote_count', 0)} |",
        f"| 决策类型 | {decision_result.get('collective_decision_metrics', {}).get('decision_type', 'N/A')} |",
        "",
        "---",
        "",
        "## AI 分析摘要",
        "",
        "> ⚠️ 以下内容由 AI 模型基于收集的数据生成，仅供参考，不构成投资建议。",
        "> 评分和决策基于真实数据计算，AI 分析为辅助解读。",
        "",
        summary,
        "",
        "---",
        "",
        "## 免责声明",
        "",
        "本报告由 AI 投资分析系统自动生成，数据来源于公开市场信息。",
        "报告中评分和决策基于真实数据计算，分析文字由 AI 辅助生成。",
        "**本报告不构成任何投资建议，投资有风险，入市需谨慎。**",
        "",
    ])
    return "\n".join(lines)


def _get_rating_label(score: float) -> str:
    if score >= 80:
        return "优秀"
    if score >= 60:
        return "良好"
    if score >= 40:
        return "一般"
    if score >= 20:
        return "较差"
    return "差"


def save_report(report_content: str, company: str, ticker: str) -> dict[str, str]:
    """保存报告为 .md 和 .docx，返回两个路径"""
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"analysis_{ticker}_{timestamp}"

    md_path = os.path.join(reports_dir, f"{base}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    docx_path = _save_docx(report_content, reports_dir, base)

    return {"md": md_path, "docx": docx_path}


def _save_docx(content: str, reports_dir: str, base: str) -> str:
    """生成 .docx 文件"""
    try:
        from docx import Document
        from docx.shared import Inches, Pt, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        style = doc.styles["Normal"]
        style.font.size = Pt(11)
        style.font.name = "Microsoft YaHei"

        for line in content.split("\n"):
            if line.startswith("# ") and not line.startswith("## "):
                doc.add_heading(line[2:], level=1)
            elif line.startswith("## "):
                doc.add_heading(line[3:], level=2)
            elif line.startswith("### "):
                doc.add_heading(line[4:], level=3)
            elif line.startswith("---"):
                doc.add_paragraph("─" * 60)
            elif line.startswith("- ") or line.startswith("* "):
                doc.add_paragraph(line[2:], style="List Bullet")
            elif line.strip():
                doc.add_paragraph(line)

        docx_path = os.path.join(reports_dir, f"{base}.docx")
        doc.save(docx_path)
        logger.info(f"DOCX报告已保存: {docx_path}")
        return docx_path
    except Exception as e:
        logger.warning(f"DOCX生成失败: {str(e)[:60]}")
        return ""


class _SafeEncoder(json.JSONEncoder):
    """安全JSON编码器，处理CrewOutput等不可序列化对象"""
    def default(self, obj):
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__}>"


def export_to_json(data: dict, company: str, ticker: str) -> str:
    """导出为JSON"""
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data_{ticker}_{timestamp}.json"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, cls=_SafeEncoder)
    return filepath


def analyze_collective_decision(decision_outputs: dict[str, Any]) -> dict[str, Any]:
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