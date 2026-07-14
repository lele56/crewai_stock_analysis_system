# src/crews/data_collection_agents.py
"""
数据收集团队 Agent 定义
"""
from crewai import Agent
from src.config import Config
from src.tools.akshare_tools import AkShareTool
from src.tools.reporting_tools import ReportWritingTool


def _agent_defaults(extra_tools=None, no_tools=False):
    kwargs = dict(
        verbose=Config.AGENT_VERBOSE,
        llm=Config.LLM_MODEL,
        allow_delegation=Config.AGENT_ALLOW_DELEGATION,
        max_iter=Config.AGENT_MAX_ITER,
        memory=False,
        cache=True,
    )
    if not no_tools:
        tools = [AkShareTool(), ReportWritingTool()]
        if extra_tools:
            tools.extend(extra_tools)
        kwargs['tools'] = tools
    return kwargs


def _get_default_agents_config() -> dict:
    return {
        "market_researcher": {
            "role": "市场研究员",
            "goal": "收集市场数据和行业信息",
            "backstory": "专注市场数据收集的专业研究员",
        },
        "financial_data_collector": {
            "role": "财务数据收集员",
            "goal": "收集公司财务报表和财务指标",
            "backstory": "专注财务数据收集的专业人员",
        },
        "technical_data_collector": {
            "role": "技术数据收集员",
            "goal": "收集技术分析所需的价格和交易数据",
            "backstory": "专注技术数据收集的专业人员",
        },
    }


def create_data_collection_agents(agents_config=None) -> dict:
    config = agents_config or _get_default_agents_config()
    agents = {}

    for agent_id, agent_cfg in config.items():
        agents[agent_id] = Agent(
            config=agent_cfg,
            **_agent_defaults()
        )

    return agents