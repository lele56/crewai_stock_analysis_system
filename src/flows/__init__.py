# src/flows/__init__.py
"""Flow 模块 — 按需导入，避免启动时加载全部依赖"""

from typing import Any

__all__ = ["SmartInvestmentFlow", "AnalysisState", "BatchAnalysisFlow", "BatchAnalysisState"]


def __getattr__(name: str) -> Any:
    if name in ("SmartInvestmentFlow", "AnalysisState"):
        from src.flows.investment_flow import AnalysisState, SmartInvestmentFlow
        return {"SmartInvestmentFlow": SmartInvestmentFlow, "AnalysisState": AnalysisState}[name]
    if name in ("BatchAnalysisFlow", "BatchAnalysisState"):
        from src.flows.batch_analysis_flow import BatchAnalysisFlow, BatchAnalysisState
        return {"BatchAnalysisFlow": BatchAnalysisFlow, "BatchAnalysisState": BatchAnalysisState}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")