# src/crews/decision_tasks.py
"""
决策团队 Task 定义
"""
from crewai import Task
from src.config import Config


def create_investment_strategy_task(tasks_config=None):
    if tasks_config and 'investment_strategy' in tasks_config:
        return Task(config=tasks_config['investment_strategy'], agent=None)
    return Task(
        description="""基于分析结果，为{company}制定投资策略：
        1. 评估当前估值水平
        2. 确定投资时机和仓位
        3. 制定买入/卖出策略
        4. 设置止损止盈位""",
        expected_output="投资策略方案，含操作建议",
        agent=None,
    )


def create_risk_assessment_task(tasks_config=None):
    if tasks_config and 'risk_assessment' in tasks_config:
        return Task(config=tasks_config['risk_assessment'], agent=None)
    return Task(
        description="""评估{company}的投资风险并制定风控策略：
        1. 综合评估各类风险
        2. 制定风险控制措施
        3. 设定风险限额
        4. 给出风险应对预案""",
        expected_output="风险评估报告",
        agent=None,
    )


def create_report_generation_task(tasks_config=None):
    if tasks_config and 'report_generation' in tasks_config:
        return Task(config=tasks_config['report_generation'], agent=None)
    return Task(
        description="""生成{company}的投资分析报告：
        1. 整合所有分析结果
        2. 生成投资建议
        3. 输出Markdown格式报告
        4. 导出JSON数据""",
        expected_output="完整的投资分析报告",
        agent=None,
    )


def create_quality_assurance_task(tasks_config=None):
    if tasks_config and 'quality_assurance' in tasks_config:
        return Task(config=tasks_config['quality_assurance'], agent=None)
    return Task(
        description="""对{company}的投资分析过程和结论进行质量审核：
        1. 检查数据来源可靠性
        2. 验证分析逻辑正确性
        3. 审核结论合理性
        4. 给出质量评分""",
        expected_output="质量审核报告",
        agent=None,
    )