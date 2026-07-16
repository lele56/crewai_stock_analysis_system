# src/crews/data_collection_agents.py
"""数据收集团队 Agent 定义"""

from crewai import Agent

from src.config import AnalysisProfile, Config
from src.tools.akshare_tools import AkShareTool
from src.tools.financial_tools import FinancialCalculatorTool
from src.tools.market_data_tool import MarketDataTool
from src.tools.reporting_tools import ReportWritingTool
from src.tools.technical_charting import ChartingTool
from src.tools.technical_tools import TechnicalAnalysisTool
from src.utils.cost_tracker import CostTracker
from src.utils.llm_factory import get_llm

_TOOL_REGISTRY = {
    "akshare_tool": AkShareTool,
    "financial_calculator_tool": FinancialCalculatorTool,
    "technical_analysis_tool": TechnicalAnalysisTool,
    "charting_tool": ChartingTool,
    "market_data_tool": MarketDataTool,
    "reporting_tool": ReportWritingTool,
}

_DEFAULT_TOOLS = [AkShareTool, FinancialCalculatorTool, MarketDataTool, TechnicalAnalysisTool, ReportWritingTool]
_TOOL_CACHE: dict[type, object] = {}


def _get_or_create_tool(cls: type) -> object:
    """懒加载工具实例，复用已有的"""
    if cls not in _TOOL_CACHE:
        _TOOL_CACHE[cls] = cls()
    return _TOOL_CACHE[cls]


def _resolve_tools(yaml_tool_names: list[str] | None) -> list:
    """根据 YAML 配置的工具名解析为工具实例，未实现的工具跳过"""
    if not yaml_tool_names:
        return [_get_or_create_tool(cls) for cls in _DEFAULT_TOOLS]
    tools = []
    for name in yaml_tool_names:
        cls = _TOOL_REGISTRY.get(name)
        if cls:
            tools.append(_get_or_create_tool(cls))
    return tools if tools else [_get_or_create_tool(cls) for cls in _DEFAULT_TOOLS]


def _agent_defaults(
    agent_cfg: dict | None = None,
    extra_tools: list | None = None,
    no_tools: bool = False,
    profile: AnalysisProfile | None = None,
    agent_name: str = "",
) -> dict:
    kwargs: dict = {
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
        yaml_tools = agent_cfg.get("tools") if agent_cfg else None
        tools = _resolve_tools(yaml_tools)
        if extra_tools:
            tools.extend(extra_tools)
        kwargs["tools"] = tools
    return kwargs


def create_data_collection_agents(
    agents_config: dict | None = None,
    profile: AnalysisProfile | None = None,
) -> dict:
    """创建数据收集 Agent 团队

    Args:
        agents_config: 自定义 Agent 配置，为 None 时使用默认配置
        profile: 分析深度，为 None 时使用 Config.ANALYSIS_PROFILE

    Returns:
        Agent ID 到 Agent 实例的映射字典
    """
    p = profile or Config.ANALYSIS_PROFILE
    profile_agents = Config.get_profile_agents("data", p)
    agents = {}

    config = agents_config or {}
    for agent_id, agent_cfg in config.items():
        if agent_id not in profile_agents:
            continue
        agents[agent_id] = Agent(config=agent_cfg, **_agent_defaults(agent_cfg, profile=p, agent_name=agent_id))

    return agents


def _get_default_agents_config() -> dict:
    """内置默认 Agent 配置（YAML 加载失败时的后备）"""
    return {
        "market_researcher": {
            "role": "市场研究员",
            "goal": "收集市场数据和行业信息",
            "backstory": "专注市场数据收集的专业研究员",
        },
        "financial_data_expert": {
            "role": "财务数据专家",
            "goal": "收集公司财务报表和财务指标",
            "backstory": "专注财务数据收集的专业人员",
        },
        "technical_analyst": {
            "role": "技术分析师",
            "goal": "收集技术分析所需的价格和交易数据",
            "backstory": "专注技术数据收集的专业人员",
        },
    }