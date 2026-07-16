# web/web_app.py
"""Flask Web应用 - 提供股票分析系统的Web界面和API接口"""

from datetime import datetime
import logging
import os
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_file

from src.monitoring.monitoring_system import MonitoringSystem
from src.stock_analysis_system import StockAnalysisSystem
from web.web_templates import INDEX_HTML, create_templates

logger = logging.getLogger(__name__)

app = Flask(__name__)
analysis_system = None
monitoring_system = None


class WebApp:
    """Web应用主类"""

    def __init__(self) -> None:
        global analysis_system, monitoring_system
        analysis_system = StockAnalysisSystem()
        monitoring_system = MonitoringSystem()
        create_templates()
        self._setup_routes()

    def _setup_routes(self) -> None:
        @app.route("/")
        def index():
            template_path = Path("templates/index.html")
            if template_path.exists():
                return render_template_string(template_path.read_text(encoding="utf-8"))
            return render_template_string(INDEX_HTML)

        @app.route("/analyze", methods=["POST"])
        def analyze():
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"success": False, "error": "缺少请求数据"}), 400
                company = data.get("company")
                ticker = data.get("ticker")
                if not company or not ticker:
                    return jsonify({"success": False, "error": "缺少公司名称或股票代码"}), 400
                logger.info(f"开始分析: {company} ({ticker})")
                result = analysis_system.run_full_analysis(company, ticker)
                return jsonify(result)
            except Exception as e:
                logger.error(f"分析失败: {str(e)}")
                return jsonify({"success": False, "error": str(e)}), 500

        @app.route("/batch_analyze", methods=["POST"])
        def batch_analyze():
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"success": False, "error": "缺少请求数据"}), 400
                stocks = data.get("stocks", [])
                strategy = data.get("strategy", "parallel")
                if not stocks:
                    return jsonify({"success": False, "error": "缺少股票列表"}), 400
                logger.info(f"批量分析: {len(stocks)} 只股票, 策略: {strategy}")
                results = analysis_system.run_batch_analysis(stocks, strategy)
                success_count = sum(1 for r in results if r.get("success"))
                return jsonify(
                    {
                        "success": True,
                        "total_count": len(stocks),
                        "success_count": success_count,
                        "failed_count": len(stocks) - success_count,
                        "success_rate": (success_count / len(stocks) * 100) if stocks else 0,
                        "results": results,
                    }
                )
            except Exception as e:
                logger.error(f"批量分析失败: {str(e)}")
                return jsonify({"success": False, "error": str(e)}), 500

        @app.route("/history", methods=["GET"])
        def get_history():
            try:
                history = analysis_system.get_analysis_history()
                return jsonify({"success": True, "history": history})
            except Exception as e:
                logger.error(f"获取历史失败: {str(e)}")
                return jsonify({"success": False, "error": str(e)}), 500

        @app.route("/reports/<path:filename>")
        def download_report(filename):
            try:
                filepath = os.path.join("data/exports", filename)
                if os.path.exists(filepath):
                    return send_file(filepath, as_attachment=True)
                return jsonify({"success": False, "error": "文件不存在"}), 404
            except Exception as e:
                logger.error(f"下载报告失败: {str(e)}")
                return jsonify({"success": False, "error": str(e)}), 500

        @app.route("/monitor/start", methods=["POST"])
        def start_monitoring():
            try:
                data = request.get_json() or {}
                interval = data.get("interval", 300)
                monitoring_system.start_monitoring(interval)
                logger.info(f"监控已启动，间隔: {interval}秒")
                return jsonify({"success": True, "message": "监控已启动"})
            except Exception as e:
                logger.error(f"启动监控失败: {str(e)}")
                return jsonify({"success": False, "error": str(e)}), 500

        @app.route("/monitor/stop", methods=["POST"])
        def stop_monitoring():
            try:
                monitoring_system.stop_monitoring()
                logger.info("监控已停止")
                return jsonify({"success": True, "message": "监控已停止"})
            except Exception as e:
                logger.error(f"停止监控失败: {str(e)}")
                return jsonify({"success": False, "error": str(e)}), 500

        @app.route("/monitor/status", methods=["GET"])
        def monitor_status():
            try:
                status = monitoring_system.get_status()
                return jsonify({"success": True, "status": status})
            except Exception as e:
                logger.error(f"获取监控状态失败: {str(e)}")
                return jsonify({"success": False, "error": str(e)}), 500

        @app.route("/monitor/add_stock", methods=["POST"])
        def add_monitor_stock():
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"success": False, "error": "缺少请求数据"}), 400
                company = data.get("company")
                ticker = data.get("ticker")
                interval = data.get("interval", 300)
                if not company or not ticker:
                    return jsonify({"success": False, "error": "缺少公司名称或股票代码"}), 400
                monitoring_system.add_stock(company, ticker, interval)
                logger.info(f"添加监控股票: {company} ({ticker})")
                return jsonify({"success": True, "message": f"已添加 {ticker} 到监控列表"})
            except Exception as e:
                logger.error(f"添加监控股票失败: {str(e)}")
                return jsonify({"success": False, "error": str(e)}), 500

        @app.route("/monitor/add_rule", methods=["POST"])
        def add_monitor_rule():
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"success": False, "error": "缺少请求数据"}), 400
                required = ["rule_id", "ticker", "rule_type", "condition", "threshold", "message"]
                for field in required:
                    if field not in data:
                        return jsonify({"success": False, "error": f"缺少字段: {field}"}), 400
                monitoring_system.add_alert_rule(
                    data["rule_id"],
                    data["ticker"],
                    data["rule_type"],
                    data["condition"],
                    data["threshold"],
                    data["message"],
                )
                logger.info(f"添加预警规则: {data['rule_id']}")
                return jsonify({"success": True, "message": f"预警规则 {data['rule_id']} 已添加"})
            except Exception as e:
                logger.error(f"添加预警规则失败: {str(e)}")
                return jsonify({"success": False, "error": str(e)}), 500

        @app.route("/api/health", methods=["GET"])
        def health_check():
            return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


def run_web_app(host: str = "0.0.0.0", port: int = 5000, debug: bool = False) -> None:
    """启动Web应用"""
    WebApp()
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_web_app(debug=True)
