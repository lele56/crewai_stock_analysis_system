# src/tools/task_orchestration_tool.py
"""任务编排工具 - 为智能体提供高级任务编排功能"""
from typing import Dict, Any, List
import logging

from ..tasks.dynamic_task_allocation import (
    get_task_allocator, get_decision_maker,
    AgentCapability, TaskComplexity, DecisionType,
)
from src.tools.collaboration_tools import CollaborationOptimizer

logger = logging.getLogger(__name__)


class TaskOrchestrationTool:
    """任务编排工具"""

    name: str = "Task Orchestration Tool"
    description: str = "提供智能体任务编排、协作优化和集体决策功能"

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.task_allocator = get_task_allocator()
        self.decision_maker = get_decision_maker()
        self.optimizer = CollaborationOptimizer()

    def _run(self, action: str, **kwargs) -> str:
        """执行任务编排操作"""
        try:
            if action == "create_task":
                return self._create_task(**kwargs)
            elif action == "allocate_tasks":
                return self._allocate_tasks()
            elif action == "complete_task":
                return self._complete_task(**kwargs)
            elif action == "create_vote":
                return self._create_vote(**kwargs)
            elif action == "cast_vote":
                return self._cast_vote(**kwargs)
            elif action == "analyze_collaboration":
                return self._analyze_collaboration()
            elif action == "optimize_workflow":
                return self._optimize_workflow()
            elif action == "get_workload":
                return self._get_workload()
            return f"未知操作: {action}"
        except Exception as e:
            logger.error(f"任务编排操作失败: {str(e)}")
            return f"错误: {str(e)}"

    def _create_task(self, name: str, description: str, capabilities: List[str],
                    complexity: str = "medium", priority: int = 1) -> str:
        capability_enums = []
        for cap_str in capabilities:
            try:
                capability_enums.append(AgentCapability(cap_str))
            except ValueError:
                logger.warning(f"未知能力: {cap_str}")
        try:
            complexity_enum = TaskComplexity(complexity)
        except ValueError:
            complexity_enum = TaskComplexity.MEDIUM
        task_id = self.task_allocator.create_task(
            name=name, description=description, required_capabilities=capability_enums,
            complexity=complexity_enum, priority=priority
        )
        return f"任务已创建 (ID: {task_id})"

    def _allocate_tasks(self) -> str:
        allocated_tasks = self.task_allocator.allocate_tasks()
        if not allocated_tasks:
            return "没有可分配的任务"
        return f"已分配 {len(allocated_tasks)} 个任务: {', '.join(allocated_tasks)}"

    def _complete_task(self, task_id: str, result: Dict[str, Any], success: bool = True) -> str:
        self.task_allocator.complete_task(task_id, result, success)
        return f"任务 {task_id} 已标记为完成"

    def _create_vote(self, topic: str, options: List[str], voters: List[str],
                    decision_type: str = "majority") -> str:
        try:
            decision_enum = DecisionType(decision_type)
        except ValueError:
            decision_enum = DecisionType.MAJORITY
        vote_id = self.decision_maker.create_vote(
            topic=topic, options=options, voters=voters, decision_type=decision_enum
        )
        return f"投票已创建 (ID: {vote_id})"

    def _cast_vote(self, vote_id: str, option: str) -> str:
        self.decision_maker.cast_vote(vote_id, self.agent_name, option)
        return f"投票已提交: {option}"

    def _analyze_collaboration(self) -> str:
        analysis = self.optimizer.analyze_collaboration_patterns()
        result = f"协作效率分析:\n- 效率分数: {analysis['collaboration_efficiency']:.2f}\n"
        result += f"- 瓶颈数量: {len(analysis['bottlenecks'])}\n"
        result += f"- 优化建议: {len(analysis['recommendations'])}条\n"
        if analysis['bottlenecks']:
            result += "\n发现的瓶颈:\n"
            for bottleneck in analysis['bottlenecks']:
                result += f"- {bottleneck}\n"
        if analysis['recommendations']:
            result += "\n优化建议:\n"
            for rec in analysis['recommendations']:
                result += f"- {rec}\n"
        return result

    def _optimize_workflow(self) -> str:
        optimization = self.optimizer.optimize_task_allocation()
        result = f"工作流程优化:\n- 优化操作: {len(optimization['optimization_actions'])}条\n"
        result += f"- 过载智能体: {len(optimization['overloaded_agents'])}个\n"
        result += f"- 低利用智能体: {len(optimization['underutilized_agents'])}个\n"
        if optimization['optimization_actions']:
            result += "\n优化操作:\n"
            for action in optimization['optimization_actions']:
                result += f"- {action}\n"
        return result

    def _get_workload(self) -> str:
        workload = self.task_allocator.get_agent_workload(self.agent_name)
        if not workload:
            return f"智能体 {self.agent_name} 的工作负载信息不可用"
        result = f"智能体 {self.agent_name} 的工作负载:\n"
        result += f"- 当前负载: {workload['current_workload']:.1f}/{workload['max_workload']:.1f}\n"
        result += f"- 负载百分比: {workload['workload_percentage']:.1f}%\n"
        result += f"- 活跃任务: {workload['active_tasks']}\n"
        result += f"- 成功率: {workload['success_rate']:.2f}\n"
        result += f"- 可用性: {'可用' if workload['availability'] else '不可用'}\n"
        result += f"- 能力: {', '.join(workload['capabilities'])}"
        return result


def get_task_orchestration_tool(agent_name: str) -> TaskOrchestrationTool:
    """获取任务编排工具"""
    return TaskOrchestrationTool(agent_name)