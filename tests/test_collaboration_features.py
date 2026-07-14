# tests/test_collaboration_features.py
"""
协作功能集成测试用例
验证集体决策、协作工具和端到端集成流程
"""
import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tasks.dynamic_task_allocation import (
    get_decision_maker, AgentCapability, TaskComplexity,
    DecisionType
)
from src.tools.collaboration_tools import (
    get_task_orchestration_tool, get_collective_decision_tool,
    create_collaborative_analysis_task, create_investment_decision_committee
)


class TestCollectiveDecision(unittest.TestCase):
    """测试集体决策"""

    def setUp(self):
        """测试前准备"""
        self.decision_maker = get_decision_maker()

    def test_vote_creation(self):
        """测试投票创建"""
        vote_id = self.decision_maker.create_vote(
            topic="是否买入AAPL",
            options=["买入", "持有", "卖出"],
            voters=["委员会主席", "风险总监", "投资经理"],
            decision_type=DecisionType.MAJORITY
        )

        self.assertIsNotNone(vote_id)
        self.assertIn(vote_id, self.decision_maker.active_votes)

    def test_voting_process(self):
        """测试投票过程"""
        vote_id = self.decision_maker.create_vote(
            topic="测试投票",
            options=["选项A", "选项B"],
            voters=["投票者1", "投票者2", "投票者3"],
            decision_type=DecisionType.MAJORITY
        )

        self.decision_maker.cast_vote(vote_id, "投票者1", "选项A")
        self.decision_maker.cast_vote(vote_id, "投票者2", "选项A")
        self.decision_maker.cast_vote(vote_id, "投票者3", "选项B")

        self.assertNotIn(vote_id, self.decision_maker.active_votes)
        self.assertTrue(any(v.vote_id == vote_id for v in self.decision_maker.vote_history))

    def test_weighted_voting(self):
        """测试加权投票"""
        weights = {"专家1": 3.0, "专家2": 1.0, "专家3": 1.0}

        vote_id = self.decision_maker.create_vote(
            topic="加权投票测试",
            options=["方案A", "方案B"],
            voters=["专家1", "专家2", "专家3"],
            decision_type=DecisionType.WEIGHTED,
            weights=weights
        )

        self.decision_maker.cast_vote(vote_id, "专家1", "方案A")
        self.decision_maker.cast_vote(vote_id, "专家2", "方案A")
        self.decision_maker.cast_vote(vote_id, "专家3", "方案B")

        result_vote = None
        for vote in self.decision_maker.vote_history:
            if vote.vote_id == vote_id:
                result_vote = vote
                break

        self.assertIsNotNone(result_vote)
        self.assertEqual(result_vote.result, "方案A")

    def test_unanimous_decision(self):
        """测试一致同意决策"""
        vote_id = self.decision_maker.create_vote(
            topic="一致同意测试",
            options=["同意", "不同意"],
            voters=["成员1", "成员2", "成员3"],
            decision_type=DecisionType.UNANIMOUS
        )

        self.decision_maker.cast_vote(vote_id, "成员1", "同意")
        self.decision_maker.cast_vote(vote_id, "成员2", "同意")
        self.decision_maker.cast_vote(vote_id, "成员3", "同意")

        result_vote = None
        for vote in self.decision_maker.vote_history:
            if vote.vote_id == vote_id:
                result_vote = vote
                break

        self.assertIsNotNone(result_vote)
        self.assertEqual(result_vote.result, "同意")
        self.assertEqual(result_vote.confidence, 1.0)

    def test_vote_status(self):
        """测试投票状态查询"""
        vote_id = self.decision_maker.create_vote(
            topic="状态查询测试",
            options=["选项1", "选项2"],
            voters=["测试者"]
        )

        status = self.decision_maker.get_vote_status(vote_id)
        self.assertIn('status', status)
        self.assertIn('topic', status)
        self.assertEqual(status['topic'], "状态查询测试")


