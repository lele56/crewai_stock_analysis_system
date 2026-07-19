# src/crews/analysis_crew.py
"""分析团队 - 使用CrewAI真正的多智能体协作
负责基本面分析、风险分析和行业分析，展示智能体间的深度协作与集体决策

重构说明：
- Agent定义: analysis_agents.py
- Task定义: analysis_tasks.py
- 执行逻辑: analysis_executor.py
"""

from datetime import datetime
import logging
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, task

from src.config import AnalysisProfile, Config
from src.crews.analysis_agents import (
    create_analysis_coordinator,
    create_fundamental_analyst,
    create_industry_expert,
    create_risk_assessment_specialist,
)
from src.crews.analysis_executor import (
    analyze_collaboration_quality,
    build_debate_prompt,
    build_iteration_prompt,
    calculate_collaboration_scores,
    collect_analysis_outputs,
    generate_agent_abstract,
    generate_final_recommendation,
    prepare_analysis_inputs,
)
from src.crews.analysis_tasks import (
    create_analysis_coordination_task,
    create_fundamental_analysis_task,
    create_industry_analysis_task,
    create_risk_assessment_task,
)
from src.utils.http_utils import with_retry

logger = logging.getLogger(__name__)


@CrewBase
class AnalysisCrew:
    """分析团队 - 展示深度协作分析和集体决策"""

    def __init__(self, profile: AnalysisProfile | None = None) -> None:
        self._profile = profile or Config.ANALYSIS_PROFILE
        self._active_agents = Config.get_profile_agents("analysis", self._profile)

    @agent
    def fundamental_analyst(self) -> Agent:
        """创建基本面分析师 Agent"""
        return create_fundamental_analyst(self.agents_config)

    @agent
    def risk_assessment_specialist(self) -> Agent:
        """创建风险评估专家 Agent"""
        return create_risk_assessment_specialist(self.agents_config)

    @agent
    def industry_expert(self) -> Agent:
        """创建行业研究专家 Agent"""
        return create_industry_expert(self.agents_config)

    @agent
    def analysis_coordinator(self) -> Agent:
        """创建分析协调员 Agent"""
        return create_analysis_coordinator()

    @task
    def fundamental_analysis_task(self) -> Task:
        """创建基本面分析任务"""
        return create_fundamental_analysis_task(self.tasks_config)

    @task
    def risk_assessment_task(self) -> Task:
        """创建风险评估任务"""
        return create_risk_assessment_task(self.tasks_config)

    @task
    def industry_analysis_task(self) -> Task:
        """创建行业分析任务"""
        return create_industry_analysis_task(self.tasks_config)

    @task
    def analysis_coordination_task(self) -> Task:
        """创建分析协调任务"""
        return create_analysis_coordination_task(self.tasks_config)

    @property
    def agents(self) -> list[Agent]:
        """获取当前 profile 下的 Agent 列表"""
        all_agents = [
            ("fundamental_analyst", self.fundamental_analyst()),
            ("risk_assessment_specialist", self.risk_assessment_specialist()),
            ("industry_expert", self.industry_expert()),
            ("analysis_coordinator", self.analysis_coordinator()),
        ]
        return [agent for name, agent in all_agents if name in self._active_agents]

    @property
    def tasks(self) -> list[Task]:
        """获取当前 profile 下的 Task 列表"""
        all_tasks = [
            ("fundamental_analyst", self.fundamental_analysis_task()),
            ("risk_assessment_specialist", self.risk_assessment_task()),
            ("industry_expert", self.industry_analysis_task()),
            ("analysis_coordinator", self.analysis_coordination_task()),
        ]
        return [task for name, task in all_tasks if name in self._active_agents]

    def create_crew(self) -> Crew:
        """创建 CrewAI Crew 实例"""
        return Crew(
            agents=self.agents,
            tasks=self._task_list,
            process=Process.sequential,
            verbose=Config.CREW_VERBOSE,
            memory=False,
            cache=True,
            planning=False,
        )

    def _setup_analysis_collaboration(self) -> None:
        """按真实依赖关系设置 context，避免幻觉级联

        依赖关系:
          fundamental_analyst     → 独立（分析原始数据）
          risk_assessment         → 独立（分析原始数据）
          industry_expert         → 独立（分析原始数据）
          analysis_coordinator    → 依赖全部前3个（汇总）
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

        # 分析协调员 → 依赖前3个全部
        coordinator = task_by_role.get("分析协调员")
        if coordinator:
            predecessors = [t for t in self._task_list if t is not coordinator]
            if predecessors:
                coordinator.context = predecessors

    @with_retry(max_retries=Config.API_RETRY_COUNT, backoff_factor=Config.API_RETRY_DELAY)
    def execute_collaborative_analysis(
        self, company: str, ticker: str, collection_data: dict[str, Any] = None
    ) -> dict[str, Any]:
        """执行多智能体协作分析

        Profile 分层:
          RAPID:    串行分析（3 分析师 + 协调员）
          STANDARD: 迭代精炼（初稿 → 协调员找矛盾 → 补充 → 结论）
          DEEP:     辩论模式（初稿 → 交叉审阅 → 修正 → 结论）
        """
        logger.info(f"启动多智能体协作分析: {company} ({ticker}), profile={self._profile.value}")

        try:
            analysis_inputs = prepare_analysis_inputs(company, ticker, collection_data)
            self._setup_analysis_collaboration()
            crew_instance = self.create_crew()
            result = crew_instance.kickoff(inputs=analysis_inputs)
            agent_outputs = collect_analysis_outputs(result.tasks_output if hasattr(result, 'tasks_output') else [])

            if self._profile == AnalysisProfile.RAPID:
                pass
            elif self._profile == AnalysisProfile.DEEP:
                agent_outputs = self._run_debate_rounds(company, ticker, agent_outputs, analysis_inputs)
            else:
                agent_outputs = self._run_iteration_round(company, ticker, agent_outputs, analysis_inputs)

            collaboration_scores = calculate_collaboration_scores(list(agent_outputs.values()))
            final_recommendation = generate_final_recommendation(collaboration_scores)

            logger.info(f"多智能体协作分析完成: {company}")
            return {
                "success": True,
                "company": company,
                "ticker": ticker,
                "result": result,
                "agent_outputs": agent_outputs,
                "collaboration_scores": collaboration_scores,
                "final_recommendation": final_recommendation,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "collaboration_metrics": analyze_collaboration_quality(collaboration_scores),
            }
        except Exception as e:
            error_msg = f"多智能体协作分析失败: {str(e)}"
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

    def _run_iteration_round(
        self, company: str, ticker: str, agent_outputs: dict[str, Any], inputs: dict
    ) -> dict[str, Any]:
        """STANDARD 迭代精炼：协调员找矛盾 → 分析师补充"""
        logger.info("[迭代] 开始迭代精炼")
        try:
            from crewai import Agent, Crew, Process, Task

            from src.utils.llm_factory import get_llm

            questions = build_iteration_prompt("", agent_outputs)
            if not questions:
                logger.info("[迭代] 无反观点，跳过迭代")
                return agent_outputs

            for q in questions[:2]:
                agent_name = q["agent"]
                agent = Agent(
                    role=f"{agent_name}（补充分析）",
                    goal="针对协调员提出的问题，补充分析",
                    backstory="补充分析专家",
                    llm=get_llm(),
                    verbose=False,
                    allow_delegation=False,
                    max_iter=1,
                )
                task = Task(
                    description=q["question"],
                    expected_output="补充分析结论",
                    agent=agent,
                )
                crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False, memory=False)
                result = crew.kickoff()
                key = f"{agent_name}_iteration"
                agent_outputs[key] = str(result.raw) if hasattr(result, "raw") else str(result)

            logger.info("[迭代] 迭代精炼完成")
            return agent_outputs
        except Exception as e:
            logger.warning(f"[迭代] 失败: {e}，使用原始输出")
            return agent_outputs

    def _run_debate_rounds(
        self, company: str, ticker: str, agent_outputs: dict[str, Any], inputs: dict
    ) -> dict[str, Any]:
        """DEEP 辩论：交叉审阅 → 质疑 → 修正"""
        logger.info("[辩论] 开始辩论模式")
        try:
            from crewai import Agent, Crew, Process, Task

            from src.utils.llm_factory import get_llm

            agent_names = [k for k in agent_outputs if not k.startswith("_") and "task_" in k]
            if len(agent_names) < 2:
                logger.info("[辩论] Agent 不足，跳过辩论")
                return agent_outputs

            abstracts = [
                generate_agent_abstract(str(agent_outputs[name]), name)
                for name in agent_names
            ]

            for i, name in enumerate(agent_names):
                peer_abstracts = [a for j, a in enumerate(abstracts) if j != i]
                prompt = build_debate_prompt(name, str(agent_outputs[name]), peer_abstracts)

                agent = Agent(
                    role=f"{name}（辩论审阅）",
                    goal="审阅其他分析师的观点，提出质疑和补充",
                    backstory="资深辩论分析师",
                    llm=get_llm(),
                    verbose=False,
                    allow_delegation=False,
                    max_iter=1,
                )
                task = Task(
                    description=prompt,
                    expected_output="审阅意见",
                    agent=agent,
                )
                crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False, memory=False)
                result = crew.kickoff()
                agent_outputs[f"{name}_debate"] = str(result.raw) if hasattr(result, "raw") else str(result)

            logger.info("[辩论] 辩论模式完成")
            return agent_outputs
        except Exception as e:
            logger.warning(f"[辩论] 失败: {e}，使用原始输出")
            return agent_outputs