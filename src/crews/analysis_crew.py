# src/crews/analysis_crew.py
"""
分析团队 - 使用CrewAI真正的多智能体协作
负责基本面分析、风险分析和行业分析，展示智能体间的深度协作与集体决策

重构说明：
- Agent定义: analysis_agents.py
- Task定义: analysis_tasks.py
- 执行逻辑: analysis_executor.py
"""
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, task
from typing import List, Dict, Any, Optional
import logging
import yaml
import os
from datetime import datetime

from src.config import Config
from src.utils.http_utils import with_retry

from src.crews.analysis_agents import (
    create_fundamental_analyst,
    create_risk_assessment_specialist,
    create_industry_expert,
    create_quantitative_analyst,
    create_analysis_coordinator,
)
from src.crews.analysis_tasks import (
    create_fundamental_analysis_task,
    create_risk_assessment_task,
    create_industry_analysis_task,
    create_quantitative_validation_task,
    create_analysis_coordination_task,
)
from src.crews.analysis_executor import (
    prepare_analysis_inputs,
    collect_analysis_outputs,
    calculate_collaboration_scores,
    generate_final_recommendation,
    analyze_collaboration_quality,
)

logger = logging.getLogger(__name__)


@CrewBase
class AnalysisCrew:
    """分析团队 - 展示深度协作分析和集体决策"""

    def __init__(self):
        """初始化分析团队"""
        self.agents_config = self._load_config('config/agents.yaml', 'agent')
        self.tasks_config = self._load_config('config/tasks.yaml', 'task')
        if not self.agents_config:
            self.agents_config = self._get_default_agents_config()
        if not self.tasks_config:
            self.tasks_config = self._get_default_tasks_config()
        logger.info(f"配置加载完成 - agents: {len(self.agents_config)}, tasks: {len(self.tasks_config)}")

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
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
        return {}

    def _get_default_agents_config(self) -> Dict[str, Any]:
        return {
            "fundamental_analyst": {
                "role": "高级基本面分析师",
                "goal": "对{company}进行深度基本面分析，评估公司内在价值和长期投资潜力",
                "backstory": "你是一位经验丰富的基本面分析师，精通财务报表分析和价值评估。"
            },
            "risk_assessment_expert": {
                "role": "风险评估专家",
                "goal": "全面评估{company}的投资风险，包括市场风险、财务风险和运营风险",
                "backstory": "你是专业的风险管理专家，擅长识别和量化各种投资风险。"
            },
            "industry_expert": {
                "role": "行业研究专家",
                "goal": "分析{company}所处行业的竞争格局、发展趋势和公司在行业中的地位",
                "backstory": "你是资深的行业研究专家，对行业发展趋势和竞争格局有深刻理解。"
            },
            "quantitative_analyst": {
                "role": "量化分析师",
                "goal": "通过量化方法验证{company}的分析结果，提供数据支持",
                "backstory": "你是专业的量化分析师，擅长使用统计和数学方法验证分析结果。"
            },
            "analysis_coordinator": {
                "role": "分析协调员",
                "goal": "协调各分析师的工作，整合分析结果并形成最终投资建议",
                "backstory": "你是优秀的分析协调员，擅长整合多方观点和促进团队协作。"
            }
        }

    def _get_default_tasks_config(self) -> Dict[str, Any]:
        return {
            "fundamental_analysis_task": {
                "description": "对{company}进行全面的基本面分析", "expected_output": "详细的基本面分析报告"
            },
            "risk_assessment_task": {
                "description": "对{company}进行全面的风险评估", "expected_output": "全面的风险评估报告"
            },
            "industry_analysis_task": {
                "description": "对{company}进行深度行业分析", "expected_output": "深度行业分析报告"
            },
            "quantitative_validation_task": {
                "description": "对{company}进行量化验证分析", "expected_output": "量化验证报告"
            },
            "analysis_coordination_task": {
                "description": "协调和整合所有分析工作", "expected_output": "最终投资分析报告"
            }
        }

    @agent
    def fundamental_analyst(self) -> Agent:
        return create_fundamental_analyst(self.agents_config)

    @agent
    def risk_assessment_specialist(self) -> Agent:
        return create_risk_assessment_specialist(self.agents_config)

    @agent
    def industry_expert(self) -> Agent:
        return create_industry_expert(self.agents_config)

    @agent
    def quantitative_analyst(self) -> Agent:
        return create_quantitative_analyst()

    @agent
    def analysis_coordinator(self) -> Agent:
        return create_analysis_coordinator()

    @task
    def fundamental_analysis_task(self) -> Task:
        return create_fundamental_analysis_task(self.tasks_config)

    @task
    def risk_assessment_task(self) -> Task:
        return create_risk_assessment_task(self.tasks_config)

    @task
    def industry_analysis_task(self) -> Task:
        return create_industry_analysis_task(self.tasks_config)

    @task
    def quantitative_validation_task(self) -> Task:
        return create_quantitative_validation_task(self.tasks_config)

    @task
    def analysis_coordination_task(self) -> Task:
        return create_analysis_coordination_task(self.tasks_config)

    @property
    def agents(self) -> List[Agent]:
        return [
            self.fundamental_analyst(),
            self.risk_assessment_specialist(),
            self.industry_expert(),
            self.quantitative_analyst(),
            self.analysis_coordinator()
        ]

    @property
    def tasks(self) -> List[Task]:
        return [
            self.fundamental_analysis_task(),
            self.risk_assessment_task(),
            self.industry_analysis_task(),
            self.quantitative_validation_task(),
            self.analysis_coordination_task()
        ]

    def create_crew(self) -> Crew:
        return Crew(
            agents=self.agents, tasks=self.tasks,
            process=Process.hierarchical,
            manager_llm=Config.LLM_MODEL,
            verbose=Config.CREW_VERBOSE,
            llm=Config.LLM_MODEL,
            memory=False, cache=True,
            planning=True, planning_llm=Config.LLM_MODEL,
            share_crew=True,
        )

    def _setup_analysis_collaboration(self):
        """设置分析任务间的协作关系 - 前3个并行，后2个串行"""
        fundamental_task = self.fundamental_analysis_task()
        risk_task = self.risk_assessment_task()
        industry_task = self.industry_analysis_task()
        quant_task = self.quantitative_validation_task()
        coordination_task = self.analysis_coordination_task()

        fundamental_task.async_execution = True
        risk_task.async_execution = True
        industry_task.async_execution = True
        quant_task.context = [fundamental_task, risk_task, industry_task]
        quant_task.async_execution = False
        coordination_task.context = [fundamental_task, risk_task, industry_task, quant_task]
        coordination_task.async_execution = False

    @with_retry(max_retries=Config.API_RETRY_COUNT, backoff_factor=Config.API_RETRY_DELAY)
    def execute_collaborative_analysis(self, company: str, ticker: str,
                                    collection_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行多智能体协作分析"""
        logger.info(f"启动多智能体协作分析: {company} ({ticker})")

        try:
            analysis_inputs = prepare_analysis_inputs(company, ticker, collection_data)
            self._setup_analysis_collaboration()
            crew_instance = self.create_crew()
            result = crew_instance.kickoff(inputs=analysis_inputs)
            agent_outputs = collect_analysis_outputs()
            collaboration_scores = calculate_collaboration_scores(agent_outputs)
            final_recommendation = generate_final_recommendation(agent_outputs, collaboration_scores)

            logger.info(f"多智能体协作分析完成: {company}")
            return {
                'success': True, 'company': company, 'ticker': ticker,
                'result': result, 'agent_outputs': agent_outputs,
                'collaboration_scores': collaboration_scores,
                'final_recommendation': final_recommendation,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'collaboration_metrics': analyze_collaboration_quality(agent_outputs)
            }
        except Exception as e:
            error_msg = f"多智能体协作分析失败: {str(e)}"
            logger.error(error_msg)
            if 'OpenAI' in str(e) or 'LiteLLM' in str(e) or '10054' in str(e):
                raise
            return {
                'success': False, 'error': error_msg,
                'company': company, 'ticker': ticker,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }