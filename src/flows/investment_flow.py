# src/flows/investment_flow.py
"""智能投资流程控制 - 使用CrewAI Flows实现智能路由和条件分支"""

from datetime import datetime
import logging
from typing import Any

from crewai.flow.flow import Flow, listen, or_, router, start
from pydantic import BaseModel

from src.crews.analysis_crew import AnalysisCrew
from src.crews.data_collection_crew import DataCollectionCrew
from src.crews.decision_crew import DecisionCrew
from src.flows.investment_flow_helpers import (
    analyze_company_profile,
    assess_data_quality,
    determine_analysis_depth,
    generate_analysis_summary,
    update_analysis_state,
    update_decision_state,
)

logger = logging.getLogger(__name__)


class AnalysisState(BaseModel):
    """分析状态模型"""

    company: str = ""
    ticker: str = ""
    market_sentiment: str = "neutral"
    financial_score: float = 0.0
    risk_level: str = "unknown"
    industry_position: str = "unknown"
    analysis_depth: str = "standard"
    final_recommendation: str = "hold"
    overall_score: float = 0.0
    current_stage: str = "initialized"
    start_time: str | None = None
    end_time: str | None = None
    data_quality: str = "unknown"
    error_count: int = 0
    warnings: list[str] = []
    data_completeness: float = 0.0
    analysis_confidence: float = 0.0
    market_volatility: str = "medium"
    company_size: str = "medium"
    industry_trend: str = "stable"
    collaboration_quality: str = "medium"
    decision_complexity: str = "standard"
    retry_attempts: dict[str, int] = {}
    alternative_paths: list[str] = []
    # 数据传递：存储各阶段产出，供下游 agent 使用
    _collection_data: dict[str, Any] = {}
    _analysis_result: dict[str, Any] = {}


