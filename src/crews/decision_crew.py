# src/crews/decision_crew.py
"""决策团队 - 使用CrewAI真正的集体决策机制
负责投资建议、报告生成和质量控制，展示智能体间的集体决策和投票机制

重构说明：
- Agent定义: decision_agents.py
- Task定义: decision_tasks.py
- 执行逻辑: decision_executor.py
- 主文件仅保留Crew编排和入口接口
"""

from datetime import datetime
import logging
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, task

from src.config import AnalysisProfile, Config

# 导入拆分后的模块
from src.crews.decision_agents import (
    create_investment_advisor,
    create_report_generator,
)
from src.crews.decision_executor import (
    analyze_collective_decision,
    calculate_decision_metrics,
    collect_decision_outputs,
    extract_final_recommendation,
    prepare_decision_inputs,
)
from src.crews.decision_tasks import (
    create_investment_strategy_task,
    create_report_generation_task,
)
from src.utils.http_utils import with_retry

logger = logging.getLogger(__name__)


@CrewBase
class DecisionCrew:
    """决策团队 - 展示集体决策和投资建议生成"""

    def __init__(self, profile: AnalysisProfile | None = None) -> None:
        self._profile = profile or Config.ANALYSIS_PROFILE
        self._active_agents = Config.get_profile_agents("decision", self._profile)

    @agent
    def investment_advisor(self) -> Agent:
        """创建投资策略顾问 Agent"""
        return create_investment_advisor(self.agents_config)

    @agent
    def report_generator(self) -> Agent:
        """创建报告生成器 Agent（含质量审核）"""
        return create_report_generator(self.agents_config)

    @task
    def investment_strategy_task(self) -> Task:
        """创建投资策略任务"""
        return create_investment_strategy_task(self.tasks_config)

    @task
    def report_generation_task(self) -> Task:
        """创建报告生成任务（含质量审核）"""
        return create_report_generation_task(self.tasks_config)

    @property
    def agents(self) -> list[Agent]:
        """获取当前 profile 下的智能体"""
        all_agents = [
            ("investment_advisor", self.investment_advisor()),
            ("report_generator", self.report_generator()),
        ]
        return [agent for name, agent in all_agents if name in self._active_agents]

    @property
    def tasks(self) -> list[Task]:
        """获取当前 profile 下的任务"""
        all_tasks = [
            ("investment_advisor", self.investment_strategy_task()),
            ("report_generator", self.report_generation_task()),
        ]
        return [task for name, task in all_tasks if name in self._active_agents]

    def create_crew(self) -> Crew:
        """创建Crew实例 - 配置集体决策机制"""
        return Crew(
            agents=self.agents,
            tasks=self._task_list,
            process=Process.sequential,
            verbose=Config.CREW_VERBOSE,
            memory=False,
            cache=True,
            planning=False,
        )

    def _setup_collective_decision_context(self) -> None:
        """按真实依赖关系设置 context

        依赖关系:
          investment_advisor      → 独立（基于分析结果制定策略）
          report_generator        → 依赖策略（整合生成报告+质量审核）
        """
        self._task_list = self.tasks
        for t, a in zip(self._task_list, self.agents, strict=False):
            t.agent = a
            t.async_execution = False

        n = len(self._task_list)
        if n <= 1:
            return

        agent_roles = [a.role for a in self.agents]
        task_by_role = dict(zip(agent_roles, self._task_list, strict=False))

        # 报告生成专家 → 依赖投资策略顾问
        reporter = task_by_role.get("报告生成专家")
        advisor = task_by_role.get("投资策略顾问")
        if reporter and advisor and reporter is not advisor:
            reporter.context = [advisor]

    @with_retry(max_retries=Config.API_RETRY_COUNT, backoff_factor=Config.API_RETRY_DELAY)
    def execute_collective_decision(
        self, company: str, ticker: str, analysis_data: dict[str, Any] = None
    ) -> dict[str, Any]:
        """执行集体决策过程，带自动重试机制"""
        logger.info(f"启动集体投资决策: {company} ({ticker})")

        try:
            decision_inputs = prepare_decision_inputs(analysis_data or {})
            self._setup_collective_decision_context()
            crew_instance = self.create_crew()
            result = crew_instance.kickoff(inputs=decision_inputs)
            decision_outputs = collect_decision_outputs(result.tasks_output if hasattr(result, 'tasks_output') else [])
            decision_analysis = analyze_collective_decision(decision_outputs)
            final_recommendation = extract_final_recommendation(decision_analysis)

            logger.info(f"集体决策完成: {company}")
            return {
                "success": True,
                "company": company,
                "ticker": ticker,
                "result": result,
                "decision_outputs": decision_outputs,
                "decision_analysis": decision_analysis,
                "final_recommendation": final_recommendation,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "collective_decision_metrics": calculate_decision_metrics(decision_analysis),
            }

        except Exception as e:
            error_msg = f"集体决策失败: {str(e)}"
            logger.error(error_msg)
            if "OpenAI" in str(e) or "LiteLLM" in str(e) or "10054" in str(e):
                raise
            return {
                "success": False,
                "error": error_msg,
                "company": company,
                "ticker": ticker,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

    def execute_decision_process(
        self, company: str, ticker: str, analysis_data: dict[str, Any] = None
    ) -> dict[str, Any]:
        """执行决策过程 - 兼容性入口"""
        try:
            logger.info(f"执行决策过程: {company} ({ticker})")
            return self.execute_collective_decision(company, ticker, analysis_data)
        except Exception as e:
            logger.error(f"执行决策过程时出错: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "company": company,
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
            }

    def get_crew_info(self) -> dict[str, Any]:
        """获取团队信息"""
        return {
            "name": "决策团队 (集体决策机制版)",
            "agents": ["投资策略顾问", "风险管理专家", "报告生成器", "质量保证专家"],
            "description": "使用CrewAI实现集体投资决策，模拟投资委员会的决策过程",
            "features": ["多角度专业分析", "并行执行加速", "质量保证环节"],
            "process": "hierarchical (层级化决策流程)",
        }