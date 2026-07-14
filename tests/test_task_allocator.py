# tests/test_task_allocator.py
"""
动态任务分配器测试
"""
import pytest
from unittest.mock import Mock
from src.tasks.dynamic_task_allocation import (
    DynamicTaskAllocator, get_task_allocator, create_analysis_task,
)
from src.tasks.task_dataclasses import (
    AgentCapability, TaskComplexity, TaskStatus,
)


class TestDynamicTaskAllocator:
    """测试动态任务分配器"""

    @pytest.fixture
    def mock_hub(self):
        hub = Mock()
        hub.send_message = Mock()
        return hub

    @pytest.fixture
    def allocator(self, mock_hub):
        return DynamicTaskAllocator(mock_hub)

    def test_register_agent(self, allocator):
        profile = allocator.register_agent(
            "基本面分析师",
            [AgentCapability.FUNDAMENTAL_ANALYSIS, AgentCapability.DATA_COLLECTION],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9, AgentCapability.DATA_COLLECTION: 0.7},
        )
        assert profile.name == "基本面分析师"
        assert "基本面分析师" in allocator.agent_profiles
        assert len(profile.capabilities) == 2

    def test_create_task(self, allocator):
        task_id = allocator.create_task(
            name="财务分析",
            description="分析财务数据",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            complexity=TaskComplexity.HIGH,
            priority=5,
        )
        assert task_id is not None
        assert len(allocator.task_queue) == 1

    def test_allocate_tasks(self, allocator):
        allocator.register_agent(
            "基本面分析师",
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
        )
        allocator.register_agent(
            "技术分析师",
            [AgentCapability.TECHNICAL_ANALYSIS],
            {AgentCapability.TECHNICAL_ANALYSIS: 0.85},
        )

        allocator.create_task(
            name="财务分析",
            description="分析财务数据",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
        )
        allocator.create_task(
            name="技术分析",
            description="分析技术指标",
            required_capabilities=[AgentCapability.TECHNICAL_ANALYSIS],
        )

        allocated = allocator.allocate_tasks()
        assert len(allocated) == 2
        assert len(allocator.active_tasks) == 2

    def test_allocate_tasks_no_agent(self, allocator):
        allocator.create_task(
            name="无人执行的任务",
            description="没有合适的Agent",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
        )
        allocated = allocator.allocate_tasks()
        assert len(allocated) == 0

    def test_allocate_tasks_unavailable_agent(self, allocator):
        allocator.register_agent(
            "忙碌分析师",
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
        )
        allocator.agent_profiles["忙碌分析师"].availability = False

        allocator.create_task(
            name="财务分析",
            description="需要基本面分析",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
        )
        allocated = allocator.allocate_tasks()
        assert len(allocated) == 0

    def test_complete_task_success(self, allocator):
        allocator.register_agent(
            "分析师",
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
        )
        task_id = allocator.create_task(
            name="财务分析",
            description="分析财务数据",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
        )
        allocator.allocate_tasks()

        allocator.complete_task(task_id, {"result": "分析完成"}, success=True)

        assert task_id in allocator.completed_tasks
        assert allocator.completed_tasks[task_id].status == TaskStatus.COMPLETED
        assert allocator.completed_tasks[task_id].result == {"result": "分析完成"}

    def test_complete_task_failure(self, allocator):
        allocator.register_agent(
            "分析师",
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
        )
        task_id = allocator.create_task(
            name="失败任务",
            description="会失败的任务",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
        )
        allocator.allocate_tasks()

        allocator.complete_task(task_id, {"error": "失败"}, success=False)

        assert allocator.completed_tasks[task_id].status == TaskStatus.FAILED

    def test_complete_task_releases_workload(self, allocator):
        allocator.register_agent(
            "分析师",
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
        )
        task_id = allocator.create_task(
            name="财务分析",
            description="分析财务数据",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            estimated_duration=30,
        )
        allocator.allocate_tasks()

        workload_before = allocator.agent_profiles["分析师"].current_workload
        allocator.complete_task(task_id, {"result": "完成"}, success=True)
        workload_after = allocator.agent_profiles["分析师"].current_workload

        assert workload_after < workload_before

    def test_dependency_ordering(self, allocator):
        allocator.register_agent(
            "分析师",
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
        )

        task1_id = allocator.create_task(
            name="前置任务",
            description="必须先完成",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
        )
        task2_id = allocator.create_task(
            name="依赖任务",
            description="依赖前置任务",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            dependencies=[task1_id],
        )

        allocated = allocator.allocate_tasks()
        assert len(allocated) == 1
        assert task1_id in allocator.active_tasks

        allocator.complete_task(task1_id, {"result": "完成"}, success=True)
        allocated2 = allocator.allocate_tasks()
        assert len(allocated2) == 1
        assert task2_id in allocator.active_tasks

    def test_get_agent_workload(self, allocator):
        allocator.register_agent(
            "分析师",
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
        )
        workload = allocator.get_agent_workload("分析师")
        assert workload['current_workload'] == 0.0
        assert workload['workload_percentage'] == 0.0
        assert workload['availability'] is True
        assert "fundamental_analysis" in workload['capabilities']

    def test_get_agent_workload_not_found(self, allocator):
        workload = allocator.get_agent_workload("不存在的Agent")
        assert workload == {}

    def test_get_allocation_statistics_empty(self, allocator):
        stats = allocator.get_allocation_statistics()
        assert stats['total_tasks'] == 0

    def test_get_allocation_statistics(self, allocator):
        allocator.register_agent(
            "分析师",
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
        )
        task_id = allocator.create_task(
            name="测试任务",
            description="测试",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
        )
        allocator.allocate_tasks()
        allocator.complete_task(task_id, {"result": "完成"}, success=True)

        stats = allocator.get_allocation_statistics()
        assert stats['total_tasks'] == 1
        assert stats['completed_tasks'] == 1

    def test_load_balancing(self, allocator):
        allocator.register_agent(
            "AgentA",
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9},
            max_workload=100.0,
        )
        allocator.register_agent(
            "AgentB",
            [AgentCapability.FUNDAMENTAL_ANALYSIS],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.85},
            max_workload=100.0,
        )

        allocator.agent_profiles["AgentA"].current_workload = 80.0
        allocator.agent_profiles["AgentB"].current_workload = 20.0

        task_id = allocator.create_task(
            name="负载均衡测试",
            description="应分配给负载低的Agent",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
        )
        allocator.allocate_tasks()

        assert allocator.active_tasks[task_id].assigned_agent == "AgentB"


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_create_analysis_task(self):
        task_id = create_analysis_task("测试公司", "TEST", "fundamental")
        assert task_id is not None
        assert isinstance(task_id, str)