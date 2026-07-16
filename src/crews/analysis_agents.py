# src/crews/analysis_agents.py
"""分析团队 Agent 定义
所有Agent工厂函数集中管理，参数统一从Config读取
"""

from crewai import Agent

from src.config import AnalysisProfile, Config
from src.tools.financial_tools import FinancialCalculatorTool
from src.tools.market_data_tool import MarketDataTool
from src.tools.reporting_tools import ReportWritingTool
from src.tools.technical_tools import TechnicalAnalysisTool
from src.utils.cost_tracker import CostTracker
from src.utils.llm_factory import get_llm

_TOOL_CLASSES = [ReportWritingTool, FinancialCalculatorTool, MarketDataTool, TechnicalAnalysisTool]
_TOOL_INSTANCES: dict[type, object] = {}


def _get_tools() -> list:
    """懒加载工具实例，复用已有的"""
    tools = []
    for cls in _TOOL_CLASSES:
        if cls not in _TOOL_INSTANCES:
            _TOOL_INSTANCES[cls] = cls()
        tools.append(_TOOL_INSTANCES[cls])
    return tools


def _agent_defaults(
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
        tools = _get_tools()
        if extra_tools:
            tools.extend(extra_tools)
        kwargs["tools"] = tools
    return kwargs


def create_fundamental_analyst(agents_config: dict | None = None) -> Agent:
    """创建基本面分析师 Agent（含量化验证能力）"""
    if agents_config and "fundamental_analyst" in agents_config:
        return Agent(config=agents_config["fundamental_analyst"], **_agent_defaults(agent_name="fundamental_analyst"))
    return Agent(
        role="高级基本面分析师",
        goal="深入分析公司的财务报表和基本面数据，评估公司内在价值，并用量化方法验证分析结论",
        backstory="""你是一位资深的基本面分析师，在华尔街工作超过20年。
        你对财务报表有着敏锐的洞察力，能够从繁杂的数据中发现关键问题。
        你擅长评估公司盈利能力、成长性和财务健康度，擅长识别财务造假和风险点。
        你的分析总是基于扎实的数据和严谨的逻辑，不被市场情绪所左右。
        同时你精通量化验证方法，能用统计模型计算合理估值区间和置信度。""",
        **_agent_defaults(agent_name="fundamental_analyst"),
    )


def create_risk_assessment_specialist(agents_config: dict | None = None) -> Agent:
    """创建风险评估专家 Agent

    Args:
        agents_config: 自定义 Agent 配置字典

    Returns:
        配置好的风险评估专家 Agent
    """
    if agents_config and "risk_assessment_specialist" in agents_config:
        return Agent(config=agents_config["risk_assessment_specialist"], **_agent_defaults(agent_name="risk_assessment_specialist"))
    return Agent(
        role="风险评估专家",
        goal="全面评估投资风险，识别潜在的下行风险和风险点",
        backstory="""你是一位严谨的风险评估专家，专注于识别和量化投资风险。
        你对市场波动、行业风险、公司特有风险都有深入的研究。
        你擅长用多种风险指标综合评估，不会放过任何潜在隐患。
        你总是给出客观冷静的风险评估，帮助投资者做好风险控制。""",
        **_agent_defaults(agent_name="risk_assessment_specialist"),
    )


def create_industry_expert(agents_config: dict | None = None) -> Agent:
    """创建行业研究专家 Agent

    Args:
        agents_config: 自定义 Agent 配置字典

    Returns:
        配置好的行业研究专家 Agent
    """
    if agents_config and "industry_expert" in agents_config:
        return Agent(config=agents_config["industry_expert"], **_agent_defaults(agent_name="industry_expert"))
    return Agent(
        role="行业研究专家",
        goal="分析行业趋势、竞争格局和公司地位，评估行业发展前景",
        backstory="""你是一位资深的行业分析师，对宏观经济和产业趋势有着深刻理解。
        你长期跟踪多个行业，了解产业链结构、竞争格局和技术变革方向。
        你能够准确判断行业生命周期和增长潜力，识别龙头企业和潜在黑马。
        你的分析帮助投资者把握行业大势，选对赛道。""",
        **_agent_defaults(agent_name="industry_expert"),
    )


def create_analysis_coordinator(agents_config: dict | None = None) -> Agent:
    """创建分析协调员 Agent

    Args:
        agents_config: 自定义 Agent 配置字典

    Returns:
        配置好的分析协调员 Agent（无工具，仅协调）
    """
    if agents_config and "analysis_coordinator" in agents_config:
        return Agent(config=agents_config["analysis_coordinator"], **_agent_defaults(no_tools=True, agent_name="analysis_coordinator"))
    return Agent(
        role="分析协调员",
        goal="协调整体分析流程，整合各方意见，形成综合分析结论",
        backstory="""你是分析团队的组织者和协调人。
        你擅长组织专家讨论，引导有效交流，整合不同观点。
        你能够发现分析中的遗漏，协调补充分析，确保分析完整全面。
        你最终负责整合所有专家意见，形成一致的分析结论。""",
        **_agent_defaults(no_tools=True, agent_name="analysis_coordinator"),
    )