# src/crews/decision_crew.py
"""
决策团队 - 使用CrewAI真正的集体决策机制
负责投资建议、报告生成和质量控制，展示智能体间的集体决策和投票机制

重构说明：
- Agent定义: decision_agents.py
- Task定义: decision_tasks.py
- 执行逻辑: decision_executor.py
- 主文件仅保留Crew编排和入口接口
"""
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from typing import List, Dict, Any, Optional
import logging
import yaml
import os
from datetime import datetime

from src.config import Config
from src.utils.http_utils import with_retry

# 导入拆分后的模块
from src.crews.decision_agents import (
    create_investment_advisor,
    create_risk_manager,
    create_report_generator,
    create_quality_assurance_specialist,
)
from src.crews.decision_tasks import (
    create_investment_strategy_task,
    create_risk_assessment_task,
    create_report_generation_task,
    create_quality_assurance_task,
)
from src.crews.decision_executor import (
    prepare_decision_inputs,
    collect_decision_outputs,
    analyze_collective_decision,
    extract_final_recommendation,
    calculate_decision_metrics,
    get_investment_rating,
    generate_analysis_summary,
    generate_investment_report,
    save_report,
    export_to_json,
)

logger = logging.getLogger(__name__)


@CrewBase
class DecisionCrew:
    """决策团队 - 展示集体决策和投资建议生成"""

    def __init__(self):
        """初始化决策团队"""
        self.agents_config = self._load_config('config/agents.yaml', 'agent')
        self.tasks_config = self._load_config('config/tasks.yaml', 'task')

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
        logger.warning(f"配置文件未找到: {config_file}，使用默认配置")
        return {}

    def _get_default_agents_config(self) -> Dict[str, Any]:
        """获取默认Agent配置"""
        return {}

    def _get_default_tasks_config(self) -> Dict[str, Any]:
        """获取默认Task配置"""
        return {}

    @agent
    def investment_advisor(self) -> Agent:
        return create_investment_advisor(self.agents_config)

    @agent
    def risk_manager(self) -> Agent:
        return create_risk_manager()

    @agent
    def report_generator(self) -> Agent:
        return create_report_generator(self.agents_config)

    @agent
    def quality_assurance_specialist(self) -> Agent:
        return create_quality_assurance_specialist(self.agents_config)

    @task
    def investment_strategy_task(self) -> Task:
        return create_investment_strategy_task(self.tasks_config)

    @task
    def risk_assessment_task(self) -> Task:
        return create_risk_assessment_task()

    @task
    def report_generation_task(self) -> Task:
        return create_report_generation_task(self.tasks_config)

    @task
    def quality_assurance_task(self) -> Task:
        return create_quality_assurance_task(self.tasks_config)

    @property
    def agents(self) -> List[Agent]:
        """获取所有智能体 - 精简为4个核心Agent"""
        return [
            self.investment_advisor(),
            self.risk_manager(),
            self.report_generator(),
            self.quality_assurance_specialist()
        ]

    @property
    def tasks(self) -> List[Task]:
        """获取所有任务 - 精简为4个核心任务"""
        return [
            self.investment_strategy_task(),
            self.risk_assessment_task(),
            self.report_generation_task(),
            self.quality_assurance_task()
        ]

    def create_crew(self) -> Crew:
        """创建Crew实例 - 配置集体决策机制"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_llm=Config.LLM_MODEL,
            verbose=Config.CREW_VERBOSE,
            llm=Config.LLM_MODEL,
            memory=False,
            cache=True,
            planning=True,
            planning_llm=Config.LLM_MODEL,
            share_crew=True,
        )

    def _setup_collective_decision_context(self):
        """设置集体决策的任务上下文 - 投资策略和风险评估并行"""
        strategy_task = self.investment_strategy_task()
        risk_task = self.risk_assessment_task()
        report_task = self.report_generation_task()
        quality_task = self.quality_assurance_task()

        strategy_task.async_execution = True
        risk_task.async_execution = True
        report_task.context = [strategy_task, risk_task]
        report_task.async_execution = False
        quality_task.context = [report_task]
        quality_task.async_execution = False

    @with_retry(max_retries=Config.API_RETRY_COUNT, backoff_factor=Config.API_RETRY_DELAY)
    def execute_collective_decision(self, company: str, ticker: str,
                                 analysis_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行集体决策过程，带自动重试机制"""
        logger.info(f"启动集体投资决策: {company} ({ticker})")

        try:
            decision_inputs = prepare_decision_inputs(company, ticker, analysis_data)
            self._setup_collective_decision_context()
            crew_instance = self.create_crew()
            result = crew_instance.kickoff(inputs=decision_inputs)
            decision_outputs = collect_decision_outputs()
            decision_analysis = analyze_collective_decision(decision_outputs)
            final_recommendation = extract_final_recommendation(decision_outputs)

            logger.info(f"集体决策完成: {company}")
            return {
                'success': True,
                'company': company,
                'ticker': ticker,
                'result': result,
                'decision_outputs': decision_outputs,
                'decision_analysis': decision_analysis,
                'final_recommendation': final_recommendation,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'collective_decision_metrics': calculate_decision_metrics(decision_analysis)
            }

        except Exception as e:
            error_msg = f"集体决策失败: {str(e)}"
            logger.error(error_msg)
            if 'OpenAI' in str(e) or 'LiteLLM' in str(e) or '10054' in str(e):
                raise
            return {
                'success': False, 'error': error_msg,
                'company': company, 'ticker': ticker,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    def execute_decision_process(self, company: str, ticker: str,
                               analysis_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行决策过程 - 兼容性入口"""
        try:
            logger.info(f"执行决策过程: {company} ({ticker})")
            return self.execute_collective_decision(company, ticker, analysis_data)
        except Exception as e:
            logger.error(f"执行决策过程时出错: {str(e)}")
            return {
                "status": "failed", "error": str(e),
                "company": company, "ticker": ticker,
                "timestamp": datetime.now().isoformat()
            }

    def get_investment_rating(self, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取投资评级 - 供主系统调用"""
        return get_investment_rating(decision_data)

    def generate_analysis_summary(self, analysis_data: Dict[str, Any]) -> str:
        """生成分析摘要 - 供主系统调用"""
        return generate_analysis_summary(analysis_data)

    def generate_investment_report(self, company: str, ticker: str,
                                  all_data: Dict[str, Any]) -> str:
        """生成投资报告 - 供主系统调用"""
        return generate_investment_report(company, ticker, all_data)

    def save_report(self, company: str, ticker: str, report_content: str) -> str:
        """保存报告 - 供主系统调用"""
        return save_report(company, ticker, report_content)

    def export_to_json(self, company: str, ticker: str, data: Dict[str, Any]) -> str:
        """导出JSON数据 - 供主系统调用"""
        return export_to_json(company, ticker, data)

    def get_crew_info(self) -> Dict[str, Any]:
        """获取团队信息"""
        return {
            'name': '决策团队 (集体决策机制版)',
            'agents': ['投资策略顾问', '风险管理专家', '报告生成器', '质量保证专家'],
            'description': '使用CrewAI实现集体投资决策，模拟投资委员会的决策过程',
            'features': ['多角度专业分析', '并行执行加速', '质量保证环节'],
            'process': 'hierarchical (层级化决策流程)'
        }