class TestCollaborationTools(unittest.TestCase):
    """测试协作工具"""

    def setUp(self):
        """测试前准备"""
        self.orchestration_tool = get_task_orchestration_tool("测试智能体")
        self.decision_tool = get_collective_decision_tool("测试智能体")

    def test_task_orchestration(self):
        """测试任务编排"""
        result = self.orchestration_tool._run(
            "create_task",
            name="编排测试任务",
            description="测试任务编排功能",
            capabilities=["fundamental_analysis"],
            complexity="high",
            priority=8
        )

        self.assertIn("任务已创建", result)

    def test_collaboration_analysis(self):
        """测试协作分析"""
        result = self.orchestration_tool._run("analyze_collaboration")

        self.assertIn("协作效率分析", result)
        self.assertIn("效率分数", result)

    def test_investment_vote_creation(self):
        """测试投资决策投票创建"""
        result = self.decision_tool._run(
            "create_investment_vote",
            company="苹果公司",
            ticker="AAPL",
            options=["买入", "持有", "卖出"]
        )

        self.assertIn("投资决策投票已创建", result)

    def test_decision_statistics(self):
        """测试决策统计"""
        result = self.decision_tool._run("get_decision_stats")

        self.assertIn("决策统计", result)
        self.assertIn("总投票数", result)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """测试前准备"""
        from src.tools.communication_tools import global_communication_hub
        global_communication_hub.message_queue.clear()
        global_communication_hub.communication_history.clear()
        global_communication_hub.delegation_records.clear()

    def test_end_to_end_collaboration(self):
        """测试端到端协作流程"""
        task_ids = create_collaborative_analysis_task(
            company="苹果公司",
            ticker="AAPL",
            analysis_types=["fundamental", "technical", "risk"]
        )

        self.assertEqual(len(task_ids), 3)

        committee_id = create_investment_decision_committee("苹果公司", "AAPL")
        self.assertIsNotNone(committee_id)

        from src.tools.communication_tools import generate_communication_summary
        comm_summary = generate_communication_summary()
        self.assertGreater(comm_summary['total_messages'], 0)

    def test_complex_workflow(self):
        """测试复杂工作流程"""
        allocator = get_task_allocator_for_test()
        decision_maker = get_decision_maker()

        allocator.register_agent(
            "multi_role_agent",
            [AgentCapability.FUNDAMENTAL_ANALYSIS, AgentCapability.TECHNICAL_ANALYSIS,
             AgentCapability.RISK_ASSESSMENT, AgentCapability.DECISION_MAKING],
            {cap: 0.8 for cap in [AgentCapability.FUNDAMENTAL_ANALYSIS, AgentCapability.TECHNICAL_ANALYSIS,
                                 AgentCapability.RISK_ASSESSMENT, AgentCapability.DECISION_MAKING]}
        )

        task_ids = []
        for i in range(5):
            task_id = allocator.create_task(
                name=f"复杂任务{i}",
                description=f"测试复杂工作流程中的任务{i}",
                required_capabilities=[AgentCapability.FUNDAMENTAL_ANALYSIS],
                complexity=TaskComplexity.MEDIUM,
                priority=5 + i
            )
            task_ids.append(task_id)

        allocated = allocator.allocate_tasks()
        self.assertEqual(len(allocated), 5)

        for task_id in task_ids[:3]:
            allocator.complete_task(task_id, {"status": "completed"}, success=True)

        vote_id = decision_maker.create_vote(
            topic="项目进展评估",
            options=["优秀", "良好", "一般", "需要改进"],
            voters=["项目经理", "技术负责人", "质量保证"],
            decision_type=DecisionType.WEIGHTED,
            weights={"项目经理": 2.0, "技术负责人": 2.0, "质量保证": 1.0}
        )

        decision_maker.cast_vote(vote_id, "项目经理", "良好")
        decision_maker.cast_vote(vote_id, "技术负责人", "优秀")
        decision_maker.cast_vote(vote_id, "质量保证", "良好")

        stats = allocator.get_allocation_statistics()
        self.assertGreaterEqual(stats['completed_tasks'], 3)

        decision_stats = decision_maker.get_decision_statistics()
        self.assertGreaterEqual(decision_stats['completed_votes'], 1)


def get_task_allocator_for_test():
    """获取测试用任务分配器"""
    from src.tasks.dynamic_task_allocation import get_task_allocator
    return get_task_allocator()


def run_collaboration_tests():
    """运行所有协作功能测试"""
    print("=" * 60)
    print("开始协作功能测试")
    print("=" * 60)

    test_suite = unittest.TestSuite()

    test_classes = [
        TestCollectiveDecision,
        TestCollaborationTools,
        TestIntegration
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun
    print(f"\n成功率: {success_rate:.2%}")

    return result.wasSuccessful()


if __name__ == "__main__":
    run_collaboration_tests()