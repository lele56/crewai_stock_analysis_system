# src/flows/investment_flow.py
"""
智能投资流程控制 - 使用CrewAI Flows实现智能路由和条件分支
"""
from crewai.flow.flow import Flow, listen, start, router, or_
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from src.crews.data_collection_crew import DataCollectionCrew
from src.crews.analysis_crew import AnalysisCrew
from src.crews.decision_crew import DecisionCrew
from src.flows.investment_flow_helpers import (
    analyze_company_profile, determine_analysis_depth, assess_data_quality,
    update_analysis_state, update_decision_state, generate_analysis_summary,
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
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    data_quality: str = "unknown"
    error_count: int = 0
    warnings: List[str] = []
    data_completeness: float = 0.0
    analysis_confidence: float = 0.0
    market_volatility: str = "medium"
    company_size: str = "medium"
    industry_trend: str = "stable"
    collaboration_quality: str = "medium"
    decision_complexity: str = "standard"
    retry_attempts: Dict[str, int] = {}
    alternative_paths: List[str] = []


class SmartInvestmentFlow(Flow[AnalysisState]):
    """智能投资分析流程"""

    def __init__(self):
        super().__init__()
        self.data_collection_crew = DataCollectionCrew()
        self.analysis_crew = AnalysisCrew()
        self.decision_crew = DecisionCrew()

    @start()
    def initialize_analysis(self):
        logger.info("=== 初始化智能投资分析流程 ===")
        self.state.current_stage = "initialization"
        self.state.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        company = input("请输入要分析的公司名称: ")
        ticker = input("请输入股票代码: ")
        company_profile = analyze_company_profile(company, ticker)
        self.state.company = company
        self.state.ticker = ticker
        self.state.company_size = company_profile.get('size', 'medium')
        self.state.industry_trend = company_profile.get('trend', 'stable')
        self.state.analysis_depth = determine_analysis_depth(company_profile)
        logger.info(f"开始分析 {company} ({ticker}), 深度: {self.state.analysis_depth}")
        return {"company": company, "ticker": ticker, "profile": company_profile}

    @listen("initialize_analysis")
    @router
    def route_data_collection(self, init_result):
        logger.info("=== 智能数据收集路由 ===")
        if self.state.company_size == "large" and self.state.analysis_depth == "deep":
            logger.info("选择全面数据收集策略")
            return "comprehensive_data_collection"
        elif self.state.market_volatility == "high":
            logger.info("选择实时数据收集策略")
            return "real_time_data_collection"
        logger.info("选择标准数据收集策略")
        return "standard_data_collection"

    @listen("route_data_collection")
    def standard_data_collection(self, route_result):
        return self._execute_data_collection("standard")

    @listen("route_data_collection")
    def comprehensive_data_collection(self, route_result):
        return self._execute_data_collection("comprehensive")

    @listen("route_data_collection")
    def real_time_data_collection(self, route_result):
        return self._execute_data_collection("real_time")

    def _execute_data_collection(self, collection_type: str):
        logger.info(f"=== {collection_type} 数据收集 ===")
        self.state.current_stage = "data_collection"
        try:
            result = self.data_collection_crew.execute_data_collection(self.state.company, self.state.ticker)
            if result['success']:
                quality = assess_data_quality(result)
                self.state.data_quality = quality['overall_quality']
                self.state.data_completeness = quality['completeness']
                logger.info(f"数据收集成功 - 质量: {self.state.data_quality}")
                return {"success": True, "data": result, "collection_type": collection_type, "data_quality": quality}
            self.state.error_count += 1
            self.state.retry_attempts['data_collection'] = self.state.retry_attempts.get('data_collection', 0) + 1
            logger.error(f"数据收集失败: {result.get('error', '未知错误')}")
            if self.state.retry_attempts['data_collection'] < 2:
                logger.info("尝试备选数据收集方法...")
                self.state.alternative_paths.append("alternative_data_collection")
                return {"success": False, "error": result.get('error'), "retry": True}
            return {"success": False, "error": result.get('error')}
        except Exception as e:
            self.state.error_count += 1
            logger.error(f"数据收集异常: {str(e)}")
            return {"success": False, "error": str(e)}

    @listen(or_("standard_data_collection", "comprehensive_data_collection", "real_time_data_collection"))
    @router
    def route_analysis_strategy(self, data_result):
        logger.info("=== 智能分析策略路由 ===")
        if not data_result.get('success', False):
            logger.info("数据收集失败，使用简化分析")
            return "simplified_analysis"
        quality = data_result.get('data_quality', {}).get('overall_quality', 'unknown')
        if quality == 'excellent' and self.state.analysis_depth == 'deep':
            return "deep_analysis"
        elif quality in ['good', 'excellent']:
            return "standard_analysis"
        return "rapid_analysis"

    @listen("route_analysis_strategy")
    def deep_analysis(self, route_result):
        return self._execute_analysis("deep")

    @listen("route_analysis_strategy")
    def standard_analysis(self, route_result):
        return self._execute_analysis("standard")

    @listen("route_analysis_strategy")
    def rapid_analysis(self, route_result):
        return self._execute_analysis("rapid")

    @listen("route_analysis_strategy")
    def simplified_analysis(self, route_result):
        return self._execute_analysis("simplified")

    def _execute_analysis(self, analysis_type: str):
        logger.info(f"=== {analysis_type} 分析 ===")
        self.state.current_stage = "analysis"
        try:
            result = self.analysis_crew.execute_collaborative_analysis(
                self.state.company, self.state.ticker,
                self._get_latest_data_collection_result()
            )
            if result['success']:
                update_analysis_state(self.state, result)
                logger.info(f"{analysis_type} 分析完成")
                return {"success": True, "analysis": result, "analysis_type": analysis_type}
            self.state.error_count += 1
            logger.error(f"{analysis_type} 分析失败: {result.get('error', '未知错误')}")
            return {"success": False, "error": result.get('error')}
        except Exception as e:
            self.state.error_count += 1
            logger.error(f"{analysis_type} 分析异常: {str(e)}")
            return {"success": False, "error": str(e)}

    @listen(or_("deep_analysis", "standard_analysis", "rapid_analysis", "simplified_analysis"))
    @router
    def route_decision_strategy(self, analysis_result):
        logger.info("=== 智能决策策略路由 ===")
        if not analysis_result.get('success', False):
            return "conservative_decision"
        quality = analysis_result.get('analysis', {}).get('collaboration_metrics', {}).get('decision_quality', 'unknown')
        if quality == 'excellent' and self.state.company_size == 'large':
            return "collective_decision"
        elif quality in ['good', 'excellent']:
            return "standard_decision"
        return "rapid_decision"

    @listen("route_decision_strategy")
    def collective_decision(self, route_result):
        return self._execute_decision("collective")

    @listen("route_decision_strategy")
    def standard_decision(self, route_result):
        return self._execute_decision("standard")

    @listen("route_decision_strategy")
    def rapid_decision(self, route_result):
        return self._execute_decision("rapid")

    @listen("route_decision_strategy")
    def conservative_decision(self, route_result):
        return self._execute_decision("conservative")

    def _execute_decision(self, decision_type: str):
        logger.info(f"=== {decision_type} 决策 ===")
        self.state.current_stage = "decision"
        try:
            result = self.decision_crew.execute_collective_decision(
                self.state.company, self.state.ticker,
                self._get_latest_analysis_result()
            )
            if result['success']:
                update_decision_state(self.state, result)
                logger.info(f"{decision_type} 决策完成")
                return {"success": True, "decision": result, "decision_type": decision_type}
            self.state.error_count += 1
            logger.error(f"{decision_type} 决策失败: {result.get('error', '未知错误')}")
            return {"success": False, "error": result.get('error')}
        except Exception as e:
            self.state.error_count += 1
            logger.error(f"{decision_type} 决策异常: {str(e)}")
            return {"success": False, "error": str(e)}

    @listen(or_("collective_decision", "standard_decision", "rapid_decision", "conservative_decision"))
    def finalize_analysis(self, decision_result):
        logger.info("=== 完成智能分析流程 ===")
        self.state.current_stage = "finalization"
        self.state.end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            if decision_result.get('success', False):
                summary = generate_analysis_summary(self.state)
                logger.info("智能分析流程成功完成")
                return {
                    "success": True, "company": self.state.company, "ticker": self.state.ticker,
                    "summary": summary, "final_recommendation": self.state.final_recommendation,
                    "overall_score": self.state.overall_score, "analysis_depth": self.state.analysis_depth,
                    "collaboration_quality": self.state.collaboration_quality,
                    "path_taken": self.state.alternative_paths,
                    "retry_attempts": self.state.retry_attempts,
                    "analysis_time": self.state.start_time, "completion_time": self.state.end_time,
                    "data_quality": self.state.data_quality, "error_count": self.state.error_count,
                    "warnings": self.state.warnings,
                }
            logger.error("智能分析流程失败")
            return {"success": False, "error": decision_result.get('error', '未知错误'),
                    "error_count": self.state.error_count, "warnings": self.state.warnings}
        except Exception as e:
            self.state.error_count += 1
            logger.error(f"完成分析异常: {str(e)}")
            return {"success": False, "error": str(e), "error_count": self.state.error_count}

    def _get_latest_data_collection_result(self) -> Optional[Dict[str, Any]]:
        return {"sample": "data"}

    def _get_latest_analysis_result(self) -> Optional[Dict[str, Any]]:
        return {"sample": "analysis"}

    def run_smart_analysis(self, company: str, ticker: str) -> Dict[str, Any]:
        self.state.company = company
        self.state.ticker = ticker
        self.state.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        profile = analyze_company_profile(company, ticker)
        self.state.analysis_depth = determine_analysis_depth(profile)
        logger.info(f"启动智能分析: {company} ({ticker}), 深度: {self.state.analysis_depth}")
        try:
            data_result = self.data_collection_crew.execute_data_collection(company, ticker)
            if not data_result['success']:
                return {"success": False, "error": "数据收集失败"}
            analysis_result = self.analysis_crew.execute_collaborative_analysis(company, ticker, data_result['data'])
            if not analysis_result['success']:
                return {"success": False, "error": "分析失败"}
            decision_result = self.decision_crew.execute_collective_decision(company, ticker, analysis_result['data'])
            if not decision_result['success']:
                return {"success": False, "error": "决策失败"}
            summary = generate_analysis_summary(self.state)
            return {
                "success": True, "company": company, "ticker": ticker,
                "summary": summary, "final_recommendation": decision_result.get('final_recommendation', {}),
                "collaboration_metrics": {
                    "data_collection": data_result.get('collaboration_metrics', {}),
                    "analysis": analysis_result.get('collaboration_metrics', {}),
                    "decision": decision_result.get('collective_decision_metrics', {})
                },
                "completion_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            return {"success": False, "error": str(e), "error_count": self.state.error_count}


if __name__ == "__main__":
    flow = SmartInvestmentFlow()