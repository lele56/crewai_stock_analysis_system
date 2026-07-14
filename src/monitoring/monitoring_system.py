# src/monitoring/monitoring_system.py
"""
监控系统 - 桥接层
封装 src/utils/monitor.py 的 StockMonitor，提供统一的 MonitoringSystem 接口
"""
import logging
from typing import Dict, Any, List, Optional, Callable

from src.utils.monitor import StockMonitor

logger = logging.getLogger(__name__)


class MonitoringSystem:
    """监控系统统一接口"""

    def __init__(self):
        self._monitor = StockMonitor()

    def add_stock(self, company: str, ticker: str, interval: int = 300) -> bool:
        return self._monitor.add_stock_to_monitor(company, ticker, interval)

    def remove_stock(self, ticker: str) -> bool:
        return self._monitor.remove_stock_from_monitor(ticker)

    def add_alert_rule(self, rule_id: str, ticker: str, rule_type: str,
                       condition: str, threshold: float, message: str) -> bool:
        return self._monitor.add_alert_rule(rule_id, ticker, rule_type, condition, threshold, message)

    def start_monitoring(self, interval: int = 300):
        self._monitor.start_monitoring(interval)

    def stop_monitoring(self):
        self._monitor.stop_monitoring()

    def get_status(self) -> Dict[str, Any]:
        return self._monitor.get_monitoring_status()

    def get_stock_status(self, ticker: str) -> Optional[Dict[str, Any]]:
        return self._monitor.get_stock_status(ticker)

    def get_alert_history(self, ticker: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        return self._monitor.get_alert_history(ticker, limit)

    def add_alert_callback(self, callback: Callable):
        self._monitor.add_alert_callback(callback)

    def configure_email_alerts(self, smtp_server: str, smtp_port: int,
                               username: str, password: str,
                               from_email: str, to_emails: List[str]):
        self._monitor.configure_email_alerts(smtp_server, smtp_port, username, password, from_email, to_emails)