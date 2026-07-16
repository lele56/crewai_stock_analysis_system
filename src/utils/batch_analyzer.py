# src/utils/batch_analyzer.py
"""批量分析器
提供高效的批量股票分析功能
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import logging
import threading
import time
from typing import Any

from src.utils.batch_report_generator import export_batch_results, generate_batch_summary

logger = logging.getLogger(__name__)


class BatchStockAnalyzer:
    """批量股票分析器"""

    def __init__(self, max_workers: int = 5, cache_enabled: bool = True) -> None:
        """初始化批量分析器

        Args:
            max_workers: 最大并发数
            cache_enabled: 是否启用缓存
        """
        self.max_workers = max_workers
        self.cache_enabled = cache_enabled
        from src.stock_analysis_system import StockAnalysisSystem

        self.analysis_system = StockAnalysisSystem()
        self.results = {}
        self.errors = []
        self.progress = {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "in_progress": 0,
            "start_time": None,
            "end_time": None,
            "estimated_remaining_time": None,
        }
        self.lock = threading.Lock()
        self.progress_callback: Callable | None = None

    def set_progress_callback(self, callback: Callable) -> None:
        """设置进度回调函数"""
        self.progress_callback = callback

    def analyze_multiple_stocks(self, stocks: list[dict[str, str]], strategy: str = "parallel") -> dict[str, Any]:
        """批量分析多只股票

        Args:
            stocks: 股票列表，每个元素包含company和ticker
            strategy: 分析策略 (parallel, sequential, adaptive)

        Returns:
            分析结果
        """
        logger.info(f"开始批量分析 {len(stocks)} 只股票，策略: {strategy}")

        self.progress["total"] = len(stocks)
        self.progress["start_time"] = datetime.now()
        self.results.clear()
        self.errors.clear()

        if strategy == "parallel":
            return self._parallel_analysis(stocks)
        if strategy == "sequential":
            return self._sequential_analysis(stocks)
        if strategy == "adaptive":
            return self._adaptive_analysis(stocks)
        raise ValueError(f"不支持的策略: {strategy}")

    def _parallel_analysis(self, stocks: list[dict[str, str]]) -> dict[str, Any]:
        """并行分析"""
        logger.info(f"使用并行分析，最大并发数: {self.max_workers}")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_stock = {executor.submit(self._analyze_single_stock_with_retry, stock): stock for stock in stocks}

            # 等待所有任务完成
            for future in as_completed(future_to_stock):
                stock = future_to_stock[future]
                try:
                    result = future.result()
                    with self.lock:
                        if result.get("success", False):
                            self.results[stock["ticker"]] = result
                            self.progress["completed"] += 1
                        else:
                            self.errors.append({"stock": stock, "error": result.get("error", "未知错误")})
                            self.progress["failed"] += 1

                    self._update_progress()
                    self._notify_progress_callback()

                except Exception as e:
                    with self.lock:
                        self.errors.append({"stock": stock, "error": str(e)})
                        self.progress["failed"] += 1

                    self._update_progress()
                    self._notify_progress_callback()

        return self._generate_batch_result()

    def _sequential_analysis(self, stocks: list[dict[str, str]]) -> dict[str, Any]:
        """顺序分析"""
        logger.info("使用顺序分析")

        for stock in stocks:
            try:
                with self.lock:
                    self.progress["in_progress"] += 1

                result = self._analyze_single_stock_with_retry(stock)

                with self.lock:
                    if result.get("success", False):
                        self.results[stock["ticker"]] = result
                        self.progress["completed"] += 1
                    else:
                        self.errors.append({"stock": stock, "error": result.get("error", "未知错误")})
                        self.progress["failed"] += 1

                self._update_progress()
                self._notify_progress_callback()

            except Exception as e:
                with self.lock:
                    self.errors.append({"stock": stock, "error": str(e)})
                    self.progress["failed"] += 1

                self._update_progress()
                self._notify_progress_callback()

            finally:
                with self.lock:
                    self.progress["in_progress"] -= 1

        return self._generate_batch_result()

    def _adaptive_analysis(self, stocks: list[dict[str, str]]) -> dict[str, Any]:
        """自适应分析"""
        logger.info("使用自适应分析")

        # 根据股票数量自适应选择策略
        if len(stocks) <= 3:
            return self._sequential_analysis(stocks)
        if len(stocks) <= 10:
            return self._parallel_analysis(stocks)
        # 分批并行处理
        return self._batch_parallel_analysis(stocks)

    def _batch_parallel_analysis(self, stocks: list[dict[str, str]]) -> dict[str, Any]:
        """分批并行分析"""
        logger.info("使用分批并行分析")

        batch_size = min(self.max_workers * 2, 10)  # 每批最多10只股票
        batches = [stocks[i : i + batch_size] for i in range(0, len(stocks), batch_size)]

        all_results = {}

        for i, batch in enumerate(batches):
            logger.info(f"处理批次 {i + 1}/{len(batches)}，包含 {len(batch)} 只股票")

            # 处理当前批次
            self._parallel_analysis(batch)

            # 合并结果
            all_results.update(self.results)

            # 批次间暂停，避免API限制
            if i < len(batches) - 1:
                time.sleep(2)

        self.results = all_results
        return self._generate_batch_result()

    def _analyze_single_stock_with_retry(self, stock: dict[str, str], max_retries: int = 2) -> dict[str, Any]:
        """带重试机制的单股票分析"""
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"分析 {stock['company']} (尝试 {attempt + 1}/{max_retries + 1})")

                result = self.analysis_system.analyze_stock(
                    stock["company"], stock["ticker"], use_cache=self.cache_enabled
                )

                if result.get("success", False):
                    return result
                if attempt < max_retries:
                    logger.warning(f"分析 {stock['company']} 失败，重试中...")
                    time.sleep(2**attempt)  # 指数退避
                else:
                    return result

            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"分析 {stock['company']} 异常，重试中... 错误: {str(e)}")
                    time.sleep(2**attempt)
                else:
                    return {"success": False, "error": str(e), "company": stock["company"], "ticker": stock["ticker"]}

        return {"success": False, "error": "重试次数超过限制", "company": stock["company"], "ticker": stock["ticker"]}

    def _update_progress(self) -> None:
        """更新进度信息"""
        total = self.progress["total"]
        completed = self.progress["completed"]
        failed = self.progress["failed"]
        self.progress["percentage"] = ((completed + failed) / total) * 100 if total > 0 else 0
        if self.progress["start_time"] and completed > 0:
            elapsed = (datetime.now() - self.progress["start_time"]).total_seconds()
            self.progress["estimated_remaining_time"] = (total - completed - failed) * (elapsed / completed)
        if self.progress["percentage"] >= 100:
            self.progress["end_time"] = datetime.now()

    def _notify_progress_callback(self) -> None:
        if self.progress_callback:
            try:
                self.progress_callback(self.progress.copy())
            except Exception as e:
                logger.error(f"进度回调失败: {str(e)}")

    def _generate_batch_result(self) -> dict[str, Any]:
        success_count = len(self.results)
        failed_count = len(self.errors)
        total_count = self.progress["total"]
        logger.info(f"批量分析完成: {success_count}/{total_count} 成功")
        return {
            "success": True,
            "total_count": total_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "success_rate": (success_count / total_count) * 100 if total_count > 0 else 0,
            "results": self.results,
            "errors": self.errors,
            "progress": self.progress.copy(),
            "summary": self._generate_summary(),
        }

    def _generate_summary(self) -> dict[str, Any]:
        return generate_batch_summary(self.results, self.errors, self.progress)

    def export_results(self, export_format: str = "json", filepath: str = "") -> str:
        """导出分析结果"""
        return export_batch_results(self.results, self.errors, export_format, filepath)

    def get_progress(self) -> dict[str, Any]:
        """获取当前进度"""
        return self.progress.copy()

    def get_results(self) -> dict[str, Any]:
        """获取分析结果"""
        return self.results.copy()

    def get_errors(self) -> list[dict[str, Any]]:
        """获取错误信息"""
        return self.errors.copy()

    def clear_results(self) -> None:
        """清空结果"""
        self.results.clear()
        self.errors.clear()
        self.progress = {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "in_progress": 0,
            "start_time": None,
            "end_time": None,
            "estimated_remaining_time": None,
        }
