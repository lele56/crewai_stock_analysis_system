# src/tasks/dynamic_task_allocation.py
"""
动态任务分配器 - 核心分配逻辑
"""
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
from collections import defaultdict
import heapq

from .task_dataclasses import (
    AgentCapability, TaskComplexity, TaskStatus, AgentProfile, DynamicTask,
    DecisionType, VotingRecord,
)
from .collective_decision_maker import get_decision_maker, create_investment_decision_vote  # noqa: F401 向后兼容

logger = logging.getLogger(__name__)


class DynamicTaskAllocator:
    """动态任务分配器"""

    def __init__(self, communication_hub):
        self.communication_hub = communication_hub
        self.agent_profiles: Dict[str, AgentProfile] = {}
        self.task_queue: List[DynamicTask] = []
        self.active_tasks: Dict[str, DynamicTask] = {}
        self.completed_tasks: Dict[str, DynamicTask] = {}
        self.allocation_history: List[Dict[str, Any]] = []
        self.load_balancing_enabled = True

    def register_agent(self, agent_name: str, capabilities: List[AgentCapability],
                      capability_scores: Dict[AgentCapability, float] = None,
                      max_workload: float = 100.0) -> AgentProfile:
        """注册智能体"""
        profile = AgentProfile(
            name=agent_name,
            capabilities=capabilities,
            capability_scores=capability_scores or {},
            max_workload=max_workload
        )
        self.agent_profiles[agent_name] = profile
        logger.info(f"智能体已注册: {agent_name}, 能力: {[cap.value for cap in capabilities]}")
        return profile

    def create_task(self, name: str, description: str,
                  required_capabilities: List[AgentCapability],
                  complexity: TaskComplexity = TaskComplexity.MEDIUM,
                  priority: int = 1, dependencies: List[str] = None,
                  estimated_duration: int = 60) -> str:
        """创建新任务"""
        task = DynamicTask(
            name=name,
            description=description,
            required_capabilities=required_capabilities,
            complexity=complexity,
            priority=priority,
            dependencies=dependencies or [],
            estimated_duration=estimated_duration,
        )
        heapq.heappush(self.task_queue, (-priority, task.id, task))
        logger.info(f"任务已创建: {name} (ID: {task.id})")
        return task.id

    def allocate_tasks(self) -> List[str]:
        """分配待处理任务"""
        allocated_tasks = []
        if not self.task_queue:
            return allocated_tasks

        skipped = set()

        while self.task_queue:
            _, task_id, task = heapq.heappop(self.task_queue)

            if not self._check_dependencies(task):
                if task_id in skipped:
                    heapq.heappush(self.task_queue, (-task.priority, task_id, task))
                    break
                heapq.heappush(self.task_queue, (-task.priority, task_id, task))
                skipped.add(task_id)
                continue

            best_agent = self._select_best_agent(task)
            if best_agent:
                self._assign_task(task, best_agent)
                allocated_tasks.append(task.id)
                skipped.clear()
            else:
                if task_id in skipped:
                    heapq.heappush(self.task_queue, (-task.priority, task_id, task))
                    break
                heapq.heappush(self.task_queue, (-task.priority, task_id, task))
                skipped.add(task_id)

        return allocated_tasks

    def _select_best_agent(self, task: DynamicTask) -> Optional[str]:
        available_agents = []
        for agent_name, profile in self.agent_profiles.items():
            if not profile.availability:
                continue
            fitness = profile.calculate_fitness(task.required_capabilities, task.complexity)
            if fitness > 0:
                available_agents.append((agent_name, fitness))

        if not available_agents:
            return None

        available_agents.sort(key=lambda x: x[1], reverse=True)

        if self.load_balancing_enabled and len(available_agents) > 1:
            top_candidates = available_agents[:3]
            best_agent = min(top_candidates,
                           key=lambda x: self.agent_profiles[x[0]].current_workload)
            return best_agent[0]
        else:
            return available_agents[0][0]

    def _assign_task(self, task: DynamicTask, agent_name: str):
        task.assigned_agent = agent_name
        task.status = TaskStatus.ASSIGNED
        task.started_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        profile = self.agent_profiles[agent_name]
        profile.current_workload += task.estimated_duration
        profile.task_history.append(task.id)

        self.allocation_history.append({
            'task_id': task.id, 'task_name': task.name,
            'agent': agent_name, 'allocated_at': task.started_at,
            'complexity': task.complexity.value, 'priority': task.priority
        })

        from ..tools.communication_tools import MessageType, MessagePriority
        self.communication_hub.send_message(
            sender="TaskAllocator", receiver=agent_name,
            message_type=MessageType.TASK_DELEGATION,
            subject=f"新任务分配: {task.name}",
            content={
                'task_id': task.id, 'task_name': task.name,
                'description': task.description,
                'complexity': task.complexity.value,
                'priority': task.priority,
                'estimated_duration': task.estimated_duration
            },
            priority=MessagePriority.HIGH
        )

        self.active_tasks[task.id] = task
        logger.info(f"任务已分配: {task.name} -> {agent_name}")

    def complete_task(self, task_id: str, result: Dict[str, Any], success: bool = True):
        if task_id not in self.active_tasks:
            logger.error(f"任务不存在或未激活: {task_id}")
            return

        task = self.active_tasks[task_id]
        task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        task.completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task.result = result

        if task.assigned_agent:
            profile = self.agent_profiles[task.assigned_agent]
            profile.current_workload -= task.estimated_duration
            profile.current_workload = max(0, profile.current_workload)

            if success:
                profile.success_rate = (profile.success_rate * len(profile.task_history) + 1) / (len(profile.task_history) + 1)
            else:
                profile.success_rate = (profile.success_rate * len(profile.task_history)) / (len(profile.task_history) + 1)

        self.completed_tasks[task_id] = task
        del self.active_tasks[task_id]
        logger.info(f"任务已完成: {task.name} ({'成功' if success else '失败'})")

    def _check_dependencies(self, task: DynamicTask) -> bool:
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
        return True

    def get_agent_workload(self, agent_name: str) -> Dict[str, Any]:
        if agent_name not in self.agent_profiles:
            return {}
        profile = self.agent_profiles[agent_name]
        active_task_count = len([t for t in self.active_tasks.values() if t.assigned_agent == agent_name])
        return {
            'current_workload': profile.current_workload,
            'max_workload': profile.max_workload,
            'workload_percentage': (profile.current_workload / profile.max_workload) * 100,
            'active_tasks': active_task_count,
            'success_rate': profile.success_rate,
            'availability': profile.availability,
            'capabilities': [cap.value for cap in profile.capabilities]
        }

    def get_allocation_statistics(self) -> Dict[str, Any]:
        total_tasks = len(self.completed_tasks) + len(self.active_tasks) + len(self.task_queue)
        if total_tasks == 0:
            return {'total_tasks': 0}

        agent_stats = defaultdict(lambda: {'assigned': 0, 'completed': 0, 'failed': 0})
        for task in self.completed_tasks.values():
            if task.assigned_agent:
                if task.status == TaskStatus.COMPLETED:
                    agent_stats[task.assigned_agent]['completed'] += 1
                else:
                    agent_stats[task.assigned_agent]['failed'] += 1
        for task in self.active_tasks.values():
            if task.assigned_agent:
                agent_stats[task.assigned_agent]['assigned'] += 1

        return {
            'total_tasks': total_tasks,
            'pending_tasks': len(self.task_queue),
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'agent_statistics': dict(agent_stats),
            'average_completion_time': self._calculate_average_completion_time()
        }

    def _calculate_average_completion_time(self) -> float:
        if not self.completed_tasks:
            return 0.0
        total_time = 0
        completed_count = 0
        for task in self.completed_tasks.values():
            if task.started_at and task.completed_at:
                try:
                    start = datetime.strptime(task.started_at, '%Y-%m-%d %H:%M:%S')
                    end = datetime.strptime(task.completed_at, '%Y-%m-%d %H:%M:%S')
                    total_time += (end - start).total_seconds()
                    completed_count += 1
                except Exception:
                    continue
        return total_time / completed_count if completed_count > 0 else 0.0


