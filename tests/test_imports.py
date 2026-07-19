# tests/test_imports.py
"""验证所有核心模块可正常导入"""


def test_import_config():
    from src.config import Config

    assert Config.LLM_MODEL is not None


def test_import_task_dataclasses():
    from src.tasks.task_dataclasses import (
        AgentCapability,
    )

    assert len(AgentCapability) > 0


def test_import_collective_decision_maker():
    from src.tasks.collective_decision_maker import (
        get_decision_maker,
    )

    assert get_decision_maker() is not None


def test_import_financial_tools():
    from src.tools.financial_tools import FinancialCalculatorTool
    from src.tools.market_data_tool import MarketDataTool

    assert FinancialCalculatorTool is not None
    assert MarketDataTool is not None


def test_import_technical_tools():
    from src.tools.technical_tools import TechnicalAnalysisTool

    assert TechnicalAnalysisTool is not None


def test_import_analysis_agents():
    from src.crews.analysis_agents import (
        create_fundamental_analyst,
    )

    assert callable(create_fundamental_analyst)


def test_import_decision_agents():
    from src.crews.decision_agents import (
        create_investment_advisor,
    )

    assert callable(create_investment_advisor)


def test_import_decision_executor():
    from src.crews.decision_executor import (
        prepare_decision_inputs,
    )

    result = prepare_decision_inputs({"analysis_result": "test"})
    assert result is not None