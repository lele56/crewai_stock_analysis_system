# src/utils/monitor.py
"""实时监控模块
提供股票实时监控、预警和通知功能
"""

from collections.abc import Callable
from datetime import datetime
import logging
import threading
import time
from typing import Any

from src.utils.monitor_alerts import MonitorAlerts

logger = logging.getLogger(__name__)


class StockMonitor:
    """股票监控器"""

    def __init__(self, analysis_system: Any = None) -> None:
        """初始化股票监控器"""
        from src.stock_analysis_system import StockAnalysisSystem

        self.analysis_system = analysis_system or StockAnalysisSystem()
        self.monitoring_stocks = {}
        self.alerts = MonitorAlerts()
        self.monitoring = False
        self.monitor_thread = None
        self.last_check_time = {}
        self.monitoring_interval = 300

    def add_stock_to_monitor(self, company: str, ticker: str, check_interval: int = 300) -> bool:
        """添加股票到监控列表"""
        try:
            self.monitoring_stocks[ticker] = {
                "company": company,
                "ticker": ticker,
                "check_interval": check_interval,
                "last_analysis": None,
                "last_score": 0,
                "last_rating": "",
                "price_history": [],
                "score_history": [],
                "alert_count": 0,
                "added_time": datetime.now(),
            }
            logger.info(f"已添加股票到监控列表: {company} ({ticker})")
            return True
        except Exception as e:
            logger.error(f"添加监控股票失败: {str(e)}")
            return False

    def remove_stock_from_monitor(self, ticker: str) -> bool:
        """从监控列表移除股票"""
        try:
            if ticker in self.monitoring_stocks:
                del self.monitoring_stocks[ticker]
                logger.info(f"已从监控列表移除: {ticker}")
                return True
            logger.warning(f"股票不在监控列表中: {ticker}")
            return False
        except Exception as e:
            logger.error(f"移除监控股票失败: {str(e)}")
            return False

    def add_alert_rule(
        self, rule_id: str, ticker: str, rule_type: str, condition: str, threshold: float, message: str
    ) -> bool:
        """添加预警规则"""
        return self.alerts.add_alert_rule(rule_id, ticker, rule_type, condition, threshold, message)

    def configure_email_alerts(
        self, smtp_server: str, smtp_port: int, username: str, password: str, from_email: str, to_emails: list[str]
    ) -> None:
        """配置邮件预警"""
        self.alerts.configure_email(smtp_server, smtp_port, username, password, from_email, to_emails)

    def add_alert_callback(self, callback: Callable) -> None:
        """添加预警回调函数"""
        self.alerts.add_alert_callback(callback)

    def start_monitoring(self, interval: int = 300) -> None:
        """启动股票监控"""
        if self.monitoring:
            logger.warning("监控已在运行中")
            return
        self.monitoring_interval = interval
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info(f"股票监控已启动，监控间隔: {interval}秒")

    def stop_monitoring(self) -> None:
        """停止股票监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("股票监控已停止")

    def _monitoring_loop(self) -> None:
        """监控循环"""
        while self.monitoring:
            try:
                self._check_all_stocks()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"监控循环异常: {str(e)}")
                time.sleep(60)

    def _check_all_stocks(self) -> None:
        """检查所有监控股票"""
        current_time = datetime.now()
        for ticker, stock_info in self.monitoring_stocks.items():
            try:
                last_check = stock_info.get("last_check_time")
                if last_check and (current_time - last_check).total_seconds() < stock_info["check_interval"]:
                    continue
                result = self.analysis_system.analyze_stock(stock_info["company"], ticker, use_cache=False)
                if result.get("success", False):
                    self._update_stock_info(ticker, result)
                    current_price = self._extract_current_price(result)
                    self.alerts.check_rules(ticker, result, current_price, self.monitoring_stocks)
                stock_info["last_check_time"] = current_time
            except Exception as e:
                logger.error(f"检查股票 {ticker} 失败: {str(e)}")

    def _update_stock_info(self, ticker: str, result: dict[str, Any]) -> None:
        """更新股票信息"""
        if ticker not in self.monitoring_stocks:
            return
        stock_info = self.monitoring_stocks[ticker]
        stock_info["last_analysis"] = result
        stock_info["last_score"] = result.get("overall_score", 0)
        stock_info["last_rating"] = result.get("investment_rating", {}).get("rating", "")
        current_price = self._extract_current_price(result)
        if current_price:
            stock_info["price_history"].append({"price": current_price, "time": datetime.now()})
            if len(stock_info["price_history"]) > 100:
                stock_info["price_history"] = stock_info["price_history"][-100:]
        score = result.get("overall_score", 0)
        stock_info["score_history"].append({"score": score, "time": datetime.now()})
        if len(stock_info["score_history"]) > 50:
            stock_info["score_history"] = stock_info["score_history"][-50:]

    def _extract_current_price(self, result: dict[str, Any]) -> float | None:
        try:
            financial_data = result.get("collection_data", {}).get("financial_data", {})
            if isinstance(financial_data, dict):
                price = financial_data.get("current_price")
                if price:
                    return float(price)
            technical_data = result.get("collection_data", {}).get("technical_analysis", {})
            if isinstance(technical_data, dict):
                price = technical_data.get("current_price")
                if price:
                    return float(price)
        except (ValueError, TypeError):
            pass
        return None

    def get_monitoring_status(self) -> dict[str, Any]:
        """获取监控状态"""
        return {
            "monitoring": self.monitoring,
            "monitored_stocks": len(self.monitoring_stocks),
            "alert_rules": len(self.alerts.alert_rules),
            "monitoring_interval": self.monitoring_interval,
            "last_check_time": self.last_check_time,
            "monitored_tickers": list(self.monitoring_stocks.keys()),
        }

    def get_stock_status(self, ticker: str) -> dict[str, Any] | None:
        """获取单只股票监控状态"""
        return self.monitoring_stocks.get(ticker)

    def get_alert_history(self, ticker: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """获取预警历史记录"""
        return self.alerts.get_alert_history(ticker, limit)


# 使用示例
if __name__ == "__main__":
    monitor = StockMonitor()
    monitor.add_stock_to_monitor("苹果公司", "AAPL", check_interval=300)
    monitor.add_stock_to_monitor("微软", "MSFT", check_interval=300)
    monitor.add_alert_rule("price_alert_aapl", "AAPL", "price", "above", 180.0, "苹果股价突破180美元")
    monitor.add_alert_rule("score_alert_msft", "MSFT", "score", "below", 60.0, "微软评分低于60分")

    def alert_callback(alert_data: dict[str, Any]) -> None:
        """预警回调示例"""
        print(f"预警触发: {alert_data['ticker']} - {alert_data['message']}")

    monitor.add_alert_callback(alert_callback)
    monitor.start_monitoring(interval=60)
    print("监控已启动，按Ctrl+C停止...")
    try:
        while True:
            time.sleep(10)
            status = monitor.get_monitoring_status()
            print(f"监控状态: {status['monitored_stocks']} 只股票, {status['alert_rules']} 个预警规则")
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        print("监控已停止")
