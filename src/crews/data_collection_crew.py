# src/crews/data_collection_crew.py
"""数据收集团队 - 直接函数调用 + 可选质检 Agent

Profile 分层:
  RAPID:    纯函数调用，零 LLM
  STANDARD: 函数调用 + 1 质检员 Agent
  DEEP:    函数调用 + 1 质检员 Agent（含补漏）
"""

from datetime import datetime
import logging
import time
from typing import Any

from src.config import AnalysisProfile, Config
from src.crews.data_collection_executor import collect_data_direct, run_quality_check
from src.crews.data_parser import collection_data_to_prompt
from src.utils.http_utils import with_retry

logger = logging.getLogger(__name__)


class DataCollectionCrew:
    """数据收集团队 - 直接调用工具获取数据，不再经过 Agent 层"""

    def __init__(self, profile: AnalysisProfile | None = None) -> None:
        self._profile = profile or Config.ANALYSIS_PROFILE

    @with_retry(max_retries=3, backoff_factor=1.0)
    def execute_data_collection(self, company: str, ticker: str) -> dict[str, Any]:
        """执行数据收集，带自动重试机制"""
        try:
            logger.info(f"[数据采集] 开始: {company} ({ticker}), profile={self._profile.value}")
            start_time = time.time()

            data = collect_data_direct(company, ticker)

            if self._profile != AnalysisProfile.RAPID:
                quality = run_quality_check(company, ticker, data, self._profile)
                logger.info(f"[数据采集] 质检: {quality['quality']}, {quality['summary']}")
            else:
                quality = {"quality": "high", "issues": [], "summary": "RAPID 模式跳过质检"}

            prompt_data = collection_data_to_prompt(data)
            effective = any(len(v) > 30 for v in prompt_data.values())

            if not effective:
                logger.warning(f"[数据采集] 数据为空或无效: {company} ({ticker})")
                return {
                    "status": "failed",
                    "error": "数据采集结果为空",
                    "company": company,
                    "ticker": ticker,
                    "timestamp": datetime.now().isoformat(),
                }

            execution_time = time.time() - start_time
            logger.info(f"[数据采集] 完成, 耗时: {execution_time:.2f}s")

            return {
                "success": True,
                "status": "success",
                "result": prompt_data,
                "collection_data": data,
                "quality": quality,
                "company": company,
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "profile": self._profile.value,
            }
        except Exception as e:
            logger.error(f"[数据采集] 失败: {str(e)}")
            if "OpenAI" in str(e) or "LiteLLM" in str(e) or "10054" in str(e):
                raise
            return {
                "status": "failed",
                "error": str(e),
                "company": company,
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
            }