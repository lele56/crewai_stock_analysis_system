# src/tools/collective_decision_tool.py
"""集体决策工具 - 为智能体提供集体决策功能"""
from typing import List
import logging

from ..tasks.dynamic_task_allocation import get_decision_maker, DecisionType

logger = logging.getLogger(__name__)


class CollectiveDecisionTool:
    """集体决策工具"""

    name: str = "Collective Decision Tool"
    description: str = "提供智能体集体决策、投票和共识形成功能"

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.decision_maker = get_decision_maker()

    def _run(self, action: str, **kwargs) -> str:
        """执行集体决策操作"""
        try:
            if action == "create_investment_vote":
                return self._create_investment_vote(**kwargs)
            elif action == "create_risk_assessment_vote":
                return self._create_risk_assessment_vote(**kwargs)
            elif action == "create_strategy_vote":
                return self._create_strategy_vote(**kwargs)
            elif action == "get_vote_status":
                return self._get_vote_status(**kwargs)
            elif action == "get_decision_stats":
                return self._get_decision_stats()
            return f"未知操作: {action}"
        except Exception as e:
            logger.error(f"集体决策操作失败: {str(e)}")
            return f"错误: {str(e)}"

    def _create_investment_vote(self, company: str, ticker: str, options: List[str] = None) -> str:
        if options is None:
            options = ["强烈买入", "买入", "持有", "卖出", "强烈卖出"]
        voters = [
            f"{self.agent_name}_committee", f"{self.agent_name}_risk_director",
            f"{self.agent_name}_portfolio_manager", f"{self.agent_name}_analyst"
        ]
        weights = {
            f"{self.agent_name}_committee": 3.0, f"{self.agent_name}_risk_director": 2.5,
            f"{self.agent_name}_portfolio_manager": 2.0, f"{self.agent_name}_analyst": 1.0
        }
        vote_id = self.decision_maker.create_vote(
            topic=f"{company}({ticker})投资决策", options=options,
            voters=voters, decision_type=DecisionType.WEIGHTED, weights=weights
        )
        return f"投资决策投票已创建 (ID: {vote_id})"

    def _create_risk_assessment_vote(self, risk_type: str, options: List[str] = None) -> str:
        if options is None:
            options = ["低风险", "中等风险", "高风险", "极高风险"]
        voters = [
            f"{self.agent_name}_risk_expert", f"{self.agent_name}_analyst",
            f"{self.agent_name}_manager"
        ]
        vote_id = self.decision_maker.create_vote(
            topic=f"{risk_type}风险评估", options=options,
            voters=voters, decision_type=DecisionType.MAJORITY
        )
        return f"风险评估投票已创建 (ID: {vote_id})"

    def _create_strategy_vote(self, strategy_name: str, options: List[str]) -> str:
        voters = [
            f"{self.agent_name}_strategist", f"{self.agent_name}_analyst",
            f"{self.agent_name}_manager"
        ]
        vote_id = self.decision_maker.create_vote(
            topic=f"{strategy_name}策略选择", options=options,
            voters=voters, decision_type=DecisionType.CONSENSUS
        )
        return f"策略投票已创建 (ID: {vote_id})"

    def _get_vote_status(self, vote_id: str) -> str:
        status = self.decision_maker.get_vote_status(vote_id)
        if 'error' in status:
            return status['error']
        result = f"投票状态 (ID: {vote_id}):\n- 状态: {status['status']}\n"
        result += f"- 主题: {status['topic']}\n- 选项: {', '.join(status['options'])}\n"
        if 'votes_cast' in status:
            result += f"- 已投票: {status['votes_cast']}/{status['total_voters']}\n"
        if 'result' in status:
            result += f"- 结果: {status['result']}\n- 置信度: {status.get('confidence', 0):.2f}\n"
        return result

    def _get_decision_stats(self) -> str:
        stats = self.decision_maker.get_decision_statistics()
        result = f"决策统计:\n- 总投票数: {stats['total_votes']}\n"
        result += f"- 活跃投票: {stats['active_votes']}\n- 完成投票: {stats['completed_votes']}\n"
        result += f"- 平均置信度: {stats['average_confidence']:.2f}\n"
        if 'decision_type_distribution' in stats:
            result += "\n决策类型分布:\n"
            for decision_type, count in stats['decision_type_distribution'].items():
                result += f"- {decision_type}: {count}\n"
        return result


def get_collective_decision_tool(agent_name: str) -> CollectiveDecisionTool:
    """获取集体决策工具"""
    return CollectiveDecisionTool(agent_name)