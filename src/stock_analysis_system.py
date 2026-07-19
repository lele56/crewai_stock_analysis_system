# src/stock_analysis_system.py
"""股票分析系统主协调器
整合所有Crews和Flows，提供统一的分析接口
"""

from collections.abc import Callable
import concurrent.futures
from datetime import datetime
import logging
import os
import threading
from typing import Any

from src.config import AnalysisProfile, Config
from src.crews.analysis_crew import AnalysisCrew
from src.crews.data_collection_crew import DataCollectionCrew
from src.crews.decision_crew import DecisionCrew
from src.crews.decision_executor import (
    export_to_json,
    generate_analysis_summary,
    generate_investment_report,
    get_investment_rating,
    save_report,
)
from src.utils.cost_tracker import CostTracker
from src.utils.llm_factory import get_llm
from src.utils.redis_cache_manager import RedisCacheManager
from src.utils.serialization import make_serializable
from src.utils.stock_reports import generate_summary_report
from src.utils.timing import timer_with_result

logger = logging.getLogger(__name__)


def _setup_root_logging() -> None:
    """配置 root logger（仅首次调用生效）"""
    root = logging.getLogger()
    if root.handlers:
        return
    _log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
    root.setLevel(_log_level)

    log_dir = os.path.dirname(os.path.abspath(__file__)) + "/../"
    log_file = os.path.join(log_dir, "log.txt")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(_log_level)
    console_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
    root.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root.addHandler(file_handler)


_setup_root_logging()


