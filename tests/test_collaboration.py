# tests/test_collaboration.py
import pytest
from src.tools.collaboration_optimizer import (
    analyze_collaboration_patterns,
    optimize_workload,
)


class TestCollaborationOptimizer:

    def test_analyze_empty(self):
        result = analyze_collaboration_patterns([], [])
        assert result["total_tasks"] == 0
        assert result["completion_rate"] == 0.0

    def test_analyze_normal(self):
        task_history = [
            {"status": "completed", "assigned_agent": "AgentA", "collaborators": ["AgentB"]},
            {"status": "completed", "assigned_agent": "AgentB", "collaborators": []},
            {"status": "failed", "assigned_agent": "AgentA"},
        ]
        communication_log = [
            {"sender": "AgentA", "receiver": "AgentB"},
            {"sender": "AgentB", "receiver": "AgentA"},
        ]
        result = analyze_collaboration_patterns(task_history, communication_log)
        assert result["total_tasks"] == 3
        assert result["completed_tasks"] == 2
        assert result["failed_tasks"] == 1
        assert result["total_messages"] == 2
        assert "recommendations" in result
        assert "bottlenecks" in result

    def test_analyze_no_failures(self):
        task_history = [
            {"status": "completed", "assigned_agent": "AgentA"},
            {"status": "completed", "assigned_agent": "AgentB"},
        ]
        result = analyze_collaboration_patterns(task_history, [])
        assert result["completion_rate"] == 1.0
        assert result["failed_tasks"] == 0

    def test_optimize_workload_balanced(self):
        workload = {"AgentA": 5, "AgentB": 5, "AgentC": 5}
        actions = optimize_workload(workload)
        assert len(actions) == 0

    def test_optimize_workload_unbalanced(self):
        workload = {"AgentA": 10, "AgentB": 2, "AgentC": 3}
        actions = optimize_workload(workload)
        assert len(actions) > 0
        action_types = {a["action"] for a in actions}
        assert "reduce_load" in action_types or "increase_load" in action_types

    def test_optimize_workload_empty(self):
        actions = optimize_workload({})
        assert len(actions) == 0