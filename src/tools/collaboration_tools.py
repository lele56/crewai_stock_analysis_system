# src/tools/collaboration_tools.py
"""智能体协作工具集 - 协作优化器"""
from typing import Dict, Any, List, Optional, Tuple
import logging
import json
from datetime import datetime

from .communication_tools import global_communication_hub, Message, MessageType, MessagePriority
from ..tasks.dynamic_task_allocation import (
    get_task_allocator, get_decision_maker, AgentCapability, TaskComplexity,
    DecisionType, DynamicTask, AgentProfile
)

logger = logging.getLogger(__name__)


class CollaborationOptimizer:
    """协作优化器 - 优化智能体间的协作效率和任务分配"""

    def __init__(self):
        self.task_allocator = get_task_allocator()
        self.decision_maker = get_decision_maker()
        self.collaboration_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Dict[str, float]] = {}

    def analyze_collaboration_patterns(self) -> Dict[str, Any]:
        """分析协作模式和效率"""
        comm_report = global_communication_hub.generate_communication_report()
        task_stats = self.task_allocator.get_allocation_statistics()
        decision_stats = self.decision_maker.get_decision_statistics()
        collaboration_efficiency = self._calculate_collaboration_efficiency(comm_report, task_stats)
        bottlenecks = self._identify_collaboration_bottlenecks(comm_report, task_stats)
        recommendations = self._generate_optimization_recommendations(
            comm_report, task_stats, decision_stats, bottlenecks
        )
        return {
            'collaboration_efficiency': collaboration_efficiency,
            'bottlenecks': bottlenecks, 'recommendations': recommendations,
            'communication_metrics': comm_report, 'task_metrics': task_stats,
            'decision_metrics': decision_stats,
            'analysis_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _calculate_collaboration_efficiency(self, comm_report: Dict[str, Any],
                                         task_stats: Dict[str, Any]) -> float:
        efficiency_score = 0.0
        comm_efficiency = comm_report.get('communication_efficiency', 0.5)
        efficiency_score += comm_efficiency * 0.3
        if task_stats.get('total_tasks', 0) > 0:
            completion_rate = task_stats.get('completed_tasks', 0) / task_stats['total_tasks']
            efficiency_score += completion_rate * 0.4
        decision_stats = self.decision_maker.get_decision_statistics()
        if decision_stats.get('total_votes', 0) > 0:
            avg_confidence = decision_stats.get('average_confidence', 0.5)
            efficiency_score += avg_confidence * 0.3
        return min(1.0, max(0.0, efficiency_score))

    def _identify_collaboration_bottlenecks(self, comm_report: Dict[str, Any],
                                          task_stats: Dict[str, Any]) -> List[str]:
        bottlenecks = []
        if comm_report.get('communication_efficiency', 1.0) < 0.5:
            bottlenecks.append("通信效率较低，响应时间过长")
        if task_stats.get('pending_tasks', 0) > 5:
            bottlenecks.append("待处理任务积压，任务分配不及时")
        agent_stats = task_stats.get('agent_statistics', {})
        if agent_stats:
            workloads = [stats.get('assigned', 0) for stats in agent_stats.values()]
            if max(workloads) - min(workloads) > 3:
                bottlenecks.append("智能体负载不均衡")
        return bottlenecks

    def _generate_optimization_recommendations(self, comm_report: Dict[str, Any],
                                             task_stats: Dict[str, Any],
                                             decision_stats: Dict[str, Any],
                                             bottlenecks: List[str]) -> List[str]:
        recommendations = []
        for bottleneck in bottlenecks:
            if "通信效率" in bottleneck:
                recommendations.append("优化消息路由机制，减少通信延迟")
                recommendations.append("增加智能体并行处理能力")
            elif "任务积压" in bottleneck:
                recommendations.append("增加任务分配频率")
                recommendations.append("优化任务优先级算法")
            elif "负载不均衡" in bottleneck:
                recommendations.append("启用动态负载均衡")
                recommendations.append("调整智能体能力权重")
        if task_stats.get('average_completion_time', 0) > 3600:
            recommendations.append("任务完成时间过长，考虑任务分解")
        if decision_stats.get('average_confidence', 0) < 0.7:
            recommendations.append("决策置信度较低，改进决策机制")
        return recommendations

    def optimize_task_allocation(self) -> Dict[str, Any]:
        """优化任务分配策略"""
        optimization_actions = []
        task_stats = self.task_allocator.get_allocation_statistics()
        agent_stats = task_stats.get('agent_statistics', {})
        overloaded_agents = []
        underutilized_agents = []
        for agent_name, stats in agent_stats.items():
            workload = self.task_allocator.get_agent_workload(agent_name)
            workload_percentage = workload.get('workload_percentage', 0)
            if workload_percentage > 80:
                overloaded_agents.append(agent_name)
            elif workload_percentage < 30:
                underutilized_agents.append(agent_name)
        if overloaded_agents and underutilized_agents:
            optimization_actions.append(
                f"负载均衡: 从{overloaded_agents}重新分配任务到{underutilized_agents}"
            )
        if len(overloaded_agents) > len(underutilized_agents):
            self.task_allocator.load_balancing_enabled = True
            optimization_actions.append("启用负载均衡模式")
        return {
            'optimization_actions': optimization_actions,
            'overloaded_agents': overloaded_agents,
            'underutilized_agents': underutilized_agents,
            'optimization_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# 便捷函数
def create_collaborative_analysis_task(company: str, ticker: str,
                                     analysis_types: List[str]) -> List[str]:
    """创建协作分析任务"""
    allocator = get_task_allocator()
    task_ids = []
    capability_mapping = {
        'fundamental': [AgentCapability.FUNDAMENTAL_ANALYSIS],
        'technical': [AgentCapability.TECHNICAL_ANALYSIS],
        'risk': [AgentCapability.RISK_ASSESSMENT],
        'quantitative': [AgentCapability.QUANTITATIVE_ANALYSIS],
        'industry': [AgentCapability.INDUSTRY_ANALYSIS]
    }
    for analysis_type in analysis_types:
        if analysis_type in capability_mapping:
            task_id = allocator.create_task(
                name=f"{analysis_type}_analysis_{company}",
                description=f"对{company}({ticker})进行{analysis_type}分析",
                required_capabilities=capability_mapping[analysis_type],
                complexity=TaskComplexity.HIGH, priority=8
            )
            task_ids.append(task_id)
    allocator.allocate_tasks()
    return task_ids


def create_investment_decision_committee(company: str, ticker: str) -> str:
    """创建投资决策委员会"""
    decision_maker = get_decision_maker()
    options = ["强烈买入", "买入", "持有", "卖出", "强烈卖出"]
    voters = [
        "investment_committee_chairman", "risk_management_director",
        "portfolio_manager", "chief_analyst", "compliance_officer"
    ]
    weights = {
        "investment_committee_chairman": 3.0, "risk_management_director": 2.5,
        "portfolio_manager": 2.0, "chief_analyst": 1.5, "compliance_officer": 1.0
    }
    return decision_maker.create_vote(
        topic=f"{company}({ticker})投资决策委员会投票",
        options=options, voters=voters, decision_type=DecisionType.WEIGHTED, weights=weights
    )


# 使用示例
if __name__ == "__main__":
    from src.tools.task_orchestration_tool import get_task_orchestration_tool
    from src.tools.collective_decision_tool import get_collective_decision_tool

    orchestration_tool = get_task_orchestration_tool("test_agent")
    decision_tool = get_collective_decision_tool("test_agent")

    task_result = orchestration_tool._run(
        "create_task", name="测试任务", description="这是一个测试任务",
        capabilities=["fundamental_analysis"], complexity="high", priority=9
    )
    logger.info(task_result)

    alloc_result = orchestration_tool._run("allocate_tasks")
    logger.info(alloc_result)

    vote_result = decision_tool._run(
        "create_investment_vote", company="苹果公司", ticker="AAPL",
        options=["买入", "持有", "卖出"]
    )
    logger.info(vote_result)

    analysis_result = orchestration_tool._run("analyze_collaboration")
    logger.info(analysis_result)