_global_task_allocator = None


def get_task_allocator(communication_hub=None) -> DynamicTaskAllocator:
    """获取全局任务分配器"""
    global _global_task_allocator
    if _global_task_allocator is None:
        if communication_hub is None:
            from ..tools.communication_tools import global_communication_hub
            communication_hub = global_communication_hub
        _global_task_allocator = DynamicTaskAllocator(communication_hub)
    return _global_task_allocator


def create_analysis_task(company: str, ticker: str, analysis_type: str) -> str:
    """创建分析任务的便捷函数"""
    allocator = get_task_allocator()
    capabilities = {
        'fundamental': [AgentCapability.FUNDAMENTAL_ANALYSIS],
        'technical': [AgentCapability.TECHNICAL_ANALYSIS],
        'risk': [AgentCapability.RISK_ASSESSMENT],
        'quantitative': [AgentCapability.QUANTITATIVE_ANALYSIS],
        'industry': [AgentCapability.INDUSTRY_ANALYSIS]
    }
    return allocator.create_task(
        name=f"{analysis_type}_analysis_{company}",
        description=f"对{company}({ticker})进行{analysis_type}分析",
        required_capabilities=capabilities.get(analysis_type, [AgentCapability.FUNDAMENTAL_ANALYSIS]),
        complexity=TaskComplexity.HIGH,
        priority=8
    )