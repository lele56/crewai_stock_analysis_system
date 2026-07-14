# tests/test_communication_tools.py
"""
通信工具测试用例
验证智能体间的消息传递、任务委托和协作管理
"""
import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.communication_tools import (
    global_communication_hub, MessageType, MessagePriority, Message,
    get_communication_tool, generate_communication_summary
)


class TestCommunicationTools(unittest.TestCase):
    """测试通信工具"""

    def setUp(self):
        """测试前准备"""
        self.hub = global_communication_hub
        self.tool1 = get_communication_tool("市场研究员")
        self.tool2 = get_communication_tool("财务分析师")

    def test_send_message(self):
        """测试发送消息"""
        message_id = self.hub.send_message(
            sender="市场研究员",
            receiver="财务分析师",
            message_type=MessageType.INFORMATION_REQUEST,
            subject="请求财务数据",
            content={"required_data": ["营收", "利润"], "deadline": "2024-01-15"},
            priority=MessagePriority.HIGH
        )

        self.assertIsNotNone(message_id)
        self.assertEqual(len(self.hub.message_queue), 1)
        self.assertEqual(len(self.hub.communication_history), 1)

    def test_task_delegation(self):
        """测试任务委托"""
        delegation_id = self.hub.delegate_task(
            delegator="市场研究员",
            delegatee="财务分析师",
            original_task="市场趋势分析",
            delegated_task="财务指标验证",
            reason="需要专业知识验证财务假设",
            deadline="2024-01-20"
        )

        self.assertIsNotNone(delegation_id)
        self.assertEqual(len(self.hub.delegation_records), 1)
        self.assertEqual(len(self.hub.message_queue), 1)

    def test_get_messages_for_agent(self):
        """测试获取智能体消息"""
        self.hub.send_message(
            sender="市场研究员",
            receiver="财务分析师",
            message_type=MessageType.INFORMATION_REQUEST,
            subject="测试消息",
            content={"test": True}
        )

        messages = self.hub.get_messages_for_agent("财务分析师")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].subject, "测试消息")

    def test_respond_to_message(self):
        """测试响应消息"""
        message_id = self.hub.send_message(
            sender="市场研究员",
            receiver="财务分析师",
            message_type=MessageType.INFORMATION_REQUEST,
            subject="请求信息",
            content={"query": "测试"},
            requires_response=True
        )

        response_id = self.hub.respond_to_message(
            message_id=message_id,
            response_content={"answer": "测试答案"},
            response_type="accept"
        )

        self.assertIsNotNone(response_id)
        self.assertEqual(len(self.hub.message_queue), 2)

    def test_collaboration_management(self):
        """测试协作管理"""
        collaboration_id = self.hub.start_collaboration(
            initiator="市场研究员",
            participants=["财务分析师", "技术分析师"],
            collaboration_topic="跨部门分析项目"
        )

        self.assertIsNotNone(collaboration_id)
        self.assertIn(collaboration_id, self.hub.active_collaborations)
        self.assertEqual(len(self.hub.active_collaborations[collaboration_id]), 3)

    def test_communication_report(self):
        """测试通信报告生成"""
        self.hub.send_message(
            sender="市场研究员",
            receiver="财务分析师",
            message_type=MessageType.INFORMATION_REQUEST,
            subject="报告测试"
        )

        self.hub.delegate_task(
            delegator="市场研究员",
            delegatee="技术分析师",
            original_task="测试任务",
            delegated_task="子任务"
        )

        report = generate_communication_summary()
        self.assertIn('total_messages', report)
        self.assertIn('total_delegations', report)
        self.assertIn('active_collaborations', report)
        self.assertGreater(report['total_messages'], 0)