# src/monitoring/monitoring_system.py
"""监控系统 - 桥接层
封装 src/utils/monitor.py 的 StockMonitor，提供统一的 MonitoringSystem 接口
"""

from collections.abc import Callable
import logging
from typing import Any

from src.utils.monitor import StockMonitor

logger = logging.getLogger(__name__)


class MonitoringSystem:
    """监控系统统一接口"""

    def __init__(self) -> None:
        """初始化监控系统"""
        self._monitor = StockMonitor()

    def add_stock(self, company: str, ticker: str, interval: int = 300) -> bool:
        """添加股票到监控"""
        return self._monitor.add_stock_to_monitor(company, ticker, interval)

    def remove_stock(self, ticker: str) -> bool:
        """从监控中移除股票"""
        return self._monitor.remove_stock_from_monitor(ticker)

    def add_alert_rule(
        self, rule_id: str, ticker: str, rule_type: str, condition: str, threshold: float, message: str
    ) -> bool:
        """添加预警规则"""
        return self._monitor.add_alert_rule(rule_id, ticker, rule_type, condition, threshold, message)

    def start_monitoring(self, interval: int = 300) -> None:
        """启动监控"""
        self._monitor.start_monitoring(interval)

    def stop_monitoring(self) -> None:
        """停止监控"""
        self._monitor.stop_monitoring()

    def get_status(self) -> dict[str, Any]:
        """获取监控状态"""
        return self._monitor.get_monitoring_status()

    def get_stock_status(self, ticker: str) -> dict[str, Any] | None:
        """获取单只股票状态"""
        return self._monitor.get_stock_status(ticker)

    def get_alert_history(self, ticker: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """获取预警历史"""
        return self._monitor.get_alert_history(ticker, limit)

    def add_alert_callback(self, callback: Callable) -> None:
        """添加预警回调"""
        self._monitor.add_alert_callback(callback)

    def configure_email_alerts(
        self, smtp_server: str, smtp_port: int, username: str, password: str, from_email: str, to_emails: list[str]
    ) -> None:
        """配置邮件预警"""
        self._monitor.configure_email_alerts(smtp_server, smtp_port, username, password, from_email, to_emails)
