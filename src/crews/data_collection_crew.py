# src/crews/data_collection_crew.py
"""
数据收集团队 - 负责市场研究、财务数据和技术分析数据收集

重构说明：
- Agent定义: data_collection_agents.py
- Task定义: data_collection_tasks.py
"""
import sys
import os
import time
import logging
from threading import Timer
from typing import Dict, Any, Optional
from datetime import datetime

sys.path.append(os.path.abspath('.'))

from crewai import Crew, Process
from src.utils.http_utils import with_retry
from src.config import Config
from src.crews.data_collection_agents import (
    create_data_collection_agents,
    _get_default_agents_config,
)
from src.crews.data_collection_tasks import (
    create_data_collection_tasks,
    _get_default_tasks_config,
)

logger = logging.getLogger(__name__)


class TimeoutException(Exception):
    """超时异常"""
    pass


class DataCollectionCrew:
    """数据收集团队"""

    def __init__(self, max_execution_time: int = 300):
        self.max_execution_time = max_execution_time
        self.start_time = None
        self.timeout_timer = None

        self.agents_config = self._load_config('config/agents.yaml')
        self.tasks_config = self._load_config('config/tasks.yaml')

        if not self.agents_config:
            logger.warning("使用内置默认agents配置")
            self.agents_config = _get_default_agents_config()
        if not self.tasks_config:
            logger.warning("使用内置默认tasks配置")
            self.tasks_config = _get_default_tasks_config()

        logger.info(f"配置加载完成 - agents: {len(self.agents_config)}, tasks: {len(self.tasks_config)}")

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        import yaml
        config_filename = os.path.basename(config_file)
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                       'config', config_filename),
            os.path.join(os.path.dirname(os.path.dirname(__file__)),
                       'config', config_filename),
            config_file,
        ]
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        logger.warning(f"未找到配置文件: {config_file}")
        return {}

    def _timeout_handler(self):
        if self.start_time and (time.time() - self.start_time) > self.max_execution_time:
            raise TimeoutException(f"执行超时，已超过 {self.max_execution_time} 秒")

    def create_crew(self, company: str, ticker: str) -> Optional[Crew]:
        """创建Crew实例"""
        try:
            agents = create_data_collection_agents(company, ticker)
            if not agents:
                logger.error("无法创建任何智能体")
                return None

            tasks = create_data_collection_tasks(company, ticker, agents)
            if not tasks:
                logger.error("无法创建任何任务")
                return None

            crew = Crew(
                agents=agents, tasks=tasks,
                process=Process.sequential,
                verbose=False, memory=False, cache=False, planning=False,
            )
            logger.info(f"✓ 成功创建Crew实例，包含 {len(agents)} 个智能体和 {len(tasks)} 个任务")
            return crew
        except Exception as e:
            logger.error(f"创建Crew实例时出错: {str(e)}")
            return None

    @with_retry(max_retries=3, backoff_factor=1.0)
    def execute_data_collection(self, company: str, ticker: str) -> Dict[str, Any]:
        """执行数据收集，带超时控制和自动重试机制"""
        try:
            logger.info(f"开始执行{company}的数据收集任务")
            self.start_time = time.time()

            self.timeout_timer = Timer(self.max_execution_time, self._timeout_handler)
            self.timeout_timer.start()

            crew = self.create_crew(company, ticker)
            if not crew:
                return {
                    "status": "failed",
                    "error": "无法创建Crew实例",
                    "company": company, "ticker": ticker,
                    "timestamp": datetime.now().isoformat()
                }

            logger.info("启动CrewAI多智能体协作...")
            result = crew.kickoff(inputs={"company": company, "ticker": ticker})

            if self.timeout_timer:
                self.timeout_timer.cancel()

            execution_time = time.time() - self.start_time
            logger.info(f"任务完成，执行时间: {execution_time:.2f} 秒")

            return {
                "status": "success",
                "result": result,
                "company": company, "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "agents_count": len(crew.agents),
                "tasks_count": len(crew.tasks)
            }
        except TimeoutException as e:
            logger.error(f"执行超时: {str(e)}")
            return {
                "status": "timeout", "error": str(e),
                "company": company, "ticker": ticker,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"数据收集失败: {str(e)}")
            if 'OpenAI' in str(e) or 'LiteLLM' in str(e) or '10054' in str(e):
                raise
            return {
                "status": "failed", "error": str(e),
                "company": company, "ticker": ticker,
                "timestamp": datetime.now().isoformat()
            }