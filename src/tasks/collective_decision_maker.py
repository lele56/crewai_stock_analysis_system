# src/tasks/collective_decision_maker.py
from collections import Counter
from dataclasses import dataclass, field
import logging
from typing import Any
from uuid import uuid4

from .task_dataclasses import DecisionType, VotingRecord

logger = logging.getLogger(__name__)


@dataclass
class CollectiveDecisionMaker:
    """集体决策器"""

    decision_type: DecisionType = DecisionType.WEIGHTED
    minimum_confidence: float = 0.3
    history: list[dict] = field(default_factory=list)

    def cast_vote(self, voter: str, vote: str, confidence: float, reasoning: str = "") -> VotingRecord:
        """投出一票"""
        return VotingRecord(
            voter=voter,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
        )

    def decide(self, votes: list[VotingRecord]) -> dict[str, Any]:
        """根据投票结果做出决策"""
        if not votes:
            return {
                "vote_id": str(uuid4())[:8],
                "result": "持有",
                "confidence": 0.0,
                "decision_type": self.decision_type.value,
                "voter_count": 0,
                "voting_details": [],
            }

        vote_counts = Counter(v.vote for v in votes)
        weighted = {}
        for v in votes:
            weighted[v.vote] = weighted.get(v.vote, 0) + v.confidence

        if self.decision_type == DecisionType.WEIGHTED:
            result = max(weighted, key=weighted.get)
            total_weight = sum(v.confidence for v in votes)
            confidence = weighted[result] / total_weight if total_weight > 0 else 0.0
        elif self.decision_type == DecisionType.MAJORITY:
            result = vote_counts.most_common(1)[0][0]
            confidence = vote_counts[result] / len(votes)
        elif self.decision_type == DecisionType.UNANIMOUS:
            if len(vote_counts) == 1:
                result = list(vote_counts.keys())[0]
                confidence = 1.0
            else:
                result = max(weighted, key=weighted.get)
                confidence = 0.3
        else:
            result = max(weighted, key=weighted.get)
            total_weight = sum(v.confidence for v in votes)
            confidence = weighted[result] / total_weight if total_weight > 0 else 0.0

        decision = {
            "vote_id": str(uuid4())[:8],
            "result": result,
            "confidence": round(min(confidence, 1.0), 4),
            "decision_type": self.decision_type.value,
            "voter_count": len(votes),
            "voting_details": [{"voter": v.voter, "vote": v.vote, "confidence": v.confidence} for v in votes],
        }

        self.history.append(decision)
        return decision

    def get_history(self) -> list[dict]:
        """获取决策历史"""
        return self.history

    def clear_history(self) -> None:
        """清空决策历史"""
        self.history.clear()


_global_decision_maker: CollectiveDecisionMaker | None = None


def get_decision_maker() -> CollectiveDecisionMaker:
    """获取全局决策器实例"""
    global _global_decision_maker
    if _global_decision_maker is None:
        _global_decision_maker = CollectiveDecisionMaker()
    return _global_decision_maker


def create_investment_decision_vote(voter: str, score: float, confidence: float, reasoning: str = "") -> VotingRecord:
    """根据评分创建投资决策投票"""
    if score >= 80:
        vote = "强烈买入"
    elif score >= 60:
        vote = "买入"
    elif score >= 40:
        vote = "持有"
    elif score >= 20:
        vote = "卖出"
    else:
        vote = "强烈卖出"
    return VotingRecord(voter=voter, vote=vote, confidence=confidence, reasoning=reasoning)


def create_vote(voter: str, vote: str, confidence: float, reasoning: str = "") -> VotingRecord:
    """兼容别名 - 供旧测试使用"""
    return VotingRecord(voter=voter, vote=vote, confidence=confidence, reasoning=reasoning)


def get_decision_statistics(self: CollectiveDecisionMaker) -> dict[str, Any]:
    """统计决策历史 - 供旧测试使用"""
    if not self.history:
        return {"total_decisions": 0, "result_distribution": {}, "average_confidence": 0.0, "recent_decisions": []}

    from collections import Counter

    results = [d["result"] for d in self.history]
    counts = Counter(results)
    avg_conf = sum(d["confidence"] for d in self.history) / len(self.history)

    return {
        "total_decisions": len(self.history),
        "result_distribution": dict(counts),
        "average_confidence": round(avg_conf, 4),
        "recent_decisions": self.history[-5:],
    }


CollectiveDecisionMaker.get_decision_statistics = get_decision_statistics
