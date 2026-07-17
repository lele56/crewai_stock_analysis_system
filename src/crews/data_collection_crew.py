# src/crews/data_collection_crew.py
"""数据收集团队 - 负责市场研究、财务数据和技术分析数据收集

重构说明：
- Agent定义: data_collection_agents.py
- Task定义: data_collection_tasks.py
"""

from datetime import datetime
import logging
import os
import time
from typing import Any

from crewai import Crew, Process
import yaml

from src.config import AnalysisProfile, Config
from src.crews.data_collection_agents import (
    _get_default_agents_config,
    create_data_collection_agents,
)
from src.crews.data_collection_tasks import (
    _get_default_tasks_config,
    create_data_collection_tasks,
)
from src.utils.http_utils import with_retry

logger = logging.getLogger(__name__)


class DataCollectionCrew:
    """数据收集团队 - 负责收集股票相关数据"""

    def __init__(self, profile: AnalysisProfile | None = None) -> None:
        self._profile = profile or Config.ANALYSIS_PROFILE
        self.agents_config = self._load_config("agents_data.yaml")
        self.tasks_config = self._load_config("tasks_data.yaml")

        if not self.agents_config:
            logger.warning("使用内置默认agents配置")
            self.agents_config = _get_default_agents_config()
        if not self.tasks_config:
            logger.warning("使用内置默认tasks配置")
            self.tasks_config = _get_default_tasks_config()

        logger.info(f"配置加载完成 - agents: {len(self.agents_config)}, tasks: {len(self.tasks_config)}")

    def _load_config(self, config_file: str) -> dict[str, Any]:
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), "config", os.path.basename(config_file))
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        logger.warning(f"未找到配置文件: {config_file}")
        return {}

    def create_crew(self, company: str, ticker: str) -> Crew | None:
        """创建Crew实例"""
        try:
            agents = create_data_collection_agents(self.agents_config, profile=self._profile)
            if not agents:
                logger.error("无法创建任何智能体")
                return None

            tasks = create_data_collection_tasks(self.tasks_config, agents=agents)
            if not tasks:
                logger.error("无法创建任何任务")
                return None

            # 数据收集有先后依赖：市场数据 → 财务数据 → 技术分析 → 协调汇总
            # 全串行执行，确保每个任务能拿到前一个任务的输出
            for task in tasks:
                task.async_execution = False
            for i in range(1, len(tasks)):
                tasks[i].context = [tasks[i - 1]]

            crew = Crew(
                agents=list(agents.values()),
                tasks=tasks,
                process=Process.sequential,
                verbose=False,
                memory=False,
                cache=False,
                planning=False,
            )
            logger.info(f"✓ 成功创建Crew实例，包含 {len(agents)} 个智能体和 {len(tasks)} 个任务")
            return crew
        except Exception as e:
            logger.error(f"创建Crew实例时出错: {str(e)}")
            return None

    @with_retry(max_retries=3, backoff_factor=1.0)
    def execute_data_collection(self, company: str, ticker: str) -> dict[str, Any]:
        """执行数据收集，带自动重试机制"""
        try:
            logger.info(f"开始执行{company}的数据收集任务")
            start_time = time.time()

            crew = self.create_crew(company, ticker)
            if not crew:
                return {
                    "status": "failed",
                    "error": "无法创建Crew实例",
                    "company": company,
                    "ticker": ticker,
                    "timestamp": datetime.now().isoformat(),
                }

            logger.info("启动CrewAI多智能体协作...")
            result = crew.kickoff(inputs={"company": company, "ticker": ticker})

            execution_time = time.time() - start_time
            logger.info(f"任务完成，执行时间: {execution_time:.2f} 秒")

            return {
                "success": True,
                "status": "success",
                "result": result,
                "company": company,
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "agents_count": len(crew.agents),
                "tasks_count": len(crew.tasks),
            }
        except Exception as e:
            logger.error(f"数据收集失败: {str(e)}")
            if "OpenAI" in str(e) or "LiteLLM" in str(e) or "10054" in str(e):
                raise
            return {
                "status": "failed",
                "error": str(e),
                "company": company,
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
            }