# src/monitoring/__init__.py
"""监控模块 — 按需导入"""

from typing import Any

__all__ = ["MonitoringSystem"]


def __getattr__(name: str) -> Any:
    if name == "MonitoringSystem":
        from src.monitoring.monitoring_system import MonitoringSystem
        return MonitoringSystem
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")