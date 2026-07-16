# tests/test_integration.py
"""集成测试 - 端到端流程（不依赖 LLM）"""

import os
import tempfile
from unittest.mock import patch

import pytest

from src.crews.decision_executor import (
    _map_score_to_vote,
    run_collective_decision_vote,
)
from src.stock_analysis_system import StockAnalysisSystem


class TestDecisionExecutorIntegration:
    """测试决策执行器集成"""

    def test_map_score_to_vote_strong_buy(self):
        assert _map_score_to_vote(90.0, 0.7) == "强烈买入"

    def test_map_score_to_vote_buy(self):
        assert _map_score_to_vote(50.0, 0.7) == "买入"

    def test_map_score_to_vote_hold(self):
        assert _map_score_to_vote(30.0, 0.7) == "持有"

    def test_map_score_to_vote_sell(self):
        assert _map_score_to_vote(15.0, 0.7) == "卖出"

    def test_map_score_to_vote_strong_sell(self):
        assert _map_score_to_vote(10.0, 0.7) == "强烈卖出"

    def test_run_collective_decision_vote(self, sample_analysis_scores):
        result = run_collective_decision_vote("测试公司", "TEST", sample_analysis_scores)
        assert result["vote_id"] is not None
        assert result["result"] in ["强烈买入", "买入", "持有", "卖出", "强烈卖出"]
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["decision_type"] == "weighted"
        assert result["voter_count"] == 3

    


class TestStockAnalysisSystemIntegration:
    """测试股票分析系统集成"""

    @pytest.fixture
    def system(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch("src.config.Config.CACHE_DIR", tmpdir):
            sys = StockAnalysisSystem()
            yield sys

    def test_initialization(self, system):
        assert system.data_collection_crew is not None
        assert system.analysis_crew is not None
        assert system.decision_crew is not None
        assert len(system.get_analysis_history()) == 0

    def test_cache_flow(self, system):
        test_data = {
            "success": True,
            "company": "测试公司",
            "ticker": "TEST",
            "final_recommendation": {"action": "持有", "confidence": 0.7},
        }
        system.cache_manager.save_to_cache("TEST", test_data)
        assert system.cache_manager.check_cache("TEST") is True
        cached = system.cache_manager.get_from_cache("TEST")
        assert cached["success"] is True
        assert cached["company"] == "测试公司"

    def test_get_cache_stats(self, system):
        system.cache_manager.save_to_cache("TEST", {"data": "test"})
        stats = system.get_cache_stats()
        assert stats["cache_size"] == 1

    def test_clear_cache(self, system):
        system.cache_manager.save_to_cache("TEST", {"data": "test"})
        system.clear_cache()
        stats = system.get_cache_stats()
        assert stats["cache_size"] == 0

    def test_add_to_history(self, system):
        result = {
            "success": True,
            "company": "测试",
            "ticker": "TEST",
            "timestamp": "2026-01-01T00:00:00",
            "overall_score": 75.0,
            "investment_rating": {"rating": "买入"},
        }
        system.cache_manager.add_to_history(result)
        assert len(system.get_analysis_history()) == 1

    def test_export_history(self, system, tmp_path):
        system.cache_manager.add_to_history(
            {
                "success": True,
                "company": "测试公司",
                "ticker": "TEST",
                "timestamp": "2026-01-01T00:00:00",
                "overall_score": 75.0,
                "investment_rating": {"rating": "持有"},
            }
        )
        filepath = str(tmp_path / "history.json")
        system.export_history(filepath)
        assert os.path.exists(filepath)

    def test_export_history_empty(self, system, tmp_path):
        filepath = str(tmp_path / "empty.json")
        system.export_history(filepath)


class TestFullWorkflow:
    """端到端工作流测试（Mock LLM）"""

    @pytest.fixture
    def mock_system(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch("src.config.Config.CACHE_DIR", tmpdir):
            sys = StockAnalysisSystem()
            yield sys

    def test_full_analyze_workflow_mocked(self, mock_system):
        """完整分析流程（Mock所有外部依赖）"""
        mock_collection_result = {
            "status": "success",
            "result": "模拟数据收集结果",
            "company": "测试公司",
            "ticker": "TEST",
            "execution_time": 1.0,
        }
        mock_analysis_result = {
            "success": True,
            "result": "模拟分析结果",
            "collaboration_scores": {
                "fundamental_score": 75,
                "risk_score": 60,
                "industry_score": 80,
                "quantitative_score": 70,
                "overall_score": 72,
            },
            "final_recommendation": {"action": "买入", "confidence": 0.8},
        }
        mock_decision_result = {
            "success": True,
            "result": "模拟决策结果",
            "final_recommendation": {"action": "买入", "confidence": 0.85},
        }

        with (
            patch.object(
                mock_system.data_collection_crew, "execute_data_collection", return_value=mock_collection_result
            ),
            patch.object(
                mock_system.analysis_crew, "execute_collaborative_analysis", return_value=mock_analysis_result
            ),
            patch.object(mock_system.decision_crew, "execute_decision_process", return_value=mock_decision_result),
            patch("src.stock_analysis_system.generate_analysis_summary", return_value="分析摘要"),
            patch("src.stock_analysis_system.generate_investment_report", return_value="投资报告"),
            patch("src.stock_analysis_system.save_report", return_value="/tmp/report.md"),
            patch("src.stock_analysis_system.export_to_json", return_value="/tmp/data.json"),
        ):
            result = mock_system.analyze_stock("测试公司", "TEST", use_cache=False)

        assert result["success"] is True
        assert result["company"] == "测试公司"
        assert result["ticker"] == "TEST"
        assert "investment_rating" in result
        assert "scores" in result

    def test_analyze_with_collection_failure(self, mock_system):
        """数据收集失败时的降级处理"""
        mock_collection_result = {
            "status": "failed",
            "error": "数据收集失败",
            "company": "测试公司",
            "ticker": "TEST",
        }

        with patch.object(
            mock_system.data_collection_crew, "execute_data_collection", return_value=mock_collection_result
        ):
            result = mock_system.analyze_stock("测试公司", "TEST", use_cache=False)

        assert result["success"] is False
        assert "数据收集失败" in result.get("error", "")

    def test_analyze_with_cache_hit(self, mock_system):
        """缓存命中时直接返回"""
        cached_result = {
            "success": True,
            "company": "测试公司",
            "ticker": "TEST",
            "final_recommendation": {"action": "持有", "confidence": 0.7},
        }
        mock_system.cache_manager.save_to_cache("TEST", cached_result)

        result = mock_system.analyze_stock("测试公司", "TEST", use_cache=True)
        assert result["success"] is True
        assert result["company"] == "测试公司"