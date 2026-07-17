# src/crews/decision_tasks.py
"""决策团队 Task 定义"""

from crewai import Task


def create_investment_strategy_task(tasks_config: dict | None = None) -> Task:
    """创建投资策略任务"""
    if tasks_config and "investment_strategy" in tasks_config:
        return Task(config=tasks_config["investment_strategy"], agent=None)
    return Task(
        description="""基于以下分析结果，为{company}（{ticker}）制定投资策略。

【协作评分】
{scores}

【分析建议】
{analysis_recommendations}

【各专家分析输出】
{analysis_outputs}

请基于以上数据：
1. 评估当前估值水平
2. 确定投资时机和仓位
3. 制定买入/卖出策略
4. 设置止损止盈位""",
        expected_output="投资策略方案，含操作建议和置信度评分",
        agent=None,
    )


def create_report_generation_task(tasks_config: dict | None = None) -> Task:
    """创建报告生成任务（含质量审核）"""
    if tasks_config and "report_generation" in tasks_config:
        return Task(config=tasks_config["report_generation"], agent=None)
    return Task(
        description="""生成{company}的投资分析报告：
        1. 整合所有分析结果
        2. 生成投资建议
        3. 输出Markdown格式报告
        4. 导出JSON数据
        5. 审核数据来源可靠性和分析逻辑正确性
        6. 给出质量评分""",
        expected_output="完整的投资分析报告（含质量审核）",
        agent=None,
    )