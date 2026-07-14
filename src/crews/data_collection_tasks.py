# src/crews/data_collection_tasks.py
"""
数据收集团队 Task 定义
"""
from crewai import Task
from src.config import Config


def _get_default_tasks_config() -> dict:
    return {
        "market_research": {
            "description": "收集{company}的市场数据和行业信息",
            "expected_output": "市场研究报告",
        },
        "financial_data_collection": {
            "description": "收集{company}的财务报表和财务指标",
            "expected_output": "财务数据报告",
        },
        "technical_data_collection": {
            "description": "收集{company}的技术分析数据",
            "expected_output": "技术数据报告",
        },
    }


def create_data_collection_tasks(tasks_config=None) -> list:
    config = tasks_config or _get_default_tasks_config()
    tasks = []

    for task_id, task_cfg in config.items():
        tasks.append(Task(
            config=task_cfg,
            agent=None,
        ))

    return tasks