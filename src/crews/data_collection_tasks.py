# src/crews/data_collection_tasks.py
"""数据收集团队 Task 定义"""

from crewai import Task

from src.crews.data_schemas import (
    FinancialDataOutput,
    FinancialRatioOutput,
    MarketResearchOutput,
    TechnicalDataOutput,
)

# task_id → agent_id 映射
_TASK_AGENT_MAP = {
    "market_research": "market_researcher",
    "financial_data_collection": "financial_data_expert",
    "financial_ratio_calculation": "financial_ratio_analyst",
    "technical_data_collection": "technical_analyst",
    "data_collection_coordination": "data_collection_coordinator",
}

# task_id → output_pydantic 模型（强制 LLM 输出结构化 JSON）
_TASK_OUTPUT_MODEL = {
    "market_research": MarketResearchOutput,
    "financial_data_collection": FinancialDataOutput,
    "financial_ratio_calculation": FinancialRatioOutput,
    "technical_data_collection": TechnicalDataOutput,
}


def _get_default_tasks_config() -> dict:
    return {
        "market_research": {
            "description": (
                "收集{company}的市场数据和行业信息。\n\n"
                "需要获取以下数据（使用 ak_share_data_tool 工具）：\n"
                "- 当前股价、涨跌幅、成交量、20日均量\n"
                "- 52周最高/最低价\n"
                "- Beta系数、30日波动率\n"
                "- 所属板块、行业名称、行业地位（龙头/领先/跟随/挑战者）\n"
                "- 市场份额、主要竞争对手\n"
                "- 行业增长率、行业规模\n"
                "- 行业发展趋势、机遇和挑战"
            ),
            "expected_output": "市场数据和行业信息的结构化报告",
        },
        "financial_data_collection": {
            "description": (
                "收集{company}(股票代码{ticker})的财务报表和关键财务指标。\n\n"
                "需要获取以下数据（使用 ak_share_data_tool 工具）：\n"
                "- 近三年营收和净利润（按年份列出）\n"
                "- 总资产、总负债、经营现金流\n"
                "- 毛利率、净利率、ROE、ROA\n"
                "- 资产负债率、流动比率、速动比率\n"
                "- 营收同比增长率、净利润同比增长率\n"
                "- PE、PB、PS、总市值、股息率"
            ),
            "expected_output": "财务数据的结构化报告",
        },
        "financial_ratio_calculation": {
            "description": (
                "对{company}(股票代码{ticker})进行财务比率分析。"
                "调用 financial_calculator_tool 两次："
                "1) ticker={ticker}, calculation_type=liquidity,profitability "
                "2) ticker={ticker}, calculation_type=leverage,growth,dcf,valuation。"
                "汇总两次结果，输出所有财务指标。\n\n"
                "需要输出的字段：\n"
                "- 近三年营收和净利润\n"
                "- 总资产、总负债、经营现金流\n"
                "- 毛利率、净利率、ROE、ROA\n"
                "- 资产负债率、流动比率、速动比率\n"
                "- 营收增长率、利润增长率\n"
                "- PE、PB、PS、总市值、股息率"
            ),
            "expected_output": "财务比率分析的结构化报告",
        },
        "technical_data_collection": {
            "description": (
                "收集{company}(股票代码{ticker})的技术分析数据。"
                "调用技术分析工具时传price_data={ticker}。\n\n"
                "需要获取以下技术指标：\n"
                "- MA5、MA20、MA50、MA200 均线\n"
                "- RSI(14)\n"
                "- MACD值、MACD信号线、MACD柱\n"
                "- 布林带上轨、中轨、下轨\n"
                "- ATR(14)"
            ),
            "expected_output": "技术分析数据的结构化报告",
        },
    }


def create_data_collection_tasks(tasks_config: dict | None = None, agents: dict | None = None) -> list:
    """创建数据收集任务列表，每个任务绑定 output_pydantic 强制结构化输出"""
    tasks = []
    config = tasks_config or _get_default_tasks_config()
    agents = agents or {}

    for task_id, task_cfg in config.items():
        agent_id = _TASK_AGENT_MAP.get(task_id)
        assigned_agent = agents.get(agent_id) if agent_id else None

        output_model = _TASK_OUTPUT_MODEL.get(task_id)
        if output_model:
            task = Task(
                description=task_cfg["description"],
                expected_output=task_cfg.get("expected_output", ""),
                agent=assigned_agent,
                output_pydantic=output_model,
            )
        else:
            task = Task(config=task_cfg, agent=assigned_agent)

        tasks.append(task)

    return tasks