class StockAnalysisSystem:
    """股票分析系统主类"""

    def __init__(self) -> None:
        self.data_collection_crew = DataCollectionCrew()
        self.analysis_crew = AnalysisCrew()
        self.decision_crew = DecisionCrew()
        self.cache_manager = RedisCacheManager()
        logger.info("股票分析系统初始化完成")

    @timer_with_result
    def analyze_stock(
        self, company: str, ticker: str,
        use_cache: bool = True,
        profile: AnalysisProfile | None = None,
        progress_callback: Callable[..., Any] | None = None,
    ) -> dict[str, Any]:
        """分析单只股票

        Args:
            company: 公司名称
            ticker: 股票代码
            use_cache: 是否使用缓存
            profile: 分析深度 (rapid/standard/deep)，None 使用默认
            progress_callback: 进度回调
        """
        p = profile or Config.ANALYSIS_PROFILE
        logger.info(f"开始分析股票: {company} ({ticker}), profile={p.value}")

        CostTracker().reset(get_llm()) if Config.LLM_COST_TRACKING else None

        if use_cache and self.cache_manager.check_cache(ticker):
            logger.info(f"使用缓存数据: {ticker}")
            return self.cache_manager.get_from_cache(ticker)

        def _report(progress: int, stage: str, message: str) -> None:
            if progress_callback:
                progress_callback({"progress": progress, "stage": stage, "status": "running", "message": message})

        def _run_stage(executor: Callable, args: tuple, timeout: int, stage_name: str) -> dict[str, Any]:
            """带超时的阶段执行"""
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as stage_executor:
                future = stage_executor.submit(executor, *args)
                try:
                    return future.result(timeout=timeout)
                except concurrent.futures.TimeoutError:
                    logger.error(f"阶段超时: {stage_name} ({timeout}s)")
                    return {"success": False, "error": f"阶段超时: {stage_name} ({timeout}秒)", "timeout": True}
                except Exception as e:
                    logger.error(f"阶段异常: {stage_name} - {e}")
                    return {"success": False, "error": str(e)}

        try:
            _report(10, "data_collection", f"第一阶段：数据收集 ({p.value})")
            logger.info(f"第一阶段：数据收集 ({p.value})")

            self.data_collection_crew._profile = p
            collection_result = self.data_collection_crew.execute_data_collection(company, ticker)
            if collection_result["status"] != "success":
                return {
                    "success": False,
                    "error": f"数据收集失败: {collection_result.get('error', '未知错误')}",
                    "company": company,
                    "ticker": ticker,
                }
            self.cache_manager.save_collection_data(ticker, collection_result)

            _report(40, "analysis", f"第二阶段：分析 ({p.value})")
            logger.info(f"第二阶段：分析 ({p.value})")

            self.analysis_crew._profile = p
            self.analysis_crew._active_agents = Config.get_profile_agents("analysis", p)
            analysis_result = self.analysis_crew.execute_collaborative_analysis(
                company, ticker, collection_result["result"])
            if not analysis_result["success"]:
                return {
                    "success": False,
                    "error": f"分析失败: {analysis_result['error']}",
                    "company": company,
                    "ticker": ticker,
                }

            _report(70, "decision", f"第三阶段：决策 ({p.value})")
            logger.info(f"第三阶段：决策 ({p.value})")

            self.decision_crew._profile = p
            self.decision_crew._active_agents = Config.get_profile_agents("decision", p)
            decision_result = self.decision_crew.execute_decision_process(company, ticker, analysis_result)
            if not decision_result["success"]:
                return {
                    "success": False,
                    "error": f"决策失败: {decision_result['error']}",
                    "company": company,
                    "ticker": ticker,
                }

            _report(90, "integrating", "整合结果")
            final_result = self._integrate_results(
                company, ticker, collection_result, analysis_result, decision_result
            )
            final_result["profile"] = p.value
            if Config.LLM_COST_TRACKING:
                final_result["cost"] = CostTracker().summary()
            if use_cache:
                self.cache_manager.save_to_cache(ticker, final_result)
            self.cache_manager.add_to_history(final_result)
            logger.info(f"股票分析完成: {company} ({ticker}), profile={p.value}")
            return final_result

        except Exception as e:
            logger.error(f"股票分析异常: {company} ({ticker}), 错误: {str(e)}")
            return {"success": False, "error": f"分析过程发生异常: {str(e)}", "company": company, "ticker": ticker}

    def analyze_multiple_stocks(
        self, stocks: list[dict[str, str]],
        max_workers: int = 3,
        profile: AnalysisProfile | None = None,
    ) -> list[dict[str, Any]]:
        """批量分析多只股票"""
        logger.info(f"开始批量分析 {len(stocks)} 只股票")
        results = []
        lock = threading.Lock()

        def analyze_single_stock(stock_data: dict[str, str]) -> None:
            """分析单只股票（线程安全）"""
            result = self.analyze_stock(stock_data["company"], stock_data["ticker"], use_cache=True, profile=profile)
            with lock:
                results.append(result)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(analyze_single_stock, stock) for stock in stocks]
            concurrent.futures.wait(futures)

        logger.info(f"批量分析完成，成功: {len([r for r in results if r['success']])}/{len(stocks)}")
        return results

    def generate_summary_report(self, results: list[dict[str, Any]]) -> str:
        """生成汇总报告"""
        return generate_summary_report(results)

    def _integrate_results(
        self, company: str, ticker: str, collection_data: dict, analysis_data: dict, decision_data: dict
    ) -> dict[str, Any]:
        scores = analysis_data.get("collaboration_scores", {})
        final_action = decision_data.get("final_recommendation", {}).get("action", "持有")
        investment_rating = get_investment_rating(final_action)
        analysis_summary = generate_analysis_summary(
            company, ticker,
            scores,
            decision_data.get("final_recommendation", {}),
            decision_data.get("collective_decision_metrics", {}),
        )
        full_report = generate_investment_report(
            company, ticker, collection_data, analysis_data, decision_data, analysis_summary
        )
        report_paths = save_report(full_report, company, ticker)
        data_path = export_to_json(
            {
                "company": company,
                "ticker": ticker,
                "collection_data": collection_data,
                "analysis_data": analysis_data,
                "decision_data": decision_data,
                "scores": scores,
                "investment_rating": investment_rating,
            },
            company,
            ticker,
        )
        charts = self._generate_charts(ticker)
        return make_serializable({
            "success": True,
            "company": company,
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "collection_data": collection_data,
            "analysis_data": analysis_data,
            "decision_data": decision_data,
            "scores": scores,
            "investment_rating": investment_rating,
            "analysis_summary": analysis_summary,
            "full_report": full_report,
            "report_path": report_paths.get("md", ""),
            "report_path_docx": report_paths.get("docx", ""),
            "data_path": data_path,
            "charts": charts,
            "overall_score": scores.get("overall_score", 0),
        })

    def get_analysis_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取分析历史"""
        return self.cache_manager.get_analysis_history(limit)

    def _generate_charts(self, ticker: str) -> list[dict[str, str]]:
        """自动生成技术图表，优先从缓存读取K线数据"""
        charts = []
        try:
            from src.tools.akshare_data_cache import load_kline_from_cache
            from src.tools.akshare_data_parser import get_stock_history_data

            df = load_kline_from_cache(ticker)
            if df is None or df.empty:
                df = get_stock_history_data(ticker, "1y")  # 缓存未命中才调 API
            if df is None or df.empty:
                return charts

            from src.tools.technical_charting import ChartingTool

            ct = ChartingTool()
            chart_types = [
                ("candlestick", "K线图"),
                ("indicators", "技术指标"),
                ("volume", "成交量"),
            ]
            for ct_type, ct_label in chart_types:
                try:
                    # 直接把 DataFrame 传给图表生成方法，跳过 _parse_or_fetch
                    os.makedirs("reports/charts", exist_ok=True)
                    if ct_type == "candlestick":
                        filepath = ct._generate_candlestick_chart(df)
                    elif ct_type == "indicators":
                        filepath = ct._generate_indicators_chart(df)
                    elif ct_type == "volume":
                        filepath = ct._generate_volume_chart(df)
                    else:
                        continue
                    filename = os.path.basename(filepath)
                    charts.append({"filename": filename, "label": ct_label, "type": ct_type})
                except Exception as e:
                    logger.warning(f"图表生成失败 ({ct_label}): {str(e)[:60]}")
        except Exception as e:
            logger.warning(f"图表自动生成失败: {str(e)[:60]}")
        return charts

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        return self.cache_manager.get_cache_stats()

    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache_manager.clear_cache()

    def export_history(self, filepath: str) -> None:
        """导出分析历史"""
        self.cache_manager.export_history(filepath)


# 使用示例
if __name__ == "__main__":
    system = StockAnalysisSystem()
    print(f"缓存: {'Redis' if system.cache_manager.connected else '内存降级'}")
    print(f"缓存统计: {system.get_cache_stats()}")
    print("=== 单个股票分析 ===")
    result = system.analyze_stock("苹果公司", "AAPL")
    if result["success"]:
        print(f"分析成功: {result['company']}")
        print(f"投资评级: {result['investment_rating']['rating']}")
        print(f"综合评分: {result['overall_score']:.1f}/100")
    else:
        print(f"分析失败: {result['error']}")

    print("\n=== 批量股票分析 ===")
    stocks = [
        {"company": "微软", "ticker": "MSFT"},
        {"company": "谷歌", "ticker": "GOOGL"},
        {"company": "亚马逊", "ticker": "AMZN"},
    ]
    batch_results = system.analyze_multiple_stocks(stocks)
    print(f"批量分析完成: {len(batch_results)} 只股票")

    summary = system.generate_summary_report(batch_results)
    print(f"\n=== 摘要报告 ===\n{summary[:500]}...")

    print(f"\n缓存统计: {system.get_cache_stats()}")