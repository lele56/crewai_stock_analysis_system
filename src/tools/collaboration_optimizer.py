# src/tools/collaboration_optimizer.py
from typing import Dict, List, Any
from collections import Counter
import logging

logger = logging.getLogger(__name__)


def analyze_collaboration_patterns(task_history: List[Dict] = None,
                                   communication_log: List[Dict] = None) -> Dict[str, Any]:
    task_history = task_history or []
    communication_log = communication_log or []

    completed_tasks = [t for t in task_history if t.get("status") == "completed"]
    failed_tasks = [t for t in task_history if t.get("status") == "failed"]

    total_tasks = len(task_history)
    completion_rate = len(completed_tasks) / total_tasks if total_tasks > 0 else 0.0

    agent_workload = Counter()
    for t in task_history:
        agent = t.get("assigned_agent", "unknown")
        agent_workload[agent] += 1

    total_messages = len(communication_log)
    collaboration_efficiency = _calculate_collaboration_efficiency(
        completed_tasks, total_messages
    )

    bottlenecks = _identify_bottlenecks(agent_workload, failed_tasks)

    recommendations = _generate_recommendations(
        completion_rate, collaboration_efficiency, bottlenecks
    )

    return {
        "total_tasks": total_tasks,
        "completed_tasks": len(completed_tasks),
        "failed_tasks": len(failed_tasks),
        "completion_rate": round(completion_rate, 4),
        "agent_workload": dict(agent_workload),
        "total_messages": total_messages,
        "collaboration_efficiency": round(collaboration_efficiency, 4),
        "bottlenecks": bottlenecks,
        "recommendations": recommendations,
    }


def _calculate_collaboration_efficiency(completed_tasks: List[Dict],
                                         total_messages: int) -> float:
    if not completed_tasks:
        return 0.0
    multi_agent_tasks = sum(
        1 for t in completed_tasks
        if len(t.get("collaborators", [])) > 1
    )
    if total_messages == 0:
        return 0.5
    base_efficiency = multi_agent_tasks / len(completed_tasks)
    message_efficiency = min(1.0, len(completed_tasks) / max(total_messages, 1))
    return (base_efficiency + message_efficiency) / 2


def _identify_bottlenecks(agent_workload: Counter,
                          failed_tasks: List[Dict]) -> List[Dict]:
    bottlenecks = []
    if not agent_workload:
        return bottlenecks

    max_load = max(agent_workload.values())
    avg_load = sum(agent_workload.values()) / len(agent_workload)

    for agent, count in agent_workload.items():
        if count > avg_load * 1.5:
            bottlenecks.append({
                "agent": agent,
                "type": "overloaded",
                "task_count": count,
                "avg_load": avg_load,
                "severity": "high" if count > max_load * 0.8 else "medium",
            })

    failure_by_agent = Counter(t.get("assigned_agent", "unknown") for t in failed_tasks)
    for agent, count in failure_by_agent.items():
        if count >= 2:
            bottlenecks.append({
                "agent": agent,
                "type": "high_failure_rate",
                "failed_count": count,
                "severity": "high",
            })

    return bottlenecks


def _generate_recommendations(completion_rate: float,
                               collaboration_efficiency: float,
                               bottlenecks: List[Dict]) -> List[str]:
    recommendations = []

    if completion_rate < 0.7:
        recommendations.append("任务完成率偏低，建议检查任务分配策略和Agent能力匹配")
    if collaboration_efficiency < 0.3:
        recommendations.append("协作效率低，建议减少不必要的Agent间通信或优化任务依赖关系")

    for b in bottlenecks:
        if b["type"] == "overloaded":
            recommendations.append(
                f"Agent '{b['agent']}' 负载过高（{b['task_count']}个任务），建议增加Agent实例或分担任务"
            )
        elif b["type"] == "high_failure_rate":
            recommendations.append(
                f"Agent '{b['agent']}' 失败率过高（{b['failed_count']}次失败），建议检查其能力配置"
            )

    if not recommendations:
        recommendations.append("当前协作状态良好，无需特别优化")

    return recommendations


def optimize_workload(agent_workload: Dict[str, int]) -> List[Dict[str, Any]]:
    actions = []
    if not agent_workload:
        return actions

    avg = sum(agent_workload.values()) / len(agent_workload)
    for agent, load in agent_workload.items():
        if load > avg * 1.5:
            actions.append({
                "action": "reduce_load",
                "agent": agent,
                "current_load": load,
                "target_load": int(avg),
                "suggestion": f"将 {agent} 的负载从 {load} 降至 {int(avg)}",
            })
        elif load < avg * 0.5:
            actions.append({
                "action": "increase_load",
                "agent": agent,
                "current_load": load,
                "target_load": int(avg),
                "suggestion": f"将 {agent} 的负载从 {load} 提升至 {int(avg)}",
            })

    return actions