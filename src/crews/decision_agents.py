# src/crews/decision_agents.py
"""决策团队 Agent 定义
所有Agent工厂函数集中管理，参数统一从Config读取
"""

from typing import Any

from crewai import Agent

from src.config import AnalysisProfile, Config
from src.tools.reporting_tools import DataExportTool, ReportWritingTool
from src.utils.cost_tracker import CostTracker
from src.utils.llm_factory import get_llm

_TOOL_INSTANCES: dict[type, object] = {}


def _get_tools() -> list:
    """懒加载工具实例，复用已有的"""
    if ReportWritingTool not in _TOOL_INSTANCES:
        _TOOL_INSTANCES[ReportWritingTool] = ReportWritingTool()
    return [_TOOL_INSTANCES[ReportWritingTool]]


def _agent_defaults(
    extra_tools: list | None = None,
    no_tools: bool = False,
    profile: AnalysisProfile | None = None,
    agent_name: str = "",
) -> dict[str, Any]:
    """Agent通用默认参数"""
    kwargs = {
        "verbose": Config.AGENT_VERBOSE,
        "llm": get_llm(),
        "allow_delegation": Config.AGENT_ALLOW_DELEGATION,
        "max_iter": Config.get_max_iter(profile),
        "memory": False,
        "cache": True,
    }
    if agent_name and Config.LLM_COST_TRACKING:
        kwargs["step_callback"] = CostTracker().step_callback(agent_name)
    if not no_tools:
        tools = _get_tools()
        if extra_tools:
            tools.extend(extra_tools)
        kwargs["tools"] = tools
    return kwargs


def create_investment_advisor(agents_config: dict | None = None) -> Agent:
    """投资策略顾问"""
    if agents_config and ("investment_advisor" in agents_config or "investment_strategy_advisor" in agents_config):
        cfg = agents_config.get("investment_advisor") or agents_config.get("investment_strategy_advisor")
        return Agent(config=cfg, **_agent_defaults(agent_name="investment_advisor"))
    return Agent(
        role="投资策略顾问",
        goal="为{company}制定投资策略，提供专业的投资建议",
        backstory="你是一位经验丰富的投资策略顾问，擅长制定长期投资策略和资产配置方案。",
        **_agent_defaults(agent_name="investment_advisor"),
    )


def create_report_generator(agents_config: dict | None = None) -> Agent:
    """报告生成器（含质量审核职能）"""
    if agents_config and "report_generator" in agents_config:
        return Agent(
        config=agents_config["report_generator"],
        **_agent_defaults(extra_tools=[DataExportTool()], agent_name="report_generator"))
    return Agent(
        role="报告生成专家",
        goal="生成专业的投资分析报告，并确保分析质量和结论的可靠性",
        backstory="""你是一位专业的报告生成专家，擅长将复杂的分析结果转化为清晰易懂的投资报告。
        同时你严格把控分析质量，能识别分析过程中的潜在问题，验证数据准确性，
        确保最终的分析结果可靠可信。""",
        **_agent_defaults(extra_tools=[DataExportTool()], agent_name="report_generator"),
    )