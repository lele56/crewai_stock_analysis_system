# tests/test_data_models.py
import pytest
from src.tasks.task_dataclasses import (
    AgentCapability, TaskComplexity, TaskStatus,
    DecisionType, VotingRecord, DynamicTask, AgentProfile,
)


class TestAgentCapability:
    def test_all_capabilities_defined(self):
        assert len(AgentCapability) == 9
        assert AgentCapability.FUNDAMENTAL_ANALYSIS.value == "fundamental_analysis"

    def test_capability_from_value(self):
        cap = AgentCapability("technical_analysis")
        assert cap == AgentCapability.TECHNICAL_ANALYSIS


class TestTaskComplexity:
    def test_complexity_levels(self):
        assert TaskComplexity.LOW.value == "low"
        assert TaskComplexity.MEDIUM.value == "medium"
        assert TaskComplexity.HIGH.value == "high"
        assert TaskComplexity.CRITICAL.value == "critical"


class TestTaskStatus:
    def test_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.ASSIGNED.value == "assigned"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"


class TestDecisionType:
    def test_decision_types(self):
        assert DecisionType.UNANIMOUS.value == "unanimous"
        assert DecisionType.WEIGHTED.value == "weighted"


class TestVotingRecord:
    def test_create_voting_record(self):
        record = VotingRecord(
            voter="分析师A",
            vote="买入",
            confidence=0.85,
            reasoning="基本面良好",
        )
        assert record.voter == "分析师A"
        assert record.vote == "买入"
        assert record.confidence == 0.85
        assert record.reasoning == "基本面良好"
        assert record.timestamp is not None


class TestDynamicTask:
    def test_create_task(self):
        task = DynamicTask(
            name="测试任务",
            description="测试描述",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
        )
        assert task.name == "测试任务"
        assert task.id is not None
        assert len(task.id) == 8
        assert task.status == TaskStatus.PENDING
        assert task.assigned_agent is None

    def test_task_ordering(self):
        t1 = DynamicTask(
            name="高优先级",
            description="",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            priority=10,
        )
        t2 = DynamicTask(
            name="低优先级",
            description="",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            priority=1,
        )
        assert t1 > t2


class TestAgentProfile:
    def test_create_profile(self):
        profile = AgentProfile(
            name="测试Agent",
            capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            capability_scores={AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
        )
        assert profile.name == "测试Agent"
        assert profile.availability is True
        assert profile.current_workload == 0.0

    def test_calculate_fitness(self):
        profile = AgentProfile(
            name="测试Agent",
            capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            capability_scores={AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
        )
        fitness = profile.calculate_fitness(
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            TaskComplexity.MEDIUM,
        )
        assert 0 < fitness <= 1.0

    def test_calculate_fitness_no_capability(self):
        profile = AgentProfile(
            name="测试Agent",
            capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            capability_scores={},
        )
        fitness = profile.calculate_fitness(
            [AgentCapability.TECHNICAL_ANALYSIS],
            TaskComplexity.MEDIUM,
        )
        assert fitness == 0.0

    def test_calculate_fitness_overloaded(self):
        profile = AgentProfile(
            name="测试Agent",
            capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            capability_scores={AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
            current_workload=100.0,
            max_workload=100.0,
        )
        fitness = profile.calculate_fitness(
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            TaskComplexity.MEDIUM,
        )
        assert fitness == 0.0