class SmartInvestmentFlow(Flow[AnalysisState]):
    """智能投资分析流程"""

    def __init__(self) -> None:
        super().__init__()
        self.data_collection_crew = DataCollectionCrew()
        self.analysis_crew = AnalysisCrew()
        self.decision_crew = DecisionCrew()

    @start()
    def initialize_analysis(self) -> dict[str, Any]:
        """初始化分析流程"""
        logger.info("=== 初始化智能投资分析流程 ===")
        self.state.current_stage = "initialization"
        self.state.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        company = input("请输入要分析的公司名称: ")
        ticker = input("请输入股票代码: ")
        company_profile = analyze_company_profile(company, ticker)
        self.state.company = company
        self.state.ticker = ticker
        self.state.company_size = company_profile.get("size", "medium")
        self.state.industry_trend = company_profile.get("trend", "stable")
        self.state.analysis_depth = determine_analysis_depth(company_profile)
        logger.info(f"开始分析 {company} ({ticker}), 深度: {self.state.analysis_depth}")
        return {"company": company, "ticker": ticker, "profile": company_profile}

    # ── 数据收集阶段 ──────────────────────────────

    @listen("initialize_analysis")
    def execute_data_collection(self, init_result: dict[str, Any]) -> dict[str, Any]:
        """执行数据收集"""
        logger.info("=== 数据收集 ===")
        self.state.current_stage = "data_collection"
        try:
            result = self.data_collection_crew.execute_data_collection(self.state.company, self.state.ticker)
            if not (result.get("success") or result.get("status") == "success"):
                return self._handle_stage_failure("data_collection", result)
            self.state._collection_data = result
            quality = assess_data_quality(result)
            self.state.data_quality = quality["overall_quality"]
            self.state.data_completeness = quality["completeness"]
            logger.info(f"数据收集成功 - 质量: {self.state.data_quality}")
            return {"success": True, "data": result, "data_quality": quality}
        except Exception as e:
            return self._handle_stage_exception("data_collection", e)

    @listen("execute_data_collection")
    @router
    def route_analysis_strategy(self, data_result: dict[str, Any]) -> str:
        """智能分析策略路由"""
        if not data_result.get("success", False):
            return "rapid_analysis"
        quality = data_result.get("data_quality", {}).get("overall_quality", "unknown")
        if quality == "excellent" and self.state.analysis_depth == "deep":
            return "deep_analysis"
        if quality in ("good", "excellent"):
            return "standard_analysis"
        return "rapid_analysis"

    # ── 分析阶段 ──────────────────────────────────

    @listen("route_analysis_strategy")
    def deep_analysis(self, route_result: dict[str, Any]) -> dict[str, Any]:
        """深度分析策略：全量 agents + 协作"""
        return self._execute_analysis("deep")

    @listen("route_analysis_strategy")
    def standard_analysis(self, route_result: dict[str, Any]) -> dict[str, Any]:
        """标准分析策略"""
        return self._execute_analysis("standard")

    @listen("route_analysis_strategy")
    def rapid_analysis(self, route_result: dict[str, Any]) -> dict[str, Any]:
        """快速分析策略：最少 agents"""
        return self._execute_analysis("rapid")

    def _execute_analysis(self, analysis_type: str) -> dict[str, Any]:
        """执行分析"""
        logger.info(f"=== {analysis_type} 分析 ===")
        self.state.current_stage = "analysis"
        try:
            result = self.analysis_crew.execute_collaborative_analysis(
                self.state.company, self.state.ticker, self._get_latest_data_collection_result()
            )
            if not result["success"]:
                return self._handle_stage_failure("analysis", result)
            self.state._analysis_result = result
            update_analysis_state(self.state, result)
            logger.info(f"{analysis_type} 分析完成")
            return {"success": True, "analysis": result, "analysis_type": analysis_type}
        except Exception as e:
            return self._handle_stage_exception("analysis", e)

    @listen(or_("deep_analysis", "standard_analysis", "rapid_analysis"))
    @router
    def route_decision_strategy(self, analysis_result: dict[str, Any]) -> str:
        """智能决策策略路由"""
        if not analysis_result.get("success", False):
            return "conservative_decision"
        consistency = (
            analysis_result.get("analysis", {})
            .get("collaboration_metrics", {})
            .get("consistency", "unknown")
        )
        if consistency == "high" and self.state.company_size == "large":
            return "collective_decision"
        if consistency in ("high", "medium"):
            return "standard_decision"
        return "rapid_decision"

    # ── 决策阶段 ──────────────────────────────────

    @listen("route_decision_strategy")
    def collective_decision(self, route_result: dict[str, Any]) -> dict[str, Any]:
        """集体决策策略：多 agents 投票"""
        return self._execute_decision("collective")

    @listen("route_decision_strategy")
    def standard_decision(self, route_result: dict[str, Any]) -> dict[str, Any]:
        """标准决策策略"""
        return self._execute_decision("standard")

    @listen("route_decision_strategy")
    def rapid_decision(self, route_result: dict[str, Any]) -> dict[str, Any]:
        """快速决策策略：单 agent 直接出结果"""
        return self._execute_decision("rapid")

    @listen("route_decision_strategy")
    def conservative_decision(self, route_result: dict[str, Any]) -> dict[str, Any]:
        """保守决策策略：数据不足时降级使用"""
        return self._execute_decision("conservative")

    def _execute_decision(self, decision_type: str) -> dict[str, Any]:
        """执行决策"""
        logger.info(f"=== {decision_type} 决策 ===")
        self.state.current_stage = "decision"
        try:
            result = self.decision_crew.execute_collective_decision(
                self.state.company, self.state.ticker, self._get_latest_analysis_result()
            )
            if not result["success"]:
                return self._handle_stage_failure("decision", result)
            update_decision_state(self.state, result)
            logger.info(f"{decision_type} 决策完成")
            return {"success": True, "decision": result, "decision_type": decision_type}
        except Exception as e:
            return self._handle_stage_exception("decision", e)

    # ── 完成阶段 ──────────────────────────────────

    @listen(or_("collective_decision", "standard_decision", "rapid_decision", "conservative_decision"))
    def finalize_analysis(self, decision_result: dict[str, Any]) -> dict[str, Any]:
        """完成分析流程"""
        logger.info("=== 完成智能分析流程 ===")
        self.state.current_stage = "finalization"
        self.state.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not decision_result.get("success", False):
            return {
                "success": False,
                "error": decision_result.get("error", "未知错误"),
                "error_count": self.state.error_count,
                "warnings": self.state.warnings,
            }
        try:
            summary = generate_analysis_summary(self.state)
            logger.info("智能分析流程成功完成")
            return {
                "success": True,
                "company": self.state.company,
                "ticker": self.state.ticker,
                "summary": summary,
                "final_recommendation": self.state.final_recommendation,
                "overall_score": self.state.overall_score,
                "analysis_depth": self.state.analysis_depth,
                "collaboration_quality": self.state.collaboration_quality,
                "path_taken": self.state.alternative_paths,
                "retry_attempts": self.state.retry_attempts,
                "analysis_time": self.state.start_time,
                "completion_time": self.state.end_time,
                "data_quality": self.state.data_quality,
                "error_count": self.state.error_count,
                "warnings": self.state.warnings,
            }
        except Exception as e:
            self.state.error_count += 1
            logger.error(f"完成分析异常: {str(e)}")
            return {"success": False, "error": str(e), "error_count": self.state.error_count}

    # ── 辅助方法 ──────────────────────────────────

    def _get_latest_data_collection_result(self) -> dict[str, Any] | None:
        return self.state._collection_data or None

    def _get_latest_analysis_result(self) -> dict[str, Any] | None:
        return self.state._analysis_result or None

    def _handle_stage_failure(self, stage: str, result: dict[str, Any]) -> dict[str, Any]:
        """统一处理阶段失败"""
        self.state.error_count += 1
        self.state.retry_attempts[stage] = self.state.retry_attempts.get(stage, 0) + 1
        logger.error(f"{stage} 失败: {result.get('error', '未知错误')}")
        if self.state.retry_attempts[stage] < 2:
            logger.info(f"尝试备选{stage}方法...")
            self.state.alternative_paths.append(f"alternative_{stage}")
            return {"success": False, "error": result.get("error"), "retry": True}
        return {"success": False, "error": result.get("error")}

    def _handle_stage_exception(self, stage: str, e: Exception) -> dict[str, Any]:
        """统一处理阶段异常"""
        self.state.error_count += 1
        logger.error(f"{stage} 异常: {str(e)}")
        return {"success": False, "error": str(e)}

    # ── 简化入口（直接调用，不走 Flow 路由）───────

    def run_smart_analysis(self, company: str, ticker: str) -> dict[str, Any]:
        """运行智能分析（简化入口）"""
        self.state.company = company
        self.state.ticker = ticker
        self.state.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        profile = analyze_company_profile(company, ticker)
        self.state.analysis_depth = determine_analysis_depth(profile)
        logger.info(f"启动智能分析: {company} ({ticker}), 深度: {self.state.analysis_depth}")
        try:
            data_result = self.data_collection_crew.execute_data_collection(company, ticker)
            if not (data_result.get("success") or data_result.get("status") == "success"):
                return {"success": False, "error": "数据收集失败"}
            analysis_result = self.analysis_crew.execute_collaborative_analysis(company, ticker, data_result)
            if not analysis_result["success"]:
                return {"success": False, "error": "分析失败"}
            update_analysis_state(self.state, analysis_result)
            decision_result = self.decision_crew.execute_collective_decision(company, ticker, analysis_result)
            if not decision_result["success"]:
                return {"success": False, "error": "决策失败"}
            update_decision_state(self.state, decision_result)
            summary = generate_analysis_summary(self.state)
            return {
                "success": True,
                "company": company,
                "ticker": ticker,
                "summary": summary,
                "final_recommendation": decision_result.get("final_recommendation", {}),
                "collaboration_metrics": {
                    "data_collection": data_result.get("collaboration_metrics", {}),
                    "analysis": analysis_result.get("collaboration_metrics", {}),
                    "decision": decision_result.get("collective_decision_metrics", {}),
                },
                "completion_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "error_count": self.state.error_count}