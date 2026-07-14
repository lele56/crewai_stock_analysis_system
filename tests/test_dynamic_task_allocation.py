# tests/test_dynamic_task_allocation.py
"""
动态任务分配测试用例
验证智能体注册、任务创建、分配和完成流程
"""
import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tasks.dynamic_task_allocation import (
    get_task_allocator, AgentCapability, TaskComplexity
)


class TestDynamicTaskAllocation(unittest.TestCase):
    """测试动态任务分配"""

    def setUp(self):
        """测试前准备"""
        self.allocator = get_task_allocator()

        self.allocator.register_agent(
            "fundamental_analyst",
            [AgentCapability.FUNDAMENTAL_ANALYSIS, AgentCapability.INDUSTRY_ANALYSIS],
            {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.9, AgentCapability.INDUSTRY_ANALYSIS: 0.8}
        )

        self.allocator.register_agent(
            "technical_analyst",
            [AgentCapability.TECHNICAL_ANALYSIS, AgentCapability.QUANTITATIVE_ANALYSIS],
            {AgentCapability.TECHNICAL_ANALYSIS: 0.9, AgentCapability.QUANTITATIVE_ANALYSIS: 0.7}
        )

    def test_agent_registration(self):
        """测试智能体注册"""
        self.assertEqual(len(self.allocator.agent_profiles), 2)
        self.assertIn("fundamental_analyst", self.allocator.agent_profiles)
        self.assertIn("technical_analyst", self.allocator.agent_profiles)

    def test_task_creation(self):
        """测试任务创建"""
        task_id = self.allocator.create_task(
            name="苹果公司基本面分析",
            description="对苹果公司进行深度基本面分析",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            complexity=TaskComplexity.HIGH,
            priority=9
        )

        self.assertIsNotNone(task_id)
        self.assertEqual(len(self.allocator.task_queue), 1)

    def test_task_allocation(self):
        """测试任务分配"""
        task_id = self.allocator.create_task(
            name="技术分析任务",
            description="技术分析测试",
            required_capabilities=[AgentCapability.TECHNICAL_ANALYSIS],
            complexity=TaskComplexity.MEDIUM,
            priority=5
        )

        allocated_tasks = self.allocator.allocate_tasks()
        self.assertEqual(len(allocated_tasks), 1)
        self.assertIn(task_id, allocated_tasks)

    def test_agent_fitness_calculation(self):
        """测试智能体适合度计算"""
        profile = self.allocator.agent_profiles["fundamental_analyst"]

        fitness = profile.calculate_fitness(
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            task_complexity=TaskComplexity.HIGH
        )

        self.assertGreater(fitness, 0.0)
        self.assertLessEqual(fitness, 1.0)

    def test_task_completion(self):
        """测试任务完成"""
        task_id = self.allocator.create_task(
            name="测试任务",
            description="测试任务完成流程",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            complexity=TaskComplexity.LOW
        )

        self.allocator.allocate_tasks()
        self.allocator.complete_task(
            task_id=task_id,
            result={"analysis": "测试结果"},
            success=True
        )

        self.assertIn(task_id, self.allocator.completed_tasks)
        self.assertNotIn(task_id, self.allocator.active_tasks)

    def test_workload_management(self):
        """测试工作负载管理"""
        profile = self.allocator.agent_profiles["fundamental_analyst"]
        initial_workload = profile.current_workload

        task_id = self.allocator.create_task(
            name="负载测试任务",
            description="测试工作负载管理",
            required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
            estimated_duration=60
        )

        self.allocator.allocate_tasks()
        self.allocator.complete_task(task_id, {"result": "完成"})

        final_workload = profile.current_workload
        self.assertEqual(final_workload, initial_workload)