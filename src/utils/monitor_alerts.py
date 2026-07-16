# src/utils/monitor_alerts.py
"""监控预警模块 - 预警规则、邮件通知和回调管理"""

from collections.abc import Callable
from datetime import datetime
import json
import logging
import os
import smtplib
from typing import Any

try:
    from email.mime.multipart import MimeMultipart
    from email.mime.text import MimeText
except ImportError:

    class MimeText:
        """邮件文本内容（fallback）"""

        def __init__(self, text: str, _subtype: str = "plain", _charset: str = "utf-8") -> None:
            self.text = text

    class MimeMultipart:
        """邮件多部分内容（fallback）"""

        def __init__(self) -> None:
            self.parts = []


logger = logging.getLogger(__name__)


class MonitorAlerts:
    """监控预警管理"""

    def __init__(self) -> None:
        """初始化预警管理器"""
        self.alert_rules = {}
        self.alert_callbacks = []
        self.email_config = {
            "enabled": False,
            "smtp_server": "",
            "smtp_port": 587,
            "username": "",
            "password": "",
            "from_email": "",
            "to_emails": [],
        }

    def add_alert_rule(
        self, rule_id: str, ticker: str, rule_type: str, condition: str, threshold: float, message: str
    ) -> bool:
        """添加预警规则"""
        try:
            self.alert_rules[rule_id] = {
                "ticker": ticker,
                "rule_type": rule_type,
                "condition": condition,
                "threshold": threshold,
                "message": message,
                "created_time": datetime.now(),
                "trigger_count": 0,
                "last_triggered": None,
                "enabled": True,
            }
            logger.info(f"已添加预警规则: {rule_id}")
            return True
        except Exception as e:
            logger.error(f"添加预警规则失败: {str(e)}")
            return False

    def configure_email(
        self, smtp_server: str, smtp_port: int, username: str, password: str, from_email: str, to_emails: list[str]
    ) -> None:
        """配置邮件预警"""
        self.email_config = {
            "enabled": True,
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "from_email": from_email,
            "to_emails": to_emails,
        }
        logger.info("邮件预警配置已启用")

    def add_alert_callback(self, callback: Callable) -> None:
        """添加预警回调"""
        self.alert_callbacks.append(callback)
        logger.info("预警回调函数已添加")

    def check_rules(
        self, ticker: str, result: dict[str, Any], current_price: float | None, monitoring_stocks: dict[str, Any]
    ) -> None:
        """检查所有预警规则是否触发"""
        for rule_id, rule in self.alert_rules.items():
            if not rule["enabled"] or rule["ticker"] != ticker:
                continue
            triggered = False
            current_score = result.get("overall_score", 0)
            current_rating = result.get("investment_rating", {}).get("rating", "")
            if rule["rule_type"] == "price" and current_price:
                triggered = self._check_price_rule(current_price, rule)
            elif rule["rule_type"] == "score":
                triggered = self._check_score_rule(current_score, rule)
            elif rule["rule_type"] == "rating_change":
                triggered = self._check_rating_change_rule(current_rating, ticker, rule, monitoring_stocks)
            if triggered:
                self._trigger(rule_id, rule, result)

    def _check_price_rule(self, price: float, rule: dict) -> bool:
        """检查价格类预警规则"""
        if rule["condition"] == "above":
            return price > rule["threshold"]
        if rule["condition"] == "below":
            return price < rule["threshold"]
        if rule["condition"] == "equal":
            return abs(price - rule["threshold"]) < 0.01
        return False

    def _check_score_rule(self, score: float, rule: dict) -> bool:
        """检查评分类预警规则"""
        if rule["condition"] == "above":
            return score > rule["threshold"]
        if rule["condition"] == "below":
            return score < rule["threshold"]
        if rule["condition"] == "equal":
            return abs(score - rule["threshold"]) < 0.1
        return False

    def _check_rating_change_rule(self, rating: str, ticker: str, rule: dict, monitoring_stocks: dict) -> bool:
        """检查评级变化类预警规则"""
        if ticker not in monitoring_stocks:
            return False
        last_rating = monitoring_stocks[ticker]["last_rating"]
        condition = rule["condition"]
        if condition == "upgrade":
            return last_rating != rating and rating in ["强烈买入", "买入"]
        if condition == "downgrade":
            return last_rating != rating and rating in ["卖出", "减持"]
        return False

    def _trigger(self, rule_id: str, rule: dict, result: dict[str, Any]) -> None:
        """触发预警"""
        rule["trigger_count"] += 1
        rule["last_triggered"] = datetime.now()
        alert_data = {
            "rule_id": rule_id,
            "ticker": rule["ticker"],
            "rule_type": rule["rule_type"],
            "message": rule["message"],
            "triggered_at": datetime.now(),
            "current_data": result,
            "trigger_count": rule["trigger_count"],
        }
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"预警回调失败: {str(e)}")
        if self.email_config["enabled"]:
            self._send_email(alert_data)
        self._log_alert(alert_data)
        logger.info(f"预警已触发: {rule_id} - {rule['ticker']}")

    def _send_email(self, alert_data: dict[str, Any]) -> None:
        """发送预警邮件"""
        try:
            if not self.email_config["enabled"]:
                return
            body = f"""股票预警通知
预警规则: {alert_data["rule_id"]} | 股票: {alert_data["ticker"]}
预警类型: {alert_data["rule_type"]}
触发时间: {alert_data["triggered_at"].strftime("%Y-%m-%d %H:%M:%S")}
预警信息: {alert_data["message"]}
评级: {alert_data["current_data"].get("investment_rating", {}).get("rating", "N/A")}
评分: {alert_data["current_data"].get("overall_score", 0):.1f}/100
此邮件由股票监控系统自动发送"""
            msg = MimeMultipart()
            msg["From"] = self.email_config["from_email"]
            msg["Subject"] = f"股票预警: {alert_data['ticker']}"
            msg.attach(MimeText(body, "plain", "utf-8"))
            server = smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"])
            server.starttls()
            server.login(self.email_config["username"], self.email_config["password"])
            for to_email in self.email_config["to_emails"]:
                msg["To"] = to_email
                server.send_message(msg)
                del msg["To"]
            server.quit()
            logger.info(f"邮件预警已发送: {alert_data['rule_id']}")
        except Exception as e:
            logger.error(f"发送邮件预警失败: {str(e)}")

    def _log_alert(self, alert_data: dict[str, Any]) -> None:
        """记录预警日志"""
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/alerts.log", "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "timestamp": alert_data["triggered_at"],
                            "rule_id": alert_data["rule_id"],
                            "ticker": alert_data["ticker"],
                            "message": alert_data["message"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except Exception as e:
            logger.error(f"记录预警日志失败: {str(e)}")

    def get_alert_history(self, ticker: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """获取预警历史"""
        alerts = []
        try:
            if os.path.exists("logs/alerts.log"):
                with open("logs/alerts.log", encoding="utf-8") as f:
                    for line in f:
                        try:
                            alert = json.loads(line.strip())
                            if ticker is None or alert.get("ticker") == ticker:
                                alerts.append(alert)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"读取预警历史失败: {str(e)}")
        alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return alerts[:limit]
