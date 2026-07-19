# src/utils/__init__.py
"""工具模块 — 按需导入"""

from typing import Any

__all__ = ["CostTracker"]


def __getattr__(name: str) -> Any:
    if name == "CostTracker":
        from src.utils.cost_tracker import CostTracker
        return CostTracker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")