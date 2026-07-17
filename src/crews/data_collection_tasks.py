# src/crews/data_collection_tasks.py
"""数据收集团队 Task 定义"""

from crewai import Task

# task_id → agent_id 映射
_TASK_AGENT_MAP = {
    "market_research": "market_researcher",
    "financial_data_collection": "financial_data_expert",
    "financial_ratio_calculation": "financial_ratio_analyst",
    "technical_data_collection": "technical_analyst",
    "data_collection_coordination": "data_collection_coordinator",
}


def _get_default_tasks_config() -> dict:
    return {
        "market_research": {
            "description": "收集{company}的市场数据和行业信息",
            "expected_output": "市场研究报告",
        },
        "financial_data_collection": {
            "description": "收集{company}(股票代码{ticker})的财务报表和关键财务指标，调用akshare_tool时传ticker={ticker}",
            "expected_output": "财务数据报告",
        },
        "financial_ratio_calculation": {
            "description": "对{company}(股票代码{ticker})进行财务比率分析。调用 financial_calculator_tool 两次：1) ticker={ticker}, calculation_type=liquidity,profitability 2) ticker={ticker}, calculation_type=leverage,growth,dcf,valuation。汇总两次结果生成报告",
            "expected_output": "财务比率分析报告",
        },
        "technical_data_collection": {
            "description": "收集{company}(股票代码{ticker})的技术分析数据，调用技术分析工具时传price_data={ticker}",
            "expected_output": "技术数据报告",
        },
    }


def create_data_collection_tasks(tasks_config: dict | None = None, agents: dict | None = None) -> list:
    """创建数据收集任务列表"""
    tasks = []
    config = tasks_config or _get_default_tasks_config()
    agents = agents or {}

    for task_id, task_cfg in config.items():
        agent_id = _TASK_AGENT_MAP.get(task_id)
        assigned_agent = agents.get(agent_id) if agent_id else None
        tasks.append(Task(config=task_cfg, agent=assigned_agent))

    return tasks