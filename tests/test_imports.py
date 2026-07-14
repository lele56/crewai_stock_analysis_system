# tests/test_imports.py
"""
验证所有核心模块可正常导入
"""
import pytest


def test_import_config():
    from src.config import Config
    assert Config.LLM_MODEL is not None


def test_import_task_dataclasses():
    from src.tasks.task_dataclasses import (
        AgentCapability, TaskComplexity, TaskStatus, DecisionType,
        VotingRecord, DynamicTask, AgentProfile,
    )
    assert len(AgentCapability) > 0


def test_import_collective_decision_maker():
    from src.tasks.collective_decision_maker import (
        CollectiveDecisionMaker, get_decision_maker, create_investment_decision_vote
    )
    assert get_decision_maker() is not None


def test_import_collaboration_optimizer():
    from src.tools.collaboration_optimizer import (
        analyze_collaboration_patterns, optimize_workload,
    )
    result = analyze_collaboration_patterns([], [])
    assert result["total_tasks"] == 0


def test_import_cache_manager():
    from src.utils.cache_manager import CacheManager, get_cache_manager
    assert get_cache_manager() is not None


def test_import_recovery_tools():
    from src.tools.reporting_tools import ReportWritingTool, DataExportTool
    assert ReportWritingTool is not None


def test_import_akshare_tools():
    from src.tools.akshare_tools import AkShareTool
    assert AkShareTool is not None


def test_import_financial_tools():
    from src.tools.financial_tools import FinancialCalculatorTool, MarketDataTool
    assert FinancialCalculatorTool is not None
    assert MarketDataTool is not None


def test_import_technical_tools():
    from src.tools.technical_tools import TechnicalAnalysisTool
    assert TechnicalAnalysisTool is not None


def test_import_communication_tools():
    from src.tools.communication_tools import (
        AgentCommunicationHub, global_communication_hub,
        generate_communication_summary, MessageType, MessagePriority,
    )
    assert global_communication_hub is not None


def test_import_analysis_agents():
    from src.crews.analysis_agents import (
        create_fundamental_analyst,
        create_risk_assessment_specialist,
        create_industry_expert,
        create_quantitative_analyst,
        create_analysis_coordinator,
    )
    assert callable(create_fundamental_analyst)


def test_import_decision_agents():
    from src.crews.decision_agents import (
        create_investment_advisor,
        create_risk_manager,
        create_portfolio_manager,
        create_market_strategist,
        create_decision_moderator,
        create_report_generator,
        create_quality_assurance_specialist,
    )
    assert callable(create_investment_advisor)


def test_import_data_collection_agents():
    from src.crews.data_collection_agents import (
        create_data_collection_agents,
        _get_default_agents_config,
    )
    assert callable(create_data_collection_agents)


def test_import_decision_executor():
    from src.crews.decision_executor import (
        run_collective_decision_vote,
        run_collaboration_optimization,
        _map_score_to_vote,
    )
    result = run_collective_decision_vote("TEST", "TST", {"fundamental": 80})
    assert result["result"] is not None