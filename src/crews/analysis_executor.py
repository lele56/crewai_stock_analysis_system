# src/crews/analysis_executor.py
"""分析团队执行器 - 结果处理、评分计算、协作分析"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── 数据截断配置 ────────────────────────────────
_MAX_RAW_DATA_CHARS = 16000  # 单次传给分析 agent 的原始数据最大字符数，防止 prompt 过大导致超时

# ── 回退路径：原始文本分析索引 ──────────────────
# 仅在结构化数据提取失败时使用，按分析类型分配文本片段
_ANALYSIS_DATA_MAP = {
    "fundamental": [1, 2],  # 基本面分析：财务数据 + 财务比率
    "risk": [0, 3],         # 风险评估：市场数据 + 技术分析
    "industry": [0],        # 行业分析：市场数据
    "all": [0, 1, 2, 3, 4],  # 兜底：全部数据
}

# ── 评分阈值 → 操作建议 ──────────────────────────
_ACTION_THRESHOLDS = (
    (80, "强烈买入", 0.95),
    (65, "买入", 0.85),
    (45, "持有", 0.60),
    (30, "卖出", 0.70),
)

# ── 标准差 → 一致性映射（越小越好）───────────────
_STD_CONSISTENCY_THRESHOLDS = (
    (10, "high"),
    (20, "medium"),
)

# ── 评分提取正则（预编译）─────────────────────────
_SCORE_PATTERNS = [
    re.compile(r"评分[：:]\s*(\d+(?:\.\d+)?)"),
    re.compile(r"score[：:\s]*(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)\s*分"),
    re.compile(r"(\d+(?:\.\d+)?)\s*/\s*100"),
]

_FINAL_SCORE_PATTERNS = [
    re.compile(r"最终.*?评分[：:]\s*(\d+(?:\.\d+)?)"),
    re.compile(r"综合评分[：:]\s*(\d+(?:\.\d+)?)"),
    re.compile(r"最终.*?(\d+(?:\.\d+)?)\s*/\s*100"),
    re.compile(r"综合评分[：:]*\s*\*{0,2}(\d+(?:\.\d+)?)\s*/\s*100"),
]


def _get_crew_output(data: Any) -> Any:
    """从 dict 或 CrewOutput 中提取核心输出对象"""
    if isinstance(data, dict):
        return data.get("result")
    return data


def _has_prompt_keys(d: dict) -> bool:
    """检查 dict 是否已包含分析所需的 prompt 字段"""
    return all(k in d for k in ("financial_data", "risk_data", "industry_data"))


def prepare_analysis_inputs(company: str, ticker: str, data_collection_result: Any) -> dict:
    """准备分析输入数据 — 优先 output_pydantic，失败回退 JSON 文本解析

    返回三个独立字段，每个分析 Agent 只取自己需要的：
      - financial_data: 基本面分析用（财务 + 比率）
      - risk_data:      风险评估用（市场 + 技术）
      - industry_data:  行业分析用（市场 + 行业）
    """
    crew_output = _get_crew_output(data_collection_result)

    # 快速路径：数据采集阶段已直接返回结构化 prompt 数据
    if isinstance(crew_output, dict) and _has_prompt_keys(crew_output):
        logger.info(
            f"数据采集已结构化: company={company}, ticker={ticker}, "
            f"financial={len(crew_output.get('financial_data', ''))}chars, "
            f"risk={len(crew_output.get('risk_data', ''))}chars, "
            f"industry={len(crew_output.get('industry_data', ''))}chars"
        )
        return {
            "company": company,
            "ticker": ticker,
            "financial_data": crew_output.get("financial_data", ""),
            "risk_data": crew_output.get("risk_data", ""),
            "industry_data": crew_output.get("industry_data", ""),
            "raw_data": crew_output.get("financial_data", ""),
        }

    # 获取 tasks_output 列表（保留原始对象以访问 .pydantic 属性）
    tasks_output = _get_tasks_output_objects(crew_output)

    # 尝试结构化解析（优先 output_pydantic）
    from src.crews.data_parser import collection_data_to_prompt, parse_collection_data

    structured = parse_collection_data(tasks_output, company=company, ticker=ticker)
    prompt_data = collection_data_to_prompt(structured)

    # 检查结构化数据是否有效
    effective = any(len(v) > 30 for v in prompt_data.values())

    if effective:
        logger.info(
            f"结构化数据提取成功: company={company}, ticker={ticker}, "
            f"financial={len(prompt_data['financial_data'])}chars, "
            f"risk={len(prompt_data['risk_data'])}chars, "
            f"industry={len(prompt_data['industry_data'])}chars"
        )
        return {
            "company": company,
            "ticker": ticker,
            **prompt_data,
            "raw_data": prompt_data["financial_data"],
        }

    # 回退：原始文本拼接
    logger.warning("结构化数据提取失败，回退到原始文本模式")
    task_texts = _extract_task_texts(crew_output)
    return _prepare_raw_inputs(company, ticker, task_texts)


def _get_tasks_output_objects(crew_output: Any) -> list[Any]:
    """获取 tasks_output 原始对象列表（保留 .pydantic 属性）"""
    if crew_output is None:
        return []
    if hasattr(crew_output, "tasks_output"):
        return list(crew_output.tasks_output)
    return []


def _extract_task_texts(crew_output: Any) -> list[str]:
    """从 CrewOutput 中提取各任务原始文本列表"""
    if crew_output is None:
        return []

    if hasattr(crew_output, "tasks_output"):
        return [str(t.raw) for t in crew_output.tasks_output if hasattr(t, "raw")]
    if hasattr(crew_output, "raw"):
        return [str(crew_output.raw)]
    if isinstance(crew_output, str):
        return [crew_output]
    return [str(crew_output)]


def _prepare_raw_inputs(company: str, ticker: str, task_texts: list[str]) -> dict:
    """回退方案：原始文本拼接 + 清洗 + 截断"""
    def _build(analysis_type: str) -> str:
        indices = _ANALYSIS_DATA_MAP.get(analysis_type, [0, 1, 2, 3, 4])
        parts = [_clean_text(task_texts[i]) for i in indices if i < len(task_texts) and task_texts[i]]
        return _trim_text("\n\n".join(parts), _MAX_RAW_DATA_CHARS)

    financial_data = _build("fundamental")
    risk_data = _build("risk")
    industry_data = _build("industry")

    logger.info(
        f"原始文本模式: company={company}, ticker={ticker}, "
        f"financial={len(financial_data)}chars, risk={len(risk_data)}chars, "
        f"industry={len(industry_data)}chars"
    )
    return {
        "company": company,
        "ticker": ticker,
        "financial_data": financial_data,
        "risk_data": risk_data,
        "industry_data": industry_data,
        "raw_data": financial_data,
    }


_CLEAN_PATTERNS = [
    (re.compile(r"```(?:json|python|text)?\s*\n"), ""),     # markdown 代码块标记
    (re.compile(r"```\s*"), ""),                              # 闭合标记
    (re.compile(r"\n{3,}"), "\n\n"),                          # 超过 2 个连续换行 → 2 个
    (re.compile(r"[ \t]{2,}"), " "),                          # 连续空格/tab → 1 个空格
    (re.compile(r"^\s*[-*]{3,}\s*$", re.MULTILINE), ""),    # 分隔线 ---
]


def _clean_text(text: str) -> str:
    """清洗数据采集输出，去除冗余格式，保留信息内容"""
    for pattern, replacement in _CLEAN_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()


def _trim_text(text: str, max_length: int) -> str:
    """截断文本到指定长度，尽量在换行处截断"""
    if len(text) <= max_length:
        return text
    logger.warning(f"数据过长 ({len(text)} 字符)，截断至 {max_length} 字符")
    truncated = text[:max_length]
    last_nl = truncated.rfind("\n")
    if last_nl > max_length * 0.7:
        return truncated[:last_nl] + f"\n... [数据已截断，原长度 {len(text)} 字符]"
    return truncated + f"\n... [数据已截断，原长度 {len(text)} 字符]"


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
    """计算协作评分，附带数据质量标记"""
    mapping = ["fundamental_score", "risk_score", "industry_score"]
    scores: dict[str, Any] = dict.fromkeys(mapping, 0)
    scores["overall_score"] = 0

    for i, output in enumerate(tasks_outputs):
        if i < len(mapping):
            text = str(output.raw) if hasattr(output, "raw") else str(output)
            scores[mapping[i]] = _extract_score_from_text(text)

    valid = [scores[k] for k in mapping if scores[k] > 0]
    scores["overall_score"] = sum(valid) / len(valid) if valid else 50.0

    # 检测可疑评分（可能是幻觉）
    scores["_data_quality"] = _check_score_quality(scores)
    return scores


def _check_score_quality(scores: dict[str, Any]) -> str:
    """检测评分质量，返回 'good' / 'suspicious' / 'unreliable'"""
    mapping = ["fundamental_score", "risk_score", "industry_score"]
    raw = [scores.get(k, 0) for k in mapping]

    if all(s == 0 for s in raw):
        return "unreliable"

    suspicious_count = 0
    for s in raw:
        if s > 0 and s % 5 == 0:
            suspicious_count += 1

    if suspicious_count >= 2:
        return "suspicious"

    # 极端偏差检测：三个分数彼此差距过大也视为可疑
    non_zero = [s for s in raw if s > 0]
    if len(non_zero) >= 2 and max(non_zero) - min(non_zero) > 60:
        return "suspicious"

    return "good"


def _extract_score_from_text(text: str) -> float:
    """从文本中提取评分（0-100）— 优先匹配最终/综合评分，回退到第一个评分"""
    for pattern in _FINAL_SCORE_PATTERNS:
        m = pattern.search(text)
        if m:
            return min(float(m.group(1)), 100.0)
    for pattern in _SCORE_PATTERNS:
        m = pattern.search(text)
        if m:
            return min(float(m.group(1)), 100.0)
    return 50.0


def generate_final_recommendation(scores: dict[str, float]) -> dict[str, Any]:
    """根据评分生成最终投资建议 — 阈值查表"""
    overall = scores.get("overall_score", 50.0)
    for threshold, action, base_confidence in _ACTION_THRESHOLDS:
        if overall >= threshold:
            return {
                "action": action,
                "confidence": round(min(overall / 100, base_confidence), 4),
                "overall_score": overall,
            }
    # 兜底：强烈卖出
    return {
        "action": "强烈卖出",
        "confidence": round(min((100 - overall) / 100, 0.9), 4),
        "overall_score": overall,
    }


def analyze_collaboration_quality(scores: dict[str, float]) -> dict[str, Any]:
    """分析协作质量 — 基于标准差"""
    keys = ["fundamental_score", "risk_score", "industry_score"]
    valid = [scores.get(k, 0) for k in keys if scores.get(k, 0) > 0]

    if len(valid) < 2:
        return {"consistency": "low", "collaboration_level": "minimal", "std_dev": 0.0}

    avg = sum(valid) / len(valid)
    variance = sum((s - avg) ** 2 for s in valid) / len(valid)
    std_dev = variance**0.5

    consistency = _std_to_consistency(std_dev)
    return {
        "consistency": consistency,
        "std_dev": round(std_dev, 2),
        "collaboration_level": "high" if len(valid) >= 3 else "medium",
    }


def _std_to_consistency(std_dev: float) -> str:
    """标准差映射到一致性等级 — 阈值查表（越小越好）"""
    for threshold, label in _STD_CONSISTENCY_THRESHOLDS:
        if std_dev < threshold:
            return label
    return "low"


# ── 协作模式 ────────────────────────────────────

def generate_agent_abstract(agent_output: str, agent_name: str) -> dict[str, Any]:
    """为辩论模式生成 200 字结构化摘要，供其他 Agent 互审

    Returns:
        {"score": 77, "rating": "良好", "key_bull_points": [...],
         "key_bear_points": [...], "key_assumptions": [...],
         "controversial_claims": [...]}
    """
    score = _extract_score_from_text(agent_output)
    rating = _score_to_rating(score)

    return {
        "score": score,
        "rating": rating,
        "key_points": agent_output[:300],
        "agent_name": agent_name,
    }


def _score_to_rating(score: float) -> str:
    if score >= 80:
        return "优秀"
    if score >= 65:
        return "良好"
    if score >= 45:
        return "一般"
    if score >= 30:
        return "较差"
    return "差"


def build_iteration_prompt(
    coordinator_output: str,
    agent_outputs: dict[str, Any],
) -> list[dict[str, str]]:
    """构建迭代精炼的问题列表（STANDARD 模式）

    协调员找出矛盾点，为每个分析师生成针对性问题。
    Returns: [{"agent": "fundamental_analyst", "question": "..."}, ...]
    """
    questions = []
    outputs = {k: str(v) for k, v in agent_outputs.items() if not k.startswith("_")}

    if len(outputs) < 2:
        return questions

    texts = list(outputs.values())
    for i, (name, _text) in enumerate(outputs.items()):
        other_texts = [t for j, t in enumerate(texts) if j != i]
        if other_texts:
            question = (
                f"请审阅其他分析师的观点，对以下矛盾或遗漏进行补充分析：\n\n"
                f"其他分析师观点摘要：\n{other_texts[0][:500]}\n\n"
                f"请针对可能的矛盾点或遗漏维度，补充你的分析（300字以内）。"
            )
            questions.append({"agent": name, "question": question})

    return questions


def build_debate_prompt(
    agent_name: str,
    own_output: str,
    peer_abstracts: list[dict[str, Any]],
) -> str:
    """构建辩论模式的审阅 prompt（DEEP 模式）

    每个分析师读其他两人的摘要，输出审阅意见。
    """
    peer_text = "\n\n".join(
        f"### {a['agent_name']} (评分: {a['score']}, {a['rating']})\n{a['key_points']}"
        for a in peer_abstracts
    )
    return (
        f"你是一位{agent_name}。请审阅其他分析师的观点摘要，找出以下问题：\n\n"
        f"你的原始分析：\n{own_output[:500]}\n\n"
        f"其他分析师观点：\n{peer_text}\n\n"
        f"请输出：\n"
        f"1. 质疑: 指出其他分析师结论中的问题或矛盾\n"
        f"2. 补充: 补充其他分析师遗漏的重要维度\n"
        f"3. 修正: 你是否需要修正自己的评分？如需要，给出新评分和理由\n\n"
        f"请控制在300字以内。